"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { ACTIVE_JOB, jobsApi, type Job } from "./api";

/**
 * Live job state. Uses the SSE stream (`/jobs/{id}/events`, cookie-authenticated,
 * same-origin) and falls back to polling where EventSource is unavailable or fails.
 */
export function useJob(orgId: string, initial: Job | null): Job | null {
  const [job, setJob] = useState<Job | null>(initial);
  const [streamFailed, setStreamFailed] = useState(false);
  const jobId = initial?.id ?? null;
  const active = job !== null && ACTIVE_JOB.has(job.status);

  // Adopt a newly started job; the effect below subscribes to it.
  const [trackedId, setTrackedId] = useState(jobId);
  if (jobId !== trackedId) {
    setTrackedId(jobId);
    setJob(initial);
    setStreamFailed(false);
  }

  useEffect(() => {
    if (!jobId || !active || typeof EventSource === "undefined") return;
    const source = new EventSource(`/api/v1/orgs/${orgId}/jobs/${jobId}/events`);
    source.addEventListener("job", (event) => {
      try {
        setJob(JSON.parse((event as MessageEvent<string>).data) as Job);
      } catch {
        // Ignore malformed frames; the next one (or polling) corrects the state.
      }
    });
    source.onerror = () => {
      source.close();
      setStreamFailed(true);
    };
    return () => source.close();
  }, [orgId, jobId, active]);

  const polling = useQuery({
    queryKey: ["job", orgId, jobId],
    queryFn: () => jobsApi.get(orgId, jobId ?? ""),
    enabled: Boolean(jobId) && active && (streamFailed || typeof EventSource === "undefined"),
    refetchInterval: 2000,
  });
  const polled = polling.data;
  const [lastPolled, setLastPolled] = useState<Job | undefined>(undefined);
  if (polled && polled !== lastPolled) {
    setLastPolled(polled);
    setJob(polled);
  }
  return job;
}
