"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Sparkles, Trash2 } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import type { Job } from "@/features/audit/api";
import { useJob } from "@/features/audit/use-job";
import { projectsApi, type Market } from "@/features/orgs/api";
import { engineLabel } from "@/features/orgs/engines";
import { errorText } from "@/features/orgs/errors";
import { useCan, useOrg } from "@/features/orgs/org-context";

import { keywordKeys, keywordsApi, type Analysis, type Position, type TrackedKeyword } from "./api";

const numberFmt = new Intl.NumberFormat();
const TABS = [
  ["rankings", "Rankings"],
  ["research", "Research"],
  ["opportunities", "Opportunities"],
  ["competitors", "Competitors"],
] as const;
type Tab = (typeof TABS)[number][0];

function marketLabel(m: Market): string {
  return `${m.country} · ${m.language} · ${m.device}${m.location ? ` · ${m.location}` : ""}`;
}

function PositionCell({ positions, engine }: { positions: Position[]; engine: string }) {
  const own = positions.filter((p) => p.engine === engine);
  if (own.length === 0) return <span className="text-muted-foreground">—</span>;
  return (
    <div className="space-y-0.5">
      {own.map((p) => {
        const change = p.position !== null && p.previous !== null ? p.previous - p.position : null;
        return (
          <div key={p.source} className="flex items-center gap-1 text-sm">
            <span className="font-medium">{p.position === null ? ">100" : p.position}</span>
            {change ? (
              change > 0 ? (
                <ArrowUp className="text-accent h-3 w-3" aria-label={`up ${change}`} />
              ) : (
                <ArrowDown className="text-destructive h-3 w-3" aria-label={`down ${-change}`} />
              )
            ) : null}
            <span className="text-muted-foreground text-xs">
              {p.source === "gsc" ? "Search Console" : p.source === "bing" ? "Bing WMT" : "live"}
            </span>
            {p.ai_cited ? (
              <Badge variant="secondary" className="px-1 text-[10px]">
                <Sparkles className="mr-0.5 h-3 w-3" aria-hidden /> AI cited
              </Badge>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function RankingsTab({ projectId, market }: { projectId: string; market: Market }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const key = [...keywordKeys.all(org.id, projectId), "list", market.id];
  const list = useQuery({
    queryKey: key,
    queryFn: () => keywordsApi.list(org.id, projectId, market.id),
  });
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState<Job | null>(null);
  const job = useJob(org.id, started);
  const engines = market.search_engines;

  async function add(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await keywordsApi.add(
        org.id,
        projectId,
        market.id,
        text
          .split("\n")
          .map((k) => k.trim())
          .filter(Boolean),
      );
      setText("");
      await queryClient.invalidateQueries({ queryKey: key });
    } catch (err) {
      setError(errorText(err, "Could not add the keywords."));
    }
  }

  async function check() {
    setError(null);
    try {
      setStarted(await keywordsApi.check(org.id, projectId));
    } catch (err) {
      setError(errorText(err, "Could not start the ranking check."));
    }
  }

  const finishedId = job && !["queued", "running"].includes(job.status) ? job.id : null;
  useEffect(() => {
    if (finishedId) void queryClient.invalidateQueries({ queryKey: key });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key is derived from stable ids
  }, [finishedId, queryClient]);

  return (
    <div className="space-y-4">
      <FormAlert message={error} />
      {canWrite ? (
        <div className="grid gap-4 md:grid-cols-[1fr_auto]">
          <form onSubmit={add} className="space-y-2">
            <Field id="new-keywords" label="Track keywords" hint="One per line.">
              <Textarea
                id="new-keywords"
                rows={3}
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </Field>
            <Button size="sm" type="submit" disabled={!text.trim()}>
              Add keywords
            </Button>
          </form>
          <div className="space-y-2">
            <Button
              onClick={() => void check()}
              disabled={Boolean(job && ["queued", "running"].includes(job.status))}
            >
              Check rankings now
            </Button>
            {job && ["queued", "running"].includes(job.status) ? (
              <p role="status" className="text-muted-foreground text-xs">
                Checking… {Math.round((job.progress ?? 0) * 100)}%
              </p>
            ) : null}
            {job?.status === "succeeded" && typeof job.result?.note === "string" ? (
              <p className="text-xs">{job.result.note}</p>
            ) : null}
          </div>
        </div>
      ) : null}
      {list.isPending ? (
        <Skeleton className="h-40" />
      ) : list.isError ? (
        <ErrorState error={list.error} />
      ) : list.data.length === 0 ? (
        <EmptyState
          title="No keywords tracked"
          description="Add keywords to track their positions in this market."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Keyword</TableHead>
              <TableHead>Intent</TableHead>
              <TableHead className="text-right">Volume</TableHead>
              {engines.map((e) => (
                <TableHead key={e}>{engineLabel(e)}</TableHead>
              ))}
              <TableHead className="sr-only">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data.map((k: TrackedKeyword) => (
              <TableRow key={k.id}>
                <TableCell className="font-medium">{k.keyword}</TableCell>
                <TableCell>
                  <Badge variant="outline">{k.intent}</Badge>
                </TableCell>
                <TableCell className="text-right text-sm">
                  {k.volume !== null ? numberFmt.format(k.volume) : "—"}
                  {k.volume_source === "bing" ? (
                    <span className="text-muted-foreground block text-[10px]">
                      Bing impressions
                    </span>
                  ) : null}
                </TableCell>
                {engines.map((e) => (
                  <TableCell key={e}>
                    <PositionCell positions={k.positions} engine={e} />
                  </TableCell>
                ))}
                <TableCell className="text-right">
                  {canWrite ? (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Stop tracking ${k.keyword}`}
                      onClick={() =>
                        void keywordsApi
                          .remove(org.id, projectId, k.id)
                          .then(() => queryClient.invalidateQueries({ queryKey: key }))
                      }
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

function AnalysisCard({ analysis }: { analysis: Analysis }) {
  return (
    <div className="space-y-3 rounded-md border p-4">
      <div className="flex flex-wrap items-baseline gap-4">
        <div>
          <div className="text-muted-foreground text-xs">Keyword difficulty</div>
          <div className="text-3xl font-semibold">{analysis.difficulty.score}</div>
          <div className="text-muted-foreground text-xs">
            confidence: {analysis.difficulty.confidence}
          </div>
        </div>
        <div className="text-muted-foreground text-xs">
          Prominence {Math.round(analysis.difficulty.prominence * 100)}% · On-target titles{" "}
          {Math.round(analysis.difficulty.targeting * 100)}% · Homepages{" "}
          {Math.round(analysis.difficulty.root_pages * 100)}% · SERP crowding{" "}
          {Math.round(analysis.difficulty.crowding * 100)}%
        </div>
        <Badge variant="outline">{analysis.intent}</Badge>
      </div>
      {analysis.features.length ? (
        <p className="text-xs">SERP features: {analysis.features.join(", ")}</p>
      ) : null}
      <ol className="space-y-1 text-sm">
        {analysis.results.slice(0, 10).map((r) => (
          <li key={r.position} className={r.is_own ? "font-semibold" : ""}>
            {r.position}. {r.title || r.domain}{" "}
            <span className="text-muted-foreground text-xs">{r.domain}</span>
            {r.is_own ? (
              <Badge className="ml-1">You</Badge>
            ) : r.is_competitor ? (
              <Badge variant="outline" className="ml-1">
                Competitor
              </Badge>
            ) : null}
          </li>
        ))}
      </ol>
      <p className="text-muted-foreground text-xs">
        {analysis.from_cache ? "From today's shared SERP cache." : "Fetched live."}{" "}
        {analysis.fetched_on}
      </p>
    </div>
  );
}

function ResearchTab({ projectId, market }: { projectId: string; market: Market }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const [seed, setSeed] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof keywordsApi.research>> | null>(
    null,
  );
  const [analysis, setAnalysis] = useState<Analysis | null>(null);

  async function search(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setResult(await keywordsApi.research(org.id, projectId, market.id, seed.trim()));
    } catch (err) {
      setError(errorText(err, "Could not research keywords."));
    }
  }

  async function analyze(keyword: string) {
    setError(null);
    try {
      setAnalysis(await keywordsApi.analyze(org.id, projectId, market.id, keyword, "google"));
    } catch (err) {
      setError(errorText(err, "Could not analyze the SERP."));
    }
  }

  async function track(keyword: string) {
    await keywordsApi.add(org.id, projectId, market.id, [keyword]);
    await queryClient.invalidateQueries({ queryKey: keywordKeys.all(org.id, projectId) });
    setResult((r) =>
      r
        ? { ...r, ideas: r.ideas.map((i) => (i.keyword === keyword ? { ...i, tracked: true } : i)) }
        : r,
    );
  }

  return (
    <div className="space-y-4">
      <form onSubmit={search} className="flex flex-wrap items-end gap-2">
        <Field id="seed" label="Seed keyword">
          <Input
            id="seed"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            className="w-72"
          />
        </Field>
        <Button type="submit" disabled={seed.trim().length < 2}>
          Find ideas
        </Button>
      </form>
      <FormAlert message={error} />
      {analysis ? <AnalysisCard analysis={analysis} /> : null}
      {result ? (
        <>
          <p className="text-muted-foreground text-xs">
            Source:{" "}
            {result.source === "google_ads"
              ? "Google Ads Keyword Planner (official volumes)"
              : "Bing Webmaster Tools (Bing search impressions)"}
          </p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Keyword</TableHead>
                <TableHead className="text-right">Volume</TableHead>
                <TableHead>Intent</TableHead>
                <TableHead>CPC</TableHead>
                <TableHead className="sr-only">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.ideas.map((i) => (
                <TableRow key={i.keyword}>
                  <TableCell>{i.keyword}</TableCell>
                  <TableCell className="text-right">
                    {i.volume !== null ? numberFmt.format(i.volume) : "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" title={i.intent_reasons.join("; ")}>
                      {i.intent}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    {i.cpc_low !== null && i.cpc_high !== null
                      ? `${i.cpc_low.toFixed(2)}–${i.cpc_high.toFixed(2)}`
                      : "—"}
                  </TableCell>
                  <TableCell className="space-x-1 text-right">
                    {canWrite ? (
                      <>
                        <Button size="sm" variant="ghost" onClick={() => void analyze(i.keyword)}>
                          Analyze SERP
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={i.tracked}
                          onClick={() => void track(i.keyword)}
                        >
                          {i.tracked ? "Tracked" : "Track"}
                        </Button>
                      </>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      ) : null}
    </div>
  );
}

function OpportunitiesTab({ projectId }: { projectId: string }) {
  const org = useOrg();
  const opps = useQuery({
    queryKey: [...keywordKeys.all(org.id, projectId), "opps"],
    queryFn: () => keywordsApi.opportunities(org.id, projectId),
  });
  if (opps.isPending) return <Skeleton className="h-40" />;
  if (opps.isError) return <ErrorState error={opps.error} />;
  if (!opps.data.has_data)
    return (
      <EmptyState
        title="Connect Search Console"
        description="Opportunities come from your own Search Console data: queries ranking 8–20 and queries whose CTR is below what their position should earn."
      />
    );
  return (
    <div className="space-y-2">
      <p className="text-muted-foreground text-xs">
        {opps.data.date_from} – {opps.data.date_to} · expected CTR from{" "}
        {opps.data.curve_source === "own"
          ? "your own Search Console data"
          : "an industry-average curve (not enough of your data yet)"}
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Query</TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="text-right">Position</TableHead>
            <TableHead className="text-right">Impressions</TableHead>
            <TableHead className="text-right">CTR / expected</TableHead>
            <TableHead className="text-right">Potential clicks</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {opps.data.items.map((o) => (
            <TableRow key={o.query}>
              <TableCell>{o.query}</TableCell>
              <TableCell>
                <Badge variant={o.kind === "striking_distance" ? "secondary" : "warning"}>
                  {o.kind === "striking_distance" ? "Striking distance" : "Low CTR"}
                </Badge>
              </TableCell>
              <TableCell className="text-right">{o.position}</TableCell>
              <TableCell className="text-right">{numberFmt.format(o.impressions)}</TableCell>
              <TableCell className="text-right">
                {(o.ctr * 100).toFixed(1)}% / {(o.expected_ctr * 100).toFixed(1)}%
              </TableCell>
              <TableCell className="text-right">+{numberFmt.format(o.potential_clicks)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function CompetitorsTab({ projectId, market }: { projectId: string; market: Market }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const base = keywordKeys.all(org.id, projectId);
  const [engine, setEngine] = useState(market.search_engines[0] ?? "google");
  const [domain, setDomain] = useState("");
  const [error, setError] = useState<string | null>(null);
  const competitors = useQuery({
    queryKey: [...base, "competitors"],
    queryFn: () => keywordsApi.competitors(org.id, projectId),
  });
  const sov = useQuery({
    queryKey: [...base, "sov", market.id, engine],
    queryFn: () => keywordsApi.shareOfVoice(org.id, projectId, market.id, engine),
  });

  async function add(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await keywordsApi.addCompetitor(org.id, projectId, domain.trim());
      setDomain("");
      await queryClient.invalidateQueries({ queryKey: [...base, "competitors"] });
    } catch (err) {
      setError(errorText(err, "Could not add the competitor."));
    }
  }

  return (
    <div className="space-y-4">
      {canWrite ? (
        <form onSubmit={add} className="flex flex-wrap items-end gap-2">
          <Field id="competitor" label="Add competitor domain">
            <Input
              id="competitor"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-64"
            />
          </Field>
          <Button type="submit" size="sm" disabled={domain.trim().length < 3}>
            Add
          </Button>
        </form>
      ) : null}
      <FormAlert message={error} />
      <ul className="flex flex-wrap gap-2">
        {(competitors.data ?? []).map((c) => (
          <li key={c.id}>
            <Badge variant="outline">
              {c.domain}
              {canWrite ? (
                <button
                  type="button"
                  className="ml-1"
                  aria-label={`Remove ${c.domain}`}
                  onClick={() =>
                    void keywordsApi
                      .removeCompetitor(org.id, projectId, c.id)
                      .then(() =>
                        queryClient.invalidateQueries({ queryKey: [...base, "competitors"] }),
                      )
                  }
                >
                  ×
                </button>
              ) : null}
            </Badge>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">Share of voice</h3>
        <NativeSelect
          aria-label="Engine"
          className="h-8 w-40"
          value={engine}
          onChange={(e) => setEngine(e.target.value as typeof engine)}
        >
          {market.search_engines.map((e) => (
            <option key={e} value={e}>
              {engineLabel(e)}
            </option>
          ))}
        </NativeSelect>
      </div>
      {sov.data && sov.data.rows.length ? (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Domain</TableHead>
                <TableHead className="text-right">Share of voice</TableHead>
                <TableHead className="text-right">Keywords ranking</TableHead>
                <TableHead className="text-right">Avg. position</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sov.data.rows.map((r) => (
                <TableRow key={r.domain}>
                  <TableCell className={r.is_own ? "font-semibold" : ""}>{r.domain}</TableCell>
                  <TableCell className="text-right">{(r.share * 100).toFixed(1)}%</TableCell>
                  <TableCell className="text-right">{r.keywords_ranking}</TableCell>
                  <TableCell className="text-right">{r.average_position ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="text-muted-foreground text-xs">
            Based on the {sov.data.date} live check of {sov.data.keywords} keywords
            {sov.data.volumes_known
              ? ", weighted by search volume."
              : "; volumes unavailable, so keywords are weighted equally."}
          </p>
        </>
      ) : (
        <p className="text-muted-foreground text-sm">
          Run a ranking check to compare against competitors.
        </p>
      )}
    </div>
  );
}

export function KeywordsPage({ projectId }: { projectId: string }) {
  const org = useOrg();
  const [tab, setTab] = useState<Tab>("rankings");
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
          <h1 className="text-2xl font-semibold">Keywords</h1>
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
      <div className="flex gap-1 border-b" role="tablist" aria-label="Keyword views">
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
            {tab === "rankings"
              ? "Your own positions come free from Search Console and Bing Webmaster Tools; live checks add competitors, SERP features and AI answers."
              : tab === "research"
                ? "Ideas from official sources, with intent and SerpTank keyword difficulty."
                : tab === "opportunities"
                  ? "Quick wins from your Search Console data."
                  : "Who you compete with on your tracked keywords."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {tab === "rankings" ? (
            <RankingsTab key={market.id} projectId={projectId} market={market} />
          ) : null}
          {tab === "research" ? (
            <ResearchTab key={market.id} projectId={projectId} market={market} />
          ) : null}
          {tab === "opportunities" ? <OpportunitiesTab projectId={projectId} /> : null}
          {tab === "competitors" ? (
            <CompetitorsTab key={market.id} projectId={projectId} market={market} />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
