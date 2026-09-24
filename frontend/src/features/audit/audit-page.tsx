"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, ExternalLink, Play, Square } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { FormAlert } from "@/components/forms/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { projectsApi } from "@/features/orgs/api";
import { engineLabel } from "@/features/orgs/engines";
import { errorText } from "@/features/orgs/errors";
import { useCan, useOrg } from "@/features/orgs/org-context";

import {
  ACTIVE_JOB,
  auditApi,
  auditKeys,
  jobsApi,
  type Crawl,
  type IssueSummary,
  type Job,
  type PageFilter,
  type Severity,
} from "./api";
import { useJob } from "./use-job";

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];
const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Notice",
};
const SEVERITY_VARIANT: Record<Severity, "destructive" | "warning" | "secondary" | "outline"> = {
  critical: "destructive",
  high: "destructive",
  medium: "warning",
  low: "secondary",
  info: "outline",
};
const STAGE_LABEL: Record<string, string> = {
  crawling: "Crawling pages",
  rendering: "Rendering JavaScript samples",
  auditing: "Running audit checks",
};
const dateFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const numberFmt = new Intl.NumberFormat();

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge variant={SEVERITY_VARIANT[severity]}>{SEVERITY_LABEL[severity]}</Badge>;
}

/** Render finding details as plain text (never as HTML - it may contain crawled content). */
export function detailText(details: Record<string, unknown>): string {
  return Object.entries(details)
    .map(([key, value]) => {
      const shown = Array.isArray(value)
        ? value.map((v) => (typeof v === "object" ? JSON.stringify(v) : String(v))).join(", ")
        : typeof value === "object" && value !== null
          ? JSON.stringify(value)
          : String(value);
      return `${key.replaceAll("_", " ")}: ${shown}`;
    })
    .join(" · ");
}

