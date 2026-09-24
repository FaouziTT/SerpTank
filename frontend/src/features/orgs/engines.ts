import type { AIEngine, SearchEngine } from "./api";

/** Display order: Google first, then the Bing family, then regional engines. */
export const SEARCH_ENGINES: { id: SearchEngine; label: string }[] = [
  { id: "google", label: "Google" },
  { id: "bing", label: "Bing" },
  { id: "yahoo", label: "Yahoo" },
  { id: "duckduckgo", label: "DuckDuckGo" },
  { id: "yandex", label: "Yandex" },
  { id: "baidu", label: "Baidu" },
  { id: "naver", label: "Naver" },
  { id: "seznam", label: "Seznam" },
];

export const AI_ENGINES: { id: AIEngine; label: string }[] = [
  { id: "google_ai_overview", label: "Google AI Overviews" },
  { id: "google_ai_mode", label: "Google AI Mode" },
  { id: "chatgpt", label: "ChatGPT" },
  { id: "perplexity", label: "Perplexity" },
  { id: "gemini", label: "Gemini" },
  { id: "copilot", label: "Copilot" },
  { id: "claude", label: "Claude" },
];

export function engineLabel(id: SearchEngine | AIEngine): string {
  return [...SEARCH_ENGINES, ...AI_ENGINES].find((e) => e.id === id)?.label ?? id;
}
