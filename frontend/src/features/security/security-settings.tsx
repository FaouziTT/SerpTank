"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Laptop, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import QRCode from "qrcode";
import { useEffect, useState, type FormEvent } from "react";

import { Field, FormAlert } from "@/components/forms/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { authApi, type SessionResponse } from "@/features/auth/api";
import { ensureCsrfToken } from "@/lib/api/client";
import { ApiError } from "@/lib/api/problem";
import { createPasskey, useWebAuthnSupport } from "@/lib/webauthn";

import { YourDataCard } from "./your-data";
import { useStepUp } from "./step-up";

function errorText(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.userMessage : fallback;
}

// ------------------------------------------------------------------- password
function PasswordCard({ hasPassword }: { hasPassword: boolean }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await authApi.changePassword(current, next);
      setCurrent("");
      setNext("");
      setMessage("Password updated. Your other sessions were signed out.");
    } catch (err) {
      setError(errorText(err, "Could not change your password."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Password</CardTitle>
        <CardDescription>
          {hasPassword
            ? "Change your password."
            : "Your account uses Google or a passkey. You can add a password."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="max-w-sm space-y-3" onSubmit={submit}>
          <FormAlert message={error} />
          {message ? (
            <p role="status" className="text-accent text-sm">
              {message}
            </p>
          ) : null}
          {hasPassword ? (
            <Field id="current-password" label="Current password">
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </Field>
          ) : null}
          <Field id="new-password" label="New password" hint="At least 12 characters.">
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={next.length < 12}>
            Update password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ----------------------------------------------------------------------- TOTP
function RecoveryCodes({ codes }: { codes: string[] }) {
  return (
    <div className="bg-muted/40 space-y-2 rounded-md border p-4">
      <p className="text-sm font-medium">Save these recovery codes somewhere safe.</p>
      <p className="text-muted-foreground text-xs">
        Each code works once. They will not be shown again.
      </p>
      <ul className="grid grid-cols-2 gap-1 font-mono text-sm" aria-label="Recovery codes">
        {codes.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ul>
    </div>
  );
}

function TotpCard({ enabled, onChange }: { enabled: boolean; onChange: () => void }) {
  const stepUp = useStepUp();
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!setup) return;
    QRCode.toDataURL(setup.otpauth_uri, { margin: 1, width: 200 }).then(setQr, () => setQr(null));
  }, [setup]);

  async function begin() {
    setError(null);
    try {
      setSetup(await stepUp(() => authApi.totpSetup()));
    } catch (err) {
      if (err instanceof Error && err.message === "cancelled") return;
      setError(errorText(err, "Could not start setup."));
    }
  }

  async function confirm(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const result = await authApi.totpConfirm(code.trim());
      setCodes(result.codes);
      setSetup(null);
      setCode("");
      onChange();
    } catch (err) {
      setError(errorText(err, "The code is incorrect."));
    }
  }

  async function disable() {
    setError(null);
    try {
      await stepUp(() => authApi.totpDisable());
      setCodes(null);
      onChange();
    } catch (err) {
      if (err instanceof Error && err.message === "cancelled") return;
      setError(errorText(err, "Could not disable the authenticator."));
    }
  }

  async function regenerate() {
    try {
      setCodes((await stepUp(() => authApi.recoveryCodes())).codes);
    } catch (err) {
      if (err instanceof Error && err.message === "cancelled") return;
      setError(errorText(err, "Could not generate new codes."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Authenticator app {enabled ? <Badge>On</Badge> : <Badge variant="secondary">Off</Badge>}
        </CardTitle>
        <CardDescription>
          Use an app like 1Password, Authy or Google Authenticator for sign-in codes.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        {codes ? <RecoveryCodes codes={codes} /> : null}
        {setup ? (
          <form className="space-y-3" onSubmit={confirm}>
            {qr ? (
              // eslint-disable-next-line @next/next/no-img-element -- data: URL generated locally
              <img src={qr} alt="QR code for your authenticator app" width={200} height={200} />
            ) : null}
            <p className="text-sm">
              Or enter this key manually: <code className="font-mono">{setup.secret}</code>
            </p>
            <Field id="totp-confirm" label="Code from your app">
              <Input
                id="totp-confirm"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </Field>
            <Button type="submit">Turn on</Button>
          </form>
        ) : enabled ? (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={regenerate}>
              New recovery codes
            </Button>
            <Button variant="destructive" onClick={disable}>
              Turn off
            </Button>
          </div>
        ) : (
          <Button onClick={begin}>Set up authenticator</Button>
        )}
      </CardContent>
    </Card>
  );
}

// ------------------------------------------------------------------- passkeys
function PasskeysCard({ onChange }: { onChange: () => void }) {
  const stepUp = useStepUp();
  const queryClient = useQueryClient();
  const passkeys = useQuery({ queryKey: ["passkeys"], queryFn: authApi.passkeys });
  const supported = useWebAuthnSupport();
  const [error, setError] = useState<string | null>(null);

  async function add() {
    setError(null);
    try {
      const options = await stepUp(() => authApi.passkeyRegisterOptions());
      const credential = await createPasskey(options as Record<string, unknown>);
      await authApi.passkeyRegister(credential, navigator.platform || "Passkey");
      await queryClient.invalidateQueries({ queryKey: ["passkeys"] });
      onChange();
    } catch (err) {
      if (err instanceof Error && err.message === "cancelled") return;
      setError(errorText(err, "The passkey was not added."));
    }
  }

  const remove = useMutation({
    mutationFn: (id: string) => stepUp(() => authApi.passkeyDelete(id)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["passkeys"] });
      onChange();
    },
    onError: (err) => setError(errorText(err, "Could not remove the passkey.")),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Passkeys</CardTitle>
        <CardDescription>
          Sign in with your fingerprint, face or device PIN. Phishing-resistant.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        {passkeys.isPending ? <Skeleton className="h-10 w-full" /> : null}
        {passkeys.isError ? (
          <ErrorState error={passkeys.error} onRetry={() => passkeys.refetch()} />
        ) : null}
        {passkeys.data?.length ? (
          <ul className="divide-y rounded-md border">
            {passkeys.data.map((p) => (
              <li key={p.id} className="flex items-center justify-between p-3 text-sm">
                <span className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4" aria-hidden /> {p.name}
                  <span className="text-muted-foreground">
                    added {new Date(p.created_at).toLocaleDateString()}
                  </span>
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Remove passkey ${p.name}`}
                  onClick={() => remove.mutate(p.id)}
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </Button>
              </li>
            ))}
          </ul>
        ) : passkeys.isSuccess ? (
          <p className="text-muted-foreground text-sm">No passkeys yet.</p>
        ) : null}
        {supported ? (
          <Button onClick={add}>Add a passkey</Button>
        ) : (
          <p className="text-muted-foreground text-sm">This browser does not support passkeys.</p>
        )}
      </CardContent>
    </Card>
  );
}

// -------------------------------------------------------------------- sessions
function SessionsCard() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: authApi.sessions });
  const revoke = useMutation({
    mutationFn: authApi.revokeSession,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sessions"] }),
  });

  async function signOutEverywhere() {
    await authApi.logoutAll();
    router.replace("/login");
    router.refresh();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active sessions</CardTitle>
        <CardDescription>Devices currently signed in to your account.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {sessions.isPending ? <Skeleton className="h-16 w-full" /> : null}
        {sessions.isError ? (
          <ErrorState error={sessions.error} onRetry={() => sessions.refetch()} />
        ) : null}
        {sessions.data ? (
          <ul className="divide-y rounded-md border">
            {sessions.data.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-4 p-3 text-sm">
                <span className="flex min-w-0 items-center gap-2">
                  <Laptop className="h-4 w-4 shrink-0" aria-hidden />
                  <span className="truncate">{s.user_agent ?? "Unknown device"}</span>
                  {s.current ? <Badge variant="secondary">This device</Badge> : null}
                </span>
                <span className="text-muted-foreground shrink-0">
                  {s.ip ?? "unknown IP"} · last active {new Date(s.last_seen_at).toLocaleString()}
                </span>
                {!s.current ? (
                  <Button variant="ghost" size="sm" onClick={() => revoke.mutate(s.id)}>
                    Sign out
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        <Button variant="outline" onClick={signOutEverywhere}>
          Sign out everywhere
        </Button>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------- Google
function GoogleCard({ linked, onChange }: { linked: boolean; onChange: () => void }) {
  const stepUp = useStepUp();
  const [error, setError] = useState<string | null>(null);

  async function link() {
    await ensureCsrfToken();
    // Full navigation to a backend route that redirects to Google (not a Next page).
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/api/v1/auth/google/start?mode=link");
  }

  async function unlink() {
    setError(null);
    try {
      await stepUp(() => authApi.googleUnlink());
      onChange();
    } catch (err) {
      if (err instanceof Error && err.message === "cancelled") return;
      setError(errorText(err, "Could not unlink Google."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Google sign-in</CardTitle>
        <CardDescription>
          {linked ? "Your Google account is linked." : "Link Google to sign in with one click."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <FormAlert message={error} />
        {linked ? (
          <Button variant="outline" onClick={unlink}>
            Unlink Google
          </Button>
        ) : (
          <Button variant="outline" onClick={link}>
            Link Google account
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export function SecuritySettings({ session }: { session: SessionResponse }) {
  const router = useRouter();
  const refresh = () => router.refresh();
  const totpEnabled = session.user.mfa_enabled;
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">Security</h1>
      <PasswordCard hasPassword={session.user.has_password} />
      <TotpCard enabled={totpEnabled} onChange={refresh} />
      <PasskeysCard onChange={refresh} />
      <GoogleCard linked={session.user.google_linked} onChange={refresh} />
      <SessionsCard />
      <YourDataCard />
    </div>
  );
}
