import type { Metadata } from "next";

import { LegalPage } from "@/features/marketing/legal";
import { publicConfig } from "@/features/marketing/site";

export const metadata: Metadata = {
  title: "Subprocessors",
  alternates: { canonical: "/subprocessors" },
};

export default async function SubprocessorsPage() {
  const config = await publicConfig();
  return (
    <LegalPage title="Subprocessors" updated="25 September 2026">
      <p>
        These are the third parties this SerpTank deployment is configured to use, generated from
        its live configuration. Hosting and database run on infrastructure operated for this
        deployment.
      </p>
      {!config ? (
        <p>The list is unavailable right now.</p>
      ) : config.subprocessors.length === 0 ? (
        <p>This deployment currently uses no third-party subprocessors.</p>
      ) : (
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="py-1">Provider</th>
              <th className="py-1">Purpose</th>
              <th className="py-1">Data</th>
            </tr>
          </thead>
          <tbody>
            {config.subprocessors.map((s) => (
              <tr key={s.name} className="border-t">
                <td className="py-1 pr-3 font-medium">{s.name}</td>
                <td className="py-1 pr-3">{s.purpose}</td>
                <td className="py-1">{s.data}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </LegalPage>
  );
}
