'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Monitor,
  Smartphone,
  Tablet,
  Globe,
  MapPin,
  Clock,
  Shield,
  LogOut,
  AlertTriangle,
  RefreshCw,
  CheckCircle
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDate, formatDistanceToNow } from '@/lib/utils';
import { notifications } from '@/lib/notification-service';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { ConfirmActionModal } from '@/components/ui/confirm-action-modal';

interface Session {
  id: string;
  device_type: 'desktop' | 'mobile' | 'tablet';
  device_name: string;
  browser: string;
  os: string;
  ip_address: string;
  location?: {
    city: string;
    country: string;
  };
  created_at: string;
  last_active: string;
  is_current: boolean;
}

function SessionsPage() {
  const [sessionToRevoke, setSessionToRevoke] = useState<Session | null>(null);
  const [showLogoutAllDialog, setShowLogoutAllDialog] = useState(false);
  const queryClient = useQueryClient();

  // Fetch sessions
  const { data: sessions = [], isLoading, error, refetch } = useQuery({
    queryKey: ['sessions'],
    queryFn: async () => {
      const response = await api.auth.getSessions();
      return response.data as Session[];
    },
  });

  // Revoke session mutation
  const revokeSession = useMutation({
    mutationFn: async (sessionId: string) => {
      return api.auth.revokeSession(sessionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      notifications.success('Session revoked', 'The session has been terminated successfully.');
      setSessionToRevoke(null);
    },
    onError: (error) => {
      notifications.handleApiError(error, 'Failed to revoke session');
    },
  });

  // Logout all sessions mutation
  const logoutAll = useMutation({
    mutationFn: async () => {
      return api.auth.logoutAll();
    },
    onSuccess: () => {
      notifications.success('All sessions terminated', 'You will need to log in again.');
      // Redirect to login after a short delay
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    },
    onError: (error) => {
      notifications.handleApiError(error, 'Failed to logout all sessions');
    },
  });

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType) {
      case 'mobile':
        return <Smartphone className="h-5 w-5" />;
      case 'tablet':
        return <Tablet className="h-5 w-5" />;
      default:
        return <Monitor className="h-5 w-5" />;
    }
  };

  const getActivityStatus = (lastActive: string) => {
    const minutesAgo = Math.floor((Date.now() - new Date(lastActive).getTime()) / 1000 / 60);
    
    if (minutesAgo < 5) {
      return { status: 'Active now', color: 'success' };
    } else if (minutesAgo < 60) {
      return { status: `Active ${minutesAgo}m ago`, color: 'warning' };
    } else {
      return { status: formatDistanceToNow(new Date(lastActive)), color: 'secondary' };
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <LoadingState message="Loading sessions..." size="lg" fullHeight />
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-8">
          <ErrorState
            error={error}
            title="Failed to load sessions"
            description="We couldn't fetch your active sessions. Please try again."
            onRetry={() => refetch()}
          />
        </div>
      </DashboardLayout>
    );
  }

  const currentSession = sessions.find(s => s.is_current);
  const otherSessions = sessions.filter(s => !s.is_current);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Active Sessions</h1>
            <p className="text-muted-foreground">
              Manage your active sessions across all devices
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => refetch()}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button
              variant="destructive"
              onClick={() => setShowLogoutAllDialog(true)}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Logout All Sessions
            </Button>
          </div>
        </div>

        {/* Security Alert */}
        <Card className="border-yellow-500/20 bg-yellow-500/5">
          <CardContent className="flex items-start gap-3 pt-6">
            <Shield className="h-5 w-5 text-yellow-500 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium">Security Tip</p>
              <p className="text-sm text-muted-foreground">
                If you notice any unfamiliar sessions, revoke them immediately and change your password.
                Enable two-factor authentication for enhanced security.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Current Session */}
        {currentSession && (
          <Card className="border-primary/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CardTitle>Current Session</CardTitle>
                  <Badge variant="default">
                    <CheckCircle className="mr-1 h-3 w-3" />
                    This Device
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      {getDeviceIcon(currentSession.device_type)}
                      <div>
                        <p className="font-medium">{currentSession.device_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {currentSession.browser} on {currentSession.os}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-6 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Globe className="h-3 w-3" />
                        {currentSession.ip_address}
                      </span>
                      {currentSession.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {currentSession.location.city}, {currentSession.location.country}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Started {formatDistanceToNow(new Date(currentSession.created_at))}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Other Sessions */}
        <Card>
          <CardHeader>
            <CardTitle>Other Sessions</CardTitle>
            <CardDescription>
              Sessions on other devices or browsers
            </CardDescription>
          </CardHeader>
          <CardContent>
            {otherSessions.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No other active sessions
              </div>
            ) : (
              <div className="space-y-4">
                {otherSessions.map((session) => {
                  const activity = getActivityStatus(session.last_active);
                  
                  return (
                    <div
                      key={session.id}
                      className="flex items-start justify-between p-4 rounded-lg border"
                    >
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          {getDeviceIcon(session.device_type)}
                          <div>
                            <p className="font-medium">{session.device_name}</p>
                            <p className="text-sm text-muted-foreground">
                              {session.browser} on {session.os}
                            </p>
                          </div>
                          <Badge variant={activity.color as any}>
                            {activity.status}
                          </Badge>
                        </div>
                        
                        <div className="flex items-center gap-6 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Globe className="h-3 w-3" />
                            {session.ip_address}
                          </span>
                          {session.location && (
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {session.location.city}, {session.location.country}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            Started {formatDistanceToNow(new Date(session.created_at))}
                          </span>
                        </div>
                      </div>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSessionToRevoke(session)}
                        className="text-destructive hover:text-destructive"
                      >
                        <LogOut className="mr-2 h-4 w-4" />
                        Revoke
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Revoke Session Modal */}
        <ConfirmActionModal
          open={!!sessionToRevoke}
          onOpenChange={() => setSessionToRevoke(null)}
          onConfirm={() => {
            if (sessionToRevoke) {
              revokeSession.mutate(sessionToRevoke.id);
            }
          }}
          type="danger"
          title="Revoke Session?"
          message="Are you sure you want to revoke this session? The device will be logged out immediately."
          confirmLabel="Revoke Session"
        />

        {/* Logout All Modal */}
        <ConfirmActionModal
          open={showLogoutAllDialog}
          onOpenChange={setShowLogoutAllDialog}
          onConfirm={() => logoutAll.mutate()}
          type="danger"
          title="Logout All Sessions?"
          message="This will log you out from all devices, including this one. You'll need to log in again to continue using the application."
          confirmLabel="Logout All Sessions"
        />
      </div>
    </DashboardLayout>
  );
}

export default withAuth(SessionsPage);