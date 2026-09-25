"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { FormAlert } from "@/components/forms/field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Confirm } from "@/features/orgs/confirm";
import { api, setCsrfToken, unwrap } from "@/lib/api/client";
import { ApiError } from "@/lib/api/problem";

import { useStepUp } from "./step-up";

async function downloadExport(): Promise<void> {
  const blob = await unwrap(api.GET("/api/v1/auth/me/export", { parseAs: "blob" }));
  const url = URL.createObjectURL(blob as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "serptank-my-data.json";
  link.click();
  URL.revokeObjectURL(url);
}

/** Data-subject rights: download a copy of your data, or delete your account. */
export function YourDataCard() {
  const stepUp = useStepUp();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState("");

  async function exportData() {
    setError(null);
    try {
      await stepUp(downloadExport);
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage : "Could not prepare your data.");
    }
  }

  async function deleteAccount() {
    setError(null);
    try {
      await stepUp(() => unwrap(api.DELETE("/api/v1/auth/me")));
      // The session (and the CSRF token bound to it) no longer exists.
      setCsrfToken(null);
      router.replace("/login?deleted=1");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage : "Could not delete your account.");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your data</CardTitle>
        <CardDescription>
          Download everything we hold about you, or delete your account.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormAlert message={error} />
        <Button variant="outline" onClick={() => void exportData()}>
          Download my data
        </Button>
        <div className="space-y-2 border-t pt-4">
          <p className="text-muted-foreground text-sm">
            Deleting your account signs you out everywhere, removes you from every organization and
            anonymises your profile now. It&apos;s permanently removed after 30 days. If you are the
            last owner of an organization, transfer or delete it first.
          </p>
          <Input
            aria-label="Type DELETE to confirm"
            placeholder="Type DELETE to confirm"
            className="max-w-xs"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
          />
          <Confirm
            trigger={
              <Button variant="destructive" disabled={confirmText !== "DELETE"}>
                Delete my account
              </Button>
            }
            title="Delete your account?"
            description="This can't be undone."
            confirmLabel="Delete account"
            onConfirm={deleteAccount}
          />
        </div>
      </CardContent>
    </Card>
  );
}
