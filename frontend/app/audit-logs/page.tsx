'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  Calendar,
  Download,
  Filter,
  Loader2,
  Search,
  Shield,
  User,
  Activity,
  FileText,
  Settings,
  Lock,
  Unlock,
  UserPlus,
  UserMinus,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { format } from 'date-fns';

interface AuditLog {
  id: string;
  timestamp: string;
  user_id: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string;
  user_agent: string;
  status: 'success' | 'failure';
  details: Record<string, any>;
}

function AuditLogsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterAction, setFilterAction] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [dateRange, setDateRange] = useState('7d');

  // Fetch audit logs
  const { data: logs, isLoading } = useQuery({
    queryKey: ['audit-logs', searchTerm, filterAction, filterStatus, dateRange],
    queryFn: async () => {
      // Mock data for now
      return [
        {
          id: '1',
          timestamp: new Date().toISOString(),
          user_id: '123',
          user_email: 'john@example.com',
          action: 'login',
          resource_type: 'auth',
          resource_id: 'session_123',
          ip_address: '192.168.1.1',
          user_agent: 'Mozilla/5.0...',
          status: 'success' as const,
          details: { method: 'password' }
        },
        {
          id: '2',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          user_id: '123',
          user_email: 'john@example.com',
          action: 'update_settings',
          resource_type: 'project',
          resource_id: 'proj_456',
          ip_address: '192.168.1.1',
          user_agent: 'Mozilla/5.0...',
          status: 'success' as const,
          details: { setting: 'api_key', old_value: '***', new_value: '***' }
        },
        {
          id: '3',
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          user_id: '456',
          user_email: 'jane@example.com',
          action: 'create_user',
          resource_type: 'user',
          resource_id: 'user_789',
          ip_address: '192.168.1.2',
          user_agent: 'Mozilla/5.0...',
          status: 'success' as const,
          details: { role: 'admin', invited_email: 'newuser@example.com' }
        },
        {
          id: '4',
          timestamp: new Date(Date.now() - 10800000).toISOString(),
          user_id: '123',
          user_email: 'john@example.com',
          action: 'delete_resource',
          resource_type: 'content',
          resource_id: 'content_101',
          ip_address: '192.168.1.1',
          user_agent: 'Mozilla/5.0...',
          status: 'failure' as const,
          details: { error: 'Insufficient permissions' }
        },
        {
          id: '5',
          timestamp: new Date(Date.now() - 14400000).toISOString(),
          user_id: '789',
          user_email: 'admin@example.com',
          action: 'export_data',
          resource_type: 'report',
          resource_id: 'report_202',
          ip_address: '192.168.1.3',
          user_agent: 'Mozilla/5.0...',
          status: 'success' as const,
          details: { format: 'csv', rows: 1500 }
        }
      ];
    }
  });

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'login':
      case 'logout':
        return <Lock className="h-4 w-4" />;
      case 'create_user':
        return <UserPlus className="h-4 w-4" />;
      case 'delete_user':
        return <UserMinus className="h-4 w-4" />;
      case 'update_settings':
        return <Settings className="h-4 w-4" />;
      case 'export_data':
        return <Download className="h-4 w-4" />;
      case 'delete_resource':
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getActionColor = (action: string) => {
    if (action.includes('delete')) return 'text-red-500';
    if (action.includes('create')) return 'text-green-500';
    if (action.includes('update')) return 'text-blue-500';
    return 'text-gray-500';
  };

  const filteredLogs = logs?.filter(log => {
    if (searchTerm && !log.user_email.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !log.action.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    if (filterAction !== 'all' && log.action !== filterAction) {
      return false;
    }
    if (filterStatus !== 'all' && log.status !== filterStatus) {
      return false;
    }
    return true;
  });

  const exportLogs = () => {
    // This would trigger a download of the filtered logs
    const csvContent = [
      ['Timestamp', 'User', 'Action', 'Resource', 'Status', 'IP Address'],
      ...(filteredLogs || []).map(log => [
        log.timestamp,
        log.user_email,
        log.action,
        `${log.resource_type}:${log.resource_id}`,
        log.status,
        log.ip_address
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString()}.csv`;
    a.click();
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Audit Logs</h1>
            <p className="text-muted-foreground">
              Track all system activities and security events
            </p>
          </div>
          <Button onClick={exportLogs}>
            <Download className="mr-2 h-4 w-4" />
            Export Logs
          </Button>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
            <CardDescription>
              Search and filter audit logs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <div className="space-y-2">
                <Label htmlFor="search">Search</Label>
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="search"
                    placeholder="Search by user or action..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-8"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="action">Action</Label>
                <Select value={filterAction} onValueChange={setFilterAction}>
                  <SelectTrigger id="action">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Actions</SelectItem>
                    <SelectItem value="login">Login</SelectItem>
                    <SelectItem value="logout">Logout</SelectItem>
                    <SelectItem value="create_user">Create User</SelectItem>
                    <SelectItem value="update_settings">Update Settings</SelectItem>
                    <SelectItem value="export_data">Export Data</SelectItem>
                    <SelectItem value="delete_resource">Delete Resource</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="status">Status</Label>
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger id="status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                    <SelectItem value="failure">Failure</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="dateRange">Date Range</Label>
                <Select value={dateRange} onValueChange={setDateRange}>
                  <SelectTrigger id="dateRange">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1d">Last 24 hours</SelectItem>
                    <SelectItem value="7d">Last 7 days</SelectItem>
                    <SelectItem value="30d">Last 30 days</SelectItem>
                    <SelectItem value="90d">Last 90 days</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Logs Table */}
        <Card>
          <CardHeader>
            <CardTitle>Activity Logs</CardTitle>
            <CardDescription>
              Detailed record of all system activities
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : (
              <div className="space-y-4">
                {filteredLogs?.map((log) => (
                  <div
                    key={log.id}
                    className="rounded-lg border p-4 space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3">
                        <div className={getActionColor(log.action)}>
                          {getActionIcon(log.action)}
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <p className="font-medium">{log.action.replace(/_/g, ' ').toUpperCase()}</p>
                            <Badge variant={log.status === 'success' ? 'default' : 'destructive'}>
                              {log.status}
                            </Badge>
                          </div>
                          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                            <span className="flex items-center">
                              <User className="mr-1 h-3 w-3" />
                              {log.user_email}
                            </span>
                            <span className="flex items-center">
                              <Calendar className="mr-1 h-3 w-3" />
                              {format(new Date(log.timestamp), 'MMM d, yyyy HH:mm:ss')}
                            </span>
                            <span className="flex items-center">
                              <Shield className="mr-1 h-3 w-3" />
                              {log.ip_address}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    {Object.keys(log.details).length > 0 && (
                      <div className="ml-7 p-3 bg-muted/50 rounded text-sm">
                        <p className="font-medium mb-1">Details:</p>
                        <div className="space-y-1">
                          {Object.entries(log.details).map(([key, value]) => (
                            <div key={key} className="flex items-center space-x-2">
                              <span className="text-muted-foreground">{key}:</span>
                              <span>{String(value)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Summary Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Events</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{filteredLogs?.length || 0}</div>
              <p className="text-xs text-muted-foreground">
                In selected time range
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {filteredLogs ? 
                  Math.round((filteredLogs.filter(l => l.status === 'success').length / filteredLogs.length) * 100) : 0}%
              </div>
              <p className="text-xs text-muted-foreground">
                Successful operations
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Users</CardTitle>
              <User className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {filteredLogs ? new Set(filteredLogs.map(l => l.user_id)).size : 0}
              </div>
              <p className="text-xs text-muted-foreground">
                Unique users in logs
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Failed Actions</CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-500">
                {filteredLogs?.filter(l => l.status === 'failure').length || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                Actions that failed
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default withAuth(AuditLogsPage);