import type { ReactNode } from "react";

import type { Operator } from "./site";

/** Shown when the deployment hasn't provided its legal operator details yet. */
export function OperatorNotice({ op }: { op: Operator }) {
  if (op.name && op.address && op.privacyEmail) return null;
  return (
    <p role="note" className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
      This deployment hasn&apos;t published its operator details yet (company name, address and
      privacy contact). Don&apos;t rely on this page until they appear.
    </p>
  );
}

export function operatorName(op: Operator): string {
  return op.name ?? "the operator of this SerpTank service";
}

export function LegalPage({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: ReactNode;
}) {
  return (
    <article className="mx-auto max-w-3xl space-y-6 px-6 py-12 text-sm leading-relaxed [&_h2]:mt-8 [&_h2]:text-lg [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc">
      <header>
        <h1 className="text-3xl font-semibold">{title}</h1>
        <p className="text-muted-foreground">Last updated {updated}</p>
      </header>
      {children}
    </article>
  );
}
