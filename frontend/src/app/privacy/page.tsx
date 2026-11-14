import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage } from "@/components/legal/LegalPage";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Privacy policy · FishEye",
  description: "What FishEye collects, why, who else sees it, and how to delete it.",
  alternates: { canonical: "/privacy" },
};

// What this says must stay true of the code: the account and pin models
// (backend app/models/community.py), photo cleaning (services/media.py),
// where others see a catch (docs/adr/0038), the AI summaries (services/rag),
// signed-out feedback (services/feedback.py), the visit count (services/visits.py),
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
        <p>
          You can use the map, the fish guides, Ask, photo ID (a few photos a day) and feedback without an account.
          What we keep:
        </p>
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
            <strong>Reports and moderation:</strong> reports you file about a catch or a comment, and a log of what moderators do.
          </li>
          <li>
            <strong>AI answers and Plus:</strong> how many AI answers you use each day, so the daily allowance works,
            and whether your account has FishEye Plus and until when. The daily count is kept under a one-way code made from your email address, not the address itself.
          </li>
          <li>
            <strong>Likes and comments:</strong> which catches you liked, and the comments you wrote. Comments and how many
            likes a catch has are public. Your name also appears on leaderboards for the public catches you share, unless you
            turn that off on your account page.
          </li>
          <li>
            <strong>Catch alerts, if you set any:</strong> the fish, the place (rounded to about a kilometre), the distance and
            your language, so we can email you. Every email has an unsubscribe link, and alerts are deleted with your account.
          </li>
          <li>
            <strong>Feedback you send:</strong> your message, the page you were on and your language. Signed in, it is
            kept with your account so we can reply; if you delete your account we keep the message without saying who
            sent it. Signed out, it is kept with no account, and with an email address only if you leave one for a
            reply.
          </li>
          <li>
            <strong>Questions Ask couldn&apos;t answer:</strong> the question, its language and the state or fish you
            picked, so we know which guides to write next. We don&apos;t record who asked, we take out email addresses,
            phone numbers and links first, and we delete them after 90 days.
          </li>
          <li>
            <strong>Visit counts:</strong> how many times each page was opened each day, and the website a link to us
            was on (its name only, such as reddit.com) or a tag in the link (such as ?ref=reddit). That is all: no IP
            address, no cookie or other identifier, nothing that tells one visitor from another or follows anyone
            between pages. We use it to see whether anyone is finding FishEye, and from where.
          </li>
          <li>
            <strong>Server logs:</strong> like most websites, our server records each request (IP address, page, time,
            browser) to keep the site running and secure. We keep these only as long as needed for that. To stop abuse,
            the server also counts requests per IP address in its memory (for example, the free photo checks a day
            without an account); those counts aren&apos;t written down and are gone within a day.
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
          <li>
            Identify a fish or a piece of fishing gear from a photo, and check that a catch photo shows the fish you
            named. This runs on our own server; your photos aren&apos;t sent to another company for it, and a photo
            checked on its own isn&apos;t kept.
          </li>
          <li>Keep FishEye safe: limit spam and abuse, act on reports, and keep the service working.</li>
          <li>Answer you when you write to us.</li>
        </ul>
        <p>
          We don&apos;t sell or rent personal information, we don&apos;t share it for advertising, and FishEye has no
          ads, no tracking cookies and no outside analytics service. The visit counts above are our own and say nothing
          about who visited.
        </p>
      </section>

      <section>
        <h2>Who else handles it</h2>
        <ul>
          <li>
            <strong>Amazon Web Services</strong> hosts FishEye&apos;s servers and database, in the United States.
          </li>
          <li>
            <strong>Anthropic</strong>, when you ask the AI in Ask: your question, and the guide passages that match it,
            are sent to Anthropic&apos;s AI model to write the answer. Your account details are not. Please don&apos;t put
            personal information in a question.
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
          for fishing rules. Counting visits uses no cookie and stores nothing in your browser. Nothing is used for
          advertising or tracking.
        </p>
      </section>

      <section>
        <h2>Your choices</h2>
        <ul>
          <li>Edit or delete any catch, make it private, or change who sees its exact spot.</li>
          <li>
            Delete your account from your <Link href="/account">account page</Link>. That deletes your account, your
            sessions and your catches with their photos. Reports you filed stay, without your name, so a moderator can
            finish reviewing them. The count of AI answers you used stays for up to 30 days under its one-way code, so deleting an account and making it again doesn&apos;t reset the free answers.
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
          Until you delete it or your account. Daily counts of AI answers are deleted after 30 days. Backups of the database may keep a copy for a short time before they
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
          FishEye accounts are for people aged {LEGAL.minimumAge} and older, and anyone under 18 needs a parent&apos;s
          permission. Anyone can browse the map and guides without an account. In line with the Children&apos;s Online
          Privacy Protection Act (COPPA), we don&apos;t knowingly collect personal information from children under{" "}
          {LEGAL.minimumAge}. If we learn that a child under {LEGAL.minimumAge} created an account, we delete it; a
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
