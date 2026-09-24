/** Minimal Mailpit API client for reading verification emails in e2e tests. */
const MAILPIT = process.env.E2E_MAILPIT_URL ?? "http://127.0.0.1:8025";

interface Summary {
  ID: string;
  To: { Address: string }[];
  Subject: string;
}

export async function latestEmailTo(address: string, subjectIncludes: string): Promise<string> {
  for (let attempt = 0; attempt < 50; attempt++) {
    const list = (await (await fetch(`${MAILPIT}/api/v1/messages?limit=50`)).json()) as {
      messages: Summary[];
    };
    const match = list.messages.find(
      (m) => m.To.some((t) => t.Address === address) && m.Subject.includes(subjectIncludes),
    );
    if (match) {
      const message = (await (await fetch(`${MAILPIT}/api/v1/message/${match.ID}`)).json()) as {
        Text: string;
      };
      return message.Text;
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`No email to ${address} matching "${subjectIncludes}"`);
}

export function linkFrom(text: string): string {
  const match = /(https?:\/\/\S+token=[A-Za-z0-9_-]+)/.exec(text);
  if (!match?.[1]) throw new Error("No link in email");
  return match[1];
}
