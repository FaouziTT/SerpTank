import type { Metadata } from "next";
import Link from "next/link";

import { LegalPage, OperatorNotice, operatorName } from "@/features/marketing/legal";
import { operator } from "@/features/marketing/site";

export const metadata: Metadata = {
  title: "Privacy policy",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  const op = operator();
  return (
    <LegalPage title="Privacy policy" updated="25 September 2026">
      <OperatorNotice op={op} />
      <p>
        This policy explains what personal data {operatorName(op)}
        {op.address ? ` (${op.address})` : ""} processes when you use SerpTank, why, and your
        rights. For questions or requests, contact{" "}
        {op.privacyEmail ? (
          <a href={`mailto:${op.privacyEmail}`}>{op.privacyEmail}</a>
        ) : (
          "the operator"
        )}
        .
      </p>
      <h2>What we collect</h2>
      <ul>
        <li>
          Account data: your name, email address, password hash (never the password), and, if you
          enable them, two-factor secrets (encrypted) and passkey public keys.
        </li>
        <li>
          Security data: sign-in times, IP address and browser for active sessions and the security
          log.
        </li>
        <li>
          Organization data you add: projects, domains, keywords, competitors, prompts and settings.
        </li>
        <li>
          Data from services you connect (for example Google Search Console, Google Analytics, Bing
          Webmaster Tools). Access tokens are stored encrypted and used only to sync your data.
        </li>
        <li>
          Billing data: handled by Stripe. We store your plan and subscription status, not card
          details.
        </li>
        <li>
          Public web data: pages we crawl for audits (we keep extracted facts, not full pages) and
          public search results.
        </li>
      </ul>
      <h2>Why we use it (legal bases)</h2>
      <ul>
        <li>To provide the service you signed up for (contract).</li>
        <li>
          To keep accounts and the platform secure, prevent abuse and keep audit logs (legitimate
          interests).
        </li>
        <li>
          To bill paid plans and meet tax and accounting obligations (contract; legal obligation).
        </li>
        <li>
          To send service emails such as verification, security alerts and alerts you turn on
          (contract; legitimate interests). We don&apos;t send marketing email without consent.
        </li>
      </ul>
      <h2>Cookies</h2>
      <p>
        We use only strictly necessary cookies: a session cookie that keeps you signed in and
        short-lived security cookies for sign-in and CSRF protection. There are no analytics or
        advertising cookies, so no cookie banner is needed.
      </p>
      <h2>Sharing</h2>
      <p>
        We share data only with the <Link href="/subprocessors">subprocessors</Link> that run the
        service, only for the purposes listed there. We don&apos;t sell personal data.
      </p>
      <h2>Retention</h2>
      <ul>
        <li>Your account data is kept while your account exists.</li>
        <li>Deleted organizations are removed after a 30-day grace period.</li>
        <li>
          When you delete your account, your profile is anonymised immediately and removed after 30
          days.
        </li>
        <li>CSV exports are kept for 24 hours.</li>
        <li>Billing records are kept as long as tax law requires.</li>
      </ul>
      <h2>Your rights</h2>
      <p>
        You can access, correct, export and delete your data. Download a copy of your data or delete
        your account under <Link href="/settings/security">Account security</Link>. You can also
        object to or restrict processing, and complain to your data protection authority.
      </p>
      <h2>Security</h2>
      <p>
        See <Link href="/security">Security</Link> for how we protect data.
      </p>
      {op.jurisdiction ? <p>Governing law: {op.jurisdiction}.</p> : null}
    </LegalPage>
  );
}
