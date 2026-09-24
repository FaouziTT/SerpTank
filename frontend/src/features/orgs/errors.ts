import { ApiError } from "@/lib/api/problem";

/** User-safe message for a failed mutation (API problem text, else a generic fallback). */
export function errorText(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.userMessage : fallback;
}
