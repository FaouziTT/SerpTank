"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Link2, Unplug } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Field, FormAlert } from "@/components/forms/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Confirm } from "@/features/orgs/confirm";
import { errorText } from "@/features/orgs/errors";
import { useCan, useOrg } from "@/features/orgs/org-context";

import { integrationKeys, integrationsApi, type ConnectionOut, type GoogleFeature } from "./api";

const FEATURES: { id: GoogleFeature; label: string; hint: string }[] = [
  { id: "gsc", label: "Search Console", hint: "Clicks, impressions, positions, URL inspection" },
  {
    id: "ga4",
    label: "Google Analytics 4",
    hint: "Organic landing-page engagement and conversions",
  },
  {
    id: "gsc_write",
    label: "Submit sitemaps",
    hint: "Lets SerpTank submit sitemaps to Search Console",
  },
  {
    id: "ads",
    label: "Google Ads Keyword Planner",
    hint: "Official search volumes (needs an Ads account)",
  },
];

const CALLBACK_ERRORS: Record<string, string> = {
  google_state_invalid:
    "The Google authorization expired or was started by someone else. Please try again.",
  google_denied: "Google access wasn't granted.",
  google_forbidden: "You no longer have permission to manage integrations in this organization.",
  google_no_refresh_token:
    "Google didn't grant offline access. Remove SerpTank in your Google account settings and try again.",
};

function StatusBadge({ connection }: { connection: ConnectionOut }) {
  if (connection.status === "active") return <Badge variant="secondary">Connected</Badge>;
  if (connection.status === "reauth_required")
    return <Badge variant="destructive">Reconnect needed</Badge>;
  return <Badge variant="warning">Last sync failed</Badge>;
}

