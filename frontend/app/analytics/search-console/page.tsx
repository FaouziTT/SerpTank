'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DetailLayout } from '@/components/layout/detail-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { 
  Search,
  TrendingUp,
  TrendingDown,
  MousePointer,
  Eye,
  RefreshCw,
  Download,
  ExternalLink,
  Globe,
  CheckCircle,
  AlertCircle,
  BarChart3,
  MapPin,
  Smartphone
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { formatNumber, formatPercentage } from '@/lib/utils';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart, PieChart, Pie, Cell } from 'recharts';
import { useToast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import { addDays, format } from 'date-fns';
import { useRealtimeQuery, useRealtimeUpdates } from '@/lib/realtime-context';
import { RealtimeIndicator } from '@/components/realtime-indicator';
import { VirtualTable, ColumnDef } from '@/components/ui/virtual-table';
import { LazyLoadWrapper } from '@/components/ui/lazy-load';

// Components for each tab
function PerformanceOverview({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="space-y-0 pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-32 mb-2" />
                <Skeleton className="h-3 w-40" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[350px] w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

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

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
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

        <Card>
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

        <Card>
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

        <Card>
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
                  tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                  labelFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
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
    </div>
  );
}

function QueriesTab({ queries, isLoading }: { queries: any[]; isLoading: boolean }) {
  const columns: ColumnDef<any>[] = [
    {
      id: 'query',
      header: 'Search Query',
      accessorKey: 'query',
      cell: ({ value, row }) => (
        <div className="flex flex-col">
          <span className="font-medium">{value}</span>
          <Badge variant="secondary" className="w-fit mt-1">
            Position: {row.position.toFixed(1)}
          </Badge>
        </div>
      ),
      width: '40%',
    },
    {
      id: 'clicks',
      header: 'Clicks',
      accessorKey: 'clicks',
      cell: ({ value }) => (
        <div className="text-right">
          <p className="font-medium">{formatNumber(value)}</p>
          <p className="text-xs text-muted-foreground">clicks</p>
        </div>
      ),
      sortable: true,
      width: '15%',
    },
    {
      id: 'impressions',
      header: 'Impressions',
      accessorKey: 'impressions',
      cell: ({ value }) => (
        <div className="text-right">
          <p className="font-medium">{formatNumber(value)}</p>
          <p className="text-xs text-muted-foreground">impressions</p>
        </div>
      ),
      sortable: true,
      width: '15%',
    },
    {
      id: 'ctr',
      header: 'CTR',
      accessorKey: 'ctr',
      cell: ({ value }) => (
        <div className="text-right">
          <p className="font-medium">{value.toFixed(2)}%</p>
          <p className="text-xs text-muted-foreground">CTR</p>
        </div>
      ),
      sortable: true,
      width: '15%',
    },
    {
      id: 'position',
      header: 'Position',
      accessorKey: 'position',
      cell: ({ value }) => (
        <div className="text-right">
          <p className="font-medium">{value.toFixed(1)}</p>
          <p className="text-xs text-muted-foreground">avg position</p>
        </div>
      ),
      sortable: true,
      width: '15%',
    },
  ];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Search Queries</CardTitle>
        <CardDescription>
          Keywords driving the most traffic to your site
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <VirtualTable
          data={queries}
          columns={columns}
          containerHeight={600}
          rowHeight={80}
          getRowId={(row) => row.query}
          stickyHeader
        />
      </CardContent>
    </Card>
  );
}

