# 45. Trying FishEye signed out, link previews, and counting visits

Date: 2026-11-06

## Context

Before promoting FishEye, two things stood between a newcomer and trying it.
Feedback and the photo ID both needed an account, and most people leave at a
sign-up form. And there was no way to tell whether promotion brought anyone:
the privacy policy promised no analytics, and an outside analytics service would
break that promise. Search engines had no sitemap, and a shared link showed no
picture.

## Decision

**Feedback without an account** (`api/feedback.py`, `services/feedback.py`).
Signed out, a message is kept with no account, `signed_out` set, and an email
address only if the sender leaves one for a reply. Five a day per IP address,
and 100 a day from everyone signed out together, so a script can fill at most
that much of the queue. The admin console and the text export say "signed out".

**A photo ID trial signed out** (`api/pins.py`, `_trial`). Five checks a day
per IP address, 500 a day from everyone signed out together. The model runs on
our server, so the cost is CPU, not an API bill. The page says the trial exists,
and once it's used up offers a free account. Signed in, the account's own
allowance (60 an hour) applies as before.

**The IP address is never stored for either.** The limits count in process
memory and forget within a day, as every rate limit here does (ADR 0021).

**Visit counts that identify no one** (`services/visits.py`,
`components/VisitCounter.tsx`). Each page opened adds one to a row of (day,
page, source). The source is the referring site's host name, or a `?ref=` tag
on the link, which is how a Reddit post or a flyer is told apart. No IP address,
cookie, identifier, user agent or full referrer is kept; the request is sent
without cookies. Pages that hold someone's id (`/community/123`) are counted by
kind, and account and admin pages aren't counted. Admins see the numbers in the
console's Visits tab and with `python -m app.cli.visits`. The privacy policy says
all of this.

**Sitemap, robots.txt and link previews** (`app/sitemap.ts`, `app/robots.ts`,
`app/opengraph-image.tsx`, `app/fish/[slug]/opengraph-image.tsx`). The site's
address comes from the request (`lib/siteOrigin.ts`), so no new setting is
needed behind Caddy. The sitemap lists the main pages and every fish guide.
Previews are in English: one picture is shown to everyone who sees a link.

## Consequences

- Counts are page views, not people: one person reading five guides is five.
  That is the price of keeping nothing that tells visitors apart.
- Visits from browsers that block scripts, and from crawlers, aren't counted.
- Lakes have no page of their own (`/map?lake=`), so they aren't in the sitemap.
