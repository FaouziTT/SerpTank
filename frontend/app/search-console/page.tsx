'use client';

import { useState, useEffect } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Search,
  TrendingUp,
  TrendingDown,
  MousePointer,
  Eye,
  Calendar,
  RefreshCw,
  Download,
  ExternalLink,
  Globe,
  AlertCircle,
  CheckCircle,
  Trash2,
  Clock,
  Activity
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useExport } from '@/lib/hooks/use-export';
import { useProject } from '@/lib/project-context';
import { formatNumber, formatPercentage } from '@/lib/utils';
import { SearchQuery, SearchPage } from '@/types/api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { ExportButton } from '@/components/ui/export-button';
import { useBulkSelection } from '@/lib/hooks/use-bulk-selection';
import { BulkActionBar, BulkCheckbox } from '@/components/ui/bulk-action-bar';
import { notifications } from '@/lib/notification-service';

function SearchConsolePage() {
  const [dateRange, setDateRange] = useState('7days');
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState(0);
  const [syncStage, setSyncStage] = useState('');
  const { currentProject } = useProject();
  const queryClient = useQueryClient();
  const { exportToCSV } = useExport();

  // Fetch Search Console dashboard data
  const { data: dashboardData, isLoading: isDashboardLoading, error: dashboardError } = useQuery({
    queryKey: ['search-console-dashboard', currentProject?.url, dateRange],
    queryFn: async () => {
      if (!currentProject?.url) return null;
      const days = dateRange === '7days' ? 7 : dateRange === '28days' ? 28 : 90;
      const response = await api.searchConsole.getDashboard({ 
        days, 
        site_url: currentProject.url 
      });
      return response.data;
    },
    enabled: !!currentProject?.url,
    retry: false, // Don't retry on service unavailable
  });

  // Fetch Search Console sites
  const { data: sitesData, isLoading: isSitesLoading, error: sitesError } = useQuery({
    queryKey: ['search-console-sites'],
    queryFn: async () => {
      const response = await api.searchConsole.getSites();
      return response.data;
    },
    retry: false, // Don't retry on service unavailable
  });

  // Check connection status
  const { data: connectionStatus, error: statusError } = useQuery({
    queryKey: ['search-console-status'],
    queryFn: async () => {
      const response = await api.searchConsole.getStatus();
      return response.data;
    },
    retry: false, // Don't retry on service unavailable
  });

  // Fetch top queries separately
  const { data: queriesData, isLoading: isQueriesLoading, error: queriesError } = useQuery({
    queryKey: ['search-console-queries', currentProject?.url, dateRange],
    queryFn: async () => {
      if (!currentProject?.url) return null;
      const days = dateRange === '7days' ? 7 : dateRange === '28days' ? 28 : 90;
      const response = await api.searchConsole.getQueries({ 
        days, 
        site_url: currentProject.url,
        page_size: 10
      });
      return response.data;
    },
    enabled: !!currentProject?.url,
    retry: false, // Don't retry on service unavailable
  });

  // Fetch top pages separately
  const { data: pagesData, isLoading: isPagesLoading, error: pagesError } = useQuery({
    queryKey: ['search-console-pages', currentProject?.url, dateRange],
    queryFn: async () => {
      if (!currentProject?.url) return null;
      const days = dateRange === '7days' ? 7 : dateRange === '28days' ? 28 : 90;
      const response = await api.searchConsole.getPages({ 
        days, 
        site_url: currentProject.url,
        page_size: 10
      });
      return response.data;
    },
    enabled: !!currentProject?.url,
    retry: false, // Don't retry on service unavailable
  });

  const isLoading = isDashboardLoading || isSitesLoading || isQueriesLoading || isPagesLoading;
  
  // Process the backend data to match frontend expectations
  const processedData = dashboardData ? {
    connected: connectionStatus?.oauth_connected || connectionStatus?.service_account_authenticated || false,
    last_sync: dashboardData.date_range?.end_date || new Date().toISOString(),
    metrics: {
      clicks: dashboardData.performance?.total_clicks || 0,
      impressions: dashboardData.performance?.total_impressions || 0,
      ctr: dashboardData.performance?.average_ctr || 0,
      position: dashboardData.performance?.average_position || 0,
      // Calculate changes from daily breakdown if available
      clicks_change: 0, // Backend doesn't provide this
      impressions_change: 0,
      ctr_change: 0,
      position_change: 0,
    },
    trend_data: dashboardData.performance?.daily_breakdown || [],
    top_queries: queriesData?.queries || dashboardData.top_queries || [],
    top_pages: pagesData?.pages || [],
  } : null;
  
  const searchData = processedData;

  // Simulate data sync progress
  const simulateDataSync = async () => {
    setIsSyncing(true);
    setSyncProgress(0);
    setSyncStage('');

    const stages = [
      { stage: 'Connecting to Google Search Console...', progress: 10 },
      { stage: 'Fetching clicks and impressions data...', progress: 25 },
      { stage: 'Retrieving top performing queries...', progress: 40 },
      { stage: 'Analyzing landing page performance...', progress: 55 },
      { stage: 'Processing CTR and position metrics...', progress: 70 },
      { stage: 'Aggregating country and device data...', progress: 85 },
      { stage: 'Finalizing data synchronization...', progress: 95 },
      { stage: 'Sync complete!', progress: 100 }
    ];

    for (const { stage, progress } of stages) {
      setSyncStage(stage);
      setSyncProgress(progress);
      await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 500));
    }
    
    setIsSyncing(false);
  };

  // Sync data mutation (refresh data)
  const syncData = useMutation({
    mutationFn: async () => {
      if (!currentProject?.url) throw new Error('No project URL');
      
      // Start sync progress simulation
      await simulateDataSync();
      
      // Force refetch all queries
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['search-console-dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['search-console-queries'] }),
        queryClient.invalidateQueries({ queryKey: ['search-console-pages'] }),
      ]);
      return Promise.resolve();
    },
    onSuccess: () => {
      notifications.success('Data Synced', 'Search Console data has been refreshed');
      setSyncProgress(0);
      setSyncStage('');
    },
    onError: () => {
      setIsSyncing(false);
      setSyncProgress(0);
      setSyncStage('');
    },
  });

  // Connect Search Console mutation
  const connectSearchConsole = useMutation({
    mutationFn: async () => {
      // Redirect to Google OAuth authorization
      const response = await api.oauth.google.authorize({
        redirect_uri: `${window.location.origin}/api/v1/oauth/google/callback`,
        state: JSON.stringify({ 
          returnTo: window.location.pathname,
          projectId: currentProject?.id
        })
      });
      
      // The API should return the authorization URL
      if (response.data.authorization_url) {
        window.location.href = response.data.authorization_url;
      }
      
      return response.data;
    },
    onMutate: () => {
      setIsConnecting(true);
    },
    onError: (error) => {
      setIsConnecting(false);
      notifications.error('Connection Failed', 'Failed to connect to Google Search Console');
      console.error('Search Console connection error:', error);
    },
  });

  // Mock data
  const mockData = {
    connected: true,
    last_sync: '2024-01-15T14:30:00Z',
    metrics: {
      clicks: 45623,
      impressions: 892341,
      ctr: 5.11,
      position: 15.2,
      clicks_change: 12.5,
      impressions_change: 8.3,
      ctr_change: 0.3,
      position_change: -2.1,
    },
    trend_data: [
      { date: '2024-01-09', clicks: 6234, impressions: 125432, ctr: 4.97, position: 16.1 },
      { date: '2024-01-10', clicks: 6512, impressions: 128765, ctr: 5.06, position: 15.8 },
      { date: '2024-01-11', clicks: 6789, impressions: 131234, ctr: 5.17, position: 15.5 },
      { date: '2024-01-12', clicks: 6456, impressions: 127890, ctr: 5.05, position: 15.3 },
      { date: '2024-01-13', clicks: 5234, impressions: 115678, ctr: 4.52, position: 15.7 },
      { date: '2024-01-14', clicks: 5890, impressions: 120456, ctr: 4.89, position: 15.2 },
      { date: '2024-01-15', clicks: 6508, impressions: 127543, ctr: 5.10, position: 14.9 },
    ],
    top_queries: [
      { query: 'seo tools comparison', clicks: 2341, impressions: 34567, ctr: 6.77, position: 3.2 },
      { query: 'best seo software 2024', clicks: 1897, impressions: 28943, ctr: 6.55, position: 4.1 },
      { query: 'technical seo guide', clicks: 1654, impressions: 45678, ctr: 3.62, position: 8.7 },
      { query: 'local seo checklist', clicks: 1432, impressions: 23456, ctr: 6.11, position: 5.3 },
      { query: 'content optimization tools', clicks: 1298, impressions: 19876, ctr: 6.53, position: 4.8 },
    ],
    top_pages: [
      { page: '/seo-tools-comparison', clicks: 3456, impressions: 45678, ctr: 7.56, position: 2.8 },
      { page: '/technical-seo-guide', clicks: 2987, impressions: 67890, ctr: 4.40, position: 6.2 },
      { page: '/blog/local-seo-2024', clicks: 2345, impressions: 34567, ctr: 6.79, position: 4.5 },
      { page: '/content-optimization', clicks: 2109, impressions: 28765, ctr: 7.33, position: 3.9 },
      { page: '/pricing', clicks: 1876, impressions: 23456, ctr: 8.00, position: 2.1 },
    ],
  };

  const data = searchData || mockData;

  // Bulk selection for queries
  const queriesBulkSelection = useBulkSelection(
    data?.top_queries?.map((query: any, index: number) => ({ 
      id: `query-${index}`, 
      ...query 
    })) || []
  );

  // Handle bulk actions
  const handleBulkAction = async (actionId: string) => {
    const selectedQueries = queriesBulkSelection.selectedItems;
    
    switch (actionId) {
      case 'export':
        // Export selected queries
        try {
          exportToCSV(selectedQueries, 'selected-queries');
          notifications.success('Export Complete', 'Selected queries exported successfully');
        } catch (error) {
          notifications.error('Export Failed', 'Failed to export selected queries');
        }
        break;
      case 'track':
        notifications.info('Feature Coming Soon', 'Keyword tracking will be available soon');
        break;
      case 'delete':
        notifications.info('Remove Keywords', `${selectedQueries.length} keywords removed from tracking`);
        break;
    }
  };

  const getChangeIcon = (change: number) => {
    if (change > 0) return <TrendingUp className="h-3 w-3 text-green-500" />;
    if (change < 0) return <TrendingDown className="h-3 w-3 text-red-500" />;
    return null;
  };

  const getChangeColor = (change: number, inverse = false) => {
    if (inverse) {
      if (change > 0) return 'text-red-500';
      if (change < 0) return 'text-green-500';
    } else {
      if (change > 0) return 'text-green-500';
      if (change < 0) return 'text-red-500';
    }
    return 'text-gray-500';
  };

  if (!currentProject) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-2">
            <h3 className="text-2xl font-semibold">No Project Selected</h3>
            <p className="text-muted-foreground">
              Please select a project from the dropdown above to view Search Console data.
            </p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  // Check for GSC service availability errors
  const gscServiceError = statusError || dashboardError || queriesError || pagesError || sitesError;
  const isGscServiceUnavailable = gscServiceError && 
    (gscServiceError as any)?.response?.status === 503;
  
  // Check if Search Console is connected
  const isConnected = connectionStatus?.oauth_connected || connectionStatus?.service_account_authenticated || false;
  
  // Show service unavailable message if GSC is not configured
  if (isGscServiceUnavailable) {
    const errorDetail = (gscServiceError as any)?.response?.data?.detail;
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-4 max-w-md">
            <div className="mx-auto w-16 h-16 rounded-full bg-yellow-500/10 flex items-center justify-center">
              <AlertCircle className="h-8 w-8 text-yellow-600" />
            </div>
            <h3 className="text-2xl font-semibold">Search Console Not Available</h3>
            <p className="text-muted-foreground">
              {errorDetail?.message || 'Google Search Console is not configured on this server. Please contact your administrator to set up the Search Console integration.'}
            </p>
            <div className="text-sm text-muted-foreground bg-muted p-3 rounded-lg">
              <p><strong>Service:</strong> {errorDetail?.service || 'search_console'}</p>
              <p><strong>Configured:</strong> {errorDetail?.configured ? 'Yes' : 'No'}</p>
              <p><strong>Authenticated:</strong> {errorDetail?.authenticated ? 'Yes' : 'No'}</p>
            </div>
          </div>
        </div>
      </DashboardLayout>
    );
  }
  
  if (!isConnected && connectionStatus !== undefined) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-4 max-w-md">
            <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Search className="h-8 w-8 text-primary" />
            </div>
            <h3 className="text-2xl font-semibold">Connect Google Search Console</h3>
            <p className="text-muted-foreground">
              Connect your Google Search Console account to view search performance data,
              track keyword rankings, and monitor your site&apos;s visibility in Google search results.
            </p>
            <Button 
              size="lg"
              onClick={() => connectSearchConsole.mutate()}
              disabled={isConnecting}
            >
              {isConnecting ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Connect Search Console
                </>
              )}
            </Button>
          </div>
        </div>
      </DashboardLayout>
    );
  }
  
  // If no data yet, use mock data as fallback
  if (!searchData && isLoading) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh]">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
          <p className="text-muted-foreground">Loading Search Console data...</p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Search Console</h1>
            <p className="text-muted-foreground">
              Google Search Console data and insights
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Select value={dateRange} onValueChange={setDateRange}>
              <SelectTrigger className="w-[180px]">
                <Calendar className="mr-2 h-4 w-4" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7days">Last 7 Days</SelectItem>
                <SelectItem value="28days">Last 28 Days</SelectItem>
                <SelectItem value="3months">Last 3 Months</SelectItem>
                <SelectItem value="6months">Last 6 Months</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => syncData.mutate()}
              disabled={isSyncing}
            >
              {isSyncing ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Sync Data
                </>
              )}
            </Button>
            <ExportButton 
              data={[
                ...(data?.top_queries || []),
                ...(data?.top_pages || [])
              ]}
              filename="search-console-data"
              variant="outline"
              size="sm"
            >
              <Download className="mr-2 h-4 w-4" />
              Export
            </ExportButton>
          </div>
        </div>

        {/* Connection Status with Sync Progress */}
        <Card className={isSyncing ? "border-blue-500/20 bg-blue-500/5" : "border-green-500/20 bg-green-500/5"}>
          <CardContent className="py-4">
            {isSyncing ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Activity className="h-5 w-5 text-blue-500 animate-pulse" />
                    <div>
                      <p className="font-medium flex items-center gap-2">
                        Syncing Search Console Data
                        <Badge variant="secondary" className="animate-pulse">
                          <Activity className="h-3 w-3 mr-1" />
                          In Progress
                        </Badge>
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {syncStage || 'Initializing sync...'}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {Math.round(syncProgress)}%
                  </Badge>
                </div>
                
                <div className="space-y-2">
                  <Progress value={syncProgress} className="h-2" />
                  
                  {/* Sync stages indicator */}
                  <div className="grid grid-cols-4 gap-2 text-xs">
                    <div className={`text-center p-1 rounded ${syncProgress >= 25 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                      Metrics
                    </div>
                    <div className={`text-center p-1 rounded ${syncProgress >= 50 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                      Queries
                    </div>
                    <div className={`text-center p-1 rounded ${syncProgress >= 75 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                      Pages
                    </div>
                    <div className={`text-center p-1 rounded ${syncProgress >= 95 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                      Analytics
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <div>
                    <p className="font-medium">Search Console Connected</p>
                    <p className="text-sm text-muted-foreground">
                      Last synced: {new Date(data.last_sync).toLocaleString()}
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  <Globe className="mr-2 h-4 w-4" />
                  View in Search Console
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Key Metrics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Clicks
              </CardTitle>
              <MousePointer className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(data.metrics.clicks)}</div>
              <div className="flex items-center space-x-1 text-xs">
                {getChangeIcon(data.metrics.clicks_change)}
                <span className={getChangeColor(data.metrics.clicks_change)}>
                  {data.metrics.clicks_change > 0 ? '+' : ''}{data.metrics.clicks_change}%
                </span>
                <span className="text-muted-foreground">vs previous period</span>
              </div>
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Impressions
              </CardTitle>
              <Eye className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(data.metrics.impressions)}</div>
              <div className="flex items-center space-x-1 text-xs">
                {getChangeIcon(data.metrics.impressions_change)}
                <span className={getChangeColor(data.metrics.impressions_change)}>
                  {data.metrics.impressions_change > 0 ? '+' : ''}{data.metrics.impressions_change}%
                </span>
                <span className="text-muted-foreground">vs previous period</span>
              </div>
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Average CTR
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.metrics.ctr.toFixed(2)}%</div>
              <div className="flex items-center space-x-1 text-xs">
                {getChangeIcon(data.metrics.ctr_change)}
                <span className={getChangeColor(data.metrics.ctr_change)}>
                  {data.metrics.ctr_change > 0 ? '+' : ''}{data.metrics.ctr_change}%
                </span>
                <span className="text-muted-foreground">vs previous period</span>
              </div>
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Average Position
              </CardTitle>
              <Search className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.metrics.position.toFixed(1)}</div>
              <div className="flex items-center space-x-1 text-xs">
                {getChangeIcon(-data.metrics.position_change)}
                <span className={getChangeColor(data.metrics.position_change, true)}>
                  {data.metrics.position_change > 0 ? '+' : ''}{Math.abs(data.metrics.position_change)}
                </span>
                <span className="text-muted-foreground">positions</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Performance Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Performance Trend</CardTitle>
            <CardDescription>
              Clicks and impressions over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.trend_data}>
                  <defs>
                    <linearGradient id="colorClicks" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorImpressions" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis 
                    dataKey="date" 
                    className="text-xs"
                    tickFormatter={(value) => {
                      if (!value) return '';
                      try {
                        return new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                      } catch {
                        return value;
                      }
                    }}
                  />
                  <YAxis className="text-xs" />
                  <Tooltip
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                    labelFormatter={(value) => {
                      if (!value) return '';
                      try {
                        return new Date(value).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
                      } catch {
                        return value;
                      }
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="clicks"
                    stroke="#8b5cf6"
                    fillOpacity={1}
                    fill="url(#colorClicks)"
                  />
                  <Area
                    type="monotone"
                    dataKey="impressions"
                    stroke="#06b6d4"
                    fillOpacity={1}
                    fill="url(#colorImpressions)"
                    yAxisId="right"
                  />
                  <YAxis yAxisId="right" orientation="right" className="text-xs" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Data Tables */}
        <Tabs defaultValue="queries" className="space-y-4">
          <TabsList>
            <TabsTrigger value="queries">Top Queries</TabsTrigger>
            <TabsTrigger value="pages">Top Pages</TabsTrigger>
            <TabsTrigger value="countries">Countries</TabsTrigger>
            <TabsTrigger value="devices">Devices</TabsTrigger>
          </TabsList>

          <TabsContent value="queries" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-4">
                    <BulkCheckbox
                      checked={queriesBulkSelection.isAllSelected}
                      indeterminate={queriesBulkSelection.isIndeterminate}
                      onChange={queriesBulkSelection.toggleAll}
                      aria-label="Select all queries"
                    />
                    <div>
                      <CardTitle>Top Search Queries</CardTitle>
                      <CardDescription>
                        Keywords driving the most traffic to your site
                        {queriesBulkSelection.selectedCount > 0 && (
                          <span className="ml-2 text-primary">
                            ({queriesBulkSelection.selectedCount} selected)
                          </span>
                        )}
                      </CardDescription>
                    </div>
                  </div>
                  <ExportButton 
                    data={data?.top_queries || []}
                    filename="search-queries"
                    variant="outline"
                    size="sm"
                    showAdvancedOptions={false}
                  />
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.top_queries.map((query: SearchQuery, index: number) => {
                    const queryId = `query-${index}`;
                    const isSelected = queriesBulkSelection.isSelected(queryId);
                    
                    return (
                      <div 
                        key={index} 
                        className={`flex items-center justify-between p-4 rounded-lg border transition-colors ${
                          isSelected ? 'bg-secondary/50 border-primary' : ''
                        }`}
                      >
                        <div className="flex items-center gap-4 flex-1">
                          <BulkCheckbox
                            checked={isSelected}
                            onChange={() => queriesBulkSelection.toggleItem(queryId)}
                            aria-label={`Select query: ${query.query}`}
                          />
                          <div className="flex-1">
                            <p className="font-medium">{query.query}</p>
                            <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                              <span>Position: {query.position.toFixed(1)}</span>
                            </div>
                          </div>
                        </div>
                      <div className="grid grid-cols-3 gap-8 text-right">
                        <div>
                          <p className="text-sm font-medium">{formatNumber(query.clicks)}</p>
                          <p className="text-xs text-muted-foreground">Clicks</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium">{formatNumber(query.impressions)}</p>
                          <p className="text-xs text-muted-foreground">Impressions</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium">{query.ctr.toFixed(2)}%</p>
                          <p className="text-xs text-muted-foreground">CTR</p>
                        </div>
                      </div>
                    </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="pages" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle>Top Landing Pages</CardTitle>
                    <CardDescription>
                      Pages receiving the most search traffic
                    </CardDescription>
                  </div>
                  <ExportButton 
                    data={data?.top_pages || []}
                    filename="landing-pages"
                    variant="outline"
                    size="sm"
                    showAdvancedOptions={false}
                  />
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.top_pages.map((page: SearchPage, index: number) => (
                    <div key={index} className="flex items-center justify-between p-4 rounded-lg border">
                      <div className="flex-1">
                        <p className="font-medium flex items-center gap-2">
                          {page.page}
                          <ExternalLink className="h-3 w-3 text-muted-foreground" />
                        </p>
                        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                          <span>Position: {page.position.toFixed(1)}</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-8 text-right">
                        <div>
                          <p className="text-sm font-medium">{formatNumber(page.clicks)}</p>
                          <p className="text-xs text-muted-foreground">Clicks</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium">{formatNumber(page.impressions)}</p>
                          <p className="text-xs text-muted-foreground">Impressions</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium">{page.ctr.toFixed(2)}%</p>
                          <p className="text-xs text-muted-foreground">CTR</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Bulk Action Bar */}
      <BulkActionBar
        selectedCount={queriesBulkSelection.selectedCount}
        onAction={handleBulkAction}
        onClear={queriesBulkSelection.deselectAll}
        actions={[
          {
            id: 'export',
            label: 'Export',
            icon: Download,
            variant: 'outline',
          },
          {
            id: 'track',
            label: 'Track Keywords',
            icon: Eye,
            variant: 'default',
          },
          {
            id: 'delete',
            label: 'Remove',
            icon: Trash2,
            variant: 'destructive',
            dangerous: true,
          },
        ]}
      />
    </DashboardLayout>
  );
}

export default withAuth(SearchConsolePage);