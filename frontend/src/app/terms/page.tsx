import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage } from "@/components/legal/LegalPage";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Terms of use · FishEye",
  description: "The agreement for using FishEye: fishing information, AI answers, FishEye Plus, what you share, and disputes.",
  alternates: { canonical: "/terms" },
};

// Rewritten 2026-11-12, when Ask's AI began answering from its own knowledge
// as well as the guides (backend services/rag/ask.py) and FishEye Plus was
// added. Read against Fishbrain's and onX's terms, Anthropic's Usage Policy
// (AI disclosure; products open to minors) and Apple's minimum terms for an
// app's own license. A draft until a lawyer has read it: see lib/legal.ts.
//
// The disclaimers, the limits on liability and the release are set apart in
// bold boxes (.legal-conspicuous): Texas enforces a release of someone's own
// negligence only when it is conspicuous and says so expressly.

const SECTIONS: [string, string][] = [
  ["agreeing", "Agreeing to these terms"],
  ["accounts", "Who can use FishEye"],
  ["information", "Fishing information is a guide, not the law"],
  ["ai-answers", "AI answers"],
  ["plus", "FishEye Plus"],
  ["your-content", "What you share"],
  ["rules", "Rules for using FishEye"],
  ["moderation", "Moderation and closing accounts"],
  ["our-content", "FishEye's own content"],
  ["third-parties", "Other people's data, services and links"],
  ["copyright", "Copyright complaints"],
  ["safety", "Your safety is yours"],
  ["disclaimers", "No warranties"],
  ["liability", "Limits on our liability"],
  ["release", "Release"],
  ["indemnity", "Claims caused by you"],
  ["disputes", "Disputes and arbitration"],
  ["changes", "Changes"],
  ["app-stores", "Apps from the App Store or Google Play"],
  ["general", "General"],
  ["contact", "Contact"],
];

/** A section's number, for the headings and for "see Section 17". */
function sec(id: string): number {
  const n = SECTIONS.findIndex(([key]) => key === id);
  if (n < 0) throw new Error(`no terms section ${id}`);
  return n + 1;
}

function Heading({ id }: { id: string }) {
  return (
    <h2>
      {sec(id)}. {SECTIONS[sec(id) - 1][1]}
    </h2>
  );
}

