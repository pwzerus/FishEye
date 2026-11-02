"""Getting back into an account when the password is forgotten.

Someone asks with their address; a link good for an hour goes to that inbox;
the link's page sets a new password, which ends every other session on the
account. Whether the address has an account is never said, by the answer or by
how long it takes: the mail goes out after the reply (api/auth.py).

Like sessions and confirmation links, only the token's SHA-256 is stored. A
link works once and a new one replaces the old.

An admin can make a link too (api/admin_community.py), to hand over by some
other means, which is the way back in while the server can't send mail. That
one lasts a day: it may wait in a chat until it's read.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, new_token, token_digest
from app.db.types import utcnow
from app.models.community import PasswordResetToken, User
from app.services import audit, mail
from app.services.auth import AuthError, check_new_password, normalize_email, revoke_all_sessions

logger = logging.getLogger(__name__)

EMAILED_HOURS = 1
HANDED_OVER_HOURS = 24
BAD_LINK = "This reset link has expired or was already used. Ask for a new one."

_SUBJECT = {
    "en": "Reset your FishEye password",
    "zh": "重置你的 FishEye 密码",
    "es": "Restablece tu contraseña de FishEye",
    "ko": "FishEye 비밀번호 재설정",
    "ja": "FishEyeのパスワードの再設定",
}
_BODY = {
    "en": "Hi {name},\n\nSomeone asked to reset the password for this FishEye account. To choose a new one, "
    "open this link:\n\n{link}\n\nIt works once, for {hours} hour(s). If this wasn't you, ignore this email: "
    "your password hasn't changed.\n\n— FishEye\n",
    "zh": "{name}，你好：\n\n有人申请重置这个 FishEye 账号的密码。要设置新密码，请打开这个链接：\n\n{link}\n\n"
    "链接只能用一次，{hours} 小时内有效。如果不是你本人操作，请忽略这封邮件，你的密码没有变。\n\n— FishEye\n",
    "es": "Hola, {name}:\n\nAlguien pidió restablecer la contraseña de esta cuenta de FishEye. Para elegir una "
    "nueva, abre este enlace:\n\n{link}\n\nFunciona una sola vez, durante {hours} hora(s). Si no fuiste tú, ignora "
    "este correo: tu contraseña no ha cambiado.\n\n— FishEye\n",
    "ko": "{name}님, 안녕하세요.\n\n이 FishEye 계정의 비밀번호 재설정 요청이 있었어요. 새 비밀번호를 정하려면 이 링크를 "
    "여세요.\n\n{link}\n\n링크는 {hours}시간 동안 한 번만 쓸 수 있어요. 직접 요청하지 않았다면 이 메일을 무시하세요. "
    "비밀번호는 바뀌지 않았어요.\n\n— FishEye\n",
    "ja": "{name} さん\n\nこのFishEyeアカウントのパスワード再設定が依頼されました。新しいパスワードを決めるには、"
    "このリンクを開いてください。\n\n{link}\n\nリンクは{hours}時間有効で、一度だけ使えます。心当たりがない場合は、"
    "このメールを無視してください。パスワードは変更されていません。\n\n— FishEye\n",
}


@dataclass(frozen=True)
class ResetMail:
    to: str
    subject: str
    text: str


def can_email() -> bool:
    """Does a link actually reach anyone? On the console backend it only
    lands in the server's log."""
    s = get_settings()
    return s.mail_backend == "smtp" and bool(s.smtp_host)


def issue(db: Session, user: User, hours: int) -> tuple[str, datetime]:
    """A fresh link for this account (the link, and when it stops working).
    Earlier ones stop working."""
    token = new_token()
    now = utcnow()
    expires = now + timedelta(hours=hours)
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    db.add(PasswordResetToken(user_id=user.id, token_hash=token_digest(token), created_at=now, expires_at=expires))
    db.flush()
    return f"{get_settings().frontend_origin.rstrip('/')}/reset-password?token={token}", expires


def mail_for(user: User, link: str, hours: int, lang: str | None = None) -> ResetMail:
    lang = lang if lang in _SUBJECT else "en"
    return ResetMail(user.email, _SUBJECT[lang], _BODY[lang].format(name=user.display_name, link=link, hours=hours))


def prepare(db: Session, email: str, lang: str | None) -> ResetMail | None:
    """The message to send, if this address has an account that may have
    one. Nothing is sent here, so that a known address takes no longer to
    answer than an unknown one."""
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not user.is_active:
        return None
    link, _ = issue(db, user, EMAILED_HOURS)
    return mail_for(user, link, EMAILED_HOURS, lang)


def deliver(message: ResetMail) -> None:
    """Run after the reply has gone. A failure can only be logged: the person
    has already been told to check their inbox."""
    try:
        mail.send(message.to, message.subject, message.text)
    except mail.MailError:
        logger.error("Password reset mail to %s failed", message.to)


def _valid_row(db: Session, token: str) -> PasswordResetToken | None:
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_digest(token or "")))
    if row is None:
        return None
    if row.expires_at <= utcnow():
        db.delete(row)
        return None
    return row


def account_for(db: Session, token: str) -> User | None:
    """The account a link would reset, without using it up: for the page to
    say it's expired before anyone has typed a password."""
    row = _valid_row(db, token)
    user = db.get(User, row.user_id) if row else None
    return user if user is not None and user.is_active else None


def reset(db: Session, token: str, new_password: str) -> User:
    """Sets the password. A password that isn't good enough leaves the link
    working, so the person can try another. Having the link proves the inbox,
    so the address counts as confirmed."""
    row = _valid_row(db, token)
    user = db.get(User, row.user_id) if row else None
    if user is None or not user.is_active:
        raise AuthError(400, BAD_LINK, "bad_reset_link")
    check_new_password(new_password, user.email)
    user.password_hash = hash_password(new_password)
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    # Whoever got in with the old password is out.
    revoke_all_sessions(db, user)
    db.delete(row)
    audit.record(db, user, "user.password_reset", "user", user.id)
    return user