// -------------------------------------------------------------------- run + progress
function RunPanel({
  projectId,
  initialJob,
  canRun,
}: {
  projectId: string;
  initialJob: Job | null;
  canRun: boolean;
}) {
  const org = useOrg();
  const queryClient = useQueryClient();
  const [started, setStarted] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const job = useJob(org.id, started ?? initialJob);
  const active = job !== null && ACTIVE_JOB.has(job.status);
  const usage = useQuery({
    queryKey: auditKeys.usage(org.id, projectId),
    queryFn: () => auditApi.usage(org.id, projectId),
  });

  const finishedId = job && !active ? job.id : null;
  useEffect(() => {
    if (finishedId)
      void queryClient.invalidateQueries({ queryKey: auditKeys.all(org.id, projectId) });
  }, [finishedId, org.id, projectId, queryClient]);

  async function start() {
    setError(null);
    try {
      const result = await auditApi.start(org.id, projectId);
      setStarted(result.job);
    } catch (err) {
      setError(errorText(err, "Could not start the audit."));
    }
  }

  async function cancel() {
    if (!job) return;
    try {
      setStarted(await jobsApi.cancel(org.id, job.id));
    } catch (err) {
      setError(errorText(err, "Could not cancel the audit."));
    }
  }

  const fetched = Number(job?.counters?.pages_fetched ?? 0);
  const budget = Number(job?.counters?.max_pages ?? 0);
  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <CardTitle>Technical SEO audit</CardTitle>
          <CardDescription>
            Crawls your site like Googlebot and checks it against Google Search Essentials, plus the
            other engines you track.
          </CardDescription>
        </div>
        {canRun ? (
          active ? (
            <Button
              variant="outline"
              onClick={() => void cancel()}
              disabled={job?.cancel_requested}
            >
              <Square className="mr-2 h-4 w-4" aria-hidden /> Stop
            </Button>
          ) : (
            <Button onClick={() => void start()} disabled={usage.data?.max_pages_next_crawl === 0}>
              <Play className="mr-2 h-4 w-4" aria-hidden /> Run audit
            </Button>
          )
        ) : null}
      </CardHeader>
      <CardContent className="space-y-3">
        <FormAlert message={error} />
        {active && job ? (
          <div className="space-y-2" role="status" aria-live="polite">
            <div className="flex justify-between text-sm">
              <span>
                {job.status === "queued"
                  ? "Waiting to start…"
                  : (STAGE_LABEL[job.stage ?? ""] ?? "Working…")}
              </span>
              <span className="text-muted-foreground">
                {budget
                  ? `${numberFmt.format(fetched)} of up to ${numberFmt.format(budget)} pages`
                  : null}
              </span>
            </div>
            <Progress value={Math.round((job.progress ?? 0) * 100)} aria-label="Audit progress" />
          </div>
        ) : null}
        {job && job.status === "failed" ? (
          <FormAlert message={`The last audit failed: ${job.error_message ?? "unknown error"}`} />
        ) : null}
        {job && job.status === "cancelled" ? (
          <p className="text-muted-foreground text-sm">The last audit was stopped.</p>
        ) : null}
        {usage.data ? (
          <p className="text-muted-foreground text-sm">
            {numberFmt.format(usage.data.pages_used_this_month)} of{" "}
            {numberFmt.format(usage.data.pages_per_month)} crawl pages used this month. The next
            audit can crawl up to {numberFmt.format(usage.data.max_pages_next_crawl)} pages
            {usage.data.domain_verified ? "." : " (verify the domain for a full crawl)."}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

// ------------------------------------------------------------------------- summary
function ScoreSummary({ crawl, engine }: { crawl: Crawl; engine: string }) {
  const counts = crawl.issue_counts as {
    scores?: Record<string, number>;
    by_severity?: Record<string, number>;
    failed_rules?: string[];
  };
  const score = counts.scores?.[engine];
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{engineLabel(engine as "google")} health score</CardDescription>
          <CardTitle className="text-4xl">
            {score !== undefined ? Math.round(score) : "—"}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground text-xs">
          100 means no issues found. Scores weigh severity and how many pages are affected.
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>Pages crawled</CardDescription>
          <CardTitle className="text-4xl">{numberFmt.format(crawl.pages_fetched)}</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground text-xs">
          {crawl.finished_at
            ? `Finished ${dateFmt.format(new Date(crawl.finished_at))}`
            : "In progress"}
          {crawl.budget_exhausted ? " · stopped at the page limit, so this is a partial audit" : ""}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>Affected URLs by severity</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {SEVERITY_ORDER.map((s) => (
            <span key={s} className="flex items-center gap-1 text-sm">
              <SeverityBadge severity={s} /> {counts.by_severity?.[s] ?? 0}
            </span>
          ))}
        </CardContent>
      </Card>
      {!crawl.render_available ? (
        <p className="text-muted-foreground text-xs md:col-span-3">
          JavaScript rendering checks were not run for this audit (renderer unavailable).
        </p>
      ) : null}
    </div>
  );
}

// -------------------------------------------------------------------------- issues
function IssueOccurrences({
  projectId,
  crawlId,
  ruleId,
}: {
  projectId: string;
  crawlId: string;
  ruleId: string;
}) {
  const org = useOrg();
  const [offset, setOffset] = useState(0);
  const detail = useQuery({
    queryKey: [...auditKeys.issue(org.id, projectId, crawlId, ruleId), offset],
    queryFn: () => auditApi.issueDetail(org.id, projectId, crawlId, ruleId, offset),
  });
  if (detail.isPending) return <Skeleton className="h-16" />;
  if (detail.isError) return <ErrorState error={detail.error} />;
  return (
    <div className="space-y-2">
      <ul className="divide-y rounded-md border text-sm" aria-label="Affected URLs">
        {detail.data.items.map((item, index) => (
          <li key={`${item.url}-${index}`} className="space-y-0.5 p-2">
            <div className="font-mono text-xs break-all">{item.url ?? "Whole site"}</div>
            {Object.keys(item.details).length ? (
              <div className="text-muted-foreground text-xs break-all">
                {detailText(item.details)}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-2 text-xs">
        <span className="text-muted-foreground">
          {offset + 1}–{Math.min(offset + 50, detail.data.total)} of {detail.data.total}
        </span>
        <Button
          variant="ghost"
          size="sm"
          disabled={offset === 0}
          onClick={() => setOffset(offset - 50)}
        >
          Previous
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled={offset + 50 >= detail.data.total}
          onClick={() => setOffset(offset + 50)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

function IssueRow({
  issue,
  projectId,
  crawlId,
}: {
  issue: IssueSummary;
  projectId: string;
  crawlId: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <li className="rounded-md border">
      <button
        type="button"
        className="hover:bg-muted/50 flex w-full items-center gap-3 p-3 text-left"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0" aria-hidden />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0" aria-hidden />
        )}
        <SeverityBadge severity={issue.severity} />
        <span className="flex-1 text-sm font-medium">{issue.title}</span>
        {issue.scope !== "all" ? (
          <Badge variant="outline">{engineLabel(issue.scope as "google")} only</Badge>
        ) : null}
        <span className="text-muted-foreground text-sm">{numberFmt.format(issue.affected)}</span>
      </button>
      {open ? (
        <div className="space-y-3 border-t p-3 text-sm">
          <p>{issue.description}</p>
          <p>
            <span className="font-medium">How to fix: </span>
            {issue.fix}
          </p>
          {issue.reference ? (
            <a
              href={issue.reference}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary inline-flex items-center gap-1 underline-offset-4 hover:underline"
            >
              Documentation <ExternalLink className="h-3 w-3" aria-hidden />
            </a>
          ) : null}
          <IssueOccurrences projectId={projectId} crawlId={crawlId} ruleId={issue.rule_id} />
        </div>
      ) : null}
    </li>
  );
}

function IssuesList({
  projectId,
  crawlId,
  engine,
}: {
  projectId: string;
  crawlId: string;
  engine: string;
}) {
  const org = useOrg();
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const issues = useQuery({
    queryKey: auditKeys.issues(org.id, projectId, crawlId, engine),
    queryFn: () => auditApi.issues(org.id, projectId, crawlId, engine),
  });
  const grouped = useMemo(() => {
    const groups = new Map<string, IssueSummary[]>();
    for (const issue of issues.data ?? []) {
      if (severity !== "all" && issue.severity !== severity) continue;
      const list = groups.get(issue.category_label) ?? [];
      list.push(issue);
      groups.set(issue.category_label, list);
    }
    return [...groups.entries()];
  }, [issues.data, severity]);

  if (issues.isPending) return <Skeleton className="h-48" />;
  if (issues.isError)
    return <ErrorState error={issues.error} onRetry={() => void issues.refetch()} />;
  if (issues.data.length === 0) {
    return (
      <EmptyState
        title="No issues found"
        description="This audit found nothing to fix for this search engine."
      />
    );
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <label htmlFor="severity-filter" className="text-sm">
          Severity
        </label>
        <NativeSelect
          id="severity-filter"
          className="h-9 w-40"
          value={severity}
          onChange={(e) => setSeverity(e.target.value as Severity | "all")}
        >
          <option value="all">All</option>
          {SEVERITY_ORDER.map((s) => (
            <option key={s} value={s}>
              {SEVERITY_LABEL[s]}
            </option>
          ))}
        </NativeSelect>
        <span className="text-muted-foreground text-xs">
          Sorted by priority: impact versus effort.
        </span>
      </div>
      {grouped.map(([category, list]) => (
        <section key={category} className="space-y-2">
          <h3 className="text-sm font-semibold">{category}</h3>
          <ul className="space-y-2">
            {list.map((issue) => (
              <IssueRow key={issue.rule_id} issue={issue} projectId={projectId} crawlId={crawlId} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------------- pages
const PAGE_FILTERS: { value: PageFilter; label: string }[] = [
  { value: "all", label: "All URLs" },
  { value: "indexable", label: "Indexable" },
  { value: "non_indexable", label: "Not indexable" },
  { value: "redirects", label: "Redirects" },
  { value: "errors", label: "Errors" },
  { value: "blocked", label: "Blocked by robots.txt" },
];

function PagesTable({ projectId, crawlId }: { projectId: string; crawlId: string }) {
  const org = useOrg();
  const [kind, setKind] = useState<PageFilter>("all");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const pages = useQuery({
    queryKey: auditKeys.pages(org.id, projectId, crawlId, kind, q, offset),
    queryFn: () => auditApi.pages(org.id, projectId, crawlId, kind, q, offset),
  });
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <NativeSelect
          aria-label="Filter URLs"
          className="h-9 w-48"
          value={kind}
          onChange={(e) => {
            setKind(e.target.value as PageFilter);
            setOffset(0);
          }}
        >
          {PAGE_FILTERS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </NativeSelect>
        <Input
          aria-label="Search URLs"
          placeholder="Search URLs"
          className="h-9 max-w-xs"
          value={q}
          maxLength={200}
          onChange={(e) => {
            setQ(e.target.value);
            setOffset(0);
          }}
        />
      </div>
      {pages.isPending ? (
        <Skeleton className="h-48" />
      ) : pages.isError ? (
        <ErrorState error={pages.error} />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>URL</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Indexable</TableHead>
                <TableHead>Depth</TableHead>
                <TableHead>Inlinks</TableHead>
                <TableHead>Words</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pages.data.items.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="max-w-md">
                    <div className="font-mono text-xs break-all">{p.url}</div>
                    {p.title ? (
                      <div className="text-muted-foreground truncate text-xs">{p.title}</div>
                    ) : null}
                    {p.redirect_to ? (
                      <div className="text-muted-foreground text-xs break-all">
                        → {p.redirect_to}
                      </div>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-sm">
                    {p.status_code ?? p.error?.replaceAll("_", " ") ?? "—"}
                  </TableCell>
                  <TableCell className="text-sm">{p.indexable_google ? "Yes" : "No"}</TableCell>
                  <TableCell className="text-sm">{p.depth ?? "—"}</TableCell>
                  <TableCell className="text-sm">{p.inlinks}</TableCell>
                  <TableCell className="text-sm">{p.word_count ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">
              {pages.data.total === 0
                ? "No URLs match."
                : `${offset + 1}–${Math.min(offset + 50, pages.data.total)} of ${numberFmt.format(pages.data.total)}`}
            </span>
            <Button
              variant="ghost"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(offset - 50)}
            >
              Previous
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={offset + 50 >= pages.data.total}
              onClick={() => setOffset(offset + 50)}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------- page
export function AuditPage({ projectId }: { projectId: string }) {
  const org = useOrg();
  const canRun = useCan("project:write");
  const [tab, setTab] = useState<"issues" | "pages">("issues");
  const [selected, setSelected] = useState<string | null>(null);
  const [engine, setEngine] = useState("google");
  const project = useQuery({
    queryKey: ["orgs", org.id, "projects", projectId],
    queryFn: () => projectsApi.get(org.id, projectId),
  });
  const crawls = useQuery({
    queryKey: auditKeys.crawls(org.id, projectId),
    queryFn: () => auditApi.list(org.id, projectId),
  });
  const latestJob = useQuery({
    queryKey: auditKeys.activeJob(org.id, projectId),
    queryFn: () => jobsApi.latest(org.id, projectId),
  });

  if (project.isError) return <ErrorState error={project.error} />;
  if (project.isPending || crawls.isPending || latestJob.isPending)
    return <Skeleton className="h-64" />;
  if (crawls.isError)
    return <ErrorState error={crawls.error} onRetry={() => void crawls.refetch()} />;

  const completed = crawls.data.filter((c) => c.status === "completed");
  const current = completed.find((c) => c.id === selected) ?? completed[0];
  const engines = current
    ? ["google", ...current.engines.filter((e) => e !== "google")]
    : ["google"];
  const initialJob = latestJob.data?.[0] ?? null;

  return (
    <div className="max-w-6xl space-y-6">
      <div>
        <Link
          href={`/orgs/${org.id}/projects/${projectId}`}
          className="text-muted-foreground text-sm hover:underline"
        >
          ← {project.data.name}
        </Link>
        <h1 className="text-2xl font-semibold">Technical audit</h1>
        <p className="text-muted-foreground text-sm">{project.data.primary_domain}</p>
      </div>
      <RunPanel projectId={projectId} initialJob={initialJob} canRun={canRun} />

      {!current ? (
        <EmptyState
          title="No audit yet"
          description={
            canRun
              ? "Run your first audit to see how search engines crawl and index this site."
              : "No audit has been run for this site yet."
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-1" role="tablist" aria-label="Search engine">
              {engines.map((e) => (
                <Button
                  key={e}
                  role="tab"
                  aria-selected={engine === e}
                  variant={engine === e ? "default" : "outline"}
                  size="sm"
                  onClick={() => setEngine(e)}
                >
                  {engineLabel(e as "google")}
                </Button>
              ))}
            </div>
            {completed.length > 1 ? (
              <NativeSelect
                aria-label="Audit history"
                className="h-9 w-64"
                value={current.id}
                onChange={(e) => setSelected(e.target.value)}
              >
                {completed.map((c) => (
                  <option key={c.id} value={c.id}>
                    {dateFmt.format(new Date(c.created_at))} · score{" "}
                    {c.score !== null ? Math.round(c.score) : "—"}
                  </option>
                ))}
              </NativeSelect>
            ) : null}
          </div>
          <ScoreSummary crawl={current} engine={engines.includes(engine) ? engine : "google"} />
          <div className="flex gap-1 border-b" role="tablist" aria-label="Audit view">
            {(["issues", "pages"] as const).map((t) => (
              <button
                key={t}
                role="tab"
                type="button"
                aria-selected={tab === t}
                className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === t ? "border-primary font-medium" : "text-muted-foreground border-transparent"}`}
                onClick={() => setTab(t)}
              >
                {t === "issues" ? "Issues" : "Crawled URLs"}
              </button>
            ))}
          </div>
          {tab === "issues" ? (
            <IssuesList
              projectId={projectId}
              crawlId={current.id}
              engine={engines.includes(engine) ? engine : "google"}
            />
          ) : (
            <PagesTable projectId={projectId} crawlId={current.id} />
          )}
        </>
      )}
    </div>
  );
}
