// k6 smoke/load test for public and read paths. Staging only.
//   k6 run -e BASE_URL=https://staging.example.com infra/k6/smoke.js
// Thresholds encode the SLOs we alert on (p95 < 800 ms, < 1% errors).
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8000";

export const options = {
  scenarios: {
    browse: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: __ENV.RAMP || "1m", target: Number(__ENV.VUS || 20) },
        { duration: __ENV.HOLD || "3m", target: Number(__ENV.VUS || 20) },
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<800"],
    checks: ["rate>0.99"],
  },
};

export default function () {
  const health = http.get(`${BASE}/healthz`, { tags: { name: "healthz" } });
  check(health, { "healthz 200": (r) => r.status === 200 });
  const plans = http.get(`${BASE}/api/v1/public/plans`, { tags: { name: "plans" } });
  check(plans, { "plans 200": (r) => r.status === 200 && r.json("plans").length === 3 });
  // Unauthenticated access must be refused quickly and cheaply.
  const session = http.get(`${BASE}/api/v1/auth/session`, {
    tags: { name: "session" },
    responseCallback: http.expectedStatuses(401),
  });
  check(session, { "anonymous session is 401": (r) => r.status === 401 });
  sleep(1);
}
