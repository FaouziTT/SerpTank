"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import type { z } from "zod";

import { Field, FormAlert } from "@/components/forms/field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ensureCsrfToken } from "@/lib/api/client";
import { ApiError } from "@/lib/api/problem";

import { authApi } from "./api";
import { emailSchema, resetSchema } from "./schemas";

export function ForgotPasswordForm() {
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit({ email }: z.infer<typeof emailSchema>) {
    setError(null);
    try {
      await ensureCsrfToken();
      await authApi.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage : "Something went wrong.");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reset your password</CardTitle>
        <CardDescription>
          {sent
            ? "If an account exists for that address, we sent a reset link. It expires in 30 minutes."
            : "Enter your email and we'll send you a reset link."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        {!sent ? (
          <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
            <Field id="email" label="Email" error={form.formState.errors.email?.message}>
              <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
            </Field>
            <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
              Send reset link
            </Button>
          </form>
        ) : null}
        <Link href="/login" className="text-primary text-sm hover:underline">
          Back to sign in
        </Link>
      </CardContent>
    </Card>
  );
}

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(token ? null : "This reset link is invalid.");
  const form = useForm<z.infer<typeof resetSchema>>({
    resolver: zodResolver(resetSchema),
    defaultValues: { new_password: "", confirm: "" },
  });

  async function onSubmit(values: z.infer<typeof resetSchema>) {
    setError(null);
    try {
      await ensureCsrfToken();
      await authApi.resetPassword(token, values.new_password);
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError && err.code === "weak_password") {
        form.setError("new_password", { message: err.userMessage });
      } else {
        setError(err instanceof ApiError ? err.userMessage : "Password reset failed.");
      }
    }
  }

  const { errors, isSubmitting } = form.formState;
  return (
    <Card>
      <CardHeader>
        <CardTitle>{done ? "Password updated" : "Choose a new password"}</CardTitle>
        <CardDescription>
          {done
            ? "All your sessions were signed out. Sign in with your new password."
            : "For your security, this signs you out on every device."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        {!done && token ? (
          <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
            <Field id="new_password" label="New password" error={errors.new_password?.message}>
              <Input
                id="new_password"
                type="password"
                autoComplete="new-password"
                {...form.register("new_password")}
              />
            </Field>
            <Field id="confirm" label="Confirm new password" error={errors.confirm?.message}>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                {...form.register("confirm")}
              />
            </Field>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              Update password
            </Button>
          </form>
        ) : null}
        <Link href="/login" className="text-primary text-sm hover:underline">
          Go to sign in
        </Link>
      </CardContent>
    </Card>
  );
}
