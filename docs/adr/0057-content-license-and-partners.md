# 0057. A wide license for what people post, partners included

Date: 2026-11-15. Status: accepted.

## Context

The terms of 2026-11-12 left people's catches, photos, notes and comments
theirs and gave FishEye a narrow license: store, copy and display them in
FishEye, ending when the content was deleted. The owner sees the data as the
company's asset and asked how other apps do it.

Read that day (not legal advice):

- Copyright protects photos, notes and comments, not facts: gear, fish and
  dates belong to no one. Taking ownership outright needs a signed writing
  (17 U.S.C. §204(a)); a nonexclusive license doesn't (§101), so apps take a
  wide license instead.
- Fishbrain's terms (updated 2025-06-03, section 2) take an unlimited,
  non-exclusive, irrevocable, perpetual, royalty-free, sublicensable and
  transferable license, may share content with partners, and let Fishbrain
  and its partners use a user's name, likeness and activity in ads. Its
  privacy policy still says it doesn't sell users' personal data to
  unrelated third parties, and that partner offers go out without giving
  the partner anyone's information.
- Meta's terms end the license on deletion, except where others are already
  using the content under it.

The owner: as wide as possible, like Fishbrain; only spots are kept back,
and whatever makes the company money comes first.

## Decision

The owner confirmed the wording in chat, change by change (2026-11-15).

- **Terms, section "Your content".** People keep ownership. FishEye and its
  affiliates get a worldwide, non-exclusive, perpetual, irrevocable,
  royalty-free, transferable and sublicensable license to use, store, copy,
  modify, translate, display and publish it in any media and make derivative
  works, including to run, promote and improve FishEye and develop new
  products. FishEye may give what people share publicly to affiliates and
  partners, the lake and any exact spot the angler made public included.
  A new paragraph lets FishEye, affiliates and partners use someone's
  display name and public catches (fish, gear) in ads, offers and sponsored
  content, in FishEye and elsewhere, unpaid. The license survives closing an
  account.
- **Terms, summary.** "You own what you post. FishEye may use it and share
  it with partners, but won't reveal your fishing spots."
- **Privacy policy.** "We never sell or hand out your fishing spots" is the
  only promise. The identity line (name and email not sold or given to
  partners) and the visit-count sentence are gone. Partners are listed
  among who else handles data. Content already given to partners or used in
  ads isn't taken back when deleted.
- Spots are named once in each place that matters (the terms' summary, the
  privacy policy's lede and its use section), not in every clause. Private
  catches stay out of what partners get; FishEye's own use of them (training
  its models, improving features) falls under the license.

## Consequences

- The live terms promise notice at least 14 days before a change that
  matters applies (a rule written into the 2026-11-12 terms, not the
  owner's). FishEye is still in testing with no real users, so the owner
  turned the site notice off (2026-11-15, `LEGAL.changeNotices`): on deploy
  only `updatedIso`, `existingUsersFromIso` and the privacy page's `UPDATED`
  change. The notice comes back once the owner says FishEye has launched. Content posted before that stays under
  the old license; using it for partners or ads would need its owner's
  consent (FTC on retroactive changes). On 2026-11-14 there were no public
  catches.
- The App Store app: sharing data with partners for their ads, or joining it
  with other companies' data for targeting, is tracking under Apple's App
  Tracking Transparency and needs the system prompt; sponsored content shown
  in FishEye isn't. Apple 5.1.2(i) still limits what app data reaches third
  parties.
- If half of revenue ever comes from selling or sharing personal
  information, the CCPA applies whatever the company's size.
- The owner may later make changes apply on posting, with a site notice,
  instead of after 14 days; the arbitration section keeps its own rule that
  a change doesn't reach a claim already raised (In re Halliburton, Tex.
  2002, as read in Carey v. 24 Hour Fitness, 5th Cir. 2012).
