"""The API's refusals in the visitor's language (knowledge/error_text.py)."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from app.knowledge import error_text as et

APP = Path(__file__).resolve().parents[1] / "app"


def test_every_message_has_every_language():
    for english, by_lang in et.TEXT.items():
        assert set(by_lang) == set(et.LANGS), english
        assert all(v.strip() for v in by_lang.values()), english
    for english, by_lang in et.FISH.items():
        assert set(by_lang) == set(et.LANGS), english


@pytest.mark.parametrize(
    ("english", "lang", "expected"),
    [
        ("Email or password is incorrect.", "ja", "メールアドレスまたはパスワードが正しくありません。"),
        ("Photos can be up to 10 MB.", "ko", "사진은 10MB까지 올릴 수 있어요."),
        (
            "This looks like a Channel Catfish, not a Bluegill. Change the fish to Channel Catfish, or use a photo of the Bluegill.",
            "zh",
            "这看起来是斑点叉尾鮰，不是蓝鳃太阳鱼。把鱼种改成斑点叉尾鮰，或者换一张蓝鳃太阳鱼的照片。",
        ),
        ("Photo check: this looks like a black bass. Which kind, the photo can't show, so the species is your call.", "es",
         "Revisión de la foto: parece ser lobina. La especie exacta no se ve en la foto: la decides tú."),
        ("Photo 2: That file is empty.", "es", "Foto 2: Ese archivo está vacío."),
        ("Something only a script sees.", "zh", "Something only a script sees."),
        ("Email or password is incorrect.", "fr", "Email or password is incorrect."),
        ("Email or password is incorrect.", None, "Email or password is incorrect."),
    ],
)
def test_a_message_in_each_language(english, lang, expected):
    assert et.tr(english, lang) == expected


def test_a_fish_the_site_has_no_name_for_stays_as_the_server_named_it():
    msg = "This looks like an Alligator Gar, not a Bluegill. It isn't on FishEye's list yet: choose Other and name it."
    assert et.tr(msg, "ja") == (
        "ブルーギルではなくAlligator Garのようです。この魚はまだFishEyeのリストにないので、「その他」を選んで名前を入力してください。"
    )


def test_the_api_answers_in_the_chosen_language(make_client):
    c = make_client()
    wrong = {"email": "nobody@example.com", "password": "not-the-password"}
    assert c.post("/api/auth/login", json=wrong).json()["detail"] == "Email or password is incorrect."
    c.cookies.set(et.LANG_COOKIE, "ko")
    assert c.post("/api/auth/login", json=wrong).json()["detail"] == "이메일 또는 비밀번호가 맞지 않아요."
    c.cookies.set(et.LANG_COOKIE, "xx")
    assert c.post("/api/auth/login", json=wrong).json()["detail"] == "Email or password is incorrect."


# Every message a person can see is translated: a new one written only in
# English fails here, as a string added only to the frontend's en.ts fails
# its type check. Admin-only and machine-facing messages stay English.
USER_FACING = [
    "api/auth.py", "api/geocode.py", "api/lake_reports.py", "api/pins.py", "api/ask.py", "api/rate_limits.py",
    "core/security.py", "services/auth.py", "services/pins.py", "services/media.py", "services/lake_reports.py",
    "services/email_verification.py", "services/fish_id.py", "services/password_reset.py", "services/feedback.py",
    "api/feedback.py", "main.py",
]
NOT_SHOWN = {
    "Requests need a Content-Length.", "Bad Content-Length.",  # no browser sends these
    "Resolve as fixed or dismissed.", "This report is already resolved.",  # admin console
}
SAMPLES = ("1", "a Bluegill", "Bluegill")


def _sentence(s: str) -> bool:
    return len(s) >= 10 and " " in s and s[:1].isupper() and s.rstrip()[-1:] in ".?!"


def _render(node: ast.AST, sample: str) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else sample for v in node.values)
    return None


def _messages(path: Path) -> set[tuple[str, ...]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            found += [*node.exc.args, *(k.value for k in node.exc.keywords)]
        elif isinstance(node, ast.keyword) and node.arg in ("detail", "busy_message", "exhausted_message"):
            found.append(node.value)
        elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets):
            found.append(node.value)
        elif isinstance(node, ast.FunctionDef) and node.name in ("password_problem", "check_claim"):
            found += [n.value for n in ast.walk(node) if isinstance(n, ast.Return) and n.value is not None]
            found += [a for n in ast.walk(node) if isinstance(n, ast.Call) for a in n.args]
    out = set()
    for node in found:
        renders = tuple(r for s in SAMPLES if (r := _render(node, s)) is not None)
        if renders and _sentence(renders[0]) and renders[0] not in NOT_SHOWN:
            out.add(renders)
    return out


@pytest.mark.parametrize("module", USER_FACING)
def test_every_message_people_see_is_translated(module):
    untranslated = sorted(
        renders[0] for renders in _messages(APP / module) if all(et.tr(r, "zh") == r for r in renders)
    )
    assert untranslated == [], f"{module}: add these to knowledge/error_text.py"


def test_the_scan_finds_messages():
    assert any("Email or password is incorrect." in r for r in _messages(APP / "services/auth.py"))
    assert any(re.match(r"^This looks like", r[0]) for r in _messages(APP / "services/fish_id.py"))
