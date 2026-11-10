# 0054. Likes, comments, leaderboards and catch alerts

Date: 2026-11-10. Status: accepted.

## Context

A tester didn't manage to share a catch and assumed the Catches page did nothing.
They suggested likes, comments and a regional ranking. The product owner asked for
those, and for one kind of email: tell me when someone confirms this fish within
so many miles of here.

## Decision

**Sharing is explained where it starts.** Three numbered steps at the top of
Catches. A catch is one fish: the form and the photo page say so. A pile or a
bucket of fish can't be read by the photo check, which names one fish per photo;
counting and naming several is left for a paid AI model, if subscriptions come.

**Likes and comments are for public, published catches.** One like per person, not
on your own catch. A comment is up to 500 characters, goes through the same word
filter as a title, and is published at once like a catch. Whoever wrote it, whoever
owns the catch and the moderators can delete it. Reports work as they do for
catches: one per person per comment, hidden at
`REPORT_AUTO_HIDE_THRESHOLD`, listed under Reports in the admin console. Likes,
comments and alerts go with the account.

**Leaderboards** are per place: the state or county being browsed, or the whole
country. Four boards, each for the last 30 days or all time: most fish (catches the
photo check backed, so posting isn't enough), most shared, most active (days with a
public catch) and most liked. They count public, published catches and show the
name those catches already show. Someone can leave them from their account page.
Equal counts share a rank.

**An angler's page** is `/community/anglers/<id>`: the name, the join date, three
counts and the public catches. No email address, nothing private, and no page at
all for someone with nothing public.

**Catch alerts** (`services/alerts.py`): a fish, a place and a radius in miles. A
new public catch of that fish, inside the radius, whose photo check backed it,
sends one email.

- What the email says is what the catch's page says to anyone: the water or county,
  not the spot and not the angler. Distance is measured to the same public point
  (ADR 0038), so a set of small radii can't be used to find a spot someone kept to
  themselves.
- The alert's own place is rounded to about a kilometre when saved.
- Only confirmed addresses get mail, or anyone could sign up with someone else's
  address and send them alerts.
- At most one email per alert per 12 hours, at most 200 per catch, sent after the
  response so a slow mail server doesn't hold up a post.
- Every email has an unsubscribe link. It opens a page with a button, because mail
  scanners open links.

## Consequences

Alerts need outgoing mail: `MAIL_BACKEND=smtp` and the `SMTP_*` settings, and
`EMAIL_VERIFICATION=on` so that addresses get confirmed. Until then people can set
alerts and the page says emails aren't on yet.

The new tables are created at startup; `users.hide_from_rankings` is added by
`db/upgrades.py`. No data has to be moved.
