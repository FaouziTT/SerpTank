"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Field, FormAlert } from "@/components/forms/field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/problem";

import { authApi, safeNextPath } from "./api";

export function MfaForm() {
  const router = useRouter();
  const next = safeNextPath(useSearchParams().get("next"));
  const [useRecovery, setUseRecovery] = useState(false);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const trimmed = value.replace(/\s+/g, "");
    if (!useRecovery && !/^\d{6}$/.test(trimmed)) {
      setError("Enter the 6-digit code from your authenticator app.");
      return;
    }
    setBusy(true);
    try {
      await authApi.verifyMfa(useRecovery ? { recovery_code: trimmed } : { code: trimmed });
      router.replace(next);
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401 && err.code === "authentication_required") {
        router.replace("/login");
        return;
      }
      setError(err instanceof ApiError ? err.userMessage : "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Two-factor authentication</CardTitle>
        <CardDescription>
          {useRecovery
            ? "Enter one of your saved recovery codes."
            : "Enter the code from your authenticator app."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          <Field id="mfa-code" label={useRecovery ? "Recovery code" : "Authentication code"}>
            <Input
              id="mfa-code"
              autoComplete="one-time-code"
              inputMode={useRecovery ? "text" : "numeric"}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              autoFocus
            />
          </Field>
          <Button type="submit" className="w-full" disabled={busy}>
            Verify
          </Button>
        </form>
        <button
          type="button"
          className="text-primary text-sm hover:underline"
          onClick={() => {
            setUseRecovery(!useRecovery);
            setValue("");
            setError(null);
          }}
        >
          {useRecovery ? "Use an authenticator code instead" : "Use a recovery code instead"}
        </button>
      </CardContent>
    </Card>
  );
}
