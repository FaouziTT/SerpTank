/** RFC 9116 security.txt, from the deployment's configured security contact. */
import { operator, siteUrl } from "@/features/marketing/site";

export const dynamic = "force-dynamic";

export function GET(): Response {
  const contact = operator().securityEmail;
  if (!contact) return new Response("Not found", { status: 404 });
  const expires = new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString();
  const body = [
    `Contact: mailto:${contact}`,
    `Expires: ${expires}`,
    "Preferred-Languages: en",
    `Canonical: ${siteUrl()}/.well-known/security.txt`,
    `Policy: ${siteUrl()}/security`,
    "",
  ].join("\n");
  return new Response(body, { headers: { "content-type": "text/plain; charset=utf-8" } });
}
