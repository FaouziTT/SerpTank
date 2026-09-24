"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { keys, orgsApi, type AuditEvent } from "./api";
import { useOrg } from "./org-context";

const timeFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

/** Human-readable labels for audit actions; unknown actions fall back to the raw code. */
const ACTION_LABELS: Record<string, string> = {
  "org.created": "Organization created",
  "org.updated": "Organization settings changed",
  "org.deleted": "Organization deleted",
  "member.left": "Member left",
  "member.removed": "Member removed",
  "member.role_changed": "Member role changed",
  "invitation.created": "Invitation sent",
  "invitation.revoked": "Invitation revoked",
  "invitation.accepted": "Invitation accepted",
  "project.created": "Project created",
  "project.deleted": "Project deleted",
  "project.domain_verified": "Domain verified",
  "api_key.created": "API key created",
  "api_key.revoked": "API key revoked",
};

function detailsText(event: AuditEvent): string {
  const entries = Object.entries(event.details ?? {});
  return entries
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(", ");
}

export function AuditLog() {
  const org = useOrg();
  const query = useInfiniteQuery({
    queryKey: keys.audit(org.id),
    queryFn: ({ pageParam }) => orgsApi.auditEvents(org.id, pageParam),
    initialPageParam: undefined as string | undefined,
    // Keyset pagination: the next page starts before the oldest event we have.
    getNextPageParam: (last) =>
      last.length === 50 ? last[last.length - 1]?.created_at : undefined,
  });

  return (
    <div className="max-w-5xl space-y-6">
      <h1 className="text-2xl font-semibold">Audit log</h1>
      {query.isPending ? (
        <Skeleton className="h-48" />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.data.pages.flat().length === 0 ? (
        <EmptyState
          title="No events yet"
          description="Security-relevant changes in this organization appear here."
        />
      ) : (
        <Card>
          <CardContent className="pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Event</TableHead>
                  <TableHead>Details</TableHead>
                  <TableHead>IP</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.data.pages.flat().map((e) => (
                  <TableRow key={e.id}>
                    <TableCell className="text-sm whitespace-nowrap">
                      {timeFmt.format(new Date(e.created_at))}
                    </TableCell>
                    <TableCell className="text-sm">{ACTION_LABELS[e.action] ?? e.action}</TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {detailsText(e)}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {e.ip_address ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {query.hasNextPage ? (
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => void query.fetchNextPage()}
                disabled={query.isFetchingNextPage}
              >
                Load older events
              </Button>
            ) : null}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
