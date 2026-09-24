/** Browser WebAuthn helpers (passkeys) built on @simplewebauthn/browser. */
import { useSyncExternalStore } from "react";

import {
  browserSupportsWebAuthn,
  startAuthentication,
  startRegistration,
} from "@simplewebauthn/browser";

export { browserSupportsWebAuthn };

type Json = Record<string, unknown>;

export async function createPasskey(optionsJSON: Json): Promise<Json> {
  const response = await startRegistration({
    optionsJSON: optionsJSON as unknown as Parameters<typeof startRegistration>[0]["optionsJSON"],
  });
  return response as unknown as Json;
}

export async function getPasskeyAssertion(optionsJSON: Json): Promise<Json> {
  const response = await startAuthentication({
    optionsJSON: optionsJSON as unknown as Parameters<typeof startAuthentication>[0]["optionsJSON"],
  });
  return response as unknown as Json;
}

const noopSubscribe = () => () => undefined;

/**
 * Hydration-safe passkey support flag: `false` during server rendering and hydration,
 * the real value on the client afterwards.
 */
export function useWebAuthnSupport(): boolean {
  return useSyncExternalStore(noopSubscribe, browserSupportsWebAuthn, () => false);
}
