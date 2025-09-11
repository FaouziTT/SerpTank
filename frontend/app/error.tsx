'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <Card className="max-w-md w-full p-6 text-center space-y-4">
        <div className="flex justify-center">
          <div className="p-3 bg-destructive/10 rounded-full">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>
        </div>
        
        <div className="space-y-2">
          <h2 className="text-xl font-semibold">Something went wrong</h2>
          <p className="text-sm text-muted-foreground">
            We apologize for the inconvenience. Please try refreshing the page.
          </p>
        </div>

        {process.env.NODE_ENV === 'development' && error && (
          <details className="text-left">
            <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground">
              Error details
            </summary>
            <div className="mt-2 p-2 bg-muted rounded text-xs font-mono overflow-x-auto">
              {error.message || error.toString()}
            </div>
          </details>
        )}

        <div className="flex gap-2 justify-center">
          <Button
            variant="default"
            size="sm"
            onClick={() => reset()}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
          <Link href="/">
            <Button variant="outline" size="sm">
              <Home className="h-4 w-4 mr-2" />
              Go Home
            </Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}