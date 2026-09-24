"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Field, FormAlert } from "@/components/forms/field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ensureCsrfToken } from "@/lib/api/client";
import { ApiError } from "@/lib/api/problem";
import { getPasskeyAssertion, useWebAuthnSupport } from "@/lib/webauthn";

import { authApi, safeNextPath } from "./api";
import { loginSchema, type LoginValues } from "./schemas";

const GOOGLE_ERRORS: Record<string, string> = {
  google_account_exists:
    "An account with this email already exists. Sign in with your password, then link Google in your security settings.",
  google_failed: "Google sign-in failed. Please try again.",
  google_cancelled: "Google sign-in was cancelled.",
};

export function LoginForm({ googleEnabled }: { googleEnabled: boolean }) {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNextPath(params.get("next"));
  const [error, setError] = useState<string | null>(
    GOOGLE_ERRORS[params.get("error") ?? ""] ?? null,
  );
  const passkeysSupported = useWebAuthnSupport();
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", remember_me: false },
  });

  async function finish(status: string) {
    if (status === "mfa_required") router.push(`/login/mfa?next=${encodeURIComponent(next)}`);
    else router.replace(next);
    router.refresh();
  }

  async function onSubmit(values: LoginValues) {
    setError(null);
    try {
      await ensureCsrfToken();
      const result = await authApi.login(values);
      await finish(result.status);
    } catch (err) {
      if (err instanceof ApiError && err.code === "email_not_verified") {
        setError("Please verify your email address first. Check your inbox for the link.");
      } else if (err instanceof ApiError && err.code === "captcha_required") {
        setError("Too many failed attempts. Please wait a few minutes and try again.");
      } else {
        setError(err instanceof ApiError ? err.userMessage : "Sign-in failed. Please try again.");
      }
    }
  }

  async function onPasskey() {
    setError(null);
    try {
      await ensureCsrfToken();
      const options = await authApi.passkeyLoginOptions();
      const credential = await getPasskeyAssertion(options as Record<string, unknown>);
      const result = await authApi.passkeyLogin(credential, form.getValues("remember_me"));
      await finish(result.status);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.userMessage : "Passkey sign-in was cancelled or failed.",
      );
    }
  }

  async function onGoogle() {
    await ensureCsrfToken(); // sets the pre-session cookie the OAuth state is bound to
    // Full navigation to a backend route that redirects to Google (not a Next page).
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/api/v1/auth/google/start?mode=login");
  }

  const { errors, isSubmitting } = form.formState;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Welcome back to SerpTank.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
          <Field id="email" label="Email" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="username webauthn"
              {...form.register("email")}
            />
          </Field>
          <Field id="password" label="Password" error={errors.password?.message}>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              {...form.register("password")}
            />
          </Field>
          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" {...form.register("remember_me")} /> Keep me signed in
            </label>
            <Link href="/forgot-password" className="text-primary hover:underline">
              Forgot password?
            </Link>
          </div>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <div className="grid gap-2">
          {passkeysSupported ? (
            <Button type="button" variant="outline" onClick={onPasskey}>
              <KeyRound className="mr-2 h-4 w-4" aria-hidden /> Sign in with a passkey
            </Button>
          ) : null}
          {googleEnabled ? (
            <Button type="button" variant="outline" onClick={onGoogle}>
              Continue with Google
            </Button>
          ) : null}
        </div>
        <p className="text-muted-foreground text-center text-sm">
          New to SerpTank?{" "}
          <Link href="/register" className="text-primary hover:underline">
            Create an account
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
