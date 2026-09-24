"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Globe, Plus } from "lucide-react";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

import { keys, orgsApi, projectsApi, type MarketIn, type Project } from "./api";
import { engineLabel } from "./engines";
import { errorText } from "./errors";
import { DEFAULT_MARKET, MarketFields, marketErrors } from "./market-fields";
import { useCan, useOrg } from "./org-context";

export function useEntitlements(orgId: string) {
  return useQuery({
    queryKey: keys.entitlements(orgId),
    queryFn: () => orgsApi.entitlements(orgId),
  });
}

function NewProjectDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const org = useOrg();
  const router = useRouter();
  const queryClient = useQueryClient();
  const entitlements = useEntitlements(org.id);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [market, setMarket] = useState<MarketIn>(DEFAULT_MARKET);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const valid =
    name.trim() && domain.trim().length >= 3 && Object.keys(marketErrors(market)).length === 0;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const project = await projectsApi.create(org.id, {
        name: name.trim(),
        domain: domain.trim(),
        markets: [market],
      });
      await queryClient.invalidateQueries({ queryKey: keys.projects(org.id) });
      router.push(`/orgs/${org.id}/projects/${project.id}`);
    } catch (err) {
      setError(errorText(err, "Could not create the project."));
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <form onSubmit={submit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>
              A project is one website. Add the markets (country, language, engines) you want to
              track.
            </DialogDescription>
          </DialogHeader>
          <FormAlert message={error} />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="project-name" label="Project name">
              <Input
                id="project-name"
                value={name}
                maxLength={120}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field id="project-domain" label="Domain" hint="For example example.com">
              <Input
                id="project-domain"
                value={domain}
                maxLength={300}
                inputMode="url"
                onChange={(e) => setDomain(e.target.value)}
              />
            </Field>
          </div>
          <h3 className="text-sm font-semibold">First market</h3>
          <MarketFields
            idPrefix="new-market"
            value={market}
            onChange={setMarket}
            entitlements={entitlements.data}
          />
          <DialogFooter>
            <Button type="submit" disabled={busy || !valid}>
              Create project
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ProjectCard({ orgId, project }: { orgId: string; project: Project }) {
  const engines = [...new Set(project.markets.flatMap((m) => m.search_engines))];
  return (
    <Link href={`/orgs/${orgId}/projects/${project.id}`} className="block">
      <Card className="hover:border-primary/50 h-full transition-colors">
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2 text-base">
            <span className="truncate">{project.name}</span>
            {project.verified ? (
              <Badge variant="secondary">
                <CheckCircle2 className="mr-1 h-3 w-3" aria-hidden /> Verified
              </Badge>
            ) : (
              <Badge variant="warning">Unverified</Badge>
            )}
          </CardTitle>
          <CardDescription className="flex items-center gap-1">
            <Globe className="h-3 w-3" aria-hidden /> {project.primary_domain}
          </CardDescription>
        </CardHeader>
        <CardContent className="text-muted-foreground text-sm">
          {project.markets.length} market{project.markets.length === 1 ? "" : "s"} ·{" "}
          {engines.map(engineLabel).join(", ")}
        </CardContent>
      </Card>
    </Link>
  );
}

export function OrgOverview() {
  const org = useOrg();
  const canWrite = useCan("project:write");
  const [open, setOpen] = useState(false);
  const projects = useQuery({
    queryKey: keys.projects(org.id),
    queryFn: () => projectsApi.list(org.id),
  });
  const entitlements = useEntitlements(org.id);
  const atLimit =
    projects.data !== undefined &&
    entitlements.data !== undefined &&
    projects.data.length >= entitlements.data.max_projects;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Projects</h1>
          {entitlements.data ? (
            <p className="text-muted-foreground text-sm">
              {entitlements.data.plan_name} plan · {projects.data?.length ?? "…"} of{" "}
              {entitlements.data.max_projects} projects
            </p>
          ) : null}
        </div>
        {canWrite ? (
          <Button
            onClick={() => setOpen(true)}
            disabled={atLimit}
            title={atLimit ? "Project limit reached for your plan" : undefined}
          >
            <Plus className="mr-2 h-4 w-4" aria-hidden /> New project
          </Button>
        ) : null}
      </div>
      {atLimit && canWrite ? (
        <p className="text-muted-foreground text-sm">
          You&apos;ve reached your plan&apos;s project limit. Upgrade to add more projects.
        </p>
      ) : null}

      {projects.isPending ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      ) : projects.isError ? (
        <ErrorState error={projects.error} onRetry={() => void projects.refetch()} />
      ) : projects.data.length === 0 ? (
        <EmptyState
          icon={Globe}
          title="No projects yet"
          description={
            canWrite
              ? "Add your first website to start auditing and tracking it."
              : "No websites have been added to this organization yet."
          }
          action={
            canWrite ? <Button onClick={() => setOpen(true)}>Add a website</Button> : undefined
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {projects.data.map((p) => (
            <ProjectCard key={p.id} orgId={org.id} project={p} />
          ))}
        </div>
      )}
      {canWrite ? <NewProjectDialog open={open} onOpenChange={setOpen} /> : null}
    </div>
  );
}
