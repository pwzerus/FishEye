# 0056. Gear on catches, and counting it

Date: 2026-11-14. Status: accepted.

## Context

The owner wants the fishing log to record gear: which bait and gear caught
which fish. Two later features need it: Plus's log analysis (an angler's own
catches by bait, time of day and weather) and totals across everyone ("bass
at this lake mostly took soft plastics"). The owner's rule (2026-11-14):
FishEye never sells or hands out spots.

Asked whether gear can be collected without asking first, the official
texts were read that day (not legal advice). In the US, at FishEye's size,
it can, if people are told:

- Gear and fish aren't sensitive data. Precise geolocation is: California
  lists it as sensitive personal information, and Texas defines it as within
  1,750 feet (Bus. & Com. Code 541.001).
- The CCPA applies above $25M in revenue, 100,000 California residents'
  data bought, sold or shared, or half of revenue from selling data
  (oag.ca.gov). The Texas TDPSA exempts SBA small businesses, except that
  they may not sell sensitive data without prior consent (541.002, 541.107).
- Apple is stricter. App Review Guideline 5.1.1(ii): an app "must secure
  user consent for the collection" of user data, offer an easy way to
  withdraw it, and "Paid functionality must not be dependent on" it.

The owner chose: on the website, no pop-up; the privacy policy says what
happens, and the account page turns it off. The App Store app asks first.
Later that day the owner added that privacy details belong in the privacy
policy, not in the forms: the one privacy line the forms show is the spot
promise, FishEye's selling point.

Asked the same day whether gear data could be sold one day, the owner
answered that only spots are off limits, and that the policy should promise
nothing else. What the texts say about selling the rest:

- Aggregate information isn't personal information. The CCPA defines it as
  information about a group with identities removed, not linked or
  reasonably linkable to anyone, and adds that it "does not mean one or
  more individual consumer records that have been deidentified" (Civ. Code
  §1798.140(b), (v)(3)). Texas leaves deidentified data out of personal
  data (541.001(19)) if the holder takes reasonable measures, commits
  publicly not to reidentify it and binds recipients by contract (541.106).
- Apple 5.1.2: data collected in an app "may only be shared with third
  parties to improve the app or serve advertising", data collected for one
  purpose may not be repurposed without further consent, and an app may not
  help anyone identify users from data it calls anonymized or aggregated.
- The FTC warns that adopting more permissive data practices, such as
  starting to share data with third parties, through a quiet, retroactive
  change to a privacy policy may be unfair or deceptive. The live policy
  said "We don't sell your data".
- The CCPA covers a business of any size that makes half its revenue from
  selling or sharing personal information (§1798.140(d)(1)(C)).

## Decision

**Gear is picked from the /gear list.** A catch names up to six items of
`app/knowledge/gear.py` without its tools (pliers and a life jacket catch
nothing), stored a row per item in `catch_gear`, so totals are a GROUP BY.
`catch_pins.gear_other` holds anything else, up to 60 characters, through
the word filter. The list's ids are named in every language by
`frontend/src/i18n/names.ts`, so one choice reads as 软虫 or Soft plastic
worms, and totals don't depend on spelling. The gear shows on the catch's
page to whoever can see the catch: a private catch's gear stays the angler's.

**Counting is on until turned off.** `users.gear_stats` is None (never
chosen, which on the website means yes), True or False. The account page's
switch sets it, and a no given anywhere holds everywhere. `User.counts_gear`
is the answer to use. None is kept apart from True so the App Store app can
ask once, before collecting gear there, from people who never chose.

**What totals may say**, when they are built: the gear and the fish only,
never the spot, the angler or a photo; a lake's totals only once enough
different anglers have catches there; nobody with `counts_gear` off. Plus's
log analysis reads the angler's own catches whatever the switch says, since
paid features can't depend on consent (Apple 5.1.1).

**Only spots are never sold.** The privacy policy promises what the owner
asked for and nothing more: FishEye never sells or hands out spots. (Until
2026-11-15 it also said identity information wasn't sold or given to
partners; ADR 0057 dropped that.) It says one thing about gear, once: FishEye uses the gear
people record to improve its own algorithms, and the account page turns
that off. It says nothing about selling anything else. The owner may sell
gear totals to partners one day, seeing them as FishEye's own data
(2026-11-14). Totals aren't personal information, so that needs no change
to the policy, as long as a lake's numbers come from enough anglers not to
point to anyone's spot. Single records, as stored, hang on an account, so
they are users' personal information. Gear, fish and dates are facts, which
copyright doesn't protect, so the terms' "you keep ownership" doesn't cover
them: what limits selling a record is whether it leads back to someone.
Without the account, name, email and lake it doesn't; with a lake and a
date it could be matched to a public catch, and so to its angler and spot.
Selling records tied to an account would need the policy to say so first. The policy no longer says "We don't
sell your data", "we don't show ads", or that cookies aren't used for ads
or tracking: the owner expects to use them for that. Two limits come from
outside the policy: information collected while the live policy said "We
don't sell your data" isn't sold without people's consent (FTC), and data
collected in the App Store app may go to third parties only to improve the
app or serve ads (Apple 5.1.2(i)).

**Telling people.** The privacy policy (dated 2026-11-14) lists gear under
What we collect and says the one sentence above under What we do with it,
in every language. Nothing is said under the field, and the account page
shows the switch without an explanation: privacy details stay in the
policy. Dropping "We don't sell your data" is a change that matters, and
the live policy promises to say so on the site before such a change
applies: a notice goes up when it goes live, and gear totals sold one day
come only from gear logged after that (there was none before).

## Consequences

- Gear goes with its catch: edited with it, deleted with it and with the
  account.
- Algorithm work, any totals shown and log analysis are later work, held
  to the rules above.
- The notes field's example no longer suggests bait.
- When this goes live, the privacy page's date (`UPDATED` in
  `frontend/src/app/privacy/page.tsx`) becomes that day. No notice goes up
  while FishEye is in testing with no real users (the owner, 2026-11-15;
  `LEGAL.changeNotices`); after launch, changes get one as the terms' did
  (`components/legal/TermsNotice`).
- Turning the switch off keeps someone's gear out of algorithm work, as
  the policy's gear sentence says. In the App Store app, gear from someone
  who said no can't be put to another use without further consent (Apple
  5.1.2(ii)).
- When the App Store app is built, its first gear entry asks while
  `gear_stats` is None and says the gear helps improve FishEye's
  algorithms, and its App Privacy answers list gear as collected and linked
  to the account, not used for tracking. If anything is ever sold, Apple
  lets app data reach third parties only to improve the app or serve ads
  (5.1.2(i)): check with App Review first, or keep catches logged in the app
  out, which means recording where a catch was logged.
