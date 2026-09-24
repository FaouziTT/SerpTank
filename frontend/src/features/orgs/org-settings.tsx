"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound } from "lucide-react";
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
import { useStepUp } from "@/features/security/step-up";

import { keys, orgsApi, type ApiKey } from "./api";
import { Confirm } from "./confirm";
import { errorText } from "./errors";
import { useCan, useOrg } from "./org-context";

const dateFmt = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

function GeneralCard() {
  const org = useOrg();
  const router = useRouter();
  const [name, setName] = useState(org.name);
  const [requireMfa, setRequireMfa] = useState(org.require_mfa);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const dirty = name.trim() !== org.name || requireMfa !== org.require_mfa;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    try {
      await orgsApi.update(org.id, {
        name: name.trim() !== org.name ? name.trim() : null,
        require_mfa: requireMfa !== org.require_mfa ? requireMfa : null,
      });
      setSaved(true);
      router.refresh();
    } catch (err) {
      setError(errorText(err, "Could not save the settings."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>General</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="max-w-md space-y-4">
          <FormAlert message={error} />
          {saved ? (
            <p role="status" className="text-sm">
              Settings saved.
            </p>
          ) : null}
          <Field id="org-settings-name" label="Organization name">
            <Input
              id="org-settings-name"
              value={name}
              maxLength={120}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={requireMfa}
              onChange={(e) => setRequireMfa(e.target.checked)}
            />
            <span>
              <span className="font-medium">Require two-factor authentication</span>
              <span className="text-muted-foreground block">
                Members without an authenticator app or passkey can&apos;t open this organization.
              </span>
            </span>
          </label>
          <Button type="submit" disabled={!dirty || !name.trim()}>
            Save
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function NewKeyForm({ onCreated }: { onCreated: (secret: string) => void }) {
  const org = useOrg();
  const stepUp = useStepUp();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"read" | "write">("read");
  const [expires, setExpires] = useState("90");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const created = await stepUp(() =>
        orgsApi.createApiKey(org.id, {
          name: name.trim(),
          scopes: scope === "write" ? ["read", "write"] : ["read"],
          expires_in_days: expires === "never" ? null : Number(expires),
        }),
      );
      setName("");
      onCreated(created.key);
      await queryClient.invalidateQueries({ queryKey: keys.apiKeys(org.id) });
    } catch (err) {
      if (err instanceof Error && err.message === "cancelled") return;
      setError(errorText(err, "Could not create the key."));
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <FormAlert message={error} />
      <div className="grid gap-3 sm:grid-cols-[1fr_9rem_9rem_auto] sm:items-end">
        <Field id="key-name" label="Key name">
          <Input
            id="key-name"
            value={name}
            maxLength={100}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field id="key-scope" label="Access">
          <NativeSelect
            id="key-scope"
            value={scope}
            onChange={(e) => setScope(e.target.value as "read" | "write")}
          >
            <option value="read">Read only</option>
            <option value="write">Read and write</option>
          </NativeSelect>
        </Field>
        <Field id="key-expiry" label="Expires">
          <NativeSelect
            id="key-expiry"
            value={expires}
            onChange={(e) => setExpires(e.target.value)}
          >
            <option value="30">30 days</option>
            <option value="90">90 days</option>
            <option value="365">1 year</option>
            <option value="never">Never</option>
          </NativeSelect>
        </Field>
        <Button type="submit" disabled={!name.trim()}>
          Create key
        </Button>
      </div>
    </form>
  );
}

function KeyRow({ apiKey }: { apiKey: ApiKey }) {
  const org = useOrg();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const expired = apiKey.expires_at !== null && new Date(apiKey.expires_at) < new Date();

  async function revoke() {
    setError(null);
    try {
      await orgsApi.revokeApiKey(org.id, apiKey.id);
      await queryClient.invalidateQueries({ queryKey: keys.apiKeys(org.id) });
    } catch (err) {
      setError(errorText(err, "Could not revoke the key."));
    }
  }

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 p-3 text-sm">
      <div>
        <div className="font-medium">
          {apiKey.name}{" "}
          {apiKey.revoked_at ? (
            <Badge variant="outline">Revoked</Badge>
          ) : expired ? (
            <Badge variant="warning">Expired</Badge>
          ) : null}
        </div>
        <div className="text-muted-foreground text-xs">
          <code>stk_live_{apiKey.prefix}_…</code> · {apiKey.scopes.join(", ")} · created{" "}
          {dateFmt.format(new Date(apiKey.created_at))} ·{" "}
          {apiKey.last_used_at
            ? `last used ${dateFmt.format(new Date(apiKey.last_used_at))}`
            : "never used"}
          {apiKey.expires_at ? ` · expires ${dateFmt.format(new Date(apiKey.expires_at))}` : ""}
        </div>
        {error ? (
          <p role="alert" className="text-destructive text-xs">
            {error}
          </p>
        ) : null}
      </div>
      {!apiKey.revoked_at ? (
        <Confirm
          trigger={
            <Button variant="ghost" size="sm">
              Revoke
            </Button>
          }
          title={`Revoke ${apiKey.name}?`}
          description="Applications using this key stop working immediately."
          confirmLabel="Revoke key"
          onConfirm={revoke}
        />
      ) : null}
    </li>
  );
}

function ApiKeysCard() {
  const org = useOrg();
  const [secret, setSecret] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const list = useQuery({ queryKey: keys.apiKeys(org.id), queryFn: () => orgsApi.apiKeys(org.id) });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="h-5 w-5" aria-hidden /> API keys
        </CardTitle>
        <CardDescription>
          Keys give programs access to this organization&apos;s projects. They can&apos;t manage
          members, billing or keys.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <NewKeyForm
          onCreated={(key) => {
            setSecret(key);
            setCopied(false);
          }}
        />
        {secret ? (
          <div className="bg-muted/40 space-y-2 rounded-md border p-4" role="status">
            <p className="text-sm font-medium">
              Copy your new key now. It won&apos;t be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="bg-background flex-1 rounded border px-2 py-1 text-sm break-all">
                {secret}
              </code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  void navigator.clipboard?.writeText(secret).then(() => setCopied(true));
                }}
              >
                <Copy className="mr-1 h-4 w-4" aria-hidden /> {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>
        ) : null}
        {list.isPending ? (
          <Skeleton className="h-16" />
        ) : list.isError ? (
          <ErrorState error={list.error} onRetry={() => void list.refetch()} />
        ) : list.data.length === 0 ? (
          <p className="text-muted-foreground text-sm">No API keys yet.</p>
        ) : (
          <ul className="divide-y rounded-md border" aria-label="API keys">
            {list.data.map((k) => (
              <KeyRow key={k.id} apiKey={k} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function DangerCard() {
  const org = useOrg();
  const router = useRouter();
  const stepUp = useStepUp();
  const [error, setError] = useState<string | null>(null);
  const [confirmName, setConfirmName] = useState("");

  async function remove() {
    setError(null);
    try {
      await stepUp(() => orgsApi.remove(org.id));
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      if (err instanceof Error && err.message === "cancelled") return;
      setError(errorText(err, "Could not delete the organization."));
    }
  }

  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CardTitle>Delete organization</CardTitle>
        <CardDescription>
          All members lose access immediately. Data is permanently deleted after 30 days.
        </CardDescription>
      </CardHeader>
      <CardContent className="max-w-md space-y-3">
        <FormAlert message={error} />
        <Field id="confirm-org-name" label={`Type "${org.name}" to confirm`}>
          <Input
            id="confirm-org-name"
            value={confirmName}
            onChange={(e) => setConfirmName(e.target.value)}
          />
        </Field>
        <Button
          variant="destructive"
          disabled={confirmName !== org.name}
          onClick={() => void remove()}
        >
          Delete organization
        </Button>
      </CardContent>
    </Card>
  );
}

export function OrgSettings() {
  const canUpdate = useCan("org:update");
  const canKeys = useCan("api_keys:manage");
  const canDelete = useCan("org:delete");
  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-2xl font-semibold">Organization settings</h1>
      {canUpdate ? (
        <GeneralCard />
      ) : (
        <p className="text-muted-foreground text-sm">
          Only admins can change organization settings.
        </p>
      )}
      {canKeys ? <ApiKeysCard /> : null}
      {canDelete ? <DangerCard /> : null}
    </div>
  );
}
