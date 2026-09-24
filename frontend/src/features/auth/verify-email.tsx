"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ensureCsrfToken } from "@/lib/api/client";

import { authApi } from "./api";

type State = "verifying" | "done" | "failed";

export function VerifyEmail() {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<State>(token ? "verifying" : "failed");
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true; // tokens are single-use: never submit twice (StrictMode)
    ensureCsrfToken()
      .then(() => authApi.verifyEmail(token))
      .then(() => setState("done"))
      .catch(() => setState("failed"));
  }, [token]);

  const copy = {
    verifying: ["Verifying your email…", "One moment."],
    done: ["Email verified", "Your email address is confirmed. You can now sign in."],
    failed: ["Link invalid or expired", "Request a new verification email from the sign-in page."],
  }[state];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{copy[0]}</CardTitle>
        <CardDescription>{copy[1]}</CardDescription>
      </CardHeader>
      <CardContent>
        {state !== "verifying" ? (
          <Link href="/login" className="text-primary text-sm hover:underline">
            Go to sign in
          </Link>
        ) : null}
      </CardContent>
    </Card>
  );
}
