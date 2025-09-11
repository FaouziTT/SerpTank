import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface ErrorStateProps {
  error: Error | string;
  onRetry?: () => void;
  title?: string;
  description?: string;
}

export function ErrorState({ 
  error, 
  onRetry, 
  title = 'Something went wrong',
  description = 'An error occurred while loading the data. Please try again.'
}: ErrorStateProps) {
  const errorMessage = error instanceof Error ? error.message : error;

  return (
    <Card className="border-destructive/20 bg-destructive/5">
      <CardContent className="flex flex-col items-center justify-center py-8 text-center">
        <div className="rounded-full bg-destructive/10 p-3 mb-4">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-sm text-muted-foreground mb-4 max-w-md">
          {description}
        </p>
        {errorMessage && (
          <p className="text-xs text-destructive mb-4 font-mono bg-destructive/10 px-3 py-1 rounded">
            {errorMessage}
          </p>
        )}
        {onRetry && (
          <Button onClick={onRetry} variant="outline" size="sm">
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        )}
      </CardContent>
    </Card>
  );
}