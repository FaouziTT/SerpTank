'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Activity, 
  Globe, 
  TrendingUp, 
  X,
  ExternalLink 
} from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api-client';

interface ProjectAnalysisLoadingProps {
  projectId: number;
  projectName: string;
  projectUrl: string;
  onComplete?: () => void;
  onClose?: () => void;
  showCloseButton?: boolean;
  redirectOnComplete?: boolean;
  redirectPath?: string;
}

interface TaskStatus {
  status: 'not_started' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  progress?: number;
  message?: string;
  error?: string;
}

interface AnalysisStatus {
  crawl: TaskStatus;
  core_web_vitals: TaskStatus;
  search_console?: TaskStatus;
  google_analytics?: TaskStatus;
}

export function ProjectAnalysisLoading({
  projectId,
  projectName,
  projectUrl,
  onComplete,
  onClose,
  showCloseButton = false,
  redirectOnComplete = true,
  redirectPath = '/dashboard'
}: ProjectAnalysisLoadingProps) {
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [progress, setProgress] = useState(0);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const router = useRouter();

  useEffect(() => {
    let interval: NodeJS.Timeout;
    let timeInterval: NodeJS.Timeout;

    const checkAnalysisStatus = async () => {
      try {
        const response = await api.projects.getAnalysisStatus(projectId.toString());
        const tasks = response.data;
        setAnalysisStatus(tasks);

        // Calculate overall progress
        const taskEntries = Object.entries(tasks) as [string, TaskStatus][];
        const totalTasks = taskEntries.length;
        const completedTasks = taskEntries.filter(([_, task]) => task.status === 'completed').length;
        const currentProgress = Math.round((completedTasks / totalTasks) * 100);
        
        setProgress(currentProgress);

        // Check if analysis is complete
        if (completedTasks === totalTasks && currentProgress === 100) {
          setIsComplete(true);
          if (interval) clearInterval(interval);
          
          if (onComplete) {
            onComplete();
          } else if (redirectOnComplete) {
            // Wait a moment to show completion, then redirect
            setTimeout(() => {
              router.push(redirectPath);
            }, 2000);
          }
        }
      } catch (error) {
        console.error('Failed to fetch analysis status:', error);
      }
    };

    // Start checking status immediately and then every 2 seconds
    checkAnalysisStatus();
    interval = setInterval(checkAnalysisStatus, 2000);

    // Track time elapsed
    timeInterval = setInterval(() => {
      setTimeElapsed(prev => prev + 1);
    }, 1000);

    return () => {
      if (interval) clearInterval(interval);
      if (timeInterval) clearInterval(timeInterval);
    };
  }, [projectId, onComplete, redirectOnComplete, redirectPath, router]);

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getTaskIcon = (task: TaskStatus) => {
    switch (task.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'in_progress':
        return <Activity className="h-5 w-5 text-blue-500 animate-pulse" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getTaskStatusBadge = (task: TaskStatus) => {
    switch (task.status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-500 text-white">Completed</Badge>;
      case 'in_progress':
        return <Badge variant="secondary" className="bg-blue-500 text-white">In Progress</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      case 'skipped':
        return <Badge variant="outline">Skipped</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  const getTaskName = (taskKey: string) => {
    const names: Record<string, string> = {
      crawl: 'Website Crawl & SEO Analysis',
      core_web_vitals: 'Core Web Vitals Analysis',
      search_console: 'Search Console Integration',
      google_analytics: 'Google Analytics Integration'
    };
    return names[taskKey] || taskKey;
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {showCloseButton && onClose && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute right-4 top-4 z-10"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
        
        <CardHeader className="text-center pb-6">
          <div className="mx-auto mb-4 p-3 bg-primary/10 rounded-full w-16 h-16 flex items-center justify-center">
            {isComplete ? (
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            ) : (
              <Activity className="h-8 w-8 text-primary animate-pulse" />
            )}
          </div>
          
          <CardTitle className="text-2xl font-bold">
            {isComplete ? 'Analysis Complete!' : 'Analyzing Your Website'}
          </CardTitle>
          
          <CardDescription className="text-base">
            {isComplete 
              ? `${projectName} has been successfully analyzed and is ready to use.`
              : `We're analyzing ${projectName} and gathering SEO insights. This typically takes 2-5 minutes.`
            }
          </CardDescription>

          <div className="flex items-center justify-center gap-2 mt-2 text-sm text-muted-foreground">
            <Globe className="h-4 w-4" />
            <span className="truncate">{projectUrl}</span>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Overall Progress */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Overall Progress</span>
              <span className="font-mono">{progress}%</span>
            </div>
            <Progress value={progress} className="h-3" />
          </div>

          {/* Task Status */}
          {analysisStatus && (
            <div className="space-y-4">
              <h4 className="font-semibold text-lg">Analysis Tasks</h4>
              <div className="grid gap-3">
                {Object.entries(analysisStatus).map(([taskKey, task]) => (
                  <motion.div
                    key={taskKey}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="flex items-center justify-between p-4 rounded-lg border bg-card/50"
                  >
                    <div className="flex items-center gap-3">
                      {getTaskIcon(task)}
                      <div>
                        <div className="font-medium">{getTaskName(taskKey)}</div>
                        {task.message && (
                          <div className="text-sm text-muted-foreground">{task.message}</div>
                        )}
                        {task.error && (
                          <div className="text-sm text-red-500">{task.error}</div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {task.progress !== undefined && task.status === 'in_progress' && (
                        <span className="text-sm text-muted-foreground">{task.progress}%</span>
                      )}
                      {getTaskStatusBadge(task)}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Time Elapsed */}
          <div className="flex items-center justify-between text-sm text-muted-foreground pt-4 border-t">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              <span>Time elapsed: {formatTime(timeElapsed)}</span>
            </div>
            {!isComplete && (
              <div className="text-xs">
                You can close this page and come back later
              </div>
            )}
          </div>

          {/* Action Buttons */}
          {isComplete && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex gap-2 pt-4"
            >
              <Button 
                onClick={() => router.push('/dashboard')}
                className="flex-1"
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                View Dashboard
              </Button>
              <Button 
                variant="outline"
                onClick={() => window.open(projectUrl, '_blank')}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Visit Site
              </Button>
            </motion.div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}