function PagesTab({ pages, isLoading }: { pages: any[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Landing Pages</CardTitle>
        <CardDescription>
          Pages receiving the most search traffic
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {pages.map((page, index) => (
            <div key={index} className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors">
              <div className="flex-1">
                <p className="font-medium flex items-center gap-2">
                  {page.page}
                  <ExternalLink className="h-3 w-3 text-muted-foreground" />
                </p>
                <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                  <Badge variant="secondary">Position: {page.position.toFixed(1)}</Badge>
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
  );
}

function CountriesTab({ data, isLoading }: { data: any; isLoading: boolean }) {
  // Mock data for countries
  const countries = [
    { country: 'United States', clicks: 12543, impressions: 234567, ctr: 5.35, flag: '🇺🇸' },
    { country: 'United Kingdom', clicks: 8234, impressions: 156789, ctr: 5.25, flag: '🇬🇧' },
    { country: 'Canada', clicks: 5678, impressions: 98765, ctr: 5.75, flag: '🇨🇦' },
    { country: 'Australia', clicks: 4321, impressions: 87654, ctr: 4.93, flag: '🇦🇺' },
    { country: 'Germany', clicks: 3456, impressions: 76543, ctr: 4.52, flag: '🇩🇪' },
  ];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance by Country</CardTitle>
        <CardDescription>
          Geographic distribution of your search traffic
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {countries.map((country, index) => (
            <div key={index} className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{country.flag}</span>
                <div>
                  <p className="font-medium">{country.country}</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-8 text-right">
                <div>
                  <p className="text-sm font-medium">{formatNumber(country.clicks)}</p>
                  <p className="text-xs text-muted-foreground">Clicks</p>
                </div>
                <div>
                  <p className="text-sm font-medium">{formatNumber(country.impressions)}</p>
                  <p className="text-xs text-muted-foreground">Impressions</p>
                </div>
                <div>
                  <p className="text-sm font-medium">{country.ctr.toFixed(2)}%</p>
                  <p className="text-xs text-muted-foreground">CTR</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function DevicesTab({ data, isLoading }: { data: any; isLoading: boolean }) {
  // Mock data for devices
  const deviceData = [
    { name: 'Desktop', value: 65, color: '#8b5cf6' },
    { name: 'Mobile', value: 30, color: '#06b6d4' },
    { name: 'Tablet', value: 5, color: '#10b981' },
  ];

  const deviceDetails = [
    { device: 'Desktop', clicks: 29654, impressions: 580234, ctr: 5.11, icon: '💻' },
    { device: 'Mobile', value: 13687, impressions: 267890, ctr: 5.11, icon: '📱' },
    { device: 'Tablet', value: 2282, impressions: 44217, ctr: 5.16, icon: '📱' },
  ];

  if (isLoading) {
    return (
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[300px] w-full" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Device Distribution</CardTitle>
          <CardDescription>
            Traffic breakdown by device type
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={deviceData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {deviceData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Device Performance</CardTitle>
          <CardDescription>
            Detailed metrics by device type
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {deviceDetails.map((device, index) => (
              <div key={index} className="flex items-center justify-between p-4 rounded-lg border">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{device.icon}</span>
                  <p className="font-medium">{device.device}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">{formatNumber(device.clicks || device.value || 0)}</p>
                  <p className="text-xs text-muted-foreground">Clicks</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SearchConsolePage() {
  const [dateRange, setDateRange] = useState<{ from: Date; to: Date }>({
    from: addDays(new Date(), -7),
    to: new Date(),
  });
  const { currentProject } = useProject();
  const { toast } = useToast();

  // Calculate days from date range
  const days = Math.ceil((dateRange.to.getTime() - dateRange.from.getTime()) / (1000 * 60 * 60 * 24));
  
  // Query key for real-time updates
  const queryKey = ['search-console-dashboard', currentProject?.url || '', days.toString()];

  // Fetch Search Console dashboard data
  const { data: dashboardData, isLoading: isDashboardLoading, refetch, error: dashboardError } = useQuery({
    queryKey,
    queryFn: async () => {
      if (!currentProject?.url) return null;
      try {
        const response = await api.searchConsole.getDashboard({ 
          days, 
          site_url: currentProject.url 
        });
        return response.data;
      } catch (error: any) {
        // Handle 503 Service Unavailable gracefully
        if (error?.response?.status === 503) {
          console.log('Google Search Console is not configured');
          return null;
        }
        throw error;
      }
    },
    enabled: !!currentProject?.url,
    retry: (failureCount, error: any) => {
      // Don't retry on 503 errors
      if (error?.response?.status === 503) return false;
      return failureCount < 2;
    },
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
  
  // Enable real-time updates for this query
  useRealtimeQuery(queryKey, 'search-console');
  
  // Subscribe to search console updates
  useRealtimeUpdates('search-console', (update) => {
    // Additional handling for specific updates if needed
    console.log('Search Console update:', update);
  });

  // Check connection status
  const { data: connectionStatus } = useQuery({
    queryKey: ['search-console-status'],
    queryFn: async () => {
      const response = await api.searchConsole.getStatus();
      return response.data;
    },
  });

  // Sync data mutation
  const syncData = useMutation({
    mutationFn: async () => {
      if (!currentProject?.url) throw new Error('No project URL');
      // Trigger a refetch of the data
      await refetch();
    },
    onSuccess: () => {
      toast({
        title: 'Data synced',
        description: 'Search Console data has been refreshed.',
      });
    },
    onError: () => {
      toast({
        title: 'Sync failed',
        description: 'Failed to sync Search Console data. Please try again.',
        variant: 'destructive',
      });
    },
  });

  // Mock data for development
  const mockData = {
    connected: true,
    last_sync: new Date().toISOString(),
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
    trend_data: Array.from({ length: days }, (_, i) => ({
      date: format(addDays(dateRange.from, i), 'yyyy-MM-dd'),
      clicks: Math.floor(Math.random() * 2000) + 5000,
      impressions: Math.floor(Math.random() * 40000) + 100000,
      ctr: Math.random() * 2 + 4,
      position: Math.random() * 5 + 13,
    })),
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

  const data = dashboardData || mockData;
  const isLoading = isDashboardLoading;

  if (!currentProject) {
    return (
      <DetailLayout
        title="Search Console"
        breadcrumbs={[
          { label: 'Analytics', href: '/analytics' },
          { label: 'Search Console' },
        ]}
        tabs={[
          {
            id: 'main',
            label: 'Overview',
            content: (
              <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
                <div className="text-center space-y-2">
                  <h3 className="text-2xl font-semibold">No Project Selected</h3>
                  <p className="text-muted-foreground">
                    Please select a project from the dropdown above to view Search Console data.
                  </p>
                </div>
              </div>
            ),
          },
        ]}
      />
    );
  }

  if (!data.connected) {
    return (
      <DetailLayout
        title="Search Console"
        breadcrumbs={[
          { label: 'Analytics', href: '/analytics' },
          { label: 'Search Console' },
        ]}
        tabs={[
          {
            id: 'main',
            label: 'Overview',
            content: (
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
                  <Button size="lg">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Connect Search Console
                  </Button>
                </div>
              </div>
            ),
          },
        ]}
      />
    );
  }

  const tabs = [
    {
      id: 'overview',
      label: 'Overview',
      icon: BarChart3,
      content: <PerformanceOverview data={data} isLoading={isLoading} />,
    },
    {
      id: 'queries',
      label: 'Queries',
      icon: Search,
      content: <QueriesTab queries={data.top_queries} isLoading={isLoading} />,
    },
    {
      id: 'pages',
      label: 'Pages',
      icon: Globe,
      content: <PagesTab pages={data.top_pages} isLoading={isLoading} />,
    },
    {
      id: 'countries',
      label: 'Countries',
      icon: MapPin,
      content: <CountriesTab data={data} isLoading={isLoading} />,
    },
    {
      id: 'devices',
      label: 'Devices',
      icon: Smartphone,
      content: <DevicesTab data={data} isLoading={isLoading} />,
    },
  ];

  return (
    <DetailLayout
      title="Search Console Analytics"
      breadcrumbs={[
        { label: 'Analytics', href: '/analytics' },
        { label: 'Search Console' },
      ]}
      actions={[
        {
          label: 'Sync Data',
          onClick: () => syncData.mutate(),
          disabled: syncData.isPending,
          icon: RefreshCw,
        },
        {
          label: 'Export',
          onClick: () => {
            toast({
              title: 'Export started',
              description: 'Your Search Console data export has been initiated.',
            });
          },
          icon: Download,
        },
        {
          label: 'View in Search Console',
          onClick: () => window.open('https://search.google.com/search-console', '_blank'),
          icon: ExternalLink,
        },
      ]}
      tabs={tabs}
    />
  );
}

export default withAuth(SearchConsolePage);