export default function TermsPage() {
  const optOut = LEGAL.optOutDays;
  return (
    <LegalPage
      title="Terms of use"
      lede="The agreement between you and FishEye. Please read it: it asks you to take responsibility for your own safety, limits what FishEye is liable for, and sends most disputes to individual arbitration."
    >
      <section className="legal-summary" aria-labelledby="short-version">
        <h2 id="short-version">The short version</h2>
        <ul>
          <li>
            <strong>FishEye is a guide.</strong> Rules, access, fish data, forecasts and AI answers can be wrong. Your
            state&apos;s current rules and the signs at the water are what count.
          </li>
          <li>
            <strong>Fishing has risks.</strong> You decide where, when and how to fish, and you take on that risk.
          </li>
          <li>
            <strong>AI answers come from an AI, not a person.</strong> They can be wrong. Check anything that matters.
          </li>
          <li>
            <strong>You own what you post.</strong> You let FishEye show it, and you&apos;re responsible for it.
          </li>
          <li>
            <strong>FishEye Plus renews until you cancel</strong>, and you can cancel any time.
          </li>
          <li>
            <strong>Disputes go to individual arbitration or small-claims court</strong>, not class actions, unless you
            opt out within {optOut} days.
          </li>
        </ul>
        <p className="legal-note">This summary helps you find your way. The full terms below are what apply.</p>
      </section>

      <nav className="legal-toc" aria-label="Contents">
        <ol>
          {SECTIONS.map(([id, title]) => (
            <li key={id}>
              <a href={`#${id}`}>{title}</a>
            </li>
          ))}
        </ol>
      </nav>

      <section id="agreeing">
        <Heading id="agreeing" />
        <p>
          These terms of use (&ldquo;terms&rdquo;) are an agreement between you and {LEGAL.operator} (&ldquo;FishEye&rdquo;,
          &ldquo;we&rdquo;, &ldquo;us&rdquo;). They cover the website at {LEGAL.site}, the FishEye app, and everything on
          them, including the map, the fish guides, Ask and its AI answers, the photo check, catches, comments and
          accounts (together, &ldquo;FishEye&rdquo;). Our <Link href="/privacy">privacy policy</Link> and{" "}
          <Link href="/copyright">copyright page</Link> are part of these terms.
        </p>
        <p>
          You accept these terms when you create an account, get FishEye Plus, or use FishEye. If you don&apos;t agree,
          please don&apos;t use FishEye. If you had an account before {LEGAL.updated}, these terms apply to you from{" "}
          {LEGAL.existingUsersFrom}; until then, the earlier terms do. If you use FishEye for an organization, you accept these terms for it as well,
          and confirm you may do so.
        </p>
        <p className="legal-conspicuous">
          Please read Section {sec("disputes")}. It says that disputes between you and FishEye are settled by binding individual
          arbitration or in small-claims court, with no class actions and no jury, unless you opt out within {optOut}{" "}
          days of first accepting these terms.
        </p>
      </section>

      <section id="accounts">
        <Heading id="accounts" />
        <ul>
          <li>
            Anyone can browse the map and guides. To have an account you must be {LEGAL.minimumAge} or older. No one
            under {LEGAL.minimumAge} may create one.
          </li>
          <li>
            If you are under 18, or under the age of majority where you live, you need a parent&apos;s or guardian&apos;s
            permission. By giving it, your parent or guardian accepts these terms for you and is responsible for your
            use of FishEye, including any purchase.
          </li>
          <li>
            Give true information, and keep it up to date. One account per person: don&apos;t make extra accounts, for
            example to get more free AI answers or photo checks.
          </li>
          <li>
            Keep your password to yourself. You are responsible for what happens on your account. Tell us at once if
            you think someone else is using it.
          </li>
          <li>
            You confirm that you are not on a U.S. government list of prohibited or restricted parties, and not in a
            country under a U.S. embargo or that the U.S. has designated as supporting terrorism.
          </li>
          <li>
            FishEye is made for fishing in the United States. If you use it elsewhere, you do so on your own initiative
            and must follow the laws where you are.
          </li>
        </ul>
      </section>

      <section id="information">
        <Heading id="information" />
        <p>
          FishEye brings together public data, its own guides, other anglers&apos; catches and computer estimates. We
          work to keep it right, but we can&apos;t promise that it is accurate, complete, up to date, or right for your
          water. Use it to plan, then check.
        </p>
        <ul>
          <li>
            <strong>Rules and licenses.</strong> Fishing licenses, seasons, size and bag limits, bait rules and closures
            change, and differ by state and by water. FishEye&apos;s summaries can be out of date or incomplete, and are
            not legal advice. The current rules of your state&apos;s fish and wildlife agency, and the signs at the
            water, are what count. You are responsible for having the right license and following the rules.
          </li>
          <li>
            <strong>Access and land.</strong> A lake, ramp, shore or spot on FishEye may be private, closed, unsafe, or
            not where the map shows it. FishEye is not a land survey and doesn&apos;t tell you who owns land; a place
            shown as public, or not marked private, may still be private. Obey posted signs, get permission before you
            fish on private land, and don&apos;t trespass.
          </li>
          <li>
            <strong>Fish and lake facts.</strong> Which fish live in a lake, stocking, depths and other facts come from
            public sources and anglers&apos; reports, which can be wrong or old.
          </li>
          <li>
            <strong>Not for navigation.</strong> FishEye&apos;s maps and positions can be off. They are not a navigation
            chart: don&apos;t steer a boat or find your way by them, and watch for hazards yourself.
          </li>
          <li>
            <strong>Weather, water and forecasts.</strong> Weather, water levels, fishing scores and best times are
            estimates from other services&apos; data and simple models. Conditions change fast, and can be different
            where you stand.
          </li>
          <li>
            <strong>Photo checks.</strong> Naming the fish or the gear in a photo is a computer&apos;s guess. Don&apos;t
            rely on it to decide whether a fish is legal to keep, protected, or safe to handle or eat.
          </li>
          <li>
            <strong>Eating fish.</strong> Whether fish from a water are safe to eat depends on local fish consumption
            advisories. Check your state&apos;s advisories before you eat your catch.
          </li>
          <li>
            <strong>Gear.</strong> Gear named in the guides is an example, not an endorsement. FishEye doesn&apos;t sell
            gear; use it as its maker says. If a link ever earns FishEye a commission, we will say so next to it.
          </li>
          <li>
            <strong>No professional advice.</strong> Nothing on FishEye is legal, medical, safety or other professional
            advice.
          </li>
        </ul>
      </section>

      <section id="ai-answers">
        <Heading id="ai-answers" />
        <p>
          Ask can give you an answer written by an AI model. It is an AI, not a person, and FishEye labels it as one.
        </p>
        <ul>
          <li>
            It answers from FishEye&apos;s guides where they cover your question, and from the model&apos;s own general
            knowledge where they don&apos;t. That knowledge isn&apos;t checked by FishEye. An answer can be wrong,
            incomplete, out of date, or wrong for your water, state or season, and the AI can&apos;t see the conditions
            where you are.
          </li>
          <li className="legal-conspicuous">
            You use AI answers at your own risk. Don&apos;t rely on one for anything that affects your safety, your
            health or the law, and use your own judgment about whether its advice is safe and suits your skill. For
            rules, licenses and limits, go to your state&apos;s fish and wildlife agency.
          </li>
          <li>
            If you are under 18, use AI answers with your parent&apos;s or guardian&apos;s involvement.
          </li>
          <li>
            Ask the AI about fishing. Don&apos;t use it to make harmful, illegal or offensive content, to get around its
            limits, or to collect answers in bulk.
          </li>
          <li>
            To write an answer, your question and the guide passages that match it are sent to our AI provider,
            Anthropic. Don&apos;t put personal information, yours or anyone else&apos;s, in a question. See the{" "}
            <Link href="/privacy">privacy policy</Link>.
          </li>
          <li>
            A free account gets a set number of AI answers a day, shown next to the button. FishEye Plus has no daily
            limit for personal use; we may slow or pause AI answers on an account whose use looks automated or abusive.
          </li>
          <li>
            AI answers may be unavailable at times, for example when our provider is down or when FishEye pauses them.
            We may change, limit or stop AI answers at any time.
          </li>
          <li>
            You may use the answers you get for your own fishing. If you share one, check it first and say it came from
            an AI. Someone else asking the same question may get the same or a similar answer.
          </li>
        </ul>
      </section>

      <section id="plus">
        <Heading id="plus" />
        <p>
          FishEye Plus is a membership. What it includes is described where you get it; today it removes the daily
          limit on AI answers. FishEye may also give Plus free to some accounts.
        </p>
        <ul>
          <li>
            <strong>Before you pay</strong>, you&apos;ll see the price, how often you&apos;ll be charged, that it renews
            automatically, and how to cancel. By buying, you authorize that charge and each renewal until you cancel.
          </li>
          <li>
            <strong>Renewal.</strong> Plus renews automatically at the end of each period, at the price then in effect,
            until you cancel. Before a yearly membership renews, we&apos;ll remind you of the price and how to cancel.
          </li>
          <li>
            <strong>Cancelling.</strong> You can cancel any time: in your Apple or Google account settings if you bought
            Plus in the app (deleting the app doesn&apos;t cancel it), or on your <Link href="/account">account page</Link>{" "}
            if you bought it on the website. Cancelling stops the next renewal; you keep Plus until the end of the period
            you paid for.
          </li>
          <li>
            <strong>Free trials.</strong> If you start a free trial, it becomes a paid membership when the trial ends
            unless you cancel before then. We&apos;ll tell you the date when you start it.
          </li>
          <li>
            <strong>Price changes.</strong> We may change the price of Plus. We&apos;ll tell you before a new price
            applies to you, with time to cancel first.
          </li>
          <li>
            <strong>Refunds.</strong> Payments are not refunded, and part periods are not refunded, except where the law
            requires it or we say otherwise. Purchases through Apple or Google are refunded only under their policies;
            ask them.
          </li>
          <li>
            <strong>If we stop offering Plus</strong>, or close your account when you haven&apos;t broken these terms,
            we&apos;ll refund the unused part of the period you paid for.
          </li>
          <li>
            <strong>Free Plus</strong> lasts for the time stated, has no cash value, and can&apos;t be transferred.
          </li>
          <li>Prices may not include taxes. You pay any taxes that apply.</li>
        </ul>
      </section>

      <section id="your-content">
        <Heading id="your-content" />
        <p>
          You keep ownership of the catches, photos, notes and comments you post. So that FishEye can run, you give
          FishEye a worldwide, non-exclusive, royalty-free license to store, copy (for example as smaller versions of a
          photo or in backups), and display them in FishEye: to everyone for a public catch or comment, and only to you
          (and moderators) for a private one. The license ends when you delete the content or your account, apart from
          copies in backups that are replaced over time.
        </p>
        <ul>
          <li>
            You&apos;re responsible for what you post. Only post photos you took or have permission to use, and
            don&apos;t post photos of other people without their OK, or anyone&apos;s personal information.
          </li>
          <li>
            When you post a catch, you choose who sees it and how exact its spot is. A photo can still give a place
            away, so think before you post. Don&apos;t post a spot that sends people onto private land.
          </li>
          <li>
            We don&apos;t check content before it appears, and we don&apos;t endorse what other anglers post. Their
            catches and comments are theirs, and may be wrong. We don&apos;t check who other anglers are, either: use
            common sense before you meet anyone you know only from FishEye.
          </li>
          <li>
            If you send us ideas or feedback, we may use them freely, without paying you or owing you anything.
          </li>
        </ul>
      </section>

      <section id="rules">
        <Heading id="rules" />
        <p>Don&apos;t use FishEye to:</p>
        <ul>
          <li>
            break the law, including fishing, wildlife, boating and trespass laws, or show yourself or encourage others
            doing so;
          </li>
          <li>harass, threaten, stalk or impersonate anyone, or post someone else&apos;s personal information;</li>
          <li>
            use slurs, or attack people for their race, ethnicity, nationality, religion, sex, sexual orientation, gender
            identity, age or disability (names and catches with slurs aren&apos;t accepted);
          </li>
          <li>
            post spam, advertising, sexual content, gratuitous violence or gore, or anything you don&apos;t have the right
            to post. Anything that sexualizes a minor is removed and reported to the authorities;
          </li>
          <li>pin a place to mislead people, or point people onto private land without permission;</li>
          <li>
            collect data from FishEye with bots or scrapers, copy its guides or data in bulk, use them to train AI
            models, or build a competing service with them;
          </li>
          <li>
            create extra accounts, share or sell an account, or get around FishEye&apos;s limits, bans or security;
          </li>
          <li>
            probe, break or overload FishEye&apos;s systems, upload malware, or reverse engineer FishEye except where the
            law allows it;
          </li>
          <li>try to make the AI produce harmful content or ignore its instructions.</li>
        </ul>
      </section>

      <section id="moderation">
        <Heading id="moderation" />
        <ul>
          <li>
            Anyone with an account can report a public catch or comment. Moderators may hide or remove content, limit
            features, or suspend or close accounts that break these terms, when the law requires it, or to protect
            people or FishEye. We usually say why, unless the law or someone&apos;s safety stops us. If you think we got
            it wrong, write to us.
          </li>
          <li>
            You can delete your account at any time from your <Link href="/account">account page</Link>. Deleting your
            account doesn&apos;t cancel Plus bought through Apple or Google; cancel it there.
          </li>
          <li>
            Sections {sec("your-content")} (the license for what you&apos;ve shared, until it is deleted) and{" "}
            {sec("our-content")} to {sec("general")} still apply after your account is closed.
          </li>
        </ul>
      </section>

      <section id="our-content">
        <Heading id="our-content" />
        <p>
          FishEye&apos;s guides, text, design, code, name and logo, and the way its data is put together, belong to
          FishEye or the people who license them to us. We give you a personal, non-commercial, non-transferable license
          to use FishEye under these terms, which ends if you break them. Share links freely, and quote a little with
          credit; don&apos;t copy the guides or data in bulk, sell them, or present them as your own.
        </p>
      </section>

      <section id="third-parties">
        <Heading id="third-parties" />
        <ul>
          <li>
            FishEye uses public data from government agencies and open projects, each credited where it appears, and on
            the <Link href="/sources">sources</Link> page. Map data is © OpenStreetMap contributors; maps are from
            MapTiler; fish photos come from Wikimedia Commons under their own licenses. Their licenses and terms apply to
            that data.
          </li>
          <li>
            Links to agency websites and other sites are for your convenience. We don&apos;t control those sites and
            aren&apos;t responsible for them.
          </li>
          <li>
            Services you use with FishEye, such as Sign in with Google, Apple&apos;s App Store, Google Play and your
            mobile data plan, have their own terms. You must follow them when you use FishEye.
          </li>
        </ul>
      </section>

      <section id="copyright">
        <Heading id="copyright" />
        <p>
          To report content that infringes your copyright, or to answer a report about yours, see{" "}
          <Link href="/copyright">Copyright &amp; content</Link>. We close the accounts of people who repeatedly infringe.
        </p>
      </section>

      <section id="safety">
        <Heading id="safety" />
        <p>
          Fishing, boating, wading, ice fishing and getting to the water carry real risks, including drowning, cold
          water, hypothermia, falls, lightning, heat, hooks and knives, wildlife, and accidents on the road. FishEye
          can&apos;t see the conditions where you are.
        </p>
        <ul>
          <li>
            You alone decide whether, where, when and how to go, and you are responsible for your own safety and for
            anyone with you, especially children.
          </li>
          <li>
            Check the weather and water, tell someone your plan, wear a life jacket on a boat and near deep or fast
            water, and stay off ice you&apos;re not sure of.
          </li>
          <li>FishEye is not an emergency service. In an emergency, call 911.</li>
        </ul>
        <p className="legal-conspicuous">
          To the fullest extent the law allows, you take on all the risks of your fishing, boating, travel and other
          activities, including risks you can&apos;t foresee, and including any that come from relying on FishEye.
        </p>
      </section>

      <section id="disclaimers">
        <Heading id="disclaimers" />
        <p className="legal-conspicuous">
          FishEye is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;. To the fullest extent the law allows,
          FishEye makes no promises or warranties of any kind, express or implied, about FishEye or anything on it,
          including its information, maps, forecasts, AI answers, photo checks and other people&apos;s content. That
          includes any promise that they are accurate, complete, current, reliable, safe, available, uninterrupted or
          free of errors, and the implied warranties of merchantability, fitness for a particular purpose, title and
          non-infringement.
        </p>
        <p>Some places don&apos;t allow some of these exclusions. There, they apply as far as the law allows.</p>
      </section>

      <section id="liability">
        <Heading id="liability" />
        <p>
          In these terms, &ldquo;FishEye&apos;s people&rdquo; means FishEye, its operator, and the people who work on it
          or for it.
        </p>
        <div className="legal-conspicuous">
          <p>To the fullest extent the law allows:</p>
          <ul>
            <li>
              FishEye&apos;s people are not liable for indirect, incidental, special, consequential, exemplary or
              punitive damages, or for lost profits, data or goodwill, even if told they were possible;
            </li>
            <li>
              FishEye&apos;s people are not liable for anything that happens while you fish, boat or travel, or at a
              place you found on or through FishEye; for fines or penalties; or for decisions you make based on
              FishEye&apos;s information or AI answers;
            </li>
            <li>
              the total liability of FishEye&apos;s people for all claims about FishEye or these terms is limited to the
              greater of US${LEGAL.liabilityFloorUsd} or what you paid FishEye in the 12 months before the claim arose.
            </li>
          </ul>
          <p>
            These limits apply whatever the legal theory: contract, warranty, negligence, strict liability or anything
            else.
          </p>
        </div>
        <p>
          They don&apos;t limit liability for gross negligence, willful misconduct or fraud, or any liability the law
          doesn&apos;t allow to be limited. Some places don&apos;t allow these limits, so they may not all apply to you.
        </p>
      </section>

      <section id="release">
        <Heading id="release" />
        <p className="legal-conspicuous">
          To the fullest extent the law allows, you release FishEye&apos;s people from all claims, known or unknown, for
          injury, death, property damage or other loss arising from your fishing, boating, travel or other activities,
          from relying on information, maps, forecasts or AI answers on FishEye, or from your disputes with other
          anglers or anyone else (such as a landowner), including claims based on the negligence of FishEye&apos;s
          people, and you promise not to sue them over such claims. This release doesn&apos;t cover gross negligence or
          willful misconduct.
        </p>
        <p>
          If you live in California, you waive California Civil Code § 1542, which says: &ldquo;A general release does
          not extend to claims that the creditor or releasing party does not know or suspect to exist in his or her
          favor at the time of executing the release and that, if known by him or her, would have materially affected
          his or her settlement with the debtor or released party.&rdquo; You waive any similar law elsewhere too.
        </p>
      </section>

      <section id="indemnity">
        <Heading id="indemnity" />
        <p>
          To the extent the law allows, you will defend and compensate FishEye&apos;s people for claims by others, and
          the losses, costs and reasonable lawyers&apos; fees that come with them, arising from what you post, from your
          breaking these terms or the law, or from your fishing or other activities (for example, trespassing at a spot
          you pinned). We&apos;ll tell you about such a claim, may choose to handle its defense ourselves, and you&apos;ll
          help as reasonably needed.
        </p>
      </section>

      <section id="disputes">
        <Heading id="disputes" />
        <p className="legal-conspicuous">
          Please read this section carefully. It affects your rights, including your right to go to court.
        </p>
        <p>
          <strong>Talk to us first.</strong> Most problems can be solved by talking. Before starting an arbitration or a
          court case, send a notice to <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a> with the
          subject &ldquo;Dispute&rdquo;, giving your name, your account email, what happened and what you want. We will
          send ours to your account email. Both sides then try in good faith to settle it for 60 days, and any time limit
          for the claim pauses meanwhile.
        </p>
        <p>
          <strong>Arbitration.</strong> If it isn&apos;t settled, you and FishEye agree that any dispute or claim
          arising from or relating to these terms or FishEye (a &ldquo;claim&rdquo;) will be decided by binding
          arbitration with a single arbitrator, on an individual basis, and not in court, except that:
        </p>
        <ul>
          <li>either side may bring an individual claim in small-claims court, if it qualifies;</li>
          <li>either side may ask a court to stop the infringement or misuse of its intellectual property;</li>
          <li>this paragraph doesn&apos;t apply if you opt out, as described below.</li>
        </ul>
        <p>
          The Federal Arbitration Act governs this section. The American Arbitration Association (AAA) runs the
          arbitration under its Consumer Arbitration Rules, and its rules for mass arbitrations where they apply (see
          adr.org). The arbitrator can award you the same individual relief a court could. For a claim you bring,
          FishEye pays the AAA&apos;s filing, administration and arbitrator fees beyond what it would cost you to file in
          court, unless the arbitrator finds your claim frivolous. Any hearing is by video or phone, or in person in
          the county where you live if you prefer.
        </p>
        <p className="legal-conspicuous">
          No class actions. You and FishEye may bring claims against each other only individually, and not as a
          plaintiff or member of any class, collective, consolidated or representative proceeding. If this sentence is
          found unenforceable for a claim, that claim goes to court instead of arbitration. If the law doesn&apos;t
          allow a request for public injunctive relief to be arbitrated, that request goes to court after the
          individual arbitration ends. If a claim goes to court, you and FishEye each give up a jury trial, to the extent
          the law allows.
        </p>
        <p>
          <strong>Opting out.</strong> You can opt out of arbitration within {optOut} days of first accepting these
          terms: email <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a> with the subject
          &ldquo;Arbitration opt-out&rdquo;, your name and your account email. Opting out changes nothing else in these
          terms.
        </p>
        <p>
          <strong>Changes to this section.</strong> A change to this section doesn&apos;t apply to a claim either side
          has already given notice of. If we make a change that matters, you may reject it within 30 days by emailing
          us, and the earlier version keeps applying to you.
        </p>
        <p>
          <strong>Time limit.</strong> To the extent the law allows, a claim must be started within two years after it
          arose, or it can&apos;t be brought.
        </p>
        <p>
          <strong>Law and courts.</strong> These terms are governed by the laws of the State of {LEGAL.governingState},
          without regard to conflict-of-law rules, and by the Federal Arbitration Act for this section. A claim that
          isn&apos;t arbitrated goes to the state or federal courts located in {LEGAL.governingState}, and you and FishEye
          agree to their jurisdiction, unless the law where you live gives you the right to bring it there.
        </p>
      </section>

      <section id="changes">
        <Heading id="changes" />
        <ul>
          <li>
            We may change FishEye, add or remove features, or stop offering it. If we stop offering something you paid
            for, Section {sec("plus")} says what you get back.
          </li>
          <li>
            We may change these terms. We update the date at the top, and for a change that matters we tell you on the
            site or by email at least {LEGAL.noticeDays} days before it applies, unless the law requires a change sooner
            or it is about a new feature. If you keep using FishEye after a change applies, you accept it. If you
            don&apos;t, stop using FishEye and delete your account.
          </li>
          <li>Features marked new or test may have more mistakes than the rest, and may change or go away.</li>
        </ul>
      </section>

      <section id="app-stores">
        <Heading id="app-stores" />
        <p>If you got the FishEye app from Apple&apos;s App Store:</p>
        <ul>
          <li>
            These terms are between you and FishEye only, not Apple. FishEye, not Apple, is responsible for the app and
            its content.
          </li>
          <li>
            Your license to the app is non-transferable and limited to use on Apple-branded products you own or control,
            as allowed by the Usage Rules in Apple&apos;s Media Services Terms and Conditions (including Family Sharing).
            Where these terms conflict with those Usage Rules, the Usage Rules apply to the app.
          </li>
          <li>FishEye, not Apple, provides any maintenance and support for the app. Apple has no obligation to.</li>
          <li>
            If the app fails to meet any warranty that applies, you may tell Apple, and Apple will refund the
            app&apos;s purchase price, if any. To the extent the law allows, Apple has no other warranty obligation for
            the app, and any other claims, losses or costs from such a failure are FishEye&apos;s responsibility, to the
            extent not disclaimed in these terms.
          </li>
          <li>
            FishEye, not Apple, is responsible for any claims about the app or your use of it, including product
            liability claims, claims that it fails to meet a legal or regulatory requirement, and claims under consumer
            protection, privacy or similar laws.
          </li>
          <li>
            If anyone claims the app or your use of it infringes their intellectual property, FishEye, not Apple, is
            responsible for investigating, defending, settling and discharging the claim.
          </li>
          <li>
            Apple and its subsidiaries are third-party beneficiaries of these terms. Once you accept them, Apple may
            enforce them against you.
          </li>
        </ul>
        <p>
          If you got the app from Google Play, Google&apos;s terms govern your purchase, and Google isn&apos;t responsible
          for the app.
        </p>
      </section>

      <section id="general">
        <Heading id="general" />
        <ul>
          <li>
            These terms, the privacy policy, the copyright page and any terms shown for a particular feature are the whole
            agreement between you and FishEye about FishEye.
          </li>
          <li>
            If a part of these terms can&apos;t be enforced, it is changed as little as needed to make it enforceable, and
            the rest still applies. If we don&apos;t enforce a part, we haven&apos;t given it up.
          </li>
          <li>
            You can&apos;t transfer these terms or your account. We may transfer them, for example to a company that
            takes over running FishEye, or in a merger or sale.
          </li>
          <li>We aren&apos;t responsible for delays or failures caused by events beyond our reasonable control.</li>
          <li>
            These terms don&apos;t make you and FishEye partners, employer and employee, or agents of each other. No one
            else may enforce them, except FishEye&apos;s people (Sections {sec("liability")} to {sec("indemnity")}) and
            Apple (Section {sec("app-stores")}).
          </li>
          <li>
            We may send you notices by email to your account address or on FishEye, and you agree that electronic notices
            and agreements count as written ones. You may send notices to the contact details below.
          </li>
          <li>
            These terms are written in English. Any translation is for convenience; the English version is the one that
            applies. &ldquo;Including&rdquo; means &ldquo;including without limitation&rdquo;.
          </li>
          <li>
            California residents: the Complaint Assistance Unit of the Division of Consumer Services of the California
            Department of Consumer Affairs can be contacted in writing at 1625 North Market Blvd., Suite N 112,
            Sacramento, CA 95834, or by phone at (800) 952-5210.
          </li>
        </ul>
      </section>

      <section id="contact">
        <Heading id="contact" />
        <p>
          {LEGAL.operator}
          <br />
          {LEGAL.mailingAddress}
          <br />
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
        </p>
        <p>Questions, complaints and claims about FishEye or the app go to this address.</p>
      </section>
    </LegalPage>
  );
}
