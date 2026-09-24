"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Field, FormAlert } from "@/components/forms/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { keys, orgsApi } from "./api";
import { errorText } from "./errors";

export function CreateOrgForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const org = await orgsApi.create(name.trim());
      await queryClient.invalidateQueries({ queryKey: keys.orgs });
      router.push(`/orgs/${org.id}`);
      // Server components (session memberships, org switcher) must re-read.
      router.refresh();
    } catch (err) {
      setError(errorText(err, "Could not create the organization."));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="max-w-sm space-y-4">
      <FormAlert message={error} />
      <Field id="org-name" label="Organization name" hint="Your company, agency or team.">
        <Input
          id="org-name"
          value={name}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
          autoComplete="organization"
        />
      </Field>
      <Button type="submit" disabled={busy || name.trim().length === 0}>
        Create organization
      </Button>
    </form>
  );
}
