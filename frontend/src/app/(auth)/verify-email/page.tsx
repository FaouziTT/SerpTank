import type { Metadata } from "next";
import { Suspense } from "react";

import { VerifyEmail } from "@/features/auth/verify-email";

export const metadata: Metadata = { title: "Verify email" };

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmail />
    </Suspense>
  );
}
