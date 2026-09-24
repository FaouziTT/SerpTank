"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
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
import { errorText } from "@/features/orgs/errors";
import { useCan, useOrg } from "@/features/orgs/org-context";

import { aiApi, aiKeys, type Rate } from "./api";

const TABS = [
  ["overview", "Overview"],
  ["prompts", "Prompts"],
  ["answers", "Answers"],
  ["readiness", "Readiness"],
] as const;
type Tab = (typeof TABS)[number][0];

export const ENGINE_LABEL: Record<string, string> = {
  google_ai_overview: "Google AI Overviews",
  google_ai_mode: "Google AI Mode",
  chatgpt: "ChatGPT",
  perplexity: "Perplexity",
  gemini: "Gemini",
  copilot: "Copilot",
  claude: "Claude",
};
const label = (engine: string) => ENGINE_LABEL[engine] ?? engine;

/** "67% (30–94%, n=3)": a rate is never shown without its sample size and interval. */
export function formatRate(rate: Rate): string {
  if (rate.rate === null) return "—";
  const pct = (v: number | null) => `${Math.round((v ?? 0) * 100)}%`;
  return `${pct(rate.rate)} (${Math.round((rate.low ?? 0) * 100)}–${pct(rate.high)}, n=${rate.trials})`;
}

function isActive(job: Job | null): boolean {
  return Boolean(job && ["queued", "running"].includes(job.status));
}

function OverviewTab({ projectId }: { projectId: string }) {
  const org = useOrg();
  const vis = useQuery({
    queryKey: [...aiKeys.all(org.id, projectId), "visibility"],
    queryFn: () => aiApi.visibility(org.id, projectId),
  });
  if (vis.isPending) return <Skeleton className="h-40" />;
  if (vis.isError) return <ErrorState error={vis.error} />;
  const data = vis.data;
  return (
    <div className="space-y-6">
      {data.engines.length === 0 ? (
        <EmptyState
          title="No AI answers sampled yet"
          description="Add prompts and run a check to see how AI answers mention and cite you."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.engines.map((e) => (
            <div key={e.engine} className="space-y-1 rounded-md border p-3 text-sm">
              <p className="font-medium">{label(e.engine)}</p>
              {e.engine === "google_ai_overview" ? (
                <p>
                  <span className="text-muted-foreground">AI Overview shown: </span>
                  {formatRate(e.answer_rate)}
                </p>
              ) : null}
              <p>
                <span className="text-muted-foreground">Mentioned: </span>
                {formatRate(e.mention_rate)}
              </p>
              <p>
                <span className="text-muted-foreground">Cited: </span>
                {formatRate(e.citation_rate)}
              </p>
              {e.avg_sentiment !== null ? (
                <p className="text-muted-foreground text-xs">
                  Tone (keyword heuristic): {e.avg_sentiment > 0 ? "+" : ""}
                  {e.avg_sentiment}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      )}
      {data.share_of_voice.length > 0 ? (
        <div>
          <h3 className="mb-1 text-sm font-medium">Share of voice in AI answers</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Brand</TableHead>
                <TableHead className="text-right">Mentions</TableHead>
                <TableHead className="text-right">Citations</TableHead>
                <TableHead className="text-right">Share</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.share_of_voice.map((r) => (
                <TableRow key={r.domain}>
                  <TableCell className={r.is_own ? "font-medium" : ""}>
                    {r.domain} {r.is_own ? <Badge variant="secondary">You</Badge> : null}
                  </TableCell>
                  <TableCell className="text-right">{r.mentions}</TableCell>
                  <TableCell className="text-right">{r.citations}</TableCell>
                  <TableCell className="text-right">
                    {r.share === null ? "—" : `${Math.round(r.share * 100)}%`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
      <div>
        <h3 className="mb-1 text-sm font-medium">From your own data</h3>
        {data.first_party.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            Import the Search Console Gen-AI report or Bing AI Performance on the Search data page
            to see first-party AI impressions and citations.
          </p>
        ) : (
          <ul className="text-sm">
            {data.first_party.map((r) => (
              <li key={`${r.source}-${r.surface}`}>
                {label(r.surface === "ai_overview" ? "google_ai_overview" : r.surface)} (
                {r.source === "bing_ai" ? "Bing Webmaster Tools" : "Search Console"}):{" "}
                {r.impressions.toLocaleString()} impressions
                {r.citations ? `, ${r.citations.toLocaleString()} citations` : ""}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function PromptsTab({ projectId, market }: { projectId: string; market: Market }) {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const queryClient = useQueryClient();
  const settings = useQuery({
    queryKey: [...aiKeys.all(org.id, projectId), "settings"],
    queryFn: () => aiApi.settings(org.id, projectId),
  });
  const prompts = useQuery({
    queryKey: [...aiKeys.all(org.id, projectId), "prompts"],
    queryFn: () => aiApi.prompts(org.id, projectId),
  });
  const suggestions = useQuery({
    queryKey: [...aiKeys.all(org.id, projectId), "suggestions", market.id],
    queryFn: () => aiApi.suggestions(org.id, projectId, market.id),
    enabled: canWrite,
  });
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState<Job | null>(null);
  const job = useJob(org.id, started);
  const refresh = () => queryClient.invalidateQueries({ queryKey: aiKeys.all(org.id, projectId) });
  const finishedId = job && !isActive(job) ? job.id : null;
  useEffect(() => {
    if (finishedId) void queryClient.invalidateQueries({ queryKey: aiKeys.all(org.id, projectId) });
  }, [finishedId, queryClient, org.id, projectId]);

  async function act(fn: () => Promise<unknown>, fallback: string) {
    setError(null);
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(errorText(err, fallback));
    }
  }

  async function add(event: FormEvent) {
    event.preventDefault();
    const lines = text
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    await act(async () => {
      await aiApi.addPrompts(org.id, projectId, market.id, lines);
      setText("");
    }, "Could not add the prompts.");
  }

  async function run() {
    setError(null);
    try {
      setStarted(await aiApi.run(org.id, projectId));
    } catch (err) {
      setError(errorText(err, "Could not start the check."));
    }
  }

  return (
    <div className="space-y-4">
      <FormAlert message={error} />
      {settings.data ? (
        <div className="flex flex-wrap gap-1" aria-label="Engines">
          {settings.data.engines
            .filter((e) => e.selected)
            .map((e) => (
              <Badge
                key={e.engine}
                variant={e.available && e.entitled ? "secondary" : "outline"}
                title={!e.entitled ? "Not included in your plan" : (e.note ?? undefined)}
              >
                {label(e.engine)}
                {!e.entitled ? " · upgrade" : !e.available ? " · not available" : ""}
              </Badge>
            ))}
          <span className="text-muted-foreground ml-2 text-xs">
            {settings.data.prompts_used_this_month.toLocaleString()} of{" "}
            {settings.data.prompts_per_month.toLocaleString()} AI samples used this month
          </span>
        </div>
      ) : null}
      {canWrite ? (
        <div className="grid gap-4 md:grid-cols-[1fr_auto]">
          <form onSubmit={add} className="space-y-2">
            <Field
              id="new-prompts"
              label="Prompts to track"
              hint="One per line, as a user would ask."
            >
              <Textarea
                id="new-prompts"
                rows={3}
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </Field>
            <Button size="sm" type="submit" disabled={!text.trim()}>
              Add prompts
            </Button>
          </form>
          <div className="space-y-2">
            <Button onClick={() => void run()} disabled={isActive(job)}>
              Check AI answers now
            </Button>
            {isActive(job) ? (
              <p role="status" className="text-muted-foreground text-xs">
                Sampling… {Math.round((job?.progress ?? 0) * 100)}%
              </p>
            ) : null}
            {job?.status === "succeeded" ? (
              <p role="status" className="text-xs">
                {typeof job.result?.note === "string"
                  ? job.result.note
                  : `Done: ${String(job.result?.samples ?? 0)} answers sampled.`}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
      {canWrite && suggestions.data && suggestions.data.length > 0 ? (
        <div>
          <h3 className="mb-1 text-sm font-medium">Suggested from your tracked keywords</h3>
          <ul className="space-y-1 text-sm">
            {suggestions.data.slice(0, 5).map((s) => (
              <li key={s.keyword} className="flex items-center gap-2">
                <span>{s.prompt}</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    void act(
                      () => aiApi.addPrompts(org.id, projectId, market.id, [s.prompt], s.keyword),
                      "Could not add the prompt.",
                    )
                  }
                >
                  Add
                </Button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {prompts.isPending ? (
        <Skeleton className="h-24" />
      ) : prompts.isError ? (
        <ErrorState error={prompts.error} />
      ) : prompts.data.length === 0 ? (
        <EmptyState
          title="No prompts yet"
          description="Track the questions your customers ask AI assistants."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Prompt</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="sr-only">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {prompts.data.map((pr) => (
              <TableRow key={pr.id}>
                <TableCell>{pr.prompt}</TableCell>
                <TableCell>
                  <Badge variant="outline">{pr.active ? "Active" : "Paused"}</Badge>
                </TableCell>
                <TableCell className="text-right">
                  {canWrite ? (
                    <div className="flex justify-end gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          void act(
                            () => aiApi.setActive(org.id, projectId, pr.id, !pr.active),
                            "Could not update the prompt.",
                          )
                        }
                      >
                        {pr.active ? "Pause" : "Resume"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label={`Delete ${pr.prompt}`}
                        onClick={() =>
                          void act(
                            () => aiApi.removePrompt(org.id, projectId, pr.id),
                            "Could not delete the prompt.",
                          )
                        }
                      >
                        <Trash2 className="h-4 w-4" aria-hidden />
                      </Button>
                    </div>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {canWrite && settings.data ? (
        <BrandTerms
          projectId={projectId}
          initial={settings.data.brand_terms}
          samples={settings.data.samples_per_prompt}
        />
      ) : null}
    </div>
  );
}

function BrandTerms({
  projectId,
  initial,
  samples,
}: {
  projectId: string;
  initial: string[];
  samples: number;
}) {
  const org = useOrg();
  const [terms, setTerms] = useState(initial.join(", "));
  const [count, setCount] = useState(String(samples));
  const [message, setMessage] = useState<string | null>(null);
  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    try {
      await aiApi.saveSettings(
        org.id,
        projectId,
        terms
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        Number(count),
      );
      setMessage("Saved.");
    } catch (err) {
      setMessage(errorText(err, "Could not save the settings."));
    }
  }
  return (
    <form
      onSubmit={save}
      className="grid gap-2 border-t pt-4 md:grid-cols-[2fr_1fr_auto] md:items-end"
    >
      <Field id="brand-terms" label="Brand names to look for" hint="Comma-separated.">
        <Input id="brand-terms" value={terms} onChange={(e) => setTerms(e.target.value)} />
      </Field>
      <Field id="samples" label="Answers per prompt">
        <Input
          id="samples"
          type="number"
          min={1}
          max={10}
          value={count}
          onChange={(e) => setCount(e.target.value)}
        />
      </Field>
      <Button type="submit" variant="outline">
        Save
      </Button>
      {message ? (
        <p role="status" className="text-xs md:col-span-3">
          {message}
        </p>
      ) : null}
    </form>
  );
}

function AnswersTab({ projectId }: { projectId: string }) {
  const org = useOrg();
  const answers = useQuery({
    queryKey: [...aiKeys.all(org.id, projectId), "answers"],
    queryFn: () => aiApi.answers(org.id, projectId),
  });
  if (answers.isPending) return <Skeleton className="h-40" />;
  if (answers.isError) return <ErrorState error={answers.error} />;
  if (answers.data.length === 0)
    return <EmptyState title="No answers yet" description="Run a check to collect AI answers." />;
  return (
    <ul className="space-y-3">
      {answers.data.map((a) => (
        <li key={a.id} className="rounded-md border p-3 text-sm">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="font-medium">{label(a.engine)}</span>
            <span className="text-muted-foreground text-xs">{a.date}</span>
            {!a.answered ? <Badge variant="outline">No AI answer shown</Badge> : null}
            {a.mentioned ? <Badge variant="secondary">Mentioned</Badge> : null}
            {a.cited ? <Badge variant="secondary">Cited</Badge> : null}
          </div>
          {a.excerpt ? <p className="text-muted-foreground">{a.excerpt}</p> : null}
          {a.citations.length > 0 ? (
            <p className="text-muted-foreground mt-1 text-xs break-all">
              Sources: {a.citations.slice(0, 5).join(" · ")}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function ReadinessTab({ projectId }: { projectId: string }) {
  const org = useOrg();
  const readiness = useQuery({
    queryKey: [...aiKeys.all(org.id, projectId), "readiness"],
    queryFn: () => aiApi.readiness(org.id, projectId),
  });
  if (readiness.isPending) return <Skeleton className="h-40" />;
  if (readiness.isError) return <ErrorState error={readiness.error} />;
  const data = readiness.data;
  if (!data.available)
    return (
      <EmptyState
        title="Readiness needs a site audit"
        description={data.note ?? "Run a site audit first."}
      />
    );
  return (
    <div className="space-y-4">
      <div className="text-4xl font-semibold" aria-label={`Readiness ${data.score} out of 100`}>
        {data.score}
        <span className="text-muted-foreground text-base font-normal">/100</span>
      </div>
      <ul className="space-y-2">
        {data.components.map((c) => (
          <li key={c.id} className="text-sm">
            <p className="font-medium">
              {c.label} <span className="text-muted-foreground font-normal">· {c.score}/100</span>
            </p>
            <ul className="text-muted-foreground list-disc pl-5 text-xs">
              {c.findings.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}

function marketLabel(m: Market): string {
  return `${m.country} · ${m.language} · ${m.device}${m.location ? ` · ${m.location}` : ""}`;
}

export function AiVisibilityPage({ projectId }: { projectId: string }) {
  const org = useOrg();
  const [tab, setTab] = useState<Tab>("overview");
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
          <h1 className="text-2xl font-semibold">AI visibility</h1>
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
      <div className="flex gap-1 border-b" role="tablist" aria-label="AI visibility views">
        {TABS.map(([id, text]) => (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={tab === id}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === id ? "border-primary font-medium" : "text-muted-foreground border-transparent"}`}
            onClick={() => setTab(id)}
          >
            {text}
          </button>
        ))}
      </div>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{TABS.find(([id]) => id === tab)?.[1]}</CardTitle>
          <CardDescription>
            {tab === "overview"
              ? "How often AI answers mention and cite you. Answers vary between runs, so every rate shows its 95% range and sample size."
              : tab === "prompts"
                ? "The questions we ask each AI engine on your behalf."
                : tab === "answers"
                  ? "The latest sampled answers: the evidence behind the numbers."
                  : "Fundamentals that let AI search engines find, read and cite your site."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {tab === "overview" ? (
            <OverviewTab projectId={projectId} />
          ) : tab === "prompts" ? (
            <PromptsTab projectId={projectId} market={market} />
          ) : tab === "answers" ? (
            <AnswersTab projectId={projectId} />
          ) : (
            <ReadinessTab projectId={projectId} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
