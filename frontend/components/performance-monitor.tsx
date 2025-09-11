'use client';

import { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface PerformanceMetrics {
  renderTime: number;
  componentName: string;
  timestamp: number;
}

// Performance monitoring hook
export function usePerformanceMonitor(componentName: string) {
  const startTime = useRef(performance.now());
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);

  useEffect(() => {
    const endTime = performance.now();
    const renderTime = endTime - startTime.current;
    
    const metric: PerformanceMetrics = {
      renderTime,
      componentName,
      timestamp: Date.now(),
    };

    setMetrics(metric);

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[Performance] ${componentName} rendered in ${renderTime.toFixed(2)}ms`);
    }

    // Send to analytics in production
    if (process.env.NODE_ENV === 'production' && window.gtag) {
      window.gtag('event', 'timing_complete', {
        name: componentName,
        value: Math.round(renderTime),
        event_category: 'Component Performance',
      });
    }
  }, [componentName]);

  return metrics;
}

// Development-only performance overlay
export function PerformanceOverlay() {
  const [metrics, setMetrics] = useState<PerformanceMetrics[]>([]);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;

    // Listen for performance events
    const handlePerformance = (event: CustomEvent<PerformanceMetrics>) => {
      setMetrics(prev => [...prev.slice(-9), event.detail]);
    };

    window.addEventListener('performance-metric', handlePerformance as any);
    return () => window.removeEventListener('performance-metric', handlePerformance as any);
  }, []);

  if (process.env.NODE_ENV !== 'development' || !isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="fixed bottom-4 left-4 z-50 bg-primary text-primary-foreground px-2 py-1 rounded text-xs"
      >
        Perf
      </button>
    );
  }

  return (
    <Card className="fixed bottom-4 left-4 z-50 w-80 max-h-96 overflow-auto">
      <CardHeader className="py-2">
        <CardTitle className="text-sm flex justify-between items-center">
          Performance Monitor
          <button
            onClick={() => setIsVisible(false)}
            className="text-muted-foreground hover:text-foreground"
          >
            ×
          </button>
        </CardTitle>
      </CardHeader>
      <CardContent className="py-2">
        <div className="space-y-2">
          {metrics.map((metric, index) => (
            <div key={index} className="flex justify-between items-center text-xs">
              <span className="truncate">{metric.componentName}</span>
              <Badge
                variant={metric.renderTime < 16 ? 'default' : metric.renderTime < 50 ? 'warning' : 'destructive'}
              >
                {metric.renderTime.toFixed(2)}ms
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// Web Vitals monitoring - Disabled until web-vitals package is installed
export function useWebVitals() {
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Core Web Vitals
    const reportWebVital = (metric: any) => {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Web Vital] ${metric.name}: ${metric.value}`);
      }

      // Send to analytics
      if (window.gtag) {
        window.gtag('event', metric.name, {
          value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
          metric_id: metric.id,
          metric_value: metric.value,
          metric_delta: metric.delta,
        });
      }
    };

    // TODO: Re-enable when web-vitals package is installed
    // import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
    //   getCLS(reportWebVital);
    //   getFID(reportWebVital);
    //   getFCP(reportWebVital);
    //   getLCP(reportWebVital);
    //   getTTFB(reportWebVital);
    // });
    
    // Log placeholder message for now
    if (process.env.NODE_ENV === 'development') {
      console.log('[Web Vitals] Monitoring disabled - web-vitals package not installed');
    }
  }, []);
}

// Resource hint component for prefetching
interface ResourceHintProps {
  href: string;
  as?: 'script' | 'style' | 'image' | 'font' | 'document';
  type?: 'prefetch' | 'preload' | 'preconnect' | 'dns-prefetch';
}

export function ResourceHint({ href, as, type = 'prefetch' }: ResourceHintProps) {
  useEffect(() => {
    const link = document.createElement('link');
    link.rel = type;
    link.href = href;
    if (as) link.as = as;
    
    document.head.appendChild(link);
    
    return () => {
      document.head.removeChild(link);
    };
  }, [href, as, type]);

  return null;
}