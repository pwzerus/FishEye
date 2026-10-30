import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage } from "@/components/legal/LegalPage";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Privacy policy · FishEye",
  description: "What FishEye collects, why, who else sees it, and how to delete it.",
};

// What this says must stay true of the code: the account and pin models
// (backend app/models/community.py), photo cleaning (services/media.py),
// where others see a catch (docs/adr/0038), the AI summaries (services/rag),
// and the hosts the browser talks to (lib/map/tiles.ts, the fish photos).
export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy policy"
      lede="FishEye collects what it needs to run your account and show your catches. We don't sell your data, we don't show ads, and we never hand out your fishing spots."
    >
      <section>
        <h2>Who we are</h2>
        <p>
          FishEye ({LEGAL.site}) is run by {LEGAL.operator}, in the United States. Questions about this policy or your
          data go to <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>.
        </p>
      </section>

      <section>
        <h2>What we collect</h2>
        <p>You can use the map, the fish guides and Ask without an account. When you create one, or share a catch, we keep:</p>
        <ul>
          <li>
            <strong>Your account:</strong> your email address and display name, and your password stored only as a
            scrypt hash we can&apos;t read back. If you sign in with Google, Google tells us your email address and an
            account ID; we never see your Google password. We record when you joined and last signed in.
          </li>
          <li>
            <strong>Your sign-in sessions:</strong> a cookie holds a random token (we keep only a hash of it), with when
            the session was last used and your browser&apos;s name and version.
          </li>
          <li>
            <strong>Catches you share:</strong> where you dropped the pin, its title, notes, fish, date and photos. We
            re-save every photo and strip its hidden data, including the GPS position and camera details, before
            storing it.
          </li>
          <li>
            <strong>Reports and moderation:</strong> reports you file about a catch, and a log of what moderators do.
          </li>
          <li>
            <strong>AI summaries:</strong> how many you use each day, so the daily allowance works.
          </li>
          <li>
            <strong>Server logs:</strong> like most websites, our server records each request (IP address, page, time,
            browser) to keep the site running and secure. We keep these only as long as needed for that.
          </li>
        </ul>
      </section>

      <section>
        <h2>Your fishing spots</h2>
        <p>
          A catch you keep <strong>private</strong> is seen by you and, when a report or a problem needs it, our
          moderators. A <strong>public</strong> catch is seen by everyone, but by default only at its lake (or, away
          from lakes, its county): the exact spot stays with you and the moderators unless you choose &ldquo;Show other
          anglers the exact spot&rdquo;. You can change that, or make a catch private, at any time.
        </p>
      </section>

      <section>
        <h2>What we do with it</h2>
        <ul>
          <li>Run your account and show your catches to you and, if you made them public, to others.</li>
          <li>Check that a catch photo shows the fish you named. This runs on our own server; your photos aren&apos;t sent to another company for it.</li>
          <li>Keep FishEye safe: limit spam and abuse, act on reports, and keep the service working.</li>
          <li>Answer you when you write to us.</li>
        </ul>
        <p>
          We don&apos;t sell or rent personal information, we don&apos;t share it for advertising, and FishEye has no
          ads, analytics or tracking cookies.
        </p>
      </section>

      <section>
        <h2>Who else handles it</h2>
        <ul>
          <li>
            <strong>Amazon Web Services</strong> hosts FishEye&apos;s servers and database, in the United States.
          </li>
          <li>
            <strong>Anthropic</strong>, when you ask for an AI summary in Ask: your question and the guide passages it
            answers from are sent to Anthropic&apos;s AI model to write the summary. Your account details are not. Please
            don&apos;t put personal information in a question.
          </li>
          <li>
            <strong>Google</strong>, only if you use &ldquo;Sign in with Google&rdquo;.
          </li>
          <li>
            <strong>OpenStreetMap&apos;s Nominatim</strong> receives the text of a place you search for, from our server,
            not from your browser.
          </li>
          <li>
            Your browser loads <strong>map tiles from MapTiler</strong> (and OpenStreetMap, if MapTiler is unavailable)
            and <strong>fish photos from Wikimedia Commons</strong> directly. Like any website, they receive your IP
            address and browser details; their own privacy policies apply.
          </li>
          <li>Authorities, if the law requires it, or to protect someone&apos;s safety.</li>
        </ul>
        <p>
          When you use &ldquo;near me&rdquo;, your device&apos;s location is used in your browser; to open catches near you
          we look up your county on our server and don&apos;t store or log the position.
        </p>
      </section>

      <section>
        <h2>Cookies and browser storage</h2>
        <p>
          One cookie keeps you signed in. Your browser also stores a few preferences, such as the state you picked
          for fishing rules. Nothing is used for advertising or tracking.
        </p>
      </section>

      <section>
        <h2>Your choices</h2>
        <ul>
          <li>Edit or delete any catch, make it private, or change who sees its exact spot.</li>
          <li>
            Delete your account from your <Link href="/account">account page</Link>. That deletes your account, your
            sessions and your catches with their photos. Reports you filed stay, without your name, so a moderator can
            finish reviewing them.
          </li>
          <li>
            Ask us for a copy of your data, or to correct or delete it, at{" "}
            <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>. We answer within 30 days.
          </li>
        </ul>
      </section>

      <section>
        <h2>How long we keep it</h2>
        <p>
          Until you delete it or your account. Backups of the database may keep a copy for a short time before they
          are replaced.
        </p>
      </section>

      <section>
        <h2>Security</h2>
        <p>
          The site uses HTTPS, passwords and session tokens are stored only as hashes, and only FishEye&apos;s
          administrators can reach the servers. No system is perfectly secure; if something goes wrong that affects
          you, we will tell you.
        </p>
      </section>

      <section>
        <h2>Children</h2>
        <p>
          FishEye accounts are for people aged {LEGAL.minimumAge} and older. Anyone can browse the map and guides
          without an account. If we learn that a child under {LEGAL.minimumAge} created an account, we delete it; a
          parent can ask us to at <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>.
        </p>
      </section>

      <section>
        <h2>Changes</h2>
        <p>
          When we change this policy we update the date above, and for a change that matters we say so on the site
          before it applies.
        </p>
      </section>
    </LegalPage>
  );
}
