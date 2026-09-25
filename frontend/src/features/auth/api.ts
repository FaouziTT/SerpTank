/** Typed wrappers around the identity API. All throw `ApiError` on failure. */
import { api, setCsrfToken, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type LoginResponse = components["schemas"]["LoginResponse"];
export type SessionResponse = components["schemas"]["SessionResponse"];
export type SessionInfo = components["schemas"]["SessionInfo"];
export type PasskeyOut = components["schemas"]["PasskeyOut"];

export const authApi = {
  login: (body: components["schemas"]["LoginRequest"]) =>
    unwrap(api.POST("/api/v1/auth/login", { body })),
  register: (body: components["schemas"]["RegisterRequest"]) =>
    unwrap(api.POST("/api/v1/auth/register", { body })),
  verifyEmail: (token: string) =>
    unwrap(api.POST("/api/v1/auth/verify-email", { body: { token } })),
  resendVerification: (email: string) =>
    unwrap(api.POST("/api/v1/auth/verify-email/resend", { body: { email } })),
  verifyMfa: (body: components["schemas"]["MfaVerifyRequest"]) =>
    unwrap(api.POST("/api/v1/auth/mfa/verify", { body })),
  forgotPassword: (email: string) =>
    unwrap(api.POST("/api/v1/auth/password/forgot", { body: { email } })),
  resetPassword: (token: string, new_password: string) =>
    unwrap(api.POST("/api/v1/auth/password/reset", { body: { token, new_password } })),
  changePassword: (current_password: string, new_password: string) =>
    unwrap(api.POST("/api/v1/auth/password/change", { body: { current_password, new_password } })),
  reauth: (body: components["schemas"]["ReauthRequest"]) =>
    unwrap(api.POST("/api/v1/auth/reauth", { body })),
  session: () => unwrap(api.GET("/api/v1/auth/session")),
  sessions: () => unwrap(api.GET("/api/v1/auth/sessions")),
  revokeSession: (session_id: string) =>
    unwrap(api.DELETE("/api/v1/auth/sessions/{session_id}", { params: { path: { session_id } } })),
  logout: async () => {
    await unwrap(api.POST("/api/v1/auth/logout"));
    setCsrfToken(null);
  },
  logoutAll: async () => {
    await unwrap(api.POST("/api/v1/auth/logout-all"));
    setCsrfToken(null);
  },
  totpSetup: () => unwrap(api.POST("/api/v1/auth/mfa/totp/setup")),
  totpConfirm: (code: string) =>
    unwrap(api.POST("/api/v1/auth/mfa/totp/confirm", { body: { code } })),
  totpDisable: () => unwrap(api.DELETE("/api/v1/auth/mfa/totp")),
  recoveryCodes: () => unwrap(api.POST("/api/v1/auth/mfa/recovery-codes")),
  passkeys: () => unwrap(api.GET("/api/v1/auth/passkeys")),
  passkeyRegisterOptions: () => unwrap(api.POST("/api/v1/auth/passkeys/register/options")),
  passkeyRegister: (credential: Record<string, unknown>, name: string) =>
    unwrap(api.POST("/api/v1/auth/passkeys/register", { body: { credential, name } })),
  passkeyDelete: (passkey_id: string) =>
    unwrap(api.DELETE("/api/v1/auth/passkeys/{passkey_id}", { params: { path: { passkey_id } } })),
  passkeyLoginOptions: () => unwrap(api.POST("/api/v1/auth/passkeys/login/options")),
  passkeyLogin: (credential: Record<string, unknown>, remember_me: boolean) =>
    unwrap(api.POST("/api/v1/auth/passkeys/login", { body: { credential, remember_me } })),
  googleUnlink: () => unwrap(api.POST("/api/v1/auth/google/unlink")),
};

/** Only allow same-site relative redirect targets (prevents open redirects). */
export function safeNextPath(next: string | null | undefined, fallback = "/dashboard"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) {
    return fallback;
  }
  return next;
}

/** Public client configuration (Turnstile site key, billing availability). */
export function publicConfig() {
  return unwrap(api.GET("/api/v1/public/config"));
}
