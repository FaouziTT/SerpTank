'use client';

import { useState, useEffect, useCallback } from 'react'; // <-- CHANGE: Imported useCallback
import { Activity, Calendar, User, Filter } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { api } from '@/lib/api-client';
import { AuditLog } from '@/types/api';
import { formatDistanceToNow, format } from 'date-fns';

interface OrganizationAuditLogsProps {
  organizationId: string;
  currentUserRole: string | null;
}

export function OrganizationAuditLogs({ organizationId, currentUserRole }: OrganizationAuditLogsProps) {
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  // <-- CHANGE: Wrapped in useCallback
  const fetchAuditLogs = useCallback(async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (filter !== 'all') {
        params.action = filter;
      }
      const response = await api.organizations.getAuditLogs(organizationId, params);
      setAuditLogs(response.data?.results || []);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
    }
  }, [organizationId, filter]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]); // <-- CHANGE: Updated dependency array

  const getActionColor = (action: string) => {
    if (action.includes('create')) return 'default';
    if (action.includes('update')) return 'secondary';
    if (action.includes('delete')) return 'destructive';
    return 'outline';
  };

  const getActionIcon = (action: string) => {
    // You can expand this to return different icons based on action type
    return Activity;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Activity Log</h3>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter actions" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Actions</SelectItem>
            <SelectItem value="create">Creates</SelectItem>
            <SelectItem value="update">Updates</SelectItem>
            <SelectItem value="delete">Deletes</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>
            Track all actions performed within this organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="h-20 bg-muted animate-pulse rounded" />
              ))}
            </div>
          ) : auditLogs.length === 0 ? (
            <div className="text-center py-6 text-muted-foreground">
              No activity logs found
            </div>
          ) : (
            <div className="space-y-4">
              {auditLogs.map((log, index) => {
                const Icon = getActionIcon(log.action);
                return (
                  <div key={log.id || index} className="flex items-start gap-3 pb-4 border-b last:border-0">
                    <div className="p-2 bg-muted rounded-full">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{log.user?.name || log.user?.email || 'System'}</span>
                        <Badge variant={getActionColor(log.action)}>
                          {log.action}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {typeof log.details === 'string' ? log.details : (log.details ? JSON.stringify(log.details) : `Performed ${log.action} action`)}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {format(new Date(log.created_at), 'MMM d, yyyy')}
                        </span>
                        <span>{formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}