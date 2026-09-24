"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Field, FormAlert } from "@/components/forms/field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ensureCsrfToken } from "@/lib/api/client";
import { ApiError } from "@/lib/api/problem";

import { authApi } from "./api";
import { PASSWORD_MIN, registerSchema, type RegisterValues } from "./schemas";

export function RegisterForm() {
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: "", email: "", password: "" },
  });

  async function onSubmit(values: RegisterValues) {
    setError(null);
    try {
      await ensureCsrfToken();
      await authApi.register(values);
      setSubmittedEmail(values.email);
    } catch (err) {
      if (err instanceof ApiError && err.code === "weak_password") {
        form.setError("password", { message: err.userMessage });
      } else {
        setError(
          err instanceof ApiError ? err.userMessage : "Registration failed. Please try again.",
        );
      }
    }
  }

  if (submittedEmail) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Check your email</CardTitle>
          <CardDescription>
            If {submittedEmail} can be registered, we sent a verification link to it. The link
            expires in 48 hours.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link href="/login" className="text-primary text-sm hover:underline">
            Back to sign in
          </Link>
        </CardContent>
      </Card>
    );
  }

  const { errors, isSubmitting } = form.formState;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>Start tracking your Google and AI-search visibility.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
          <Field id="full_name" label="Full name" error={errors.full_name?.message}>
            <Input id="full_name" autoComplete="name" {...form.register("full_name")} />
          </Field>
          <Field id="email" label="Work email" error={errors.email?.message}>
            <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
          </Field>
          <Field
            id="password"
            label="Password"
            error={errors.password?.message}
            hint={`At least ${PASSWORD_MIN} characters. A passphrase of several words works well.`}
          >
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              {...form.register("password")}
            />
          </Field>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </form>
        <p className="text-muted-foreground text-center text-sm">
          Already have an account?{" "}
          <Link href="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
