import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage } from "@/components/legal/LegalPage";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Terms of use · FishEye",
  description: "The rules for using FishEye and sharing catches on it.",
};

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of use"
      lede="FishEye helps you find water and learn to fish. These terms are the rules for using it and for sharing catches on it."
    >
      <section>
        <h2>Agreeing to these terms</h2>
        <p>
          FishEye ({LEGAL.site}) is run by {LEGAL.operator}. By using FishEye you agree to these terms and to
          our <Link href="/privacy">privacy policy</Link>. If you don&apos;t agree, please don&apos;t use FishEye.
        </p>
      </section>

      <section>
        <h2>Who can have an account</h2>
        <p>
          You must be {LEGAL.minimumAge} or older to create an account. If you are under 18, you need a parent&apos;s or
          guardian&apos;s permission. One account per person; keep your password to yourself. You&apos;re responsible
          for what happens on your account.
        </p>
      </section>

      <section>
        <h2>Fishing information is a guide, not the law</h2>
        <ul>
          <li>
            <strong>Check the official rules.</strong> Licenses, seasons, size and bag limits and bait rules change and
            differ by state and by water. FishEye&apos;s summaries and links can be out of date or incomplete. Your state
            fish and wildlife agency&apos;s current rules are what count.
          </li>
          <li>
            <strong>Access can be wrong.</strong> Lakes, entrances, public land and fish species come from public data
            and other people&apos;s reports, which can be wrong or out of date. Obey posted signs, don&apos;t trespass, and
            ask before you fish on private land.
          </li>
          <li>
            <strong>AI answers can be wrong.</strong> Ask&apos;s summaries are written by an AI model from FishEye&apos;s
            guides. Check anything that matters.
          </li>
          <li>
            <strong>Your safety is yours.</strong> Weather, water and ice conditions change fast. Wear a life jacket on
            a boat and follow local safety rules.
          </li>
        </ul>
      </section>

      <section>
        <h2>What you share</h2>
        <p>
          You keep ownership of the catches, photos and notes you post. So that FishEye can show them, you give
          FishEye a worldwide, non-exclusive, royalty-free license to store, copy (for example as smaller versions of a
          photo), and display them in the service: to everyone for a public catch, and only to you (and moderators)
          for a private one. The license ends when you delete the catch or your account, apart from copies in backups
          that are replaced over time.
        </p>
        <p>Only post photos you took or have permission to use, and don&apos;t post photos of other people without their OK.</p>
      </section>

      <section>
        <h2>Rules for catches and accounts</h2>
        <p>Don&apos;t use FishEye to:</p>
        <ul>
          <li>break the law, including fishing and wildlife laws, or show yourself doing so;</li>
          <li>harass, threaten or impersonate anyone, or post someone else&apos;s personal information;</li>
          <li>post spam, advertising, sexual or violent content, or anything you don&apos;t have the right to post;</li>
          <li>pin a place to mislead people, or point people onto private land without permission;</li>
          <li>collect data from FishEye with bots or scrapers, or get around its limits or security.</li>
        </ul>
        <p>
          Anyone can report a public catch. Moderators may hide or remove content and suspend or close accounts that
          break these rules. If you think we got it wrong, write to us.
        </p>
      </section>

      <section>
        <h2>Other people&apos;s data and content</h2>
        <p>
          FishEye uses public data from government agencies and open projects, each credited where it appears. Map
          data is © OpenStreetMap contributors; maps are from MapTiler. Their own licenses and terms apply to that
          data. To report content that infringes your copyright, see{" "}
          <Link href="/copyright">Copyright &amp; content</Link>.
        </p>
      </section>

      <section>
        <h2>FishEye is provided as it is</h2>
        <p>
          We work to keep FishEye accurate and running, but it is provided &ldquo;as is&rdquo; and &ldquo;as
          available&rdquo;, without warranties of any kind, to the extent the law allows. To the extent the law allows,
          FishEye and its operator are not liable for indirect or consequential losses, or for anything that happens
          while fishing or travelling to a place found on FishEye, and our total liability to you for any claim is
          limited to US$50. Some places don&apos;t allow these limits, so they may not all apply to you.
        </p>
      </section>

      <section>
        <h2>Ending or changing</h2>
        <p>
          You can stop using FishEye and delete your account at any time from your{" "}
          <Link href="/account">account page</Link>. We may change or stop parts of FishEye. When we change these terms
          we update the date above, and for a change that matters we say so on the site before it applies; using
          FishEye after that means you accept the new terms.
        </p>
      </section>

      <section>
        <h2>Law and disputes</h2>
        <p>
          These terms are governed by the laws of the State of {LEGAL.governingState} and of the United States. Any
          dispute goes to the state or federal courts located in {LEGAL.governingState}, unless the law where you live
          says otherwise.
        </p>
      </section>

      <section>
        <h2>Contact</h2>
        <p>
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
        </p>
      </section>
    </LegalPage>
  );
}
