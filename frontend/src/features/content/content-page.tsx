"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

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
import type { Job } from "@/features/audit/api";
import { useJob } from "@/features/audit/use-job";
import { projectsApi, type Market } from "@/features/orgs/api";
import { errorText } from "@/features/orgs/errors";
import { useCan, useOrg } from "@/features/orgs/org-context";

import {
  contentApi,
  contentKeys,
  type BriefData,
  type CheckResult,
  type OptimizationResult,
  type Rewrite,
} from "./api";

const TABS = [
  ["optimizer", "Page optimizer"],
  ["briefs", "Content briefs"],
  ["map", "Keyword map"],
  ["cannibalization", "Cannibalization"],
] as const;
type Tab = (typeof TABS)[number][0];

const STATUS_VARIANT = {
  pass: "secondary",
  warn: "outline",
  fail: "destructive",
  info: "outline",
} as const;
const STATUS_LABEL = { pass: "Pass", warn: "Improve", fail: "Fix", info: "Info" } as const;
const MAP_LABEL: Record<string, string> = {
  aligned: "Aligned",
  mismatch: "Different page ranks",
  unassigned: "No target page",
  not_ranking: "Not ranking yet",
};
const SKIP_LABEL: Record<string, string> = {
  robots: "blocked by robots.txt",
  robots_error: "robots.txt error",
  unreachable: "unreachable",
  not_html: "not HTML",
};

function isActive(job: Job | null): boolean {
  return Boolean(job && ["queued", "running"].includes(job.status));
}

/** Refresh `key` once a started job finishes. */
function useRefreshOnFinish(job: Job | null, key: unknown[]) {
  const queryClient = useQueryClient();
  const finishedId = job && !isActive(job) ? job.id : null;
  useEffect(() => {
    if (finishedId) void queryClient.invalidateQueries({ queryKey: key });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key is derived from stable ids
  }, [finishedId, queryClient]);
}

