"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Field, FormAlert } from "@/components/forms/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { useStepUp } from "@/features/security/step-up";

import { keys, orgsApi, type Member, type MemberRole } from "./api";
import { Confirm } from "./confirm";
import { errorText } from "./errors";
import { useCan, useOrg } from "./org-context";
import { assignableRoles, ROLE_LABELS } from "./permissions";

const dateFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

function MemberRow({ member, currentUserId }: { member: Member; currentUserId: string }) {
  const org = useOrg();
  const router = useRouter();
  const stepUp = useStepUp();
  const queryClient = useQueryClient();
  const manage = useCan("members:manage");
  const [error, setError] = useState<string | null>(null);
  const roles = assignableRoles(org.role);
  const isSelf = member.user_id === currentUserId;
  // Admins can't change owners; only owners can.
  const editable = manage && (member.role !== "owner" || org.role === "owner");

  async function changeRole(role: MemberRole) {
    setError(null);
    try {
      await stepUp(() => orgsApi.changeRole(org.id, member.id, role));
      await queryClient.invalidateQueries({ queryKey: keys.members(org.id) });
      if (isSelf) router.refresh();
    } catch (err) {
      setError(errorText(err, "Could not change the role."));
    }
  }

  async function remove() {
    setError(null);
    try {
      await stepUp(() => orgsApi.removeMember(org.id, member.id));
      if (isSelf) {
        router.push("/dashboard");
        router.refresh();
        return;
      }
      await queryClient.invalidateQueries({ queryKey: keys.members(org.id) });
    } catch (err) {
      setError(errorText(err, "Could not remove the member."));
    }
  }

  return (
    <TableRow>
      <TableCell>
        <div className="font-medium">
          {member.full_name || member.email}{" "}
          {isSelf ? <span className="text-muted-foreground">(you)</span> : null}
        </div>
        <div className="text-muted-foreground text-xs">{member.email}</div>
        {error ? (
          <p role="alert" className="text-destructive text-xs">
            {error}
          </p>
        ) : null}
      </TableCell>
      <TableCell>
        {editable ? (
          <NativeSelect
            aria-label={`Role for ${member.email}`}
            value={member.role}
            className="h-9 w-32"
            onChange={(e) => void changeRole(e.target.value as MemberRole)}
          >
            {[...new Set([member.role, ...roles])].map((r) => (
              <option key={r} value={r} disabled={!roles.includes(r)}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </NativeSelect>
        ) : (
          ROLE_LABELS[member.role]
        )}
      </TableCell>
      <TableCell>
        {member.mfa_enabled ? (
          <Badge variant="secondary">MFA on</Badge>
        ) : (
          <Badge variant="warning">No MFA</Badge>
        )}
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {dateFmt.format(new Date(member.joined_at))}
      </TableCell>
      <TableCell className="text-right">
        {editable || isSelf ? (
          <Confirm
            trigger={
              <Button variant="ghost" size="sm">
                {isSelf ? "Leave" : "Remove"}
              </Button>
            }
            title={isSelf ? `Leave ${org.name}?` : `Remove ${member.email}?`}
            description={
              isSelf
                ? "You will lose access to this organization until you're invited again."
                : "They lose access immediately. Their past activity stays in the audit log."
            }
            confirmLabel={isSelf ? "Leave" : "Remove"}
            onConfirm={remove}
          />
        ) : null}
      </TableCell>
    </TableRow>
  );
}

function InviteForm() {
  const org = useOrg();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<MemberRole>("editor");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const roles = assignableRoles(org.role);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSent(null);
    try {
      await orgsApi.invite(org.id, email.trim(), role);
      setSent(`Invitation sent to ${email.trim()}.`);
      setEmail("");
      await queryClient.invalidateQueries({ queryKey: keys.invitations(org.id) });
    } catch (err) {
      setError(errorText(err, "Could not send the invitation."));
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <FormAlert message={error} />
      {sent ? (
        <p role="status" className="text-sm">
          {sent}
        </p>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-[1fr_10rem_auto] sm:items-end">
        <Field id="invite-email" label="Email">
          <Input
            id="invite-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field id="invite-role" label="Role">
          <NativeSelect
            id="invite-role"
            value={role}
            onChange={(e) => setRole(e.target.value as MemberRole)}
          >
            {roles.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Button type="submit" disabled={!email.includes("@")}>
          Send invite
        </Button>
      </div>
    </form>
  );
}

function PendingInvitations() {
  const org = useOrg();
  const queryClient = useQueryClient();
  const invitations = useQuery({
    queryKey: keys.invitations(org.id),
    queryFn: () => orgsApi.invitations(org.id),
  });
  const [error, setError] = useState<string | null>(null);

  if (invitations.isPending) return <Skeleton className="h-16" />;
  if (invitations.isError)
    return <ErrorState error={invitations.error} onRetry={() => void invitations.refetch()} />;
  const pending = invitations.data.filter((i) => !i.accepted_at && !i.revoked_at);
  if (pending.length === 0)
    return <p className="text-muted-foreground text-sm">No pending invitations.</p>;

  async function revoke(id: string) {
    setError(null);
    try {
      await orgsApi.revokeInvitation(org.id, id);
      await queryClient.invalidateQueries({ queryKey: keys.invitations(org.id) });
    } catch (err) {
      setError(errorText(err, "Could not revoke the invitation."));
    }
  }

  return (
    <div className="space-y-2">
      <FormAlert message={error} />
      <ul className="divide-y rounded-md border" aria-label="Pending invitations">
        {pending.map((inv) => {
          const expired = new Date(inv.expires_at) < new Date();
          return (
            <li key={inv.id} className="flex items-center justify-between gap-2 p-3 text-sm">
              <span>
                {inv.email} · {ROLE_LABELS[inv.role]}{" "}
                {expired ? (
                  <Badge variant="warning">Expired</Badge>
                ) : (
                  <span className="text-muted-foreground">
                    until {dateFmt.format(new Date(inv.expires_at))}
                  </span>
                )}
              </span>
              <Button variant="ghost" size="sm" onClick={() => void revoke(inv.id)}>
                Revoke
              </Button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function MembersPage({ currentUserId }: { currentUserId: string }) {
  const org = useOrg();
  const manage = useCan("members:manage");
  const members = useQuery({
    queryKey: keys.members(org.id),
    queryFn: () => orgsApi.members(org.id),
  });

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-2xl font-semibold">Members</h1>
      <Card>
        <CardContent className="pt-6">
          {members.isPending ? (
            <Skeleton className="h-24" />
          ) : members.isError ? (
            <ErrorState error={members.error} onRetry={() => void members.refetch()} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Security</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="sr-only">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.data.map((m) => (
                  <MemberRow key={m.id} member={m} currentUserId={currentUserId} />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      {manage ? (
        <Card>
          <CardHeader>
            <CardTitle>Invite people</CardTitle>
            <CardDescription>
              Invitations are tied to the email address and expire after 7 days.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <InviteForm />
            <PendingInvitations />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
