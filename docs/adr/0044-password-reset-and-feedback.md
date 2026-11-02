# 44. Forgotten passwords, feedback from the account, and the admin's Users screen

Date: 2026-11-02

## Context

Before opening FishEye to people outside the team, three gaps. Someone who
forgot a password was locked out for good. "Send feedback" opened a mail app,
which many people don't have set up and which left no record in FishEye. And
the admin console could only make someone an admin or suspend them, with no way
to see an account, help someone locked out, or remove one.

## Decision

**Password reset by emailed link** (`services/password_reset.py`). A link is good
for an hour and works once; only its SHA-256 is stored. The answer is the same
for any address, and at the same speed: the mail goes out after the reply. Using
a link ends every other session and signs this browser in. A password that isn't
good enough leaves the link working, so the person can try another. Checking a
link doesn't use it up, so a mail app scanning links can't spend it.

**It depends on mail being set up**, which it isn't until `MAIL_BACKEND=smtp`. So
the page asks `/api/auth/providers` whether mail can go out, and otherwise says
who to write to, rather than promising a message that never comes.

**An admin can make a link by hand** (Users, the account, "Make a password reset
link"), good for a day, shown once, to send by any other means. That's the way
back in while there is no mail, and for someone whose mail doesn't arrive. Not for
an admin's own account or another admin's: whoever holds the link can take the
account. It's in the audit log, without the token.

**Feedback is sent from the account** (`services/feedback.py`): one box, one
button, with the page and language added. Signed out, it asks to sign in, and
gives the address for someone who can't. Limits: 10 a day per account; a double
tap is one message. No word filter, since only admins read it and it may have to
quote what someone said. A deleted account's messages stay, without a name.

**Feedback can be read by Claude Code as well as in the console.** The console's
"Copy for Claude" button and `python -m app.cli.feedback` give the same text:
newest first, with the page and language, an account number, and no name or
address, since those aren't needed to act on it. It says that what follows is what
users wrote, to be weighed, not instructions to follow, because anyone can type
anything into that box. `--json` is for scripts, `--done 3 7` marks messages
handled.

**The Users screen lists, then opens one account.** Filters, search by name,
address or number, and sorting; actions moved off the row into the account, which
shows what you need before acting on it. Added: rename, confirm an address by
hand, sign out everywhere, delete. An admin can't be deleted from here or have
their password link made; remove the role first.

## Consequences

- Until SMTP is set up, each forgotten password is a message to the contact
  address and a link made by hand. Fine for a few testers; not for many.
- Rate limits are per process, as elsewhere (ADR 0021).
- Replies to feedback are still by email, from the admin's own mail app. Worth
  revisiting if there's a lot to reply to.
