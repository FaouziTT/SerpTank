'use client';

import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { DashboardPageHeader } from '@/components/layout/dashboard-page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { 
  Activity, 
  TrendingUp, 
  TrendingDown,
  Users, 
  Globe,
  BarChart3,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  MousePointer,
  Eye,
  RefreshCw,
  FolderOpen,
  Minus,
  Settings,
  Sparkles,
  ArrowRight,
  Zap,
  Target,
  TrendingDown as TrendingDownIcon,
  TrendingUp as TrendingUpIcon
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { dedupedApi as api } from '@/lib/api-deduped';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { CrawlerLoadingBanner } from '@/components/ui/crawler-loading-banner';
import { useCrawlerStatus } from '@/lib/hooks/use-crawler-status';
import { formatNumber, formatPercentage, formatDate, formatRelativeTime } from '@/lib/utils';
import { DashboardSkeleton } from '@/components/ui/dashboard-skeleton';
import { useOnboardingCheck } from '@/hooks/use-onboarding-check';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingState } from '@/components/ui/loading-state';
import { useAutoRefresh, useRefreshInterval } from '@/lib/hooks/use-auto-refresh';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState, useEffect } from 'react';
import { useRealtimeMetrics, useWebSocketSync } from '@/lib/websocket-sync';
import { useDashboardQueries } from '@/lib/hooks/use-parallel-queries';
import { SetupProgress, SetupStatus } from '@/components/dashboard/setup-progress';

