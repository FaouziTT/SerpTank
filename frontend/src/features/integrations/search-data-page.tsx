"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Field, FormAlert } from "@/components/forms/field";
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
import { Textarea } from "@/components/ui/textarea";
import { projectsApi } from "@/features/orgs/api";
import { errorText } from "@/features/orgs/errors";
import { useCan, useOrg } from "@/features/orgs/org-context";

import {
  importCsv,
  indexingApi,
  integrationKeys,
  integrationsApi,
  sourcesApi,
  type LinkableKind,
  type Performance,
  type Source,
} from "./api";

const numberFmt = new Intl.NumberFormat();
const dateFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const pct = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`;
const SOURCE_LABEL: Record<LinkableKind, string> = {
  gsc: "Google Search Console",
  ga4: "Google Analytics 4",
  bing: "Bing Webmaster Tools",
};

function useProjectKey(projectId: string) {
  const org = useOrg();
  return integrationKeys.project(org.id, projectId);
}

// -------------------------------------------------------------------------- sources
function SourceRow({
  projectId,
  kind,
  source,
}: {
  projectId: string;
  kind: LinkableKind;
  source: Source | undefined;
}) {
  const org = useOrg();
  const canManage = useCan("integrations:manage");
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const key = useProjectKey(projectId);
  const [choice, setChoice] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const google = kind !== "bing";
  const options = useQuery({
    queryKey: google ? integrationKeys.googleProps(org.id) : integrationKeys.bingSites(org.id),
    queryFn: async () => {
      if (!google)
        return (await integrationsApi.bingSites(org.id)).map((o) => ({ id: o.id, label: o.label }));
      const props = await integrationsApi.googleProperties(org.id);
      return kind === "gsc" ? props.gsc_sites : props.ga4_properties;
    },
    enabled: canManage && !source,
    retry: false,
  });

  async function link() {
    setError(null);
    try {
      await sourcesApi.link(org.id, projectId, kind, choice);
      await queryClient.invalidateQueries({ queryKey: key });
      await queryClient.invalidateQueries({ queryKey: ["orgs", org.id, "projects"] });
    } catch (err) {
      setError(errorText(err, "Could not link the property."));
    }
  }

  async function sync() {
    setError(null);
    try {
      await sourcesApi.sync(org.id, projectId, kind);
      setMessage("Sync started. New data appears here when it finishes.");
    } catch (err) {
      setError(errorText(err, "Could not start the sync."));
    }
  }

  async function unlink() {
    await sourcesApi.unlink(org.id, projectId, kind);
    await queryClient.invalidateQueries({ queryKey: key });
  }

  return (
    <li className="space-y-2 rounded-md border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-sm font-medium">{SOURCE_LABEL[kind]}</div>
          {source ? (
            <div className="text-muted-foreground text-xs">
              {source.property_id} ·{" "}
              {source.last_sync_at
                ? `last sync ${dateFmt.format(new Date(source.last_sync_at))} (${source.last_sync_status ?? "unknown"})`
                : "not synced yet"}
            </div>
          ) : (
            <div className="text-muted-foreground text-xs">Not linked</div>
          )}
        </div>
        {source ? (
          <div className="flex gap-2">
            {canWrite ? (
              <Button size="sm" variant="outline" onClick={() => void sync()}>
                Sync now
              </Button>
            ) : null}
            {canManage ? (
              <Button size="sm" variant="ghost" onClick={() => void unlink()}>
                Unlink
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>
      {!source && canManage ? (
        options.isError ? (
          <p className="text-muted-foreground text-xs">
            Connect {google ? "Google" : "Bing Webmaster Tools"} on the{" "}
            <Link href={`/orgs/${org.id}/integrations`} className="underline">
              Integrations
            </Link>{" "}
            page first.
          </p>
        ) : (
          <div className="flex flex-wrap items-end gap-2">
            <NativeSelect
              aria-label={`${SOURCE_LABEL[kind]} property`}
              className="h-9 max-w-md"
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
            >
              <option value="">{options.isPending ? "Loading…" : "Choose a property"}</option>
              {(options.data ?? []).map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </NativeSelect>
            <Button size="sm" onClick={() => void link()} disabled={!choice}>
              Link
            </Button>
          </div>
        )
      ) : null}
      <FormAlert message={error} />
      {message ? (
        <p role="status" className="text-xs">
          {message}
        </p>
      ) : null}
    </li>
  );
}

// ---------------------------------------------------------------------- performance
function MetricTable({ title, rows }: { title: string; rows: Performance["top_queries"] }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{title.includes("page") ? "Page" : "Query"}</TableHead>
            <TableHead className="text-right">Clicks</TableHead>
            <TableHead className="text-right">Impressions</TableHead>
            <TableHead className="text-right">CTR</TableHead>
            <TableHead className="text-right">Position</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.key}>
              <TableCell className="max-w-xs text-sm break-all">{r.key}</TableCell>
              <TableCell className="text-right text-sm">{numberFmt.format(r.clicks)}</TableCell>
              <TableCell className="text-right text-sm">
                {numberFmt.format(r.impressions)}
              </TableCell>
              <TableCell className="text-right text-sm">{pct(r.ctr)}</TableCell>
              <TableCell className="text-right text-sm">{r.position ?? "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function PerformanceCard({ projectId }: { projectId: string }) {
  const org = useOrg();
  const [source, setSource] = useState<"gsc" | "bing">("gsc");
  const [days, setDays] = useState(28);
  const perf = useQuery({
    queryKey: [...useProjectKey(projectId), "performance", source, days],
    queryFn: () => sourcesApi.performance(org.id, projectId, source, days),
  });
  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
        <div className="space-y-1.5">
          <CardTitle>Search performance</CardTitle>
          <CardDescription>
            Your own first-party data: real clicks and impressions, no estimates.
          </CardDescription>
        </div>
        <div className="flex gap-2">
          <NativeSelect
            aria-label="Data source"
            className="h-9 w-44"
            value={source}
            onChange={(e) => setSource(e.target.value as "gsc" | "bing")}
          >
            <option value="gsc">Google (Search Console)</option>
            <option value="bing">Bing Webmaster Tools</option>
          </NativeSelect>
          <NativeSelect
            aria-label="Period"
            className="h-9 w-32"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>7 days</option>
            <option value={28}>28 days</option>
            <option value={90}>3 months</option>
          </NativeSelect>
        </div>
      </CardHeader>
      <CardContent>
        {perf.isPending ? (
          <Skeleton className="h-32" />
        ) : perf.isError ? (
          <ErrorState error={perf.error} />
        ) : !perf.data.has_data ? (
          <EmptyState
            title="No data yet"
            description={`Link a ${source === "gsc" ? "Search Console property" : "Bing Webmaster Tools site"} above and run a sync.`}
          />
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {[
                ["Clicks", numberFmt.format(perf.data.clicks)],
                ["Impressions", numberFmt.format(perf.data.impressions)],
                ["CTR", pct(perf.data.ctr)],
                ["Avg. position", perf.data.position ?? "—"],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <div className="text-muted-foreground text-xs">{label}</div>
                  <div className="text-2xl font-semibold">{value}</div>
                </div>
              ))}
            </div>
            <p className="text-muted-foreground text-xs">
              {perf.data.date_from} – {perf.data.date_to}
            </p>
            <MetricTable title="Top queries" rows={perf.data.top_queries} />
            {perf.data.top_pages.length ? (
              <MetricTable title="Top pages" rows={perf.data.top_pages} />
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// --------------------------------------------------------------------------- vitals
const ASSESSMENT: Record<
  string,
  { label: string; variant: "secondary" | "warning" | "destructive" | "outline" }
> = {
  good: { label: "Good", variant: "secondary" },
  needs_improvement: { label: "Needs improvement", variant: "warning" },
  poor: { label: "Poor", variant: "destructive" },
  unknown: { label: "Not enough data", variant: "outline" },
};

function VitalsCard({ projectId }: { projectId: string }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const [message, setMessage] = useState<string | null>(null);
  const vitals = useQuery({
    queryKey: [...useProjectKey(projectId), "vitals"],
    queryFn: () => sourcesApi.vitals(org.id, projectId),
  });
  async function refresh() {
    try {
      await sourcesApi.sync(org.id, projectId, "vitals");
      setMessage("Fetching the latest field data…");
    } catch (err) {
      setMessage(errorText(err, "Could not refresh Core Web Vitals."));
    }
  }
  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <CardTitle>Core Web Vitals</CardTitle>
          <CardDescription>
            Real-user p75 from the Chrome UX Report (last 28 days of visits).
          </CardDescription>
        </div>
        {canWrite ? (
          <Button size="sm" variant="outline" onClick={() => void refresh()}>
            Refresh
          </Button>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-2">
        {message ? (
          <p role="status" className="text-xs">
            {message}
          </p>
        ) : null}
        {vitals.isPending ? (
          <Skeleton className="h-24" />
        ) : vitals.isError ? (
          <ErrorState error={vitals.error} />
        ) : vitals.data.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No field data yet. Sites need enough Chrome traffic to appear in the Chrome UX Report.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Target</TableHead>
                <TableHead>Device</TableHead>
                <TableHead className="text-right">LCP</TableHead>
                <TableHead className="text-right">INP</TableHead>
                <TableHead className="text-right">CLS</TableHead>
                <TableHead>Assessment</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {vitals.data.map((v) => (
                <TableRow key={`${v.target}-${v.form_factor}`}>
                  <TableCell className="max-w-xs text-xs break-all">
                    {v.scope === "origin" ? `${v.target} (whole site)` : v.target}
                  </TableCell>
                  <TableCell className="text-sm">
                    {v.form_factor === "PHONE" ? "Mobile" : "Desktop"}
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {v.lcp_ms !== null ? `${(v.lcp_ms / 1000).toFixed(1)} s` : "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {v.inp_ms !== null ? `${Math.round(v.inp_ms)} ms` : "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {v.cls !== null ? v.cls.toFixed(2) : "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={ASSESSMENT[v.assessment]?.variant ?? "outline"}>
                      {ASSESSMENT[v.assessment]?.label ?? v.assessment}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

// ------------------------------------------------------------------ AI performance
function AiPerformanceCard({ projectId }: { projectId: string }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const key = [...useProjectKey(projectId), "ai"];
  const totals = useQuery({
    queryKey: key,
    queryFn: () => sourcesApi.aiPerformance(org.id, projectId),
  });
  const [source, setSource] = useState<"gsc_genai" | "bing_ai">("gsc_genai");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setError(null);
    setResult(null);
    try {
      const imported = await importCsv(org.id, projectId, source, file);
      setResult(
        `Imported ${numberFmt.format(imported.rows)} rows (${imported.date_from} – ${imported.date_to})` +
          (imported.bad_rows ? `, skipped ${imported.bad_rows} invalid rows` : "") +
          ".",
      );
      await queryClient.invalidateQueries({ queryKey: key });
    } catch (err) {
      setError(errorText(err, "Could not import the file."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI search performance</CardTitle>
        <CardDescription>
          Google&apos;s Generative AI report (AI Overviews, AI Mode) and Bing&apos;s AI Performance
          report (Copilot citations) have no API yet. Export them as CSV and import them here.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {totals.data && totals.data.length > 0 ? (
          <div className="grid gap-3 md:grid-cols-3">
            {totals.data.map((t) => (
              <div key={`${t.source}-${t.surface}`} className="rounded-md border p-3">
                <div className="text-muted-foreground text-xs">
                  {t.surface === "ai_overview"
                    ? "AI Overviews"
                    : t.surface === "ai_mode"
                      ? "AI Mode"
                      : "Copilot"}
                </div>
                <div className="text-xl font-semibold">
                  {numberFmt.format(t.surface === "copilot" ? t.citations : t.impressions)}
                </div>
                <div className="text-muted-foreground text-xs">
                  {t.surface === "copilot" ? "citations" : "impressions"} · {t.date_from} –{" "}
                  {t.date_to}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">No AI search data imported yet.</p>
        )}
        {canWrite ? (
          <form onSubmit={upload} className="flex flex-wrap items-end gap-2">
            <NativeSelect
              aria-label="Report type"
              className="h-9 w-64"
              value={source}
              onChange={(e) => setSource(e.target.value as "gsc_genai" | "bing_ai")}
            >
              <option value="gsc_genai">Search Console: Generative AI report</option>
              <option value="bing_ai">Bing: AI Performance report</option>
            </NativeSelect>
            <Input
              aria-label="CSV file"
              type="file"
              accept=".csv,text/csv"
              className="h-9 max-w-xs"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <Button type="submit" size="sm" disabled={!file}>
              Import CSV
            </Button>
          </form>
        ) : null}
        <FormAlert message={error} />
        {result ? (
          <p role="status" className="text-sm">
            {result}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

// ------------------------------------------------------------------------- indexing
function IndexingCard({
  projectId,
  verified,
  domain,
  indexnow,
}: {
  projectId: string;
  verified: boolean;
  domain: string;
  indexnow: Source | undefined;
}) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const key = useProjectKey(projectId);
  const [urls, setUrls] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const log = useQuery({
    queryKey: [...key, "submissions"],
    queryFn: () => indexingApi.submissions(org.id, projectId),
  });

  async function run(action: () => Promise<unknown>, done?: string) {
    setError(null);
    setMessage(null);
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: key });
      if (done) setMessage(done);
    } catch (err) {
      setError(errorText(err, "The request failed."));
    }
  }

  const keyValue = indexnow?.property_id;
  const keyVerified = Boolean(indexnow?.settings.verified);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Instant indexing (IndexNow)</CardTitle>
        <CardDescription>
          Notify Bing, Yandex, Seznam and Naver about new or changed pages. Google doesn&apos;t use
          IndexNow; it discovers changes through your sitemap.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <FormAlert message={error} />
        {message ? <p role="status">{message}</p> : null}
        {!verified ? (
          <p className="text-muted-foreground">Verify domain ownership before submitting URLs.</p>
        ) : null}
        {!indexnow ? (
          canWrite ? (
            <Button
              size="sm"
              onClick={() => void run(() => indexingApi.createKey(org.id, projectId))}
            >
              Create IndexNow key
            </Button>
          ) : null
        ) : (
          <div className="space-y-2">
            <p>
              Publish a text file at{" "}
              <code className="bg-muted rounded px-1 break-all">{`https://${domain}/${keyValue}.txt`}</code>{" "}
              containing only <code className="bg-muted rounded px-1 break-all">{keyValue}</code>.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {keyVerified ? (
                <Badge variant="secondary">Key file verified</Badge>
              ) : (
                <Badge variant="warning">Key file not found yet</Badge>
              )}
              {canWrite ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void run(() => indexingApi.verifyKey(org.id, projectId))}
                >
                  Check key file
                </Button>
              ) : null}
              {canWrite && keyVerified && verified ? (
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={Boolean(indexnow.settings.auto_submit)}
                    onChange={(e) =>
                      void run(() => indexingApi.setAuto(org.id, projectId, e.target.checked))
                    }
                  />
                  Submit new and changed pages automatically after each audit
                </label>
              ) : null}
            </div>
          </div>
        )}
        {canWrite && verified && keyVerified ? (
          <form
            className="space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              const list = urls.split(/\s+/).filter(Boolean);
              void run(
                () => indexingApi.submit(org.id, projectId, list, "indexnow"),
                `Submitted ${list.length} URL(s).`,
              ).then(() => setUrls(""));
            }}
          >
            <Field
              id="submit-urls"
              label="Submit URLs now"
              hint="One URL per line, on this project's domain."
            >
              <Textarea
                id="submit-urls"
                rows={4}
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
              />
            </Field>
            <Button size="sm" type="submit" disabled={!urls.trim()}>
              Submit
            </Button>
          </form>
        ) : null}
        {log.data && log.data.length > 0 ? (
          <ul className="divide-y rounded-md border text-xs" aria-label="Recent submissions">
            {log.data.slice(0, 10).map((s) => (
              <li key={s.id} className="flex justify-between gap-2 p-2">
                <span>
                  {dateFmt.format(new Date(s.submitted_at))} · {s.channel} · {s.url_count} URL(s) ·{" "}
                  {s.trigger}
                </span>
                <span>{s.status_code ?? "failed"}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}

function InspectionCard({ projectId, hasGsc }: { projectId: string; hasGsc: boolean }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const key = [...useProjectKey(projectId), "inspections"];
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const list = useQuery({
    queryKey: key,
    queryFn: () => indexingApi.inspections(org.id, projectId),
    enabled: hasGsc,
  });
  async function inspect(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await indexingApi.inspect(org.id, projectId, url.trim());
      setUrl("");
      await queryClient.invalidateQueries({ queryKey: key });
    } catch (err) {
      setError(errorText(err, "Could not inspect the URL."));
    }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>URL inspection</CardTitle>
        <CardDescription>
          Google&apos;s own index status for a URL, from Search Console.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {!hasGsc ? (
          <p className="text-muted-foreground">
            Link a Search Console property above to inspect URLs.
          </p>
        ) : (
          <>
            {canWrite ? (
              <form onSubmit={inspect} className="flex flex-wrap gap-2">
                <Input
                  aria-label="URL to inspect"
                  className="h-9 max-w-lg"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://…"
                />
                <Button size="sm" type="submit" disabled={url.trim().length < 8}>
                  Inspect
                </Button>
              </form>
            ) : null}
            <FormAlert message={error} />
            <ul className="divide-y rounded-md border" aria-label="Inspections">
              {(list.data ?? []).map((i) => (
                <li key={i.id} className="space-y-0.5 p-2">
                  <div className="font-mono text-xs break-all">{i.url}</div>
                  <div className="text-xs">
                    <Badge variant={i.verdict === "PASS" ? "secondary" : "warning"}>
                      {i.coverage_state ?? i.verdict ?? "Unknown"}
                    </Badge>{" "}
                    {i.last_crawl_time
                      ? `last crawled ${dateFmt.format(new Date(i.last_crawl_time))}`
                      : "never crawled"}
                    {i.google_canonical && i.google_canonical !== i.url
                      ? ` · Google chose ${i.google_canonical}`
                      : ""}
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------- page
export function SearchDataPage({ projectId }: { projectId: string }) {
  const org = useOrg();
  const project = useQuery({
    queryKey: ["orgs", org.id, "projects", projectId],
    queryFn: () => projectsApi.get(org.id, projectId),
  });
  const sources = useQuery({
    queryKey: [...useProjectKey(projectId), "sources"],
    queryFn: () => sourcesApi.list(org.id, projectId),
  });
  if (project.isPending || sources.isPending) return <Skeleton className="h-64" />;
  if (project.isError) return <ErrorState error={project.error} />;
  if (sources.isError) return <ErrorState error={sources.error} />;
  const byKind = new Map(sources.data.map((s) => [s.kind, s]));
  return (
    <div className="max-w-5xl space-y-6">
      <div>
        <Link
          href={`/orgs/${org.id}/projects/${projectId}`}
          className="text-muted-foreground text-sm hover:underline"
        >
          ← {project.data.name}
        </Link>
        <h1 className="text-2xl font-semibold">Search data</h1>
        <p className="text-muted-foreground text-sm">{project.data.primary_domain}</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Data sources</CardTitle>
          <CardDescription>
            Synced daily. Linking a Search Console property you own also verifies the domain.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {(["gsc", "ga4", "bing"] as const).map((kind) => (
              <SourceRow key={kind} projectId={projectId} kind={kind} source={byKind.get(kind)} />
            ))}
          </ul>
        </CardContent>
      </Card>
      <PerformanceCard projectId={projectId} />
      <VitalsCard projectId={projectId} />
      <AiPerformanceCard projectId={projectId} />
      <InspectionCard projectId={projectId} hasGsc={byKind.has("gsc")} />
      <IndexingCard
        projectId={projectId}
        verified={project.data.verified}
        domain={project.data.primary_domain}
        indexnow={byKind.get("indexnow")}
      />
    </div>
  );
}
