"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError } from "@/lib/api/problem";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}

/**
 * Error display. Only API problem details (which are written to be user-safe) are
 * shown verbatim; any other error becomes a generic message. The trace id lets support
 * find the server-side log entry.
 */
export function ErrorState({ error, onRetry, title = "Something went wrong" }: ErrorStateProps) {
  const message =
    error instanceof ApiError ? error.userMessage : "We couldn't load this. Please try again.";
  const traceId = error instanceof ApiError ? error.problem.trace_id : null;
  return (
    <Card className="border-destructive/20 bg-destructive/5">
      <CardContent className="flex flex-col items-center justify-center py-8 text-center">
        <div className="bg-destructive/10 mb-4 rounded-full p-3">
          <AlertTriangle className="text-destructive h-6 w-6" aria-hidden />
        </div>
        <h3 className="mb-2 text-lg font-semibold">{title}</h3>
        <p className="text-muted-foreground mb-2 max-w-md text-sm">{message}</p>
        {traceId ? <p className="text-muted-foreground mb-4 text-xs">Trace ID: {traceId}</p> : null}
        {onRetry ? (
          <Button onClick={onRetry} variant="outline" size="sm">
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden /> Try again
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
