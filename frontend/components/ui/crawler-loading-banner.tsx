'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Search, BarChart3, CheckCircle, AlertTriangle, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface CrawlerStatus {
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  progress?: number;
  current_url?: string;
  urls_discovered?: number;
  urls_crawled?: number;
  urls_analyzed?: number;
  errors_count?: number;
  estimated_completion?: string;
  message?: string;
}

interface CrawlerLoadingBannerProps {
  crawlerStatus: CrawlerStatus | null;
  onDismiss?: () => void;
  showDismissButton?: boolean;
  className?: string;
}

export function CrawlerLoadingBanner({ 
  crawlerStatus, 
  onDismiss, 
  showDismissButton = false,
  className = ""
}: CrawlerLoadingBannerProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (crawlerStatus && (crawlerStatus.status === 'PENDING' || crawlerStatus.status === 'IN_PROGRESS')) {
      setIsVisible(true);
    } else if (crawlerStatus?.status === 'COMPLETED' || crawlerStatus?.status === 'FAILED') {
      // Show completion status briefly then auto-hide
      const timer = setTimeout(() => {
        setIsVisible(false);
      }, 5000);
      return () => clearTimeout(timer);
    } else {
      setIsVisible(false);
    }
  }, [crawlerStatus]);

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.();
  };

  const getStatusIcon = () => {
    switch (crawlerStatus?.status) {
      case 'PENDING':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'IN_PROGRESS':
        return <Search className="h-4 w-4 animate-pulse" />;
      case 'COMPLETED':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'FAILED':
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      default:
        return <Loader2 className="h-4 w-4 animate-spin" />;
    }
  };

  const getStatusColor = () => {
    switch (crawlerStatus?.status) {
      case 'COMPLETED':
        return 'border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-800';
      case 'FAILED':
        return 'border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800';
      case 'IN_PROGRESS':
        return 'border-blue-200 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-800';
      default:
        return 'border-yellow-200 bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-800';
    }
  };

  const getStatusMessage = () => {
    if (crawlerStatus?.message) {
      return crawlerStatus.message;
    }

    switch (crawlerStatus?.status) {
      case 'PENDING':
        return 'Preparing to analyze your website...';
      case 'IN_PROGRESS':
        return crawlerStatus.current_url 
          ? `Analyzing: ${crawlerStatus.current_url}` 
          : 'Crawling your website and analyzing pages...';
      case 'COMPLETED':
        return 'Website analysis completed successfully!';
      case 'FAILED':
        return 'Analysis encountered some issues but has completed.';
      default:
        return 'Processing...';
    }
  };

  const getProgressValue = () => {
    if (crawlerStatus?.progress !== undefined) {
      return crawlerStatus.progress;
    }
    
    // Calculate progress based on crawled vs discovered
    if (crawlerStatus?.urls_discovered && crawlerStatus?.urls_crawled) {
      return (crawlerStatus.urls_crawled / crawlerStatus.urls_discovered) * 100;
    }
    
    return crawlerStatus?.status === 'IN_PROGRESS' ? 45 : 0;
  };

  if (!crawlerStatus || !isVisible) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -20, scale: 0.95 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className={className}
      >
        <Card className={`${getStatusColor()} border-2 shadow-sm`}>
          <CardContent className="p-4">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 mt-0.5">
                {getStatusIcon()}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <h4 className="font-semibold text-sm">
                    {crawlerStatus.status === 'COMPLETED' 
                      ? 'Analysis Complete' 
                      : crawlerStatus.status === 'FAILED'
                      ? 'Analysis Complete with Issues'
                      : 'Analyzing Your Website'
                    }
                  </h4>
                  <Badge 
                    variant={crawlerStatus.status === 'COMPLETED' ? 'default' : 
                             crawlerStatus.status === 'FAILED' ? 'destructive' : 
                             'secondary'}
                  >
                    {crawlerStatus.status.replace('_', ' ').toLowerCase()}
                  </Badge>
                </div>
                
                <p className="text-sm text-muted-foreground mb-3">
                  {getStatusMessage()}
                </p>

                {/* Progress bar for active crawls */}
                {(crawlerStatus.status === 'PENDING' || crawlerStatus.status === 'IN_PROGRESS') && (
                  <div className="space-y-2 mb-3">
                    <Progress value={getProgressValue()} className="h-2" />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>
                        {crawlerStatus.urls_crawled || 0} of {crawlerStatus.urls_discovered || '...'} pages analyzed
                      </span>
                      {crawlerStatus.estimated_completion && (
                        <span>Est. completion: {crawlerStatus.estimated_completion}</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Stats row */}
                <div className="flex items-center gap-6 text-xs">
                  {crawlerStatus.urls_discovered && (
                    <div className="flex items-center gap-1">
                      <Search className="h-3 w-3" />
                      <span>{crawlerStatus.urls_discovered} discovered</span>
                    </div>
                  )}
                  {crawlerStatus.urls_analyzed && (
                    <div className="flex items-center gap-1">
                      <BarChart3 className="h-3 w-3" />
                      <span>{crawlerStatus.urls_analyzed} analyzed</span>
                    </div>
                  )}
                  {crawlerStatus.errors_count && crawlerStatus.errors_count > 0 && (
                    <div className="flex items-center gap-1 text-amber-600">
                      <AlertTriangle className="h-3 w-3" />
                      <span>{crawlerStatus.errors_count} issues found</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Dismiss button */}
              {(showDismissButton || crawlerStatus.status === 'COMPLETED' || crawlerStatus.status === 'FAILED') && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 flex-shrink-0"
                  onClick={handleDismiss}
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}

export default CrawlerLoadingBanner;