'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Loader2,
  Search,
  BarChart3,
  TrendingUp,
  Activity,
  AlertCircle,
  ExternalLink
} from 'lucide-react';

export interface SetupTask {
  status: 'not_started' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  progress?: number;
  message?: string;
  error?: string;
}

export interface SetupStatus {
  crawl: SetupTask;
  core_web_vitals: SetupTask;
  search_console: SetupTask;
  google_analytics: SetupTask;
}

interface SetupProgressProps {
  setupStatus: SetupStatus;
  projectUrl: string;
}

export function SetupProgress({ setupStatus, projectUrl }: SetupProgressProps) {
  const tasks = [
    {
      id: 'crawl',
      name: 'Website Crawl',
      description: 'Analyzing your website structure and content',
      icon: Search,
      task: setupStatus.crawl,
    },
    {
      id: 'core_web_vitals',
      name: 'Core Web Vitals',
      description: 'Measuring site performance and user experience',
      icon: Activity,
      task: setupStatus.core_web_vitals,
    },
    {
      id: 'search_console',
      name: 'Search Console',
      description: 'Connect to see search performance data',
      icon: TrendingUp,
      task: setupStatus.search_console,
      optional: true,
    },
    {
      id: 'google_analytics',
      name: 'Google Analytics',
      description: 'Connect to see traffic and conversion data',
      icon: BarChart3,
      task: setupStatus.google_analytics,
      optional: true,
    },
  ];

  const completedTasks = tasks.filter(t => t.task.status === 'completed').length;
  const totalRequired = tasks.filter(t => !t.optional).length;
  const overallProgress = Math.round((completedTasks / totalRequired) * 100);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'in_progress':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'skipped':
        return <AlertCircle className="h-5 w-5 text-gray-400" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string, optional?: boolean) => {
    if (optional && status === 'not_started') {
      return <Badge variant="outline">Optional</Badge>;
    }
    
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-500 hover:bg-green-600">Complete</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      case 'in_progress':
        return <Badge variant="default">In Progress</Badge>;
      case 'skipped':
        return <Badge variant="secondary">Skipped</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Setting Up Your Project</CardTitle>
            <CardDescription>
              We&apos;re analyzing {projectUrl} to give you the best SEO insights
            </CardDescription>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold">{overallProgress}%</div>
            <div className="text-sm text-muted-foreground">Complete</div>
          </div>
        </div>
        <Progress value={overallProgress} className="mt-4" />
      </CardHeader>
      <CardContent className="space-y-4">
        {tasks.map((task) => (
          <div key={task.id} className="flex items-start space-x-4 p-4 rounded-lg border bg-card">
            <div className="flex-shrink-0 mt-1">
              {getStatusIcon(task.task.status)}
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">{task.name}</h4>
                {getStatusBadge(task.task.status, task.optional)}
              </div>
              <p className="text-sm text-muted-foreground">
                {task.task.message || task.description}
              </p>
              {task.task.progress !== undefined && task.task.status === 'in_progress' && (
                <Progress value={task.task.progress} className="h-2 mt-2" />
              )}
              {task.task.error && (
                <p className="text-sm text-red-500 mt-2">{task.task.error}</p>
              )}
              {task.optional && task.task.status === 'not_started' && (
                <Button variant="outline" size="sm" className="mt-2">
                  <ExternalLink className="mr-2 h-3 w-3" />
                  Connect
                </Button>
              )}
            </div>
          </div>
        ))}
        
        {overallProgress === 100 && (
          <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <p className="text-sm font-medium text-green-900 dark:text-green-100">
                Initial setup complete! Your dashboard is ready.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}