function DashboardPage() {
  const { currentProject } = useProject();
  const queryClient = useQueryClient();
  const { interval, setInterval } = useRefreshInterval(60000);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const { scrollY } = useScroll();
  
  // Crawler status for current project
  const { crawlerStatus, isActive: isCrawlerActive, dismissStatus } = useCrawlerStatus(currentProject?.id?.toString());
  
  
  // Check if user needs onboarding
  useOnboardingCheck();
  
  // Enable real-time metric updates via WebSocket
  const { isConnected: wsConnected } = useWebSocketSync();
  useRealtimeMetrics('dashboard', currentProject?.id);
  
  // Log WebSocket connection status
  useEffect(() => {
    console.log('Dashboard WebSocket connection status:', wsConnected ? 'Connected' : 'Disconnected');
  }, [wsConnected]);

  // Use auto-refresh for dashboard metrics
  const { refresh: autoRefresh } = useAutoRefresh(
    ['dashboard-metrics', currentProject?.id],
    interval,
    { enabled: autoRefreshEnabled && !!currentProject }
  );

  // Use optimized parallel queries for faster loading
  const { 
    results: [healthResult, metricsResult, activitiesResult], 
    isLoading, 
    hasError, 
    errors,
    isFetching 
  } = useDashboardQueries(currentProject || undefined);

  // Query for project details to check setup status
  const { data: projectDetails } = useQuery({
    queryKey: ['project', currentProject?.id],
    queryFn: async () => {
      if (!currentProject?.id) return null;
      const response = await api.projects.get(currentProject.id);
      return response.data;
    },
    enabled: !!currentProject?.id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Check if Google Search Console is not configured (503 error)
  const isSearchConsoleNotConfigured = (() => {
    if (!metricsResult?.error) return false;
    const error = metricsResult.error as any;
    return error?.response?.status === 503;
  })();
  const searchConsoleError = metricsResult?.error;

  // Parse setup status
  const setupStatus: SetupStatus | null = (() => {
    if (!projectDetails?.setup_status) return null;
    try {
      return JSON.parse(projectDetails.setup_status);
    } catch {
      return null;
    }
  })();

  // Check if initial setup is complete
  const isSetupComplete = !setupStatus || 
    (setupStatus.crawl.status === 'completed' && 
     setupStatus.core_web_vitals.status === 'completed');

  // Get the most recent update time from query execution
  const getLastUpdateTime = () => {
    const queryTimes = [
      healthResult?.dataUpdatedAt,
      metricsResult?.dataUpdatedAt,
      activitiesResult?.dataUpdatedAt
    ].filter(Boolean);
    
    if (queryTimes.length === 0) {
      return new Date().toISOString();
    }
    
    // Return the most recent update time
    const mostRecentTime = Math.max(...queryTimes);
    return new Date(mostRecentTime).toISOString();
  };

  // Process the parallel query results
  const dashboardData = (() => {
    if (!healthResult?.data && !metricsResult?.data && !activitiesResult?.data) {
      return null;
    }

    const health = healthResult?.data || {};
    const searchConsole = metricsResult?.data || {};
    const activities = activitiesResult?.data || { activities: [] };

    // Extract Search Console metrics from nested structure
    const searchMetrics = searchConsole.performance || {};
    
    // Count issues by severity from technical_issues array
    const technicalIssues = health.technical_issues || [];
    const criticalCount = technicalIssues.filter((issue: any) => issue.severity === 'critical').length;
    const warningCount = technicalIssues.filter((issue: any) => issue.severity === 'warning').length;
    const passedCount = health.passed_count || 0; // This might need to be calculated differently

    return {
      overallHealth: health.health_score || health.overall_score || 0,
      organicTraffic: searchMetrics.total_impressions || 0,
      clicks: searchMetrics.total_clicks || 0,
      ctr: searchMetrics.average_ctr || 0,
      avgPosition: searchMetrics.average_position || 0,
      conversionRate: 0, // Will be loaded separately
      issues: {
        critical: criticalCount,
        warning: warningCount,
        passed: passedCount,
      },
      recentScans: activities.activities?.filter((a: { type: string }) => 
        a.type === 'scan' || a.type === 'crawl' || a.type === 'diagnostic'
      ) || [],
      trends: {
        health: health.score_change || 0,
        traffic: searchMetrics.impressions_change || 0,
        clicks: searchMetrics.clicks_change || 0,
        ctr: searchMetrics.ctr_change || 0,
        position: searchMetrics.position_change || 0,
        conversion: 0,
      },
      lastSync: getLastUpdateTime(),
      isSearchConsoleConnected: !isSearchConsoleNotConfigured && !!searchConsole.performance,
    };
  })();

  // Enhanced refetch function for all parallel queries
  const refetch = async () => {
    await Promise.all([
      healthResult.refetch(),
      metricsResult.refetch(),
      activitiesResult.refetch()
    ]);
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  const handleIntervalChange = (value: string) => {
    const newInterval = parseInt(value, 10);
    setInterval(newInterval);
  };

  // Helper function to get trend icon
  const getTrendIcon = (value: number, inverse = false) => {
    if (inverse) {
      if (value > 0) return <TrendingDown className="h-3 w-3 text-green-500" />;
      if (value < 0) return <TrendingUp className="h-3 w-3 text-red-500" />;
    } else {
      if (value > 0) return <TrendingUp className="h-3 w-3 text-green-500" />;
      if (value < 0) return <TrendingDown className="h-3 w-3 text-red-500" />;
    }
    return <Minus className="h-3 w-3 text-gray-500" />;
  };

  const getTrendColor = (value: number, inverse = false) => {
    if (inverse) {
      if (value > 0) return 'text-green-500';
      if (value < 0) return 'text-red-500';
    } else {
      if (value > 0) return 'text-green-500';
      if (value < 0) return 'text-red-500';
    }
    return 'text-gray-500';
  };

  // Handle different states
  if (!currentProject) {
    return (
      <DashboardLayout>
        <EmptyState 
          icon={FolderOpen}
          title="No Project Selected"
          description="Please select a project from the dropdown above to view dashboard metrics."
        />
      </DashboardLayout>
    );
  }

  if (isLoading) {
    return (
      <DashboardLayout>
        <DashboardSkeleton />
      </DashboardLayout>
    );
  }

  if (hasError || !dashboardData) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-8">
          <ErrorState
            error={errors?.[0] as Error || new Error('Failed to load dashboard data')}
            title="Dashboard Error"
            description="We couldn't fetch your dashboard metrics. This might be due to configuration issues or network problems."
            onRetry={handleRefresh}
          />
        </div>
      </DashboardLayout>
    );
  }

  return (
      <DashboardLayout>
        <div className="space-y-8 relative z-10">
          {/* Crawler Loading Banner */}
          {isCrawlerActive && crawlerStatus && currentProject && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <CrawlerLoadingBanner
                crawlerStatus={crawlerStatus}
                onDismiss={dismissStatus}
                showDismissButton={crawlerStatus.status === 'COMPLETED' || crawlerStatus.status === 'FAILED'}
              />
            </motion.div>
          )}
          
          {/* Google Integration Banner */}
          {!dashboardData?.isSearchConsoleConnected && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <Card className="border-primary/20 bg-primary/5 backdrop-blur-sm card-float">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent" />
                <CardContent className="py-6 relative">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="rounded-full bg-primary/10 p-3 neon-glow-blue">
                        <Settings className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-bold text-lg text-gradient-electric">Unlock Full Dashboard Insights</h3>
                        <p className="text-sm text-muted-foreground">
                          Connect Google Search Console and GA4 to see real-time traffic, clicks, and conversion data
                        </p>
                      </div>
                    </div>
                    <SimpleMagneticWrapper>
                      <CTAButton
                        size="lg"
                        onClick={() => window.location.href = '/settings'}
                      >
                        Connect Google Services
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </CTAButton>
                    </SimpleMagneticWrapper>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Optimized Header - Research-based 2025 standards */}
          <DashboardPageHeader
            title="Your SEO Command Center"
            description="Real-time insights and AI-powered recommendations to dominate search results"
            badge={{
              icon: <Sparkles className="mr-1 h-3 w-3" />,
              text: "AI-Powered Dashboard",
              variant: "secondary"
            }}
            actions={
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  {/* Live indicator */}
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse neon-glow-green" />
                    <span className="text-sm text-green-600 font-medium">Live</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Last updated: {formatRelativeTime(dashboardData.lastSync)}
                  </span>
                  {(isFetching || isRefreshing) && (
                    <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Select
                    value={interval.toString()}
                    onValueChange={handleIntervalChange}
                    disabled={!autoRefreshEnabled}
                  >
                    <SelectTrigger className="h-10 w-[160px] bg-card/80 backdrop-blur-sm border-border/50">
                      <Clock className="mr-2 h-4 w-4" />
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="30000">30 seconds</SelectItem>
                      <SelectItem value="60000">1 minute</SelectItem>
                      <SelectItem value="300000">5 minutes</SelectItem>
                      <SelectItem value="600000">10 minutes</SelectItem>
                      <SelectItem value="1800000">30 minutes</SelectItem>
                    </SelectContent>
                  </Select>

                  <SimpleMagneticWrapper>
                    <MagneticButton
                      variant="ghost"
                      size="sm"
                      onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
                      className={`${autoRefreshEnabled ? 'neon-glow-blue' : 'opacity-50'} bg-card/80 backdrop-blur-sm`}
                      magneticStrength={0}
                    >
                      {autoRefreshEnabled ? 'Auto' : 'Manual'}
                    </MagneticButton>
                  </SimpleMagneticWrapper>

                  <SimpleMagneticWrapper>
                    <CTAButton
                      size="sm"
                      onClick={handleRefresh}
                      disabled={isRefreshing || isFetching}
                      className="gap-2"
                    >
                      <RefreshCw className={`h-4 w-4 ${isRefreshing || isFetching ? 'animate-spin' : ''}`} />
                      Refresh
                    </CTAButton>
                  </SimpleMagneticWrapper>
                </div>
              </div>
            }
          />

        {/* Show setup progress if initial setup is not complete */}
        {!isSetupComplete && setupStatus && currentProject && (
          <SetupProgress 
            setupStatus={setupStatus} 
            projectUrl={currentProject.url} 
          />
        )}

          {/* Key Metrics - Only show when setup is complete or data is available */}
          {(isSetupComplete || dashboardData.overallHealth > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="grid gap-6 md:grid-cols-2 lg:grid-cols-4"
          >
            {/* Overall Health Score */}
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              whileHover={{ y: -10 }}
              className="group"
            >
              <Card className="metric-card border-border/50 bg-card/80 backdrop-blur-sm overflow-hidden card-float h-full">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 relative">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Overall Health Score
                  </CardTitle>
                  <div className="rounded-full bg-primary/10 p-3 neon-glow-blue group-hover:scale-110 transition-transform duration-300">
                    <Activity className="h-5 w-5 text-primary" />
                  </div>
                </CardHeader>
                <CardContent className="relative">
                  <div className="text-4xl font-bold transition-all duration-300 metric-number text-gradient-electric">
                    {dashboardData.overallHealth > 0 ? `${dashboardData.overallHealth}%` : 'N/A'}
                  </div>
                  {dashboardData.trends.health !== 0 && (
                    <div className="flex items-center space-x-1 text-sm mt-2">
                      {getTrendIcon(dashboardData.trends.health)}
                      <span className={getTrendColor(dashboardData.trends.health)}>
                        {Math.abs(dashboardData.trends.health)}%
                      </span>
                      <span className="text-muted-foreground">from last scan</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Organic Traffic (Impressions) */}
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              whileHover={{ y: -10 }}
              className="group"
            >
              <Card className="metric-card border-border/50 bg-card/80 backdrop-blur-sm overflow-hidden card-float h-full">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/[0.02] via-primary/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 relative">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Organic Impressions
                  </CardTitle>
                  <div className="rounded-full bg-blue-500/10 p-3 neon-glow-blue group-hover:scale-110 transition-transform duration-300">
                    <Eye className="h-5 w-5 text-blue-500" />
                  </div>
                </CardHeader>
                <CardContent className="relative">
                  {dashboardData.isSearchConsoleConnected ? (
                    <>
                      <div className="text-4xl font-bold transition-all duration-300 metric-number text-gradient">
                        {dashboardData.organicTraffic > 0 ? formatNumber(dashboardData.organicTraffic) : '0'}
                      </div>
                      {dashboardData.trends.traffic !== 0 && (
                        <div className="flex items-center space-x-1 text-sm mt-2">
                          {getTrendIcon(dashboardData.trends.traffic)}
                          <span className={getTrendColor(dashboardData.trends.traffic)}>
                            {Math.abs(dashboardData.trends.traffic)}%
                          </span>
                          <span className="text-muted-foreground">from last month</span>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="space-y-3">
                      <div className="text-lg font-medium text-muted-foreground">Not Connected</div>
                      <SimpleMagneticWrapper>
                        <MagneticButton
                          variant="ghost"
                          size="sm"
                          className="h-auto p-0 text-xs text-primary"
                          onClick={() => window.location.href = '/settings'}
                          magneticStrength={0}
                        >
                          Connect Google Search Console →
                        </MagneticButton>
                      </SimpleMagneticWrapper>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Clicks & CTR */}
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              whileHover={{ y: -10 }}
              className="group"
            >
              <Card className="metric-card border-border/50 bg-card/80 backdrop-blur-sm overflow-hidden card-float h-full">
                <div className="absolute inset-0 bg-gradient-to-br from-green-500/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 relative">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Clicks & CTR
                  </CardTitle>
                  <div className="rounded-full bg-green-500/10 p-3 neon-glow-green group-hover:scale-110 transition-transform duration-300">
                    <MousePointer className="h-5 w-5 text-green-500" />
                  </div>
                </CardHeader>
                <CardContent className="relative">
                  {dashboardData.isSearchConsoleConnected ? (
                    <>
                      <div className="text-4xl font-bold transition-all duration-300 metric-number text-gradient-neon">
                        {dashboardData.clicks > 0 ? formatNumber(dashboardData.clicks) : '0'}
                      </div>
                      <div className="text-sm text-muted-foreground mt-2">
                        CTR: <span className="font-semibold text-green-500">{dashboardData.ctr > 0 ? `${dashboardData.ctr.toFixed(2)}%` : '0%'}</span>
                        {dashboardData.trends.ctr !== 0 && (
                          <span className={`ml-1 ${getTrendColor(dashboardData.trends.ctr)}`}>
                            ({dashboardData.trends.ctr > 0 ? '+' : ''}{dashboardData.trends.ctr.toFixed(1)}%)
                          </span>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="space-y-3">
                      <div className="text-lg font-medium text-muted-foreground">Not Connected</div>
                      <p className="text-xs text-muted-foreground">Connect to track clicks</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Average Position */}
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              whileHover={{ y: -10 }}
              className="group"
            >
              <Card className="metric-card border-border/50 bg-card/80 backdrop-blur-sm overflow-hidden card-float h-full">
                <div className="absolute inset-0 bg-gradient-to-br from-amber-500/[0.02] via-yellow-500/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 relative">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Avg. Position
                  </CardTitle>
                  <div className="rounded-full bg-amber-500/10 p-3 group-hover:scale-110 transition-transform duration-300">
                    <Globe className="h-5 w-5 text-amber-500" />
                  </div>
                </CardHeader>
                <CardContent className="relative">
                  {dashboardData.isSearchConsoleConnected ? (
                    <>
                      <div className="text-4xl font-bold transition-all duration-300 metric-number text-gradient">
                        {dashboardData.avgPosition > 0 ? dashboardData.avgPosition.toFixed(1) : '—'}
                      </div>
                      {dashboardData.trends.position !== 0 && (
                        <div className="flex items-center space-x-1 text-sm mt-2">
                          {getTrendIcon(dashboardData.trends.position, true)}
                          <span className={getTrendColor(dashboardData.trends.position, true)}>
                            {Math.abs(dashboardData.trends.position).toFixed(1)}
                          </span>
                          <span className="text-muted-foreground">
                            positions {dashboardData.trends.position < 0 ? 'improved' : 'dropped'}
                          </span>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="space-y-3">
                      <div className="text-lg font-medium text-muted-foreground">Not Connected</div>
                      <p className="text-xs text-muted-foreground">Track keyword rankings</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
          )}

          {/* Issues Overview - Only show when setup is complete */}
          {isSetupComplete && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="group"
          >
            <Card className="bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <CardHeader className="relative">
                <CardTitle className="text-2xl font-bold text-gradient">Site Issues Overview</CardTitle>
                <CardDescription className="text-base">
                  Current technical and content issues detected on your site
                </CardDescription>
              </CardHeader>
              <CardContent className="relative">
                <div className="grid gap-6 md:grid-cols-3">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="flex items-center space-x-4 rounded-2xl border p-6 border-destructive/20 bg-destructive/5 card-float group/item"
                  >
                    <div className="rounded-full bg-destructive/10 p-3 neon-glow-pink group-hover/item:scale-110 transition-transform duration-300">
                      <XCircle className="h-8 w-8 text-destructive" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Critical Issues</p>
                      <p className="text-3xl font-bold text-destructive metric-number">{dashboardData.issues.critical}</p>
                    </div>
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="flex items-center space-x-4 rounded-2xl border p-6 border-yellow-500/20 bg-yellow-500/5 card-float group/item"
                  >
                    <div className="rounded-full bg-yellow-500/10 p-3 group-hover/item:scale-110 transition-transform duration-300">
                      <AlertCircle className="h-8 w-8 text-yellow-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Warnings</p>
                      <p className="text-3xl font-bold text-yellow-500 metric-number">{dashboardData.issues.warning}</p>
                    </div>
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="flex items-center space-x-4 rounded-2xl border p-6 border-green-500/20 bg-green-500/5 card-float group/item"
                  >
                    <div className="rounded-full bg-green-500/10 p-3 neon-glow-green group-hover/item:scale-110 transition-transform duration-300">
                      <CheckCircle className="h-8 w-8 text-green-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Passed Checks</p>
                      <p className="text-3xl font-bold text-green-500 metric-number">{dashboardData.issues.passed}</p>
                    </div>
                  </motion.div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
          )}

          {/* Recent Scans - Always show */}
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.7 }}
            className="group"
          >
            <Card className="bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <CardHeader className="relative">
                <CardTitle className="text-2xl font-bold text-gradient">Recent Diagnostic Scans</CardTitle>
                <CardDescription className="text-base">
                  Your site health history and recent scan results
                </CardDescription>
              </CardHeader>
              <CardContent className="relative">
                {dashboardData.recentScans.length > 0 ? (
                  <div className="space-y-4">
                    {dashboardData.recentScans.slice(0, 5).map((scan: any, index: number) => (
                      <motion.div
                        key={scan.id || index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center justify-between rounded-2xl border p-6 bg-card/50 backdrop-blur-sm card-float group/item"
                      >
                        <div className="flex items-center space-x-4">
                          <div className="rounded-full bg-primary/10 p-3 neon-glow-blue group-hover/item:scale-110 transition-transform duration-300">
                            <Clock className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="text-sm font-medium">
                              {formatDate(scan.created_at || scan.date)}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Health Score: <span className="font-semibold text-gradient">{scan.score || scan.health_score || 'N/A'}%</span>
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={scan.status === 'completed' ? 'default' : 'secondary'} className="px-3 py-1">
                            {scan.status || 'completed'}
                          </Badge>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={Activity}
                    title="No recent scans"
                    description="Run a diagnostic scan to see your site's health status"
                    action={{
                      label: 'Run Scan',
                      onClick: () => {
                        // Navigate to diagnostic page
                        window.location.href = '/diagnostic';
                      }
                    }}
                  />
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.8 }}
            className="group"
          >
            <Card className="bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <CardHeader className="relative">
                <CardTitle className="text-2xl font-bold text-gradient">Quick Actions</CardTitle>
                <CardDescription className="text-base">
                  Common tasks and workflows to improve your SEO
                </CardDescription>
              </CardHeader>
              <CardContent className="relative">
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    whileHover={{ y: -5 }}
                    className="group/action"
                  >
                    <SimpleMagneticWrapper>
                      <button 
                        className="flex items-center space-x-4 rounded-2xl border p-6 text-left transition-all hover:bg-secondary/50 bg-card/50 backdrop-blur-sm card-float w-full group-hover/action:border-primary/50"
                        onClick={() => window.location.href = '/diagnostic'}
                      >
                        <div className="rounded-full bg-primary/10 p-3 neon-glow-blue group-hover/action:scale-110 transition-transform duration-300">
                          <Activity className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                          <p className="font-semibold text-lg">Run Diagnostic Scan</p>
                          <p className="text-sm text-muted-foreground">
                            Analyze your site health
                          </p>
                        </div>
                      </button>
                    </SimpleMagneticWrapper>
                  </motion.div>
                  
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    whileHover={{ y: -5 }}
                    className="group/action"
                  >
                    <SimpleMagneticWrapper>
                      <button 
                        className="flex items-center space-x-4 rounded-2xl border p-6 text-left transition-all hover:bg-secondary/50 bg-card/50 backdrop-blur-sm card-float w-full group-hover/action:border-accent/50"
                        onClick={() => window.location.href = '/market-simulation'}
                      >
                        <div className="rounded-full bg-accent/10 p-3 neon-glow-green group-hover/action:scale-110 transition-transform duration-300">
                          <BarChart3 className="h-6 w-6 text-accent" />
                        </div>
                        <div>
                          <p className="font-semibold text-lg">View Market Analysis</p>
                          <p className="text-sm text-muted-foreground">
                            Check competitive landscape
                          </p>
                        </div>
                      </button>
                    </SimpleMagneticWrapper>
                  </motion.div>
                  
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    whileHover={{ y: -5 }}
                    className="group/action"
                  >
                    <SimpleMagneticWrapper>
                      <button 
                        className="flex items-center space-x-4 rounded-2xl border p-6 text-left transition-all hover:bg-secondary/50 bg-card/50 backdrop-blur-sm card-float w-full group-hover/action:border-destructive/50"
                        onClick={() => window.location.href = '/profitability'}
                      >
                        <div className="rounded-full bg-destructive/10 p-3 neon-glow-pink group-hover/action:scale-110 transition-transform duration-300">
                          <TrendingUp className="h-6 w-6 text-destructive" />
                        </div>
                        <div>
                          <p className="font-semibold text-lg">ROI Calculator</p>
                          <p className="text-sm text-muted-foreground">
                            Track profitability metrics
                          </p>
                        </div>
                      </button>
                    </SimpleMagneticWrapper>
                  </motion.div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </DashboardLayout>
  );
}

export default withAuth(DashboardPage);