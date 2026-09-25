// k6 spike test: many organizations start ranking checks at once (the heaviest job
// fan-out). Uses pre-created staging API keys (one per org/project) from a JSON file:
//   [{"key": "stk_live_...", "org": "<uuid>", "project": "<uuid>"}, ...]
//   k6 run -e BASE_URL=https://staging.example.com -e TARGETS=targets.json infra/k6/rank-spike.js
// Expect 202 (queued) or 409 (already running) - never 5xx - and fast responses:
// the API only enqueues; workers absorb the load.
import http from "k6/http";
import { check } from "k6";
import { SharedArray } from "k6/data";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8000";
const targets = new SharedArray("targets", () => JSON.parse(open(__ENV.TARGETS || "targets.json")));

export const options = {
  scenarios: {
    spike: { executor: "per-vu-iterations", vus: Math.min(targets.length, 200), iterations: 1 },
  },
  thresholds: {
    "http_req_duration{name:check}": ["p(95)<1500"],
    checks: ["rate>0.99"],
  },
};

export default function () {
  const t = targets[(__VU - 1) % targets.length];
  const res = http.post(`${BASE}/api/v1/orgs/${t.org}/projects/${t.project}/keywords/check`, null, {
    headers: { authorization: `Bearer ${t.key}` },
    tags: { name: "check" },
  });
  check(res, { "queued or already running": (r) => r.status === 202 || r.status === 409 });
}
