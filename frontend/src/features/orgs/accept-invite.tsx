"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormAlert } from "@/components/forms/field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { orgsApi } from "./api";
import { errorText } from "./errors";

/**
 * Accepts an organization invitation for the signed-in user. The invitation is bound to
 * the invited email address; the API rejects it for any other account.
 */
export function AcceptInvite({ token, email }: { token: string | null; email: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Keep the token out of the address bar (history, screenshots) once we've read it.
  useEffect(() => {
    if (token) window.history.replaceState(null, "", "/invite");
  }, [token]);

  if (!token) {
    return (
      <FormAlert message="This invitation link is incomplete. Open the link from your email again." />
    );
  }

  async function accept() {
    if (!token) return;
    setError(null);
    setBusy(true);
    try {
      const org = await orgsApi.acceptInvitation(token);
      router.push(`/orgs/${org.id}`);
      router.refresh();
    } catch (err) {
      setError(errorText(err, "Could not accept the invitation."));
      setBusy(false);
    }
  }

  return (
    <Card className="mx-auto max-w-md">
      <CardHeader>
        <CardTitle>Join organization</CardTitle>
        <CardDescription>
          You&apos;re signed in as <strong>{email}</strong>. The invitation must have been sent to
          this address.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        <div className="flex gap-2">
          <Button onClick={() => void accept()} disabled={busy}>
            Accept invitation
          </Button>
          <Button variant="outline" asChild>
            <Link href="/dashboard">Not now</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
