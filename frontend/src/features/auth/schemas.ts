import { z } from "zod";

// Client-side validation mirrors the API's rules for fast feedback; the API remains
// the authority (e.g. breached-password checks happen server-side only).
export const PASSWORD_MIN = 12;

export const loginSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
  remember_me: z.boolean(),
  captcha_token: z.string().optional(),
});

export const registerSchema = z.object({
  full_name: z.string().trim().min(1, "Enter your name.").max(200),
  email: z.email("Enter a valid email address."),
  password: z
    .string()
    .min(PASSWORD_MIN, `Use at least ${PASSWORD_MIN} characters.`)
    .max(128, "Use at most 128 characters."),
});

export const emailSchema = z.object({ email: z.email("Enter a valid email address.") });

export const resetSchema = z
  .object({
    new_password: z.string().min(PASSWORD_MIN, `Use at least ${PASSWORD_MIN} characters.`).max(128),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, {
    message: "Passwords do not match.",
    path: ["confirm"],
  });

export const mfaSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^\d{6}$/, "Enter the 6-digit code."),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
