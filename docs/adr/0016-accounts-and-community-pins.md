# ADR 0016: Accounts, community catch pins, and moderation

## Status
Accepted. Supersedes the "single shared token, no accounts" shortcut in
ADR 0003 for admin access (the token still works for scripts).

## Context

The map shows where fish *officially* are (TPWD surveys, ADR 0002) and
where they've been *recorded* (GBIF, ADR 0012). Anglers also know where
they caught something last weekend, and a beginner in a new town wants
exactly that. Letting people pin catches — with photos — needs accounts,
and user content needs moderation and an admin to do it.

Decisions made with the user up front:
- Sign-in: email + password, plus optional Google.
- Publishing: immediate, with reporting and after-the-fact moderation
  (not pre-approval).
- Privacy: each pin is public or "only me".

## Decision

### Accounts and sessions
- **Server-side sessions** in an httpOnly, SameSite=Lax cookie. The DB
  stores only a SHA-256 of the token. Chosen over JWTs because logout,
  password change ("sign out other devices") and suspension must take
  effect immediately, which a stateless token can't do before it expires.
- **Passwords**: scrypt (n=2^14, r=8, p=1) from the standard library, with
  parameters stored in the hash so they can be raised and old hashes
  upgraded at next login. Length-based rules (8–128, a small common-password
  list, not the email), per NIST SP 800-63B, rather than composition rules.
- **Brute force**: per-email and per-IP sliding-window limits on login,
  per-IP on registration. Unknown email and wrong password return the same
  401 and take the same time (a dummy hash is verified).
- **CSRF**: SameSite=Lax, plus an Origin check on every state-changing
  request (only the frontend's origin is accepted). CORS allows exactly
  that origin with credentials.
- **Google** (optional, off unless `GOOGLE_CLIENT_ID/SECRET` are set):
  authorization-code flow with PKCE and a `state` cookie; the profile comes
  from Google's userinfo endpoint using the token we just exchanged, and
  unverified Google emails are refused. **Accounts are never merged by
  email**: local emails aren't verified in this demo, so a Google sign-in
  whose email matches an existing password account is refused with a
  message to sign in and connect Google from the account page. The return
  path after sign-in is restricted to same-site relative paths (no open
  redirect).
- **The first admin comes from the command line** (`python -m
  app.cli.users create-admin`), never from the web: no "first sign-up is
  admin" rule for someone to race.

### Pins and photos
- A pin is a point, title, optional species (guide species or free text),
  date, note, visibility, and up to 4 photos. It links to the nearest lake
  centre within 3 km as a UI hint only.
- **Pins never become lake data**: not WaterbodySpecies, not scoring input,
  not AI advisor facts — the same line ADR 0012 drew for GBIF.
- **Visibility lives in one function** (`services/pins.can_view`): owner and
  admins always; everyone else only public + published. The list, detail
  and photo endpoints all use it. Invisible pins are 404, not 403.
- **Photos are decoded and re-encoded** (JPEG, ≤2048 px, 640 px thumbnail).
  That strips EXIF — notably the GPS coordinates phones embed, which would
  otherwise leak a private spot — and guarantees that only real images are
  ever served. A pixel ceiling blocks decompression bombs. Files live under
  `MEDIA_ROOT` behind a `MediaStore` interface (local folder now, object
  storage later) and are served by an endpoint that applies `can_view`,
  never as a static folder. Public photos are cacheable for an hour, a
  private pin's for five minutes and only by the browser.
- Owners can edit, change visibility, add/remove photos and delete (which
  deletes the files) while a pin is published. Deleting an account deletes
  its pins and photos.

### Moderation and admin
- Anyone signed in can report a public pin, once. Reports from **3
  different people** hide it (`status=hidden`, reason `reports`) until an
  admin reviews it; the owner still sees it with an explanation.
- Admins resolve report groups (dismiss — which restores an auto-hidden
  pin —, hide, remove), set any pin's status, permanently purge a pin with
  its files, promote/demote and suspend/reactivate users (suspension
  revokes all sessions at once), and read the audit log.
- **Every moderation and account action writes an audit entry in the same
  transaction**, including the system's own auto-hide (actor "System").
- Lock-out guards: an admin can't change their own role or status, and the
  last active admin can't be demoted, suspended or deleted (web or CLI).

### Hardening after an independent security review

A separate review of the finished feature found issues that the first
version's tests didn't cover. Each is fixed and has a regression test in
`backend/tests/test_hardening.py`:

- **Recent sign-in for account-recovery changes.** Setting a Google-only
  account's first password, disconnecting Google, connecting a *new*
  Google account and deleting a passwordless account need a session under
  15 minutes old; otherwise the API answers 403 with
  `X-Reauth-Required: 1` (exposed via CORS). Password accounts confirm with
  `POST /api/auth/reauth` (rate-limited like login), which replaces the
  session; Google-only accounts sign in with the same Google account again.
  A stolen, days-old cookie can browse but can't take the account over.
- **Deleting an account leaves no dangling references.** SQLite now
  enforces foreign keys (`PRAGMA foreign_keys=ON` on every connection), so
  the declared `ON DELETE` rules actually run. Reports a deleted user filed
  stay in the queue ("Deleted account"), and audit entries keep an
  `actor_label` snapshot ("Name <email>"), so the log still says who acted.
  Ids are `AUTOINCREMENT` and never reused, so an old link or audit entry
  can't come to point at someone else's account or pin.
- **Moderated pins are frozen.** A hidden or removed pin can't be edited,
  have photos changed, or be deleted by its owner (409) until a moderator
  decides, so reported content can't be quietly rewritten, and deleting it
  can't erase the reports. An owner deleting a *published* pin that has
  open reports is recorded in the audit log.
- **Request size is capped before the body is read.** Pin routes accept
  `max photos × max photo size + 1 MB`, everything else 256 KB; a chunked
  or multipart body without `Content-Length` is refused (411). Upload
  routes are synchronous, so Pillow's decoding runs in the threadpool, not
  on the event loop, and each file is read with a hard cap.
- **No 500s from input.** Path ids are bounded (1 … 2³¹−1 → 422), a
  duplicate-report race returns 409, non-ASCII OAuth state is a normal
  refusal, and the stored OAuth return path is re-validated (plain visible
  ASCII, no `|`, ≤ 200 chars).
- Smaller fixes: phone "MPO" JPEGs are accepted (first frame kept); the
  rate limiter never allocates on a check and evicts empty keys; the admin
  token is compared in constant time; photos are `Cache-Control: private`
  so no shared cache keeps serving a photo after its pin goes private.

## Consequences

- Rate limits and sessions' "last seen" throttling are in-process, fine
  for one worker. A multi-worker deployment needs Redis for the limiters.
- There's no email: no verification, no password reset by mail. A user who
  forgets a password needs an admin (or Google). That's the next piece of
  infrastructure a public launch needs, along with terms of use and a
  takedown contact (docs/commercialization.md).
- Schema changes are new tables only, so the existing `create_all` on
  startup picks them up without a migration. (A database that already has
  community tables from before the hardening needs them dropped and
  recreated; nothing outside the demo has any.)
- Audit entries keep a deleted user's name and email. That's the point of
  an audit log; a public launch needs its retention period written into the
  privacy policy.
- Tests cover the security properties directly (hashed tokens, logout
  invalidating copies of a cookie, cross-site writes refused, EXIF GPS
  gone from stored photos, private pins 404 to strangers, open-redirect
  attempts, account-merge refusal, last-admin guards).