function CheckRow({ check }: { check: CheckResult }) {
  const suggestions = check.detail.suggestions ?? [];
  return (
    <li className="border-b py-2 last:border-0">
      <div className="flex items-start gap-2">
        <Badge variant={STATUS_VARIANT[check.status]} className="mt-0.5 shrink-0">
          {STATUS_LABEL[check.status]}
        </Badge>
        <div className="space-y-1 text-sm">
          <p>{check.message}</p>
          {check.recommendation ? (
            <p className="text-muted-foreground">{check.recommendation}</p>
          ) : null}
          {suggestions.length > 0 ? (
            <ul className="text-muted-foreground list-disc pl-5 text-xs">
              {suggestions.map((s) => (
                <li key={s.url}>
                  {s.title} — <span className="break-all">{s.url}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    </li>
  );
}

function OptimizationDetail({ projectId, id }: { projectId: string; id: string }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const key = [...contentKeys.all(org.id, projectId), "optimization", id];
  const detail = useQuery({
    queryKey: key,
    queryFn: () => contentApi.optimization(org.id, projectId, id),
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (detail.isPending) return <Skeleton className="h-64" />;
  if (detail.isError) return <ErrorState error={detail.error} />;
  const row = detail.data;
  if (row.status === "running") return <p role="status">Analysis in progress…</p>;
  if (row.status === "failed")
    return <FormAlert message={row.error ?? "The analysis failed. Try again."} />;
  const result = row.result as unknown as OptimizationResult;
  const rewrite = row.rewrite as unknown as Rewrite | null;

  async function suggest() {
    setError(null);
    setBusy(true);
    try {
      queryClient.setQueryData(key, await contentApi.rewrite(org.id, projectId, id));
    } catch (err) {
      setError(errorText(err, "AI suggestions are unavailable right now."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="text-4xl font-semibold" aria-label={`Score ${row.score ?? 0} out of 100`}>
          {row.score ?? "—"}
          <span className="text-muted-foreground text-base font-normal">/100</span>
        </div>
        <div className="text-sm">
          <p className="font-medium">“{row.keyword}”</p>
          <p className="text-muted-foreground break-all">{row.url}</p>
          <p className="text-muted-foreground">
            Intent: {result.intent.primary}
            {result.serp.own_position ? ` · Google position ${result.serp.own_position}` : ""}
            {result.serp.ai_answer
              ? result.serp.ai_cited
                ? " · cited in the AI Overview"
                : " · AI Overview does not cite you"
              : ""}
          </p>
        </div>
      </div>
      {!result.serp.available ? (
        <FormAlert message={result.serp.note ?? "Live search results were unavailable."} />
      ) : null}
      <ul aria-label="Checks">
        {result.checks.map((c) => (
          <CheckRow key={c.id} check={c} />
        ))}
      </ul>
      {result.term_gaps.length > 0 ? (
        <div>
          <h3 className="mb-1 text-sm font-medium">Subtopics on ranking pages</h3>
          <div className="flex flex-wrap gap-1">
            {result.term_gaps.map((g) => (
              <Badge key={g.term} variant={g.your_uses ? "secondary" : "outline"}>
                {g.term}
                <span className="text-muted-foreground ml-1 text-[10px]">
                  {g.your_uses ? "✓" : `${g.competitors_using} pages`}
                </span>
              </Badge>
            ))}
          </div>
        </div>
      ) : null}
      {result.competitors.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>Ranking page</TableHead>
              <TableHead className="text-right">Words</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.competitors.map((c) => (
              <TableRow key={c.url}>
                <TableCell>{c.position}</TableCell>
                <TableCell className="text-sm">{c.domain}</TableCell>
                <TableCell className="text-right text-sm">
                  {c.word_count ?? (
                    <span className="text-muted-foreground">
                      {SKIP_LABEL[c.skipped ?? ""] ?? c.skipped}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
      <div className="space-y-2 rounded-md border p-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-medium">AI rewrite suggestions</h3>
          {canWrite ? (
            <Button size="sm" variant="outline" disabled={busy} onClick={() => void suggest()}>
              <Sparkles className="mr-1 h-4 w-4" aria-hidden />
              {rewrite ? "Suggest again" : "Suggest"}
            </Button>
          ) : null}
        </div>
        <FormAlert message={error} />
        {rewrite ? (
          <dl className="grid gap-1 text-sm sm:grid-cols-[8rem_1fr]">
            <dt className="text-muted-foreground">Title</dt>
            <dd>{rewrite.title}</dd>
            <dt className="text-muted-foreground">Meta description</dt>
            <dd>{rewrite.meta_description}</dd>
            <dt className="text-muted-foreground">H1</dt>
            <dd>{rewrite.h1}</dd>
            {rewrite.sections_to_add.length > 0 ? (
              <>
                <dt className="text-muted-foreground">Sections to add</dt>
                <dd>{rewrite.sections_to_add.join(" · ")}</dd>
              </>
            ) : null}
          </dl>
        ) : (
          <p className="text-muted-foreground text-xs">
            Optional, AI-generated drafts grounded in this analysis. Review before publishing.
          </p>
        )}
      </div>
    </div>
  );
}

function OptimizerTab({ projectId, market }: { projectId: string; market: Market }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const key = [...contentKeys.all(org.id, projectId), "optimizations"];
  const list = useQuery({
    queryKey: key,
    queryFn: () => contentApi.optimizations(org.id, projectId),
  });
  const [url, setUrl] = useState("");
  const [keyword, setKeyword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState<Job | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const job = useJob(org.id, started);
  useRefreshOnFinish(job, contentKeys.all(org.id, projectId));

  async function start(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const res = await contentApi.optimize(org.id, projectId, market.id, keyword, url);
      setSelected(res.optimization.id);
      setStarted(res.job);
    } catch (err) {
      setError(errorText(err, "Could not start the analysis."));
    }
  }

  const current = selected ?? list.data?.[0]?.id ?? null;
  return (
    <div className="space-y-4">
      <FormAlert message={error} />
      {canWrite ? (
        <form onSubmit={start} className="grid gap-2 md:grid-cols-[2fr_1fr_auto] md:items-end">
          <Field id="opt-url" label="Page URL">
            <Input
              id="opt-url"
              type="url"
              placeholder="https://"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </Field>
          <Field id="opt-keyword" label="Target keyword">
            <Input id="opt-keyword" value={keyword} onChange={(e) => setKeyword(e.target.value)} />
          </Field>
          <Button type="submit" disabled={!url.trim() || !keyword.trim() || isActive(job)}>
            Analyze
          </Button>
        </form>
      ) : null}
      {isActive(job) ? (
        <p role="status" className="text-muted-foreground text-sm">
          {job?.stage ?? "Analyzing"}… {Math.round((job?.progress ?? 0) * 100)}%
        </p>
      ) : null}
      {list.isPending ? (
        <Skeleton className="h-24" />
      ) : list.isError ? (
        <ErrorState error={list.error} />
      ) : list.data.length === 0 ? (
        <EmptyState
          title="No analyses yet"
          description="Compare a page with what ranks on Google for its keyword."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[16rem_1fr]">
          <ul className="space-y-1" aria-label="Analyses">
            {list.data.map((o) => (
              <li key={o.id}>
                <button
                  type="button"
                  aria-current={o.id === current}
                  onClick={() => setSelected(o.id)}
                  className={`w-full rounded-md px-2 py-1.5 text-left text-sm ${o.id === current ? "bg-muted font-medium" : "hover:bg-muted/50"}`}
                >
                  <span className="block truncate">{o.keyword}</span>
                  <span className="text-muted-foreground block text-xs">
                    {o.status === "completed" ? `Score ${o.score}` : o.status}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {current ? <OptimizationDetail key={current} projectId={projectId} id={current} /> : null}
        </div>
      )}
    </div>
  );
}

function BriefDetail({ projectId, id }: { projectId: string; id: string }) {
  const org = useOrg();
  const detail = useQuery({
    queryKey: [...contentKeys.all(org.id, projectId), "brief", id],
    queryFn: () => contentApi.brief(org.id, projectId, id),
  });
  if (detail.isPending) return <Skeleton className="h-64" />;
  if (detail.isError) return <ErrorState error={detail.error} />;
  if (detail.data.status === "running") return <p role="status">Building the brief…</p>;
  if (detail.data.status === "failed")
    return <FormAlert message={detail.data.error ?? "The brief failed. Try again."} />;
  const brief = detail.data.brief as unknown as BriefData;
  const list = (title: string, items: string[]) =>
    items.length > 0 ? (
      <div>
        <h3 className="mb-1 text-sm font-medium">{title}</h3>
        <ul className="list-disc pl-5 text-sm">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    ) : null;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="text-sm">
          <p className="font-medium">“{brief.keyword}”</p>
          <p className="text-muted-foreground">
            Intent: {brief.intent} · Schema: {brief.schema_type}
            {brief.word_count_range
              ? ` · ${brief.word_count_range[0]}–${brief.word_count_range[1]} words`
              : ""}
          </p>
        </div>
        <Button asChild size="sm" variant="outline">
          <a href={contentApi.markdownUrl(org.id, projectId, id)} download>
            <Download className="mr-1 h-4 w-4" aria-hidden /> Markdown
          </a>
        </Button>
      </div>
      {brief.notes.map((n) => (
        <p key={n} className="text-muted-foreground text-xs">
          {n}
        </p>
      ))}
      {list(
        "Suggested outline",
        brief.outline.map((s) => `${s.heading} (${s.pages} ranking pages)`),
      )}
      {list("Questions to answer", brief.questions)}
      {list("Terms to cover", brief.terms)}
      {list("Secondary keywords", brief.secondary_keywords)}
      {list(
        "Link from these pages",
        brief.internal_links.map((l) => `${l.title} — ${l.url}`),
      )}
    </div>
  );
}

function BriefsTab({ projectId, market }: { projectId: string; market: Market }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const list = useQuery({
    queryKey: [...contentKeys.all(org.id, projectId), "briefs"],
    queryFn: () => contentApi.briefs(org.id, projectId),
  });
  const [keyword, setKeyword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState<Job | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const job = useJob(org.id, started);
  useRefreshOnFinish(job, contentKeys.all(org.id, projectId));

  async function start(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const res = await contentApi.createBrief(org.id, projectId, market.id, keyword);
      setSelected(res.brief.id);
      setStarted(res.job);
    } catch (err) {
      setError(errorText(err, "Could not start the brief."));
    }
  }

  const current = selected ?? list.data?.[0]?.id ?? null;
  return (
    <div className="space-y-4">
      <FormAlert message={error} />
      {canWrite ? (
        <form onSubmit={start} className="flex flex-wrap items-end gap-2">
          <Field id="brief-keyword" label="Keyword to write for">
            <Input
              id="brief-keyword"
              className="w-80"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={!keyword.trim() || isActive(job)}>
            Create brief
          </Button>
        </form>
      ) : null}
      {list.isPending ? (
        <Skeleton className="h-24" />
      ) : list.isError ? (
        <ErrorState error={list.error} />
      ) : list.data.length === 0 ? (
        <EmptyState
          title="No briefs yet"
          description="Build an outline from what ranks on Google for a keyword."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[16rem_1fr]">
          <ul className="space-y-1" aria-label="Briefs">
            {list.data.map((b) => (
              <li key={b.id}>
                <button
                  type="button"
                  aria-current={b.id === current}
                  onClick={() => setSelected(b.id)}
                  className={`w-full truncate rounded-md px-2 py-1.5 text-left text-sm ${b.id === current ? "bg-muted font-medium" : "hover:bg-muted/50"}`}
                >
                  {b.keyword}
                </button>
              </li>
            ))}
          </ul>
          {current ? <BriefDetail key={current} projectId={projectId} id={current} /> : null}
        </div>
      )}
    </div>
  );
}

function TargetEditor({
  projectId,
  keywordId,
  value,
}: {
  projectId: string;
  keywordId: string;
  value: string | null;
}) {
  const org = useOrg();
  const queryClient = useQueryClient();
  const [text, setText] = useState(value ?? "");
  const [error, setError] = useState<string | null>(null);
  async function save(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await contentApi.setTarget(org.id, projectId, keywordId, text.trim() || null);
      await queryClient.invalidateQueries({ queryKey: contentKeys.all(org.id, projectId) });
    } catch (err) {
      setError(errorText(err, "Could not save the target page."));
    }
  }
  return (
    <form onSubmit={save} className="flex gap-1">
      <Input
        aria-label="Target page"
        className="h-8 min-w-56 text-xs"
        placeholder="https://"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Button size="sm" variant="outline" type="submit" disabled={text === (value ?? "")}>
        Save
      </Button>
      {error ? (
        <span role="alert" className="text-destructive text-xs">
          {error}
        </span>
      ) : null}
    </form>
  );
}

function MapTab({ projectId }: { projectId: string }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const map = useQuery({
    queryKey: [...contentKeys.all(org.id, projectId), "map"],
    queryFn: () => contentApi.keywordMap(org.id, projectId),
  });
  if (map.isPending) return <Skeleton className="h-40" />;
  if (map.isError) return <ErrorState error={map.error} />;
  if (map.data.length === 0)
    return (
      <EmptyState
        title="No tracked keywords"
        description="Track keywords first, then assign each one the page that should rank."
      />
    );
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Keyword</TableHead>
          <TableHead>Target page</TableHead>
          <TableHead>Ranking page (Google)</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {map.data.map((r) => (
          <TableRow key={r.keyword_id}>
            <TableCell className="font-medium">{r.keyword}</TableCell>
            <TableCell>
              {canWrite ? (
                <TargetEditor projectId={projectId} keywordId={r.keyword_id} value={r.target_url} />
              ) : (
                <span className="text-xs break-all">{r.target_url ?? "—"}</span>
              )}
            </TableCell>
            <TableCell className="text-xs break-all">
              {r.ranking_url ?? "—"}
              {r.position !== null ? (
                <span className="text-muted-foreground"> · #{r.position}</span>
              ) : null}
            </TableCell>
            <TableCell>
              <Badge variant={r.status === "mismatch" ? "destructive" : "outline"}>
                {MAP_LABEL[r.status] ?? r.status}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function CannibalizationTab({ projectId }: { projectId: string }) {
  const org = useOrg();
  const report = useQuery({
    queryKey: [...contentKeys.all(org.id, projectId), "cannibalization"],
    queryFn: () => contentApi.cannibalization(org.id, projectId),
  });
  if (report.isPending) return <Skeleton className="h-40" />;
  if (report.isError) return <ErrorState error={report.error} />;
  if (!report.data.has_search_console_data)
    return (
      <EmptyState
        title="Search Console data needed"
        description="Connect Google Search Console for this project to find pages competing for the same queries."
      />
    );
  if (report.data.issues.length === 0)
    return (
      <EmptyState
        title="No cannibalization found"
        description={`No query split its impressions across several of your pages in the last ${report.data.window_days} days.`}
      />
    );
  return (
    <div className="space-y-4">
      {report.data.issues.map((issue) => (
        <div key={issue.query} className="rounded-md border p-3">
          <p className="text-sm font-medium">
            {issue.query}{" "}
            <span className="text-muted-foreground font-normal">
              · {issue.impressions.toLocaleString()} impressions
            </span>
          </p>
          <ul className="mt-1 space-y-0.5 text-xs">
            {issue.pages.map((p) => (
              <li key={p.page} className="break-all">
                {Math.round(p.share * 100)}% · pos {p.position} · {p.page}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function marketLabel(m: Market): string {
  return `${m.country} · ${m.language} · ${m.device}${m.location ? ` · ${m.location}` : ""}`;
}

export function ContentPage({ projectId }: { projectId: string }) {
  const org = useOrg();
  const [tab, setTab] = useState<Tab>("optimizer");
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
            className="text-muted-foreground text-sm hover:underline"
          >
            ← {project.data.name}
          </Link>
          <h1 className="text-2xl font-semibold">Content</h1>
        </div>
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
      </div>
      <div className="flex gap-1 border-b" role="tablist" aria-label="Content views">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={tab === id}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === id ? "border-primary font-medium" : "text-muted-foreground border-transparent"}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{TABS.find(([id]) => id === tab)?.[1]}</CardTitle>
          <CardDescription>
            {tab === "optimizer"
              ? "Explainable checks against the pages that rank on Google for your keyword."
              : tab === "briefs"
                ? "Outlines, questions and terms taken from what ranks today."
                : tab === "map"
                  ? "Which page should rank for each keyword, and which page Google actually shows."
                  : "Queries where several of your pages compete in Google Search Console."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {tab === "optimizer" ? (
            <OptimizerTab projectId={projectId} market={market} />
          ) : tab === "briefs" ? (
            <BriefsTab projectId={projectId} market={market} />
          ) : tab === "map" ? (
            <MapTab projectId={projectId} />
          ) : (
            <CannibalizationTab projectId={projectId} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
