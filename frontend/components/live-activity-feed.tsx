'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Activity,
  Bell,
  CheckCircle,
  AlertCircle,
  Info,
  X,
  Clock,
  TrendingUp,
  FileText,
  Search,
  DollarSign,
  Users
} from 'lucide-react';
import { formatDistanceToNow } from '@/lib/utils';
import { useWebSocketEvent } from '@/lib/hooks/use-websocket';
import { cn } from '@/lib/utils';

interface ActivityItem {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  category: 'diagnostic' | 'content' | 'market' | 'profitability' | 'general';
  title: string;
  description: string;
  timestamp: string;
  project_id?: string;
  read?: boolean;
}

const activityIcons = {
  diagnostic: Activity,
  content: FileText,
  market: TrendingUp,
  profitability: DollarSign,
  general: Info,
};

const typeIcons = {
  info: Info,
  success: CheckCircle,
  warning: AlertCircle,
  error: AlertCircle,
};

export function LiveActivityFeed({ maxItems = 50 }: { maxItems?: number }) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Listen for all activity-related WebSocket events
  useWebSocketEvent('activity', (activity: ActivityItem) => {
    setActivities((prev) => {
      const newActivities = [
        { ...activity, id: activity.id || `${Date.now()}`, read: false },
        ...prev
      ].slice(0, maxItems);
      
      // Update unread count
      const unread = newActivities.filter(a => !a.read).length;
      setUnreadCount(unread);
      
      return newActivities;
    });
  }, [maxItems]);

  // Convert other WebSocket events to activities
  useWebSocketEvent('diagnostic_update', (data: any) => {
    const activity: ActivityItem = {
      id: `diag-${Date.now()}`,
      type: 'info',
      category: 'diagnostic',
      title: 'Site Health Updated',
      description: data.message || 'Diagnostic scan completed',
      timestamp: new Date().toISOString(),
      project_id: data.project_id,
      read: false,
    };
    setActivities((prev) => [activity, ...prev].slice(0, maxItems));
  }, [maxItems]);

  useWebSocketEvent('task_progress', (data: any) => {
    if (data.status === 'completed' || data.status === 'failed') {
      const activity: ActivityItem = {
        id: `task-${Date.now()}`,
        type: data.status === 'completed' ? 'success' : 'error',
        category: 'general',
        title: data.status === 'completed' ? 'Task Completed' : 'Task Failed',
        description: data.message || `Background task ${data.status}`,
        timestamp: new Date().toISOString(),
        project_id: data.project_id,
        read: false,
      };
      setActivities((prev) => [activity, ...prev].slice(0, maxItems));
    }
  }, [maxItems]);

  const markAsRead = (id: string) => {
    setActivities((prev) =>
      prev.map((activity) =>
        activity.id === id ? { ...activity, read: true } : activity
      )
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const markAllAsRead = () => {
    setActivities((prev) =>
      prev.map((activity) => ({ ...activity, read: true }))
    );
    setUnreadCount(0);
  };

  const clearAll = () => {
    setActivities([]);
    setUnreadCount(0);
  };

  return (
    <>
      {/* Floating Activity Button */}
      <div className="fixed bottom-4 right-4 z-40">
        <Button
          size="lg"
          className="relative rounded-full h-14 w-14 p-0"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge 
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center"
              variant="destructive"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
        </Button>
      </div>

      {/* Activity Feed Panel */}
      {isExpanded && (
        <Card className="fixed bottom-20 right-4 w-96 h-[500px] z-40 shadow-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-lg">Live Activity Feed</CardTitle>
              <CardDescription>Real-time updates from your projects</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {activities.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  disabled={unreadCount === 0}
                >
                  Mark all read
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {activities.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[400px] text-center p-6">
                <Activity className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-sm text-muted-foreground">
                  No activities yet. Real-time updates will appear here as they happen.
                </p>
              </div>
            ) : (
              <ScrollArea className="h-[400px]">
                <div className="p-4 space-y-3">
                  {activities.map((activity) => {
                    const CategoryIcon = activityIcons[activity.category];
                    const TypeIcon = typeIcons[activity.type];
                    
                    return (
                      <div
                        key={activity.id}
                        className={cn(
                          "p-3 rounded-lg border transition-all cursor-pointer",
                          !activity.read && "bg-primary/5 border-primary/20",
                          activity.read && "hover:bg-muted/50"
                        )}
                        onClick={() => markAsRead(activity.id)}
                      >
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5">
                            <CategoryIcon className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div className="flex-1 space-y-1">
                            <div className="flex items-start justify-between gap-2">
                              <p className="text-sm font-medium">{activity.title}</p>
                              <TypeIcon 
                                className={cn(
                                  "h-3 w-3 flex-shrink-0",
                                  activity.type === 'success' && "text-green-500",
                                  activity.type === 'warning' && "text-yellow-500",
                                  activity.type === 'error' && "text-red-500",
                                  activity.type === 'info' && "text-blue-500"
                                )}
                              />
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {activity.description}
                            </p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              {formatDistanceToNow(activity.timestamp)}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            )}
            {activities.length > 0 && (
              <div className="border-t p-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={clearAll}
                >
                  Clear all activities
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </>
  );
}