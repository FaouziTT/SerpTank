import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage, OperatorNotice, operatorName } from "@/features/marketing/legal";
import { operator } from "@/features/marketing/site";

export const metadata: Metadata = {
  title: "Data processing terms",
  alternates: { canonical: "/dpa" },
};

export default function DpaPage() {
  const op = operator();
  return (
    <LegalPage title="Data processing terms" updated="25 September 2026">
      <OperatorNotice op={op} />
      <p>
        When your organization&apos;s data includes personal data (for example team members or data
        from connected services), {operatorName(op)} processes it on your behalf as a processor
        under these terms (GDPR Art. 28).
      </p>
      <h2>Our commitments</h2>
      <ul>
        <li>
          We process personal data only to provide SerpTank, following your documented instructions.
        </li>
        <li>People with access are bound by confidentiality.</li>
        <li>
          We apply the security measures described on our{" "}
          <Link href="/security">Security page</Link>.
        </li>
        <li>
          We use only the <Link href="/subprocessors">listed subprocessors</Link>, bound by
          equivalent obligations, and we notify you of changes.
        </li>
        <li>We help you respond to data-subject requests. Export and deletion are self-serve.</li>
        <li>We notify you of a personal data breach without undue delay.</li>
        <li>
          At the end of the service we delete your data after the 30-day grace period, unless the
          law requires otherwise.
        </li>
      </ul>
      <p>
        For a countersigned copy, contact{" "}
        {op.privacyEmail ? (
          <a href={`mailto:${op.privacyEmail}`}>{op.privacyEmail}</a>
        ) : (
          "the operator"
        )}
        .
      </p>
    </LegalPage>
  );
}
