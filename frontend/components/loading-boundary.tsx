'use client';

import React, { Suspense, ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

interface LoadingBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  suspense?: boolean;
  delay?: number;
  minHeight?: string;
  className?: string;
}

export function LoadingBoundary({
  children,
  fallback,
  suspense = true,
  delay = 0,
  minHeight = '200px',
  className,
}: LoadingBoundaryProps) {
  const defaultFallback = fallback || (
    <LoadingFallback minHeight={minHeight} className={className} />
  );

  if (!suspense) {
    return <>{children}</>;
  }

  if (delay > 0) {
    return (
      <Suspense fallback={<DelayedLoading delay={delay} fallback={defaultFallback} />}>
        {children}
      </Suspense>
    );
  }

  return <Suspense fallback={defaultFallback}>{children}</Suspense>;
}

// Default loading fallback
export function LoadingFallback({
  minHeight = '200px',
  className,
  message,
}: {
  minHeight?: string;
  className?: string;
  message?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center space-y-4',
        className
      )}
      style={{ minHeight }}
    >
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      {message && (
        <p className="text-sm text-muted-foreground">{message}</p>
      )}
    </div>
  );
}

// Delayed loading component that only shows after a delay
function DelayedLoading({
  delay,
  fallback,
}: {
  delay: number;
  fallback: ReactNode;
}) {
  const [showLoading, setShowLoading] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setShowLoading(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  if (!showLoading) {
    return null;
  }

  return <>{fallback}</>;
}

// Page-level loading skeleton
export function PageLoadingSkeleton() {
  return (
    <div className="space-y-6 p-6">
      {/* Header skeleton */}
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      
      {/* Content skeleton */}
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

// Card loading skeleton
export function CardLoadingSkeleton() {
  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-8 w-8 rounded-full" />
      </div>
      <Skeleton className="h-20 w-full" />
      <div className="flex justify-between items-center">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-16" />
      </div>
    </div>
  );
}

// List loading skeleton
export function ListLoadingSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center space-x-4 p-4 border rounded-lg">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-8 w-20" />
        </div>
      ))}
    </div>
  );
}

// Table loading skeleton
export function TableLoadingSkeleton({ 
  rows = 5, 
  columns = 4 
}: { 
  rows?: number; 
  columns?: number;
}) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex space-x-4 p-4 border-b">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex space-x-4 p-4">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

// Form loading skeleton
export function FormLoadingSkeleton({ fields = 4 }: { fields?: number }) {
  return (
    <div className="space-y-6">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-full" />
        </div>
      ))}
      <div className="flex gap-2">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-24" />
      </div>
    </div>
  );
}

// Hook for managing loading states
export function useLoadingState<T>(
  promise: () => Promise<T>,
  deps: React.DependencyList = []
) {
  const [state, setState] = React.useState<{
    loading: boolean;
    error: Error | null;
    data: T | null;
  }>({
    loading: true,
    error: null,
    data: null,
  });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const memoizedPromise = React.useMemo(() => promise, [promise, ...deps]);

  React.useEffect(() => {
    let cancelled = false;

    setState({ loading: true, error: null, data: null });

    memoizedPromise()
      .then((data) => {
        if (!cancelled) {
          setState({ loading: false, error: null, data });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ loading: false, error, data: null });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [memoizedPromise]);

  return state;
}

// HOC for adding loading boundary to components
export function withLoadingBoundary<P extends object>(
  Component: React.ComponentType<P>,
  loadingBoundaryProps?: Omit<LoadingBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <LoadingBoundary {...loadingBoundaryProps}>
      <Component {...props} />
    </LoadingBoundary>
  );

  WrappedComponent.displayName = `withLoadingBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}