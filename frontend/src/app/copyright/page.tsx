import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage } from "@/components/legal/LegalPage";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Copyright & content · FishEye",
  description: "How to report a catch that breaks the rules, or content that infringes your copyright.",
};

// The notice and counter-notice follow the US Digital Millennium Copyright
// Act (17 U.S.C. § 512). Its safe harbour also needs an agent registered
// with the US Copyright Office; until then, notices go to the contact email.
export default function CopyrightPage() {
  return (
    <LegalPage
      title="Copyright & content"
      lede="How to tell us about a catch that breaks the rules, or a photo or text posted without the owner's permission."
    >
      <section>
        <h2>A catch that breaks the rules</h2>
        <p>
          Open the catch and use <strong>Report</strong>. Pick the reason (spam, an inappropriate photo, a wrong
          location, private property, something unsafe or illegal) and add a note. A catch that several people report
          is hidden until a moderator looks at it. You need an account to report, so one person can&apos;t hide a catch
          on their own.
        </p>
        <p>
          Something else, such as your personal information posted by someone else, or a catch pointing people onto
          your land: write to <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a> with the link.
        </p>
      </section>

      <section>
        <h2>Copyright notices</h2>
        <p>
          If something on FishEye uses your copyrighted work without permission, send a notice to{" "}
          <a href={`mailto:${LEGAL.contactEmail}?subject=${encodeURIComponent("Copyright notice")}`}>{LEGAL.contactEmail}</a>{" "}
          with the subject &ldquo;Copyright notice&rdquo; and:
        </p>
        <ol>
          <li>the work you say is infringed;</li>
          <li>the link to the catch or page on FishEye that uses it;</li>
          <li>your name, postal address, phone number and email address;</li>
          <li>a statement that you believe in good faith the use isn&apos;t authorised by you, your agent or the law;</li>
          <li>
            a statement that the information in your notice is accurate and, under penalty of perjury, that you own the
            copyright or may act for its owner;
          </li>
          <li>your physical or electronic signature (typing your full name is enough).</li>
        </ol>
        <p>
          We take the content down, tell the person who posted it, and give them a copy of the notice. Knowingly false
          claims can make the person who sends them liable for damages.
        </p>
      </section>

      <section>
        <h2>If your catch was taken down</h2>
        <p>
          If you believe it was removed by mistake, or you have the right to post it, send a counter-notice to the same
          address with: the link to what was removed; a statement, under penalty of perjury, that you believe in good
          faith it was removed by mistake or misidentification; your name, address and phone number; your consent to
          the jurisdiction of the federal court for your address (or, outside the US, any court where FishEye may be
          found), and to accept service from the person who sent the notice; and your signature. Unless the person who
          complained tells us within 10 business days that they have gone to court, we may put the content back.
        </p>
      </section>

      <section>
        <h2>Repeat infringers</h2>
        <p>
          We close the accounts of people who repeatedly post content that infringes others&apos; copyright. See also the{" "}
          <Link href="/terms">terms of use</Link>.
        </p>
      </section>
    </LegalPage>
  );
}
