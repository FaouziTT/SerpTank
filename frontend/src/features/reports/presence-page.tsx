"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Printer } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { FormAlert } from "@/components/forms/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatRate, ENGINE_LABEL } from "@/features/ai-visibility/ai-page";
import type { EngineVisibility } from "@/features/ai-visibility/api";
import type { Job } from "@/features/audit/api";
import { useJob } from "@/features/audit/use-job";
import { projectsApi, type Market } from "@/features/orgs/api";
import { engineLabel } from "@/features/orgs/engines";
import { errorText } from "@/features/orgs/errors";
import { useCan, useOrg } from "@/features/orgs/org-context";

import {
  reportKeys,
  reportsApi,
  type AlertKind,
  type AlertRule,
  type EnginePresence,
  type ExportKind,
  type GscTotals,
} from "./api";

const num = new Intl.NumberFormat();
const BUCKETS = [
  ["top3", "1–3"],
  ["top10", "4–10"],
  ["top20", "11–20"],
  ["top100", "21–100"],
  ["not_ranking", "Not ranking"],
] as const;
const EXPORTS: [ExportKind, string][] = [
  ["rankings", "Rankings"],
  ["gsc_queries", "Search Console queries"],
  ["audit_issues", "Audit issues"],
  ["ai_answers", "AI answers"],
];

function Delta({ current, previous }: { current: number; previous: number }) {
  if (!previous) return null;
  const change = (current - previous) / previous;
  return (
    <span className={change >= 0 ? "text-accent text-xs" : "text-destructive text-xs"}>
      {change >= 0 ? "+" : ""}
      {Math.round(change * 100)}% vs previous 28 days
    </span>
  );
}

function Stat({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-md border p-3">
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
      {children}
    </div>
  );
}

