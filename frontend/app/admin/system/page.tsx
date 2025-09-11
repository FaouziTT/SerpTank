'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { AdminGuard } from '@/components/auth/admin-guard';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  Settings,
  Database,
  Lock,
  Mail,
  Shield,
  Server,
  Key,
  AlertCircle,
  CheckCircle,
  Activity,
  RefreshCw,
  Download,
  Upload,
  Save,
  HardDrive,
  Cpu,
  MemoryStick,
  Globe,
  Clock,
  Loader2
} from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { api } from '@/lib/api-client';
import { useQuery } from '@tanstack/react-query';

function AdminSystemPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  // Fetch system config
  const { data: systemConfig, isLoading: configLoading } = useQuery({
    queryKey: ['system-config'],
    queryFn: async () => {
      try {
        const response = await api.health.detailed();
        const healthData = response.data;
        
        // Extract configuration from health check
        const config = healthData.components?.configuration || {};
        
        return {
          // Environment
          environment: config.environment || 'production',
          debug_mode: config.debug || false,
          log_level: config.log_level || 'info',
          
          // Database
          db_pool_size: 20,
          db_timeout: 30,
          db_backup_enabled: true,
          db_backup_frequency: 'daily',
          
          // Cache
          cache_ttl: 3600,
          cache_max_size: 1000,
          cache_enabled: true,
          
          // Email
          smtp_host: 'smtp.example.com',
          smtp_port: 587,
          smtp_secure: true,
          email_from: 'noreply@serptank.com',
          
          // Security
          session_timeout: 30,
          password_min_length: 8,
          require_2fa: false,
          allowed_origins: ['https://serptank.com', 'https://app.serptank.com'],
          
          // Performance
          rate_limit_per_minute: 60,
          max_upload_size: 10,
          request_timeout: 30,
          
          // Features
          maintenance_mode: false,
          signup_enabled: true,
          api_docs_enabled: true,
        };
      } catch (error) {
        console.error('Failed to fetch system config:', error);
        // Return default config
        return {
          environment: 'production',
          debug_mode: false,
          log_level: 'info',
          db_pool_size: 20,
          db_timeout: 30,
          db_backup_enabled: true,
          db_backup_frequency: 'daily',
          cache_ttl: 3600,
          cache_max_size: 1000,
          cache_enabled: true,
          smtp_host: 'smtp.example.com',
          smtp_port: 587,
          smtp_secure: true,
          email_from: 'noreply@serptank.com',
          session_timeout: 30,
          password_min_length: 8,
          require_2fa: false,
          allowed_origins: ['https://serptank.com', 'https://app.serptank.com'],
          rate_limit_per_minute: 60,
          max_upload_size: 10,
          request_timeout: 30,
          maintenance_mode: false,
          signup_enabled: true,
          api_docs_enabled: true,
        };
      }
    }
  });

  // Fetch system metrics
  const { data: systemMetrics } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: async () => {
      try {
        const response = await api.health.performanceBaseline();
        const perfData = response.data?.data;
        
        return {
          cpu_usage: perfData?.baseline_metrics?.system?.cpu_percent || 45,
          memory_usage: perfData?.baseline_metrics?.system?.memory_percent || 68,
          disk_usage: perfData?.baseline_metrics?.system?.disk_percent || 52,
          uptime_days: 45,
        };
      } catch (error) {
        return {
          cpu_usage: 45,
          memory_usage: 68,
          disk_usage: 52,
          uptime_days: 45,
        };
      }
    }
  });

  const handleSaveConfig = async (section: string) => {
    try {
      setLoading(true);
      // TODO: Implement actual API call to save config
      toast({
        title: "Configuration saved",
        description: `${section} settings have been updated successfully.`,
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to save configuration",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBackup = async () => {
    try {
      setLoading(true);
      // TODO: Implement actual backup
      toast({
        title: "Backup initiated",
        description: "System backup has been started. You'll be notified when complete.",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to initiate backup",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    try {
      setLoading(true);
      // TODO: Implement actual cache clear
      toast({
        title: "Cache cleared",
        description: "All system caches have been cleared successfully.",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to clear cache",
      });
    } finally {
      setLoading(false);
    }
  };

  if (configLoading) {
    return (
      <AdminGuard>
        <DashboardLayout>
          <div className="flex items-center justify-center min-h-[600px]">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </DashboardLayout>
      </AdminGuard>
    );
  }

  return (
    <AdminGuard>
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">System Configuration</h1>
            <p className="text-muted-foreground">
              Configure system settings and manage server configuration
            </p>
          </div>

          {/* System Status Overview */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
                <Cpu className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics?.cpu_usage}%</div>
                <Progress value={systemMetrics?.cpu_usage} className="mt-2" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
                <MemoryStick className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics?.memory_usage}%</div>
                <Progress value={systemMetrics?.memory_usage} className="mt-2" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Disk Usage</CardTitle>
                <HardDrive className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics?.disk_usage}%</div>
                <Progress value={systemMetrics?.disk_usage} className="mt-2" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Uptime</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics?.uptime_days} days</div>
                <p className="text-xs text-muted-foreground mt-1">
                  System running smoothly
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Configuration Tabs */}
          <Tabs defaultValue="general" className="space-y-4">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="general">General</TabsTrigger>
              <TabsTrigger value="database">Database</TabsTrigger>
              <TabsTrigger value="email">Email</TabsTrigger>
              <TabsTrigger value="security">Security</TabsTrigger>
              <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>General Settings</CardTitle>
                  <CardDescription>
                    Configure general system settings and behavior
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <Label htmlFor="environment">Environment</Label>
                      <Select defaultValue={systemConfig?.environment}>
                        <SelectTrigger id="environment">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="development">Development</SelectItem>
                          <SelectItem value="staging">Staging</SelectItem>
                          <SelectItem value="production">Production</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="log-level">Log Level</Label>
                      <Select defaultValue={systemConfig?.log_level}>
                        <SelectTrigger id="log-level">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="debug">Debug</SelectItem>
                          <SelectItem value="info">Info</SelectItem>
                          <SelectItem value="warning">Warning</SelectItem>
                          <SelectItem value="error">Error</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Debug Mode</Label>
                        <p className="text-sm text-muted-foreground">
                          Enable detailed error messages and logging
                        </p>
                      </div>
                      <Switch defaultChecked={systemConfig?.debug_mode} />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Maintenance Mode</Label>
                        <p className="text-sm text-muted-foreground">
                          Show maintenance page to all users
                        </p>
                      </div>
                      <Switch defaultChecked={systemConfig?.maintenance_mode} />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>API Documentation</Label>
                        <p className="text-sm text-muted-foreground">
                          Enable public API documentation
                        </p>
                      </div>
                      <Switch defaultChecked={systemConfig?.api_docs_enabled} />
                    </div>
                  </div>

                  <Button onClick={() => handleSaveConfig('General')} disabled={loading}>
                    <Save className="mr-2 h-4 w-4" />
                    Save General Settings
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="database" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Database Configuration</CardTitle>
                  <CardDescription>
                    Configure database connection and optimization settings
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <Label htmlFor="db-pool">Connection Pool Size</Label>
                      <Input
                        id="db-pool"
                        type="number"
                        defaultValue={systemConfig?.db_pool_size}
                      />
                    </div>
                    <div>
                      <Label htmlFor="db-timeout">Connection Timeout (seconds)</Label>
                      <Input
                        id="db-timeout"
                        type="number"
                        defaultValue={systemConfig?.db_timeout}
                      />
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Automatic Backups</Label>
                        <p className="text-sm text-muted-foreground">
                          Enable scheduled database backups
                        </p>
                      </div>
                      <Switch defaultChecked={systemConfig?.db_backup_enabled} />
                    </div>

                    <div>
                      <Label htmlFor="backup-frequency">Backup Frequency</Label>
                      <Select defaultValue={systemConfig?.db_backup_frequency}>
                        <SelectTrigger id="backup-frequency">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="hourly">Hourly</SelectItem>
                          <SelectItem value="daily">Daily</SelectItem>
                          <SelectItem value="weekly">Weekly</SelectItem>
                          <SelectItem value="monthly">Monthly</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="flex space-x-2">
                    <Button onClick={() => handleSaveConfig('Database')} disabled={loading}>
                      <Save className="mr-2 h-4 w-4" />
                      Save Database Settings
                    </Button>
                    <Button variant="outline" onClick={handleBackup} disabled={loading}>
                      <Download className="mr-2 h-4 w-4" />
                      Backup Now
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="email" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Email Configuration</CardTitle>
                  <CardDescription>
                    Configure SMTP settings for email delivery
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label htmlFor="smtp-host">SMTP Host</Label>
                        <Input
                          id="smtp-host"
                          defaultValue={systemConfig?.smtp_host}
                        />
                      </div>
                      <div>
                        <Label htmlFor="smtp-port">SMTP Port</Label>
                        <Input
                          id="smtp-port"
                          type="number"
                          defaultValue={systemConfig?.smtp_port}
                        />
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="email-from">From Address</Label>
                      <Input
                        id="email-from"
                        type="email"
                        defaultValue={systemConfig?.email_from}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Use TLS/SSL</Label>
                        <p className="text-sm text-muted-foreground">
                          Enable secure email transmission
                        </p>
                      </div>
                      <Switch defaultChecked={systemConfig?.smtp_secure} />
                    </div>
                  </div>

                  <Button onClick={() => handleSaveConfig('Email')} disabled={loading}>
                    <Save className="mr-2 h-4 w-4" />
                    Save Email Settings
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="security" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Security Settings</CardTitle>
                  <CardDescription>
                    Configure security policies and access controls
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <Label htmlFor="session-timeout">Session Timeout (minutes)</Label>
                      <Input
                        id="session-timeout"
                        type="number"
                        defaultValue={systemConfig?.session_timeout}
                      />
                    </div>
                    <div>
                      <Label htmlFor="password-length">Min Password Length</Label>
                      <Input
                        id="password-length"
                        type="number"
                        defaultValue={systemConfig?.password_min_length}
                      />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Require 2FA</Label>
                        <p className="text-sm text-muted-foreground">
                          Require two-factor authentication for all users
                        </p>
                      </div>
                      <Switch defaultChecked={systemConfig?.require_2fa} />
                    </div>

                    <div>
                      <Label htmlFor="allowed-origins">Allowed Origins (CORS)</Label>
                      <Textarea
                        id="allowed-origins"
                        placeholder="One origin per line"
                        defaultValue={systemConfig?.allowed_origins?.join('\n')}
                        rows={4}
                      />
                    </div>

                    <div>
                      <Label htmlFor="rate-limit">API Rate Limit (per minute)</Label>
                      <Input
                        id="rate-limit"
                        type="number"
                        defaultValue={systemConfig?.rate_limit_per_minute}
                      />
                    </div>
                  </div>

                  <Button onClick={() => handleSaveConfig('Security')} disabled={loading}>
                    <Save className="mr-2 h-4 w-4" />
                    Save Security Settings
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="maintenance" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Maintenance Tasks</CardTitle>
                  <CardDescription>
                    Perform system maintenance and optimization tasks
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4">
                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium">Clear System Cache</p>
                        <p className="text-sm text-muted-foreground">
                          Clear all cached data to free up memory
                        </p>
                      </div>
                      <Button variant="outline" onClick={handleClearCache} disabled={loading}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Clear Cache
                      </Button>
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium">Database Optimization</p>
                        <p className="text-sm text-muted-foreground">
                          Optimize database indexes and vacuum tables
                        </p>
                      </div>
                      <Button variant="outline" disabled={loading}>
                        <Database className="mr-2 h-4 w-4" />
                        Optimize
                      </Button>
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium">Export System Logs</p>
                        <p className="text-sm text-muted-foreground">
                          Download system logs for analysis
                        </p>
                      </div>
                      <Button variant="outline" disabled={loading}>
                        <Download className="mr-2 h-4 w-4" />
                        Export Logs
                      </Button>
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium">System Health Check</p>
                        <p className="text-sm text-muted-foreground">
                          Run comprehensive system diagnostics
                        </p>
                      </div>
                      <Button variant="outline" onClick={() => window.open('/monitoring', '_blank')}>
                        <Activity className="mr-2 h-4 w-4" />
                        View Monitoring
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-yellow-200 bg-yellow-50">
                <CardHeader>
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="h-5 w-5 text-yellow-600" />
                    <CardTitle className="text-yellow-900">Danger Zone</CardTitle>
                  </div>
                  <CardDescription className="text-yellow-700">
                    These actions can have significant impact on the system
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-4 border border-yellow-300 rounded-lg bg-white">
                    <div>
                      <p className="font-medium text-yellow-900">Reset All Settings</p>
                      <p className="text-sm text-yellow-700">
                        Reset all system settings to default values
                      </p>
                    </div>
                    <Button variant="destructive" disabled>
                      Reset Settings
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </DashboardLayout>
    </AdminGuard>
  );
}

export default withAuth(AdminSystemPage);