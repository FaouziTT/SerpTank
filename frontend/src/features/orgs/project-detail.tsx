"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Field, FormAlert } from "@/components/forms/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";

import {
  keys,
  projectsApi,
  type Market,
  type MarketIn,
  type Project,
  type VerificationMethod,
} from "./api";
import { Confirm } from "./confirm";
import { engineLabel } from "./engines";
import { errorText } from "./errors";
import { DEFAULT_MARKET, MarketFields, marketErrors } from "./market-fields";
import { useEntitlements } from "./org-overview";
import { useCan, useOrg } from "./org-context";

type Instructions = Awaited<ReturnType<typeof projectsApi.startVerification>>;

function CopyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-muted-foreground text-xs">{label}</p>
      <code className="bg-muted block rounded px-2 py-1 text-sm break-all">{value}</code>
    </div>
  );
}

function VerificationCard({ project, canWrite }: { project: Project; canWrite: boolean }) {
  const org = useOrg();
  const queryClient = useQueryClient();
  const [instructions, setInstructions] = useState<Instructions | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start(method: VerificationMethod) {
    setError(null);
    setResult(null);
    try {
      setInstructions(await projectsApi.startVerification(org.id, project.id, method));
    } catch (err) {
      setError(errorText(err, "Could not start verification."));
    }
  }

  async function check() {
    setError(null);
    try {
      const res = await projectsApi.checkVerification(org.id, project.id);
      setResult(res.detail);
      if (res.verified) {
        await queryClient.invalidateQueries({ queryKey: keys.projects(org.id) });
      }
    } catch (err) {
      setError(errorText(err, "Could not check verification."));
    }
  }

  if (project.verified) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="text-accent h-5 w-5" aria-hidden /> Domain verified
          </CardTitle>
          <CardDescription>
            Ownership of {project.primary_domain} is verified
            {project.verification_method ? ` (${project.verification_method.toUpperCase()})` : ""}.
            Deep crawls and indexing submissions are enabled.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Verify domain ownership</CardTitle>
        <CardDescription>
          Required before deep or scheduled crawls and before submitting URLs to search engines.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        {!canWrite ? (
          <p className="text-muted-foreground text-sm">
            Ask an editor or admin to verify this domain.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void start("dns")}>
              Use a DNS TXT record
            </Button>
            <Button variant="outline" onClick={() => void start("html")}>
              Upload a file
            </Button>
          </div>
        )}
        {instructions?.method === "dns" ? (
          <div className="space-y-3" aria-label="DNS instructions">
            <p className="text-sm">Add this TXT record at your DNS provider:</p>
            <CopyValue label="Host / name" value={instructions.dns_record_name ?? ""} />
            <CopyValue label="Value" value={instructions.dns_record_value ?? ""} />
          </div>
        ) : null}
        {instructions?.method === "html" ? (
          <div className="space-y-3" aria-label="File instructions">
            <p className="text-sm">
              Publish a plain-text file at this URL containing only the token:
            </p>
            <CopyValue label="URL" value={instructions.file_url ?? ""} />
            <CopyValue label="File contents" value={instructions.file_contents ?? ""} />
          </div>
        ) : null}
        {instructions ? <Button onClick={() => void check()}>Check now</Button> : null}
        {result ? (
          <p role="status" className="text-sm">
            {result}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function MarketRow({
  market,
  onRemove,
  removable,
}: {
  market: Market;
  onRemove?: () => void;
  removable: boolean;
}) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3">
      <div className="space-y-1">
        <p className="text-sm font-medium">
          {market.country} · {market.language} · {market.device === "mobile" ? "Mobile" : "Desktop"}
          {market.location ? ` · ${market.location}` : ""}
        </p>
        <div className="flex flex-wrap gap-1">
          {market.search_engines.map((e) => (
            <Badge key={e} variant="outline">
              {engineLabel(e)}
            </Badge>
          ))}
          {market.ai_engines.map((e) => (
            <Badge key={e} variant="secondary">
              {engineLabel(e)}
            </Badge>
          ))}
        </div>
      </div>
      {onRemove && removable ? (
        <Confirm
          trigger={
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Remove market ${market.country}-${market.language}`}
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </Button>
          }
          title="Remove this market?"
          description="Tracking for this market stops. Historical data already collected is kept."
          confirmLabel="Remove"
          onConfirm={onRemove}
        />
      ) : null}
    </li>
  );
}

function AddMarketDialog({
  project,
  open,
  onOpenChange,
}: {
  project: Project;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const org = useOrg();
  const queryClient = useQueryClient();
  const entitlements = useEntitlements(org.id);
  const [market, setMarket] = useState<MarketIn>(DEFAULT_MARKET);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await projectsApi.addMarket(org.id, project.id, market);
      await queryClient.invalidateQueries({ queryKey: keys.projects(org.id) });
      setMarket(DEFAULT_MARKET);
      onOpenChange(false);
    } catch (err) {
      setError(errorText(err, "Could not add the market."));
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <form onSubmit={submit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Add market</DialogTitle>
          </DialogHeader>
          <FormAlert message={error} />
          <MarketFields
            idPrefix="add-market"
            value={market}
            onChange={setMarket}
            entitlements={entitlements.data}
          />
          <DialogFooter>
            <Button type="submit" disabled={Object.keys(marketErrors(market)).length > 0}>
              Add market
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RenameForm({ project }: { project: Project }) {
  const org = useOrg();
  const queryClient = useQueryClient();
  const [name, setName] = useState(project.name);
  const rename = useMutation({
    mutationFn: () => projectsApi.rename(org.id, project.id, name.trim()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.projects(org.id) }),
  });
  return (
    <form
      className="flex max-w-md items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        rename.mutate();
      }}
    >
      <div className="flex-1">
        <Field
          id="rename-project"
          label="Project name"
          error={rename.isError ? errorText(rename.error, "Could not rename.") : undefined}
        >
          <Input
            id="rename-project"
            value={name}
            maxLength={120}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
      </div>
      <Button
        type="submit"
        variant="outline"
        disabled={!name.trim() || name.trim() === project.name}
      >
        Save
      </Button>
    </form>
  );
}

function ScheduleForm({ project }: { project: Project }) {
  const org = useOrg();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  async function change(value: string) {
    setError(null);
    try {
      await projectsApi.update(org.id, project.id, {
        crawl_schedule: value as "off" | "weekly" | "monthly",
      });
      await queryClient.invalidateQueries({ queryKey: keys.projects(org.id) });
    } catch (err) {
      setError(errorText(err, "Could not change the schedule."));
    }
  }

  return (
    <div className="max-w-md">
      <Field
        id="crawl-schedule"
        label="Automatic audits"
        error={error ?? undefined}
        hint={
          project.verified
            ? "Re-crawl and re-audit the site on a schedule."
            : "Verify the domain to schedule audits."
        }
      >
        <NativeSelect
          id="crawl-schedule"
          value={project.crawl_schedule}
          disabled={!project.verified}
          onChange={(e) => void change(e.target.value)}
        >
          <option value="off">Off</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </NativeSelect>
      </Field>
    </div>
  );
}

export function ProjectDetail({ projectId }: { projectId: string }) {
  const org = useOrg();
  const router = useRouter();
  const queryClient = useQueryClient();
  const canWrite = useCan("project:write");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const project = useQuery({
    queryKey: keys.project(org.id, projectId),
    queryFn: () => projectsApi.get(org.id, projectId),
  });

  if (project.isPending) return <Skeleton className="h-64" />;
  if (project.isError)
    return <ErrorState error={project.error} onRetry={() => void project.refetch()} />;
  const p = project.data;

  async function removeMarket(marketId: string) {
    setError(null);
    try {
      await projectsApi.removeMarket(org.id, p.id, marketId);
      await queryClient.invalidateQueries({ queryKey: keys.projects(org.id) });
    } catch (err) {
      setError(errorText(err, "Could not remove the market."));
    }
  }

  async function deleteProject() {
    setError(null);
    try {
      await projectsApi.remove(org.id, p.id);
      await queryClient.invalidateQueries({ queryKey: keys.projects(org.id) });
      router.push(`/orgs/${org.id}`);
    } catch (err) {
      setError(errorText(err, "Could not delete the project."));
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{p.name}</h1>
        <p className="text-muted-foreground text-sm">{p.primary_domain}</p>
      </div>
      <FormAlert message={error} />
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4">
          <div className="space-y-1.5">
            <CardTitle>Technical SEO audit</CardTitle>
            <CardDescription>
              Crawl the site and check indexability, structure, content and page experience.
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button asChild variant="outline">
              <Link href={`/orgs/${org.id}/projects/${p.id}/search`}>Search data</Link>
            </Button>
            <Button asChild>
              <Link href={`/orgs/${org.id}/projects/${p.id}/audit`}>Open audit</Link>
            </Button>
          </div>
        </CardHeader>
      </Card>
      <VerificationCard project={p} canWrite={canWrite} />

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="space-y-1.5">
            <CardTitle>Markets</CardTitle>
            <CardDescription>Where and on which engines this site is measured.</CardDescription>
          </div>
          {canWrite ? (
            <Button variant="outline" size="sm" onClick={() => setAdding(true)}>
              <Plus className="mr-1 h-4 w-4" aria-hidden /> Add market
            </Button>
          ) : null}
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {p.markets.map((m) => (
              <MarketRow
                key={m.id}
                market={m}
                removable={p.markets.length > 1}
                onRemove={canWrite ? () => removeMarket(m.id) : undefined}
              />
            ))}
          </ul>
        </CardContent>
      </Card>
      {canWrite ? <AddMarketDialog project={p} open={adding} onOpenChange={setAdding} /> : null}

      {canWrite ? (
        <Card>
          <CardHeader>
            <CardTitle>Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <RenameForm key={p.name} project={p} />
            <ScheduleForm key={`${p.crawl_schedule}-${p.verified}`} project={p} />
            <Confirm
              trigger={<Button variant="destructive">Delete project</Button>}
              title={`Delete ${p.name}?`}
              description="The project and its tracking stop immediately. Data is permanently removed after the retention period."
              confirmLabel="Delete project"
              onConfirm={deleteProject}
            />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
