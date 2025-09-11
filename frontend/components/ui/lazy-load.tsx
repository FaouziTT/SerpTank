'use client';

import { lazy, Suspense, ComponentType, ReactNode } from 'react';
import Image from 'next/image';
import { Loader2 } from 'lucide-react';
import { ErrorBoundary } from '@/components/error-boundary';

interface LazyLoadProps {
  fallback?: ReactNode;
  errorFallback?: ComponentType<{ error: Error; reset: () => void }>;
}

// Helper to create lazy loaded components with error boundary
export function createLazyComponent<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  options?: LazyLoadProps
) {
  const LazyComponent = lazy(importFn);

  return function LazyLoadWrapper(props: React.ComponentProps<T>) {
    return (
      <ErrorBoundary fallback={options?.errorFallback}>
        <Suspense
          fallback={
            options?.fallback || (
              <div className="flex items-center justify-center min-h-[200px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            )
          }
        >
          <LazyComponent {...props} />
        </Suspense>
      </ErrorBoundary>
    );
  };
}

// Intersection Observer hook for lazy loading on viewport entry
import { useEffect, useRef, useState } from 'react';

export function useLazyLoad<T extends HTMLElement = HTMLDivElement>(
  options?: IntersectionObserverInit
) {
  const ref = useRef<T>(null);
  const [isIntersecting, setIsIntersecting] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsIntersecting(true);
          setHasLoaded(true);
          observer.disconnect();
        }
      },
      {
        threshold: 0.1,
        rootMargin: '50px',
        ...options,
      }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [options]);

  return {
    ref,
    isIntersecting,
    hasLoaded,
  };
}

// Lazy loading wrapper component
interface LazyLoadWrapperProps {
  children: ReactNode;
  placeholder?: ReactNode;
  className?: string;
  once?: boolean;
}

export function LazyLoadWrapper({
  children,
  placeholder,
  className,
  once = true,
}: LazyLoadWrapperProps) {
  const { ref, hasLoaded, isIntersecting } = useLazyLoad();
  const shouldRender = once ? hasLoaded : isIntersecting;

  return (
    <div ref={ref} className={className}>
      {shouldRender ? (
        children
      ) : (
        placeholder || (
          <div className="flex items-center justify-center min-h-[200px]">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )
      )}
    </div>
  );
}

// Image lazy loading component
interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  placeholder?: string;
  onLoad?: () => void;
  onError?: () => void;
  width?: number;
  height?: number;
}

export function LazyImage({
  src,
  alt,
  placeholder,
  onLoad,
  onError,
  className,
  ...props
}: LazyImageProps) {
  const { ref, hasLoaded } = useLazyLoad();
  const [imageSrc, setImageSrc] = useState<string | Blob>(placeholder || '');
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    if (hasLoaded && src) {
      const img = new globalThis.Image();
      img.src = typeof src === 'string' ? src : URL.createObjectURL(src);
      img.onload = () => {
        setImageSrc(src);
        setIsLoaded(true);
        onLoad?.();
      };
      img.onerror = () => {
        setHasError(true);
        onError?.();
      };
    }
  }, [hasLoaded, src, onLoad, onError]);

  return (
    <div ref={ref} className="relative">
      {hasError ? (
        <div className={cn('flex items-center justify-center bg-muted', className)}>
          <span className="text-muted-foreground">Failed to load image</span>
        </div>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          {...props}
          src={imageSrc}
          alt={alt}
          className={cn(
            'transition-opacity duration-300',
            isLoaded ? 'opacity-100' : 'opacity-0',
            className
          )}
        />
      )}
      {!isLoaded && !hasError && placeholder && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}
    </div>
  );
}

import { cn } from '@/lib/utils';