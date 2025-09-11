'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Activity, 
  Clock, 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Pause, 
  Play,
  RefreshCw,
  Search,
  FileText,
  BarChart,
  Globe
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export type CrawlerStage = 
  | 'preparing' 
  | 'discovering' 
  | 'crawling' 
  | 'analyzing' 
  | 'processing' 
  | 'generating_report' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

export interface CrawlerProgress {
  stage: CrawlerStage;
  percentage: number;
  details: {
    pagesDiscovered?: number;
    pagesCrawled?: number;
    pagesAnalyzed?: number;
    errors?: number;
    warnings?: number;
    estimatedTimeRemaining?: number;
    startTime?: Date;
    currentUrl?: string;
    throughput?: number; // pages per second
  };
  message?: string;
}

interface CrawlerProgressProps {
  progress: CrawlerProgress;
  onCancel?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onRetry?: () => void;
  canCancel?: boolean;
  canPause?: boolean;
  showDetails?: boolean;
  className?: string;
}

const STAGE_CONFIG = {
  preparing: {
    icon: RefreshCw,
    label: 'Preparing Analysis',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    description: 'Initializing crawler and validating configuration'
  },
  discovering: {
    icon: Search,
    label: 'Discovering Pages',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100',
    description: 'Finding all pages on your website'
  },
  crawling: {
    icon: Globe,
    label: 'Crawling Website',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
    description: 'Analyzing pages and collecting data'
  },
  analyzing: {
    icon: BarChart,
    label: 'Analyzing Data',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    description: 'Processing collected data and identifying issues'
  },
  processing: {
    icon: Activity,
    label: 'Processing Results',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    description: 'Calculating scores and metrics'
  },
  generating_report: {
    icon: FileText,
    label: 'Generating Report',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    description: 'Compiling analysis results'
  },
  completed: {
    icon: CheckCircle,
    label: 'Analysis Complete',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    description: 'Analysis completed successfully'
  },
  failed: {
    icon: XCircle,
    label: 'Analysis Failed',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    description: 'An error occurred during analysis'
  },
  cancelled: {
    icon: Pause,
    label: 'Analysis Cancelled',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    description: 'Analysis was cancelled by user'
  }
};

export function CrawlerProgress({ 
  progress, 
  onCancel, 
  onPause, 
  onResume, 
  onRetry,
  canCancel = true,
  canPause = true,
  showDetails = true,
  className = ''
}: CrawlerProgressProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const stageConfig = STAGE_CONFIG[progress.stage];
  const Icon = stageConfig.icon;
  
  const isRunning = !['completed', 'failed', 'cancelled'].includes(progress.stage);
  const isCompleted = progress.stage === 'completed';
  const isFailed = progress.stage === 'failed';
  const isCancelled = progress.stage === 'cancelled';

  useEffect(() => {
    if (!isRunning || !progress.details.startTime) return;

    const interval = setInterval(() => {
      const now = new Date();
      const start = new Date(progress.details.startTime!);
      setElapsedTime(Math.floor((now.getTime() - start.getTime()) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isRunning, progress.details.startTime]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatETA = (seconds?: number) => {
    if (!seconds) return 'Calculating...';
    if (seconds < 60) return `${seconds}s remaining`;
    if (seconds < 3600) return `${Math.ceil(seconds / 60)}m remaining`;
    return `${Math.ceil(seconds / 3600)}h remaining`;
  };

  return (
    <Card className={`border-2 ${isCompleted ? 'border-green-500/50 bg-green-50/50' : isFailed ? 'border-red-500/50 bg-red-50/50' : 'border-primary/20'} ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${stageConfig.bgColor}`}>
              <Icon className={`h-5 w-5 ${stageConfig.color} ${isRunning ? 'animate-pulse' : ''}`} />
            </div>
            <div>
              <CardTitle className="text-lg">{stageConfig.label}</CardTitle>
              <CardDescription>{stageConfig.description}</CardDescription>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {progress.details.startTime && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDuration(elapsedTime)}
              </Badge>
            )}
            
            {isRunning && canPause && onPause && (
              <Button variant="outline" size="sm" onClick={onPause}>
                <Pause className="h-4 w-4" />
              </Button>
            )}
            
            {isRunning && canCancel && onCancel && (
              <Button variant="outline" size="sm" onClick={onCancel}>
                Cancel
              </Button>
            )}
            
            {isFailed && onRetry && (
              <Button variant="outline" size="sm" onClick={onRetry}>
                <RefreshCw className="h-4 w-4 mr-1" />
                Retry
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">
              {progress.message || `${Math.round(progress.percentage)}% Complete`}
            </span>
            {progress.details.estimatedTimeRemaining && (
              <span className="text-muted-foreground">
                {formatETA(progress.details.estimatedTimeRemaining)}
              </span>
            )}
          </div>
          <Progress 
            value={progress.percentage} 
            className={`h-2 ${isCompleted ? 'bg-green-100' : isFailed ? 'bg-red-100' : ''}`}
          />
        </div>

        {/* Current Activity */}
        {progress.details.currentUrl && isRunning && (
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-sm font-medium mb-1">Currently analyzing:</p>
            <p className="text-xs text-muted-foreground truncate font-mono">
              {progress.details.currentUrl}
            </p>
          </div>
        )}

        {/* Detailed Stats */}
        {showDetails && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {progress.details.pagesDiscovered !== undefined && (
              <div className="text-center p-2 bg-blue-50 rounded-lg">
                <p className="text-lg font-bold text-blue-600">{progress.details.pagesDiscovered}</p>
                <p className="text-xs text-blue-600">Discovered</p>
              </div>
            )}
            
            {progress.details.pagesCrawled !== undefined && (
              <div className="text-center p-2 bg-purple-50 rounded-lg">
                <p className="text-lg font-bold text-purple-600">{progress.details.pagesCrawled}</p>
                <p className="text-xs text-purple-600">Crawled</p>
              </div>
            )}
            
            {progress.details.pagesAnalyzed !== undefined && (
              <div className="text-center p-2 bg-green-50 rounded-lg">
                <p className="text-lg font-bold text-green-600">{progress.details.pagesAnalyzed}</p>
                <p className="text-xs text-green-600">Analyzed</p>
              </div>
            )}
            
            {progress.details.errors !== undefined && progress.details.errors > 0 && (
              <div className="text-center p-2 bg-red-50 rounded-lg">
                <p className="text-lg font-bold text-red-600">{progress.details.errors}</p>
                <p className="text-xs text-red-600">Errors</p>
              </div>
            )}
          </div>
        )}

        {/* Performance Stats */}
        {showDetails && progress.details.throughput && (
          <div className="flex justify-between text-sm text-muted-foreground border-t pt-2">
            <span>Processing Speed:</span>
            <span>{progress.details.throughput.toFixed(1)} pages/sec</span>
          </div>
        )}

        {/* Error/Warning Messages */}
        {(progress.details.errors && progress.details.errors > 0) && (
          <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 p-2 rounded">
            <AlertTriangle className="h-4 w-4" />
            <span>{progress.details.errors} errors encountered during analysis</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}