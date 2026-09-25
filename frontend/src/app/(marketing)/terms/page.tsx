import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage, OperatorNotice, operatorName } from "@/features/marketing/legal";
import { operator } from "@/features/marketing/site";

export const metadata: Metadata = {
  title: "Terms of service",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  const op = operator();
  return (
    <LegalPage title="Terms of service" updated="25 September 2026">
      <OperatorNotice op={op} />
      <p>
        These terms are an agreement between you (or the organization you represent) and{" "}
        {operatorName(op)} for use of SerpTank.
      </p>
      <h2>Your account</h2>
      <p>
        Keep your credentials safe and tell us about unauthorised use. Organization owners control
        who has access to their organization and its data.
      </p>
      <h2>Acceptable use</h2>
      <ul>
        <li>
          Only audit, submit for indexing, or connect sites you own or are authorised to manage.
        </li>
        <li>
          Don&apos;t use SerpTank to attack, overload or scrape systems in breach of their terms.
        </li>
        <li>Don&apos;t attempt to bypass plan limits, rate limits or security controls.</li>
      </ul>
      <p>Our crawler identifies itself as SerpTankBot and follows robots.txt.</p>
      <h2>Plans and payment</h2>
      <p>
        Paid plans renew until cancelled. Payments are handled by Stripe. If a payment fails, paid
        features stay on during a grace period and then revert to the free plan. Your historical
        data is kept.
      </p>
      <h2>Data and third-party sources</h2>
      <p>
        You own your data. Search data, AI answers and third-party metrics are observations at a
        point in time and can change. We show where each figure comes from and don&apos;t guarantee
        rankings or traffic. Our <Link href="/privacy">privacy policy</Link> and{" "}
        <Link href="/dpa">data processing terms</Link> apply.
      </p>
      <h2>Termination</h2>
      <p>
        You can delete your organization or account at any time. We may suspend accounts that breach
        these terms, and will tell you why unless the law prevents it.
      </p>
      <h2>Liability</h2>
      <p>
        The service is provided as described. To the extent the law allows, our liability is limited
        to the fees you paid in the 12 months before the claim.
      </p>
      {op.jurisdiction ? <p>Governing law: {op.jurisdiction}.</p> : null}
    </LegalPage>
  );
}
