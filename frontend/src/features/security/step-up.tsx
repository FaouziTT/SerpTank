"use client";

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { Field, FormAlert } from "@/components/forms/field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { authApi } from "@/features/auth/api";
import { ApiError } from "@/lib/api/problem";

type Runner = <T>(action: () => Promise<T>) => Promise<T>;

const StepUpContext = createContext<Runner | null>(null);

/**
 * Step-up authentication: runs an action and, if the API answers `reauth_required`,
 * asks for the password (or an authenticator code), re-authenticates and retries once.
 */
export function StepUpProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const pending = useRef<{ resolve: () => void; reject: (e: unknown) => void } | null>(null);

  const askForReauth = useCallback(
    () =>
      new Promise<void>((resolve, reject) => {
        pending.current = { resolve, reject };
        setPassword("");
        setError(null);
        setOpen(true);
      }),
    [],
  );

  const run: Runner = useCallback(
    async (action) => {
      try {
        return await action();
      } catch (err) {
        if (!(err instanceof ApiError) || err.code !== "reauth_required") throw err;
        await askForReauth();
        return action();
      }
    },
    [askForReauth],
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = password.trim();
    try {
      await authApi.reauth(/^\d{6}$/.test(value) ? { code: value } : { password: value });
      setOpen(false);
      pending.current?.resolve();
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage : "Could not confirm your identity.");
    }
  }

  function cancel(nextOpen: boolean) {
    if (nextOpen) return;
    setOpen(false);
    pending.current?.reject(new Error("cancelled"));
  }

  return (
    <StepUpContext.Provider value={run}>
      {children}
      <Dialog open={open} onOpenChange={cancel}>
        <DialogContent>
          <form onSubmit={submit} className="space-y-4">
            <DialogHeader>
              <DialogTitle>Confirm it&apos;s you</DialogTitle>
              <DialogDescription>
                Enter your password or a code from your authenticator app to continue.
              </DialogDescription>
            </DialogHeader>
            <FormAlert message={error} />
            <Field id="stepup-secret" label="Password or authentication code">
              <Input
                id="stepup-secret"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
              />
            </Field>
            <DialogFooter>
              <Button type="submit">Confirm</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </StepUpContext.Provider>
  );
}

export function useStepUp(): Runner {
  const run = useContext(StepUpContext);
  if (!run) throw new Error("useStepUp must be used inside <StepUpProvider>");
  return run;
}
