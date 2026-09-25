import type { Metadata } from "next";

import { LegalPage } from "@/features/marketing/legal";
import { operator } from "@/features/marketing/site";

export const metadata: Metadata = { title: "Security", alternates: { canonical: "/security" } };

export default function SecurityPage() {
  const op = operator();
  return (
    <LegalPage title="Security" updated="25 September 2026">
      <p>
        How SerpTank protects your account and data. Everything below is how the product works
        today.
      </p>
      <h2>Accounts</h2>
      <ul>
        <li>Passwords are hashed with Argon2id and checked against known-breached passwords.</li>
        <li>
          Two-factor authentication with authenticator apps or passkeys, which organizations can
          require.
        </li>
        <li>
          Sensitive actions such as role changes, billing, deletion and data export ask you to
          confirm your identity again.
        </li>
        <li>
          Browser sessions use secure, HttpOnly cookies. No tokens are stored in the browser. Every
          change is CSRF-protected.
        </li>
      </ul>
      <h2>Your data</h2>
      <ul>
        <li>
          Every organization&apos;s data is isolated in the application and again by database
          row-level security.
        </li>
        <li>
          Integration tokens and secrets are encrypted with AES-256-GCM and a rotating key ring.
        </li>
        <li>Download links are signed and expire after 15 minutes.</li>
        <li>
          An audit log records sign-ins, role changes, integrations, exports and billing changes.
        </li>
      </ul>
      <h2>Infrastructure</h2>
      <ul>
        <li>
          TLS everywhere, strict Content-Security-Policy, and no internal services exposed to the
          internet.
        </li>
        <li>
          Every outbound request, including our crawler, the JavaScript renderer and webhooks, goes
          through a client that blocks internal and private addresses.
        </li>
        <li>Dependencies are locked and audited, and containers run unprivileged.</li>
      </ul>
      <h2>Reporting a vulnerability</h2>
      <p>
        {op.securityEmail ? (
          <>
            Please email <a href={`mailto:${op.securityEmail}`}>{op.securityEmail}</a>. See also{" "}
            <a href="/.well-known/security.txt">security.txt</a>.
          </>
        ) : (
          "A security contact hasn't been published for this deployment yet."
        )}
      </p>
    </LegalPage>
  );
}