function GoogleCard({
  connection,
  available,
}: {
  connection: ConnectionOut | undefined;
  available: boolean;
}) {
  const org = useOrg();
  const canManage = useCan("integrations:manage");
  const queryClient = useQueryClient();
  const [features, setFeatures] = useState<GoogleFeature[]>(
    connection ? (connection.features as GoogleFeature[]) : ["gsc", "ga4"],
  );
  const [error, setError] = useState<string | null>(null);

  async function connect() {
    setError(null);
    try {
      const { authorization_url } = await integrationsApi.startGoogle(org.id, features);
      window.location.assign(authorization_url);
    } catch (err) {
      setError(errorText(err, "Could not start the Google connection."));
    }
  }

  async function disconnect() {
    try {
      await integrationsApi.disconnect(org.id, "google");
      await queryClient.invalidateQueries({ queryKey: integrationKeys.overview(org.id) });
    } catch (err) {
      setError(errorText(err, "Could not disconnect Google."));
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <CardTitle className="flex items-center gap-2">
            Google {connection ? <StatusBadge connection={connection} /> : null}
          </CardTitle>
          <CardDescription>
            {connection
              ? `Connected as ${connection.account_label ?? "a Google account"}.`
              : "Connect Search Console and Analytics with read-only access. We never post or change anything unless you grant sitemap submission."}
          </CardDescription>
        </div>
        {connection && canManage ? (
          <Confirm
            trigger={
              <Button variant="outline" size="sm">
                <Unplug className="mr-1 h-4 w-4" aria-hidden /> Disconnect
              </Button>
            }
            title="Disconnect Google?"
            description="SerpTank's access is revoked and linked properties are unlinked. Data already synced stays."
            confirmLabel="Disconnect"
            onConfirm={disconnect}
          />
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        {!available ? (
          <p className="text-muted-foreground text-sm">
            Google integrations aren&apos;t configured on this server yet.
          </p>
        ) : canManage ? (
          <>
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">Permissions</legend>
              {FEATURES.map((f) => (
                <label key={f.id} className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={features.includes(f.id)}
                    onChange={(e) =>
                      setFeatures(
                        e.target.checked ? [...features, f.id] : features.filter((x) => x !== f.id),
                      )
                    }
                  />
                  <span>
                    {f.label}
                    {connection?.features.includes(f.id) ? (
                      <CheckCircle2
                        className="text-accent ml-1 inline h-3 w-3"
                        aria-label="granted"
                      />
                    ) : null}
                    <span className="text-muted-foreground block text-xs">{f.hint}</span>
                  </span>
                </label>
              ))}
            </fieldset>
            <Button onClick={() => void connect()} disabled={features.length === 0}>
              <Link2 className="mr-2 h-4 w-4" aria-hidden />
              {connection ? "Update Google permissions" : "Connect Google"}
            </Button>
          </>
        ) : (
          <p className="text-muted-foreground text-sm">Ask an admin to connect Google.</p>
        )}
      </CardContent>
    </Card>
  );
}

function BingCard({ connection }: { connection: ConnectionOut | undefined }) {
  const org = useOrg();
  const canManage = useCan("integrations:manage");
  const queryClient = useQueryClient();
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await integrationsApi.connectBing(org.id, key.trim());
      setKey("");
      await queryClient.invalidateQueries({ queryKey: integrationKeys.overview(org.id) });
    } catch (err) {
      setError(errorText(err, "Could not connect Bing Webmaster Tools."));
    }
  }

  async function disconnect() {
    await integrationsApi.disconnect(org.id, "bing");
    await queryClient.invalidateQueries({ queryKey: integrationKeys.overview(org.id) });
  }

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <CardTitle className="flex items-center gap-2">
            Bing Webmaster Tools {connection ? <StatusBadge connection={connection} /> : null}
          </CardTitle>
          <CardDescription>
            Bing also powers Yahoo, DuckDuckGo and Copilot answers. Create an API key in Bing
            Webmaster Tools (Settings → API access) and paste it here. It&apos;s stored encrypted.
          </CardDescription>
        </div>
        {connection && canManage ? (
          <Confirm
            trigger={
              <Button variant="outline" size="sm">
                <Unplug className="mr-1 h-4 w-4" aria-hidden /> Disconnect
              </Button>
            }
            title="Disconnect Bing?"
            description="The API key is deleted and linked sites are unlinked. Synced data stays."
            confirmLabel="Disconnect"
            onConfirm={disconnect}
          />
        ) : null}
      </CardHeader>
      <CardContent>
        {canManage ? (
          <form onSubmit={submit} className="flex max-w-lg flex-wrap items-end gap-2">
            <FormAlert message={error} />
            <div className="min-w-64 flex-1">
              <Field id="bing-key" label={connection ? "Replace API key" : "API key"}>
                <Input
                  id="bing-key"
                  type="password"
                  autoComplete="off"
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                />
              </Field>
            </div>
            <Button type="submit" disabled={key.trim().length < 16}>
              {connection ? "Update key" : "Connect Bing"}
            </Button>
          </form>
        ) : (
          <p className="text-muted-foreground text-sm">
            Ask an admin to connect Bing Webmaster Tools.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function IntegrationsPage() {
  const org = useOrg();
  const params = useSearchParams();
  const overview = useQuery({
    queryKey: integrationKeys.overview(org.id),
    queryFn: () => integrationsApi.overview(org.id),
  });
  const connected = params.get("connected");
  const error = params.get("error");

  if (overview.isPending) return <Skeleton className="h-64" />;
  if (overview.isError)
    return <ErrorState error={overview.error} onRetry={() => void overview.refetch()} />;
  const byProvider = new Map(overview.data.connections.map((c) => [c.provider, c]));
  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Integrations</h1>
        <p className="text-muted-foreground text-sm">
          First-party data from your own accounts. Link properties to projects on each
          project&apos;s Search data page.
        </p>
      </div>
      {connected === "google" ? (
        <p role="status" className="rounded-md border p-3 text-sm">
          Google is connected.
        </p>
      ) : null}
      {error ? (
        <FormAlert
          message={CALLBACK_ERRORS[error] ?? "The Google connection failed. Please try again."}
        />
      ) : null}
      <GoogleCard
        connection={byProvider.get("google")}
        available={overview.data.google_available}
      />
      <BingCard connection={byProvider.get("bing")} />
      <Card>
        <CardHeader>
          <CardTitle>Core Web Vitals (Chrome UX Report)</CardTitle>
          <CardDescription>
            {overview.data.vitals_available
              ? "Available for every project - no connection needed. Real-user data comes from Chrome's public UX report."
              : "Not configured on this server yet."}
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