function Overview({ projectId, market }: { projectId: string; market: Market }) {
  const org = useOrg();
  const presence = useQuery({
    queryKey: [...reportKeys.project(org.id, projectId), "presence", market.id],
    queryFn: () => reportsApi.presence(org.id, projectId, market.id),
  });
  if (presence.isPending) return <Skeleton className="h-64" />;
  if (presence.isError) return <ErrorState error={presence.error} />;
  const data = presence.data;
  const engines = data.engines as unknown as EnginePresence[];
  const gsc = data.gsc as { current: GscTotals; previous: GscTotals; latest_date: string } | null;
  const audit = data.audit as {
    score: number | null;
    date: string;
    issues: Record<string, number>;
  } | null;
  const vitals = data.vitals as { pass_rate: number | null; assessed: number; poor: number } | null;
  const ai = (data.ai as { engines: EngineVisibility[] }).engines;
  const opportunities = data.opportunities as {
    query: string;
    impressions: number;
    position: number;
  }[];
  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Search Presence Score" value={data.score === null ? "—" : `${data.score}/100`}>
          <p className="text-muted-foreground text-xs">
            {data.score === null
              ? "Track keywords and run a ranking check to score this market."
              : data.score_parts.ai === null
                ? "Classic search only (no AI citation data yet)."
                : "80% classic search share of voice, 20% AI citations."}
          </p>
        </Stat>
        <Stat label="Google clicks (28 days)" value={gsc ? num.format(gsc.current.clicks) : "—"}>
          {gsc ? (
            <Delta current={gsc.current.clicks} previous={gsc.previous.clicks} />
          ) : (
            <p className="text-muted-foreground text-xs">Connect Search Console.</p>
          )}
        </Stat>
        <Stat
          label="Site audit"
          value={audit?.score != null ? `${Math.round(audit.score)}/100` : "—"}
        >
          <p className="text-muted-foreground text-xs">
            {audit ? `Audited ${audit.date}` : "Run a site audit."}
          </p>
        </Stat>
        <Stat
          label="Core Web Vitals pass rate"
          value={vitals?.pass_rate != null ? `${Math.round(vitals.pass_rate * 100)}%` : "—"}
        >
          <p className="text-muted-foreground text-xs">
            {vitals ? `${vitals.assessed} origins/pages with field data` : "No field data yet."}
          </p>
        </Stat>
      </div>
      <div>
        <h3 className="mb-1 text-sm font-medium">Rankings by engine</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Engine</TableHead>
              <TableHead className="text-right">Share of voice</TableHead>
              {BUCKETS.map(([id, text]) => (
                <TableHead key={id} className="text-right">
                  {text}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {engines.map((e) => (
              <TableRow key={e.engine}>
                <TableCell className="font-medium">
                  {engineLabel(e.engine as Parameters<typeof engineLabel>[0])}
                </TableCell>
                <TableCell className="text-right">
                  {e.share_of_voice === null
                    ? "No data"
                    : `${(e.share_of_voice * 100).toFixed(1)}%`}
                </TableCell>
                {BUCKETS.map(([id]) => (
                  <TableCell key={id} className="text-right">
                    {e.keywords ? (e.distribution[id] ?? 0) : "—"}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {!data.volumes_known && engines.some((e) => e.keywords) ? (
          <p className="text-muted-foreground mt-1 text-xs">
            Search volumes are unavailable, so every keyword counts equally.
          </p>
        ) : null}
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <h3 className="mb-1 text-sm font-medium">AI answers (30 days)</h3>
          {ai.length === 0 ? (
            <p className="text-muted-foreground text-sm">No AI answers sampled yet.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {ai.map((e) => (
                <li key={e.engine}>
                  {ENGINE_LABEL[e.engine] ?? e.engine}: cited {formatRate(e.citation_rate)}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="mb-1 text-sm font-medium">Top opportunities (positions 8–20)</h3>
          {opportunities.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              {gsc ? "No striking-distance queries right now." : "Needs Search Console data."}
            </p>
          ) : (
            <ul className="space-y-1 text-sm">
              {opportunities.map((o) => (
                <li key={o.query}>
                  {o.query}{" "}
                  <span className="text-muted-foreground">
                    · #{o.position} · {num.format(o.impressions)} impressions
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function Exports({ projectId }: { projectId: string }) {
  const org = useOrg();
  const queryClient = useQueryClient();
  const key = [...reportKeys.project(org.id, projectId), "exports"];
  const list = useQuery({ queryKey: key, queryFn: () => reportsApi.exports(org.id, projectId) });
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState<Job | null>(null);
  const job = useJob(org.id, started);
  const finishedId = job && !["queued", "running"].includes(job.status) ? job.id : null;
  useEffect(() => {
    if (finishedId) void queryClient.invalidateQueries({ queryKey: key });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key is derived from stable ids
  }, [finishedId, queryClient]);

  async function start(kind: ExportKind) {
    setError(null);
    try {
      setStarted((await reportsApi.startExport(org.id, projectId, kind)).job);
      await queryClient.invalidateQueries({ queryKey: key });
    } catch (err) {
      setError(errorText(err, "Could not start the export."));
    }
  }

  async function download(id: string) {
    setError(null);
    try {
      const link = await reportsApi.exportLink(org.id, projectId, id);
      window.location.assign(link.url);
    } catch (err) {
      setError(errorText(err, "The download link could not be created."));
    }
  }

  return (
    <div className="space-y-3">
      <FormAlert message={error} />
      <div className="flex flex-wrap gap-2">
        {EXPORTS.map(([kind, text]) => (
          <Button key={kind} size="sm" variant="outline" onClick={() => void start(kind)}>
            Export {text}
          </Button>
        ))}
      </div>
      {list.data && list.data.length > 0 ? (
        <ul className="space-y-1 text-sm">
          {list.data.slice(0, 10).map((e) => (
            <li key={e.id} className="flex items-center gap-2">
              <span>{EXPORTS.find(([k]) => k === e.kind)?.[1] ?? e.kind}</span>
              <Badge variant="outline">{e.status}</Badge>
              {e.status === "completed" ? (
                <>
                  <span className="text-muted-foreground text-xs">
                    {num.format(e.rows ?? 0)} rows
                  </span>
                  <Button size="sm" variant="ghost" onClick={() => void download(e.id)}>
                    <Download className="mr-1 h-4 w-4" aria-hidden /> CSV
                  </Button>
                </>
              ) : null}
              {e.error ? <span className="text-destructive text-xs">{e.error}</span> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-muted-foreground text-xs">
          Exports are kept for 24 hours; download links last 15 minutes.
        </p>
      )}
    </div>
  );
}

function AlertRow({ projectId, rule }: { projectId: string; rule: AlertRule }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const [threshold, setThreshold] = useState(rule.threshold === null ? "" : String(rule.threshold));
  const [error, setError] = useState<string | null>(null);
  async function save(next: Partial<{ active: boolean; email: boolean }>) {
    setError(null);
    try {
      await reportsApi.setAlert(org.id, projectId, rule.kind as AlertKind, {
        active: next.active ?? rule.active,
        email: next.email ?? rule.email,
        threshold: threshold === "" ? null : Number(threshold),
      });
      await queryClient.invalidateQueries({
        queryKey: [...reportKeys.project(org.id, projectId), "alerts"],
      });
    } catch (err) {
      setError(errorText(err, "Could not save the alert."));
    }
  }
  return (
    <TableRow>
      <TableCell>{rule.label}</TableCell>
      <TableCell>
        <input
          type="checkbox"
          aria-label={`${rule.label} on`}
          checked={rule.active}
          disabled={!canWrite}
          onChange={(e) => void save({ active: e.target.checked })}
        />
      </TableCell>
      <TableCell>
        <input
          type="checkbox"
          aria-label={`${rule.label} by email`}
          checked={rule.email}
          disabled={!canWrite || !rule.active}
          onChange={(e) => void save({ email: e.target.checked })}
        />
      </TableCell>
      <TableCell>
        {rule.threshold_meaning ? (
          <div className="flex items-center gap-1">
            <Input
              aria-label={`${rule.label} threshold`}
              className="h-8 w-16"
              type="number"
              min={0}
              value={threshold}
              disabled={!canWrite}
              onChange={(e) => setThreshold(e.target.value)}
              onBlur={() => void save({})}
            />
            <span className="text-muted-foreground text-xs">{rule.threshold_meaning}</span>
          </div>
        ) : null}
        {error ? (
          <span role="alert" className="text-destructive text-xs">
            {error}
          </span>
        ) : null}
      </TableCell>
    </TableRow>
  );
}

function Alerts({ projectId }: { projectId: string }) {
  const org = useOrg();
  const rules = useQuery({
    queryKey: [...reportKeys.project(org.id, projectId), "alerts"],
    queryFn: () => reportsApi.alerts(org.id, projectId),
  });
  if (rules.isPending) return <Skeleton className="h-32" />;
  if (rules.isError) return <ErrorState error={rules.error} />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Alert</TableHead>
          <TableHead>On</TableHead>
          <TableHead>Email</TableHead>
          <TableHead>Threshold</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rules.data.map((rule) => (
          <AlertRow key={rule.kind} projectId={projectId} rule={rule} />
        ))}
      </TableBody>
    </Table>
  );
}

function marketLabel(m: Market): string {
  return `${m.country} · ${m.language} · ${m.device}${m.location ? ` · ${m.location}` : ""}`;
}

export function PresencePage({ projectId }: { projectId: string }) {
  const org = useOrg();
  const [marketId, setMarketId] = useState<string | null>(null);
  const project = useQuery({
    queryKey: ["orgs", org.id, "projects", projectId],
    queryFn: () => projectsApi.get(org.id, projectId),
  });
  if (project.isPending) return <Skeleton className="h-64" />;
  if (project.isError) return <ErrorState error={project.error} />;
  const market = project.data.markets.find((m) => m.id === marketId) ?? project.data.markets[0];
  if (!market)
    return <EmptyState title="No market" description="Add a market to the project first." />;
  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link
            href={`/orgs/${org.id}/projects/${projectId}`}
            className="text-muted-foreground text-sm hover:underline print:hidden"
          >
            ← {project.data.name}
          </Link>
          <h1 className="text-2xl font-semibold">Search Presence</h1>
          <p className="text-muted-foreground hidden text-sm print:block">
            {project.data.name} · {marketLabel(market)} · {new Date().toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-2 print:hidden">
          <NativeSelect
            aria-label="Market"
            className="h-9 w-72"
            value={market.id}
            onChange={(e) => setMarketId(e.target.value)}
          >
            {project.data.markets.map((m) => (
              <option key={m.id} value={m.id}>
                {marketLabel(m)}
              </option>
            ))}
          </NativeSelect>
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <Printer className="mr-1 h-4 w-4" aria-hidden /> Print / PDF
          </Button>
        </div>
      </div>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Overview</CardTitle>
          <CardDescription>
            Google first; other engines and AI answers side by side. Everything shown comes from
            your own data or our observations — blanks mean no data yet.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Overview projectId={projectId} market={market} />
        </CardContent>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2 print:hidden">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Exports</CardTitle>
            <CardDescription>CSV files that are safe to open in spreadsheets.</CardDescription>
          </CardHeader>
          <CardContent>
            <Exports projectId={projectId} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Alerts</CardTitle>
            <CardDescription>
              In-app for everyone on the project; email is optional.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Alerts projectId={projectId} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
