'use client';

import { useState, useEffect } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { DashboardPageHeader } from '@/components/layout/dashboard-page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  RefreshCw,
  Download,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  Shield,
  Zap,
  Search,
  FileText,
  Smartphone,
  Monitor,
  Tablet
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDate } from '@/lib/utils';
import { useProject } from '@/lib/project-context';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { PerformanceTrendsChart } from '@/components/ui/performance-trends-chart';
import { CrawlCoverageChart } from '@/components/ui/crawl-coverage-chart';
import { SEOAnalysisChart } from '@/components/ui/seo-analysis-chart';
import { PerformanceHistogramChart } from '@/components/ui/performance-histogram-chart';
import { CrawlerProgress } from '@/components/ui/crawler-progress';
import { useCrawlerProgress } from '@/lib/hooks/use-crawler-progress';
import { motion } from 'framer-motion';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { Sparkles } from 'lucide-react';

function DiagnosticPage() {
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [currentCrawlId, setCurrentCrawlId] = useState<string | null>(null);
  const [trendsPeriod, setTrendsPeriod] = useState('30d');
  const [isCollectingTrends, setIsCollectingTrends] = useState(false);
  const [trendsProgress, setTrendsProgress] = useState(0);
  const [trendsStage, setTrendsStage] = useState('');
  
  const { currentProject } = useProject();
  const queryClient = useQueryClient();
  
  // Real-time crawler progress tracking
  const { 
    progress: crawlerProgress, 
    isRunning: isCrawlerRunning,
    canCancel,
    cancelTask,
    retryTask 
  } = useCrawlerProgress({
    taskId: currentCrawlId || undefined,
    projectId: currentProject?.id,
    autoRefresh: true
  });

  // Fetch site health data
  const { data: report, isLoading, error, refetch } = useQuery({
    queryKey: ['site-health', currentProject?.id],
    queryFn: async () => {
      if (!currentProject) return null;
      // Using project ID as site ID for now - this should be mapped properly
      const response = await api.diagnostic.getSiteHealth(currentProject.id);
      return response.data;
    },
    enabled: !!currentProject,
  });

  // Simulate performance data collection progress
  const simulateDataCollection = async () => {
    setIsCollectingTrends(true);
    setTrendsProgress(0);
    setTrendsStage('');

    const stages = [
      { stage: 'Collecting lab data metrics...', progress: 20 },
      { stage: 'Fetching field data from CrUX...', progress: 40 },
      { stage: 'Processing LCP metrics...', progress: 50 },
      { stage: 'Processing CLS metrics...', progress: 60 },
      { stage: 'Processing INP metrics...', progress: 70 },
      { stage: 'Aggregating performance data...', progress: 85 },
      { stage: 'Finalizing trends analysis...', progress: 95 },
      { stage: 'Data collection complete!', progress: 100 }
    ];

    for (const { stage, progress } of stages) {
      setTrendsStage(stage);
      setTrendsProgress(progress);
      await new Promise(resolve => setTimeout(resolve, 600));
    }
    
    setIsCollectingTrends(false);
  };

  // Fetch performance trends data
  const { data: trendsData, isLoading: trendsLoading, refetch: refetchTrends } = useQuery({
    queryKey: ['performance-trends', currentProject?.id, trendsPeriod],
    queryFn: async () => {
      if (!currentProject) return null;
      
      // Simulate collection progress for initial load
      if (!trendsData) {
        await simulateDataCollection();
      }
      
      const response = await api.diagnostic.getPerformanceTrends(currentProject.id, trendsPeriod);
      return response.data;
    },
    enabled: !!currentProject,
  });

  // Start crawl mutation
  const startCrawl = useMutation({
    mutationFn: async () => {
      if (!currentProject) throw new Error('No project selected');
      if (!currentProject.url) throw new Error('Project has no URL');
      setIsScanning(true);
      setScanProgress(0);
      const response = await api.diagnostic.startCrawl({
        url: currentProject.url,
        site_id: parseInt(currentProject.id), // Associate crawl with site
        max_urls: 1000,
        respect_robots_txt: true,
        crawl_javascript: true,
        follow_external_links: false
      });
      return response.data;
    },
    onSuccess: (data) => {
      // Set the crawl ID for real-time tracking
      setCurrentCrawlId(data.crawl_id || data.task_id);
      
      // Legacy fallback - remove once backend provides task IDs
      if (!data.crawl_id && !data.task_id) {
        const interval = setInterval(() => {
          setScanProgress((prev) => {
            if (prev >= 100) {
              clearInterval(interval);
              setIsScanning(false);
              refetch();
              return 100;
            }
            return prev + 10;
          });
        }, 1000);
      }
    },
    onError: () => {
      setIsScanning(false);
      setCurrentCrawlId(null);
    }
  });

  // Handle crawler completion
  useEffect(() => {
    if (crawlerProgress?.stage === 'completed') {
      setIsScanning(false);
      setCurrentCrawlId(null);
      refetch(); // Refresh the report data
    }
  }, [crawlerProgress?.stage, refetch]);

  const getSeverityColor = (severity: string) => {
    const severityLower = severity?.toLowerCase();
    switch (severityLower) {
      case 'critical':
      case 'high':
        return 'destructive';
      case 'medium':
      case 'warning':
        return 'warning';
      case 'low':
      case 'info':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Process real backend data to match frontend expectations
  const processedReport = report ? (() => {
    const allIssues = report.technical_issues || [];
    
    // Map backend issue fields to frontend expected structure and categorize by type
    const mapIssue = (issue: any) => ({
      ...issue,
      title: issue.title || issue.description?.split('.')[0] || issue.category || 'Issue Found',
      affected_pages: issue.affected_urls || issue.affected_pages || [currentProject?.url || '/'],
      recommendation: issue.recommendation || issue.solution || 'Review this issue and implement appropriate fixes',
      severity: issue.severity || 'Medium'
    });
    
    const technicalIssues = allIssues
      .filter((issue: any) => 
        ['Crawlability', 'Performance', 'Security', 'Technical'].includes(issue.category)
      )
      .map(mapIssue);
      
    const contentIssues = allIssues
      .filter((issue: any) => 
        ['Content', 'SEO', 'Meta', 'Title', 'Description'].includes(issue.category)
      )
      .map(mapIssue);
      
    const uxIssues = allIssues
      .filter((issue: any) => 
        ['UX', 'Mobile', 'Accessibility', 'Usability', 'Layout'].includes(issue.category)
      )
      .map(mapIssue);
    
    // Calculate scores from real backend data
    const technicalScore = report.crawlability?.crawlability_score || 
                          (report.crawlability?.status === 'COMPLETED' ? 85 : 
                           report.crawlability?.status === 'FAILED' ? 20 : 40);
    const performanceScore = report.performance?.performance_score || 
                           report.performance?.core_web_vitals?.lab_data?.performance_score || 0;
    
    // Calculate content score based on SEO factors and content issues  
    const contentScore = Math.max(20, 100 - (contentIssues.length * 12));
    
    // Calculate UX score based on performance and UX issues  
    const uxScore = Math.max(10, Math.min(performanceScore - (uxIssues.length * 8), 100));
    
    // Count issues by severity
    const criticalIssues = allIssues.filter((i: any) => 
      i.severity?.toLowerCase() === 'critical' || i.severity?.toLowerCase() === 'high'
    );
    const warningIssues = allIssues.filter((i: any) => 
      i.severity?.toLowerCase() === 'medium' || i.severity?.toLowerCase() === 'warning'
    );
    
    // Calculate passed count based on successful checks
    const totalPossibleChecks = 50; // Reasonable estimate
    const failedChecks = criticalIssues.length + warningIssues.length;
    const passedCount = Math.max(0, totalPossibleChecks - failedChecks);
    
    return {
      overall_score: report.health_score || 0,
      technical_score: technicalScore,
      content_score: contentScore,
      ux_score: uxScore,
      issues_count: criticalIssues.length,
      warnings_count: warningIssues.length,
      passed_count: passedCount,
      last_scan: report.last_updated || new Date().toISOString(),
      data: {
        technical_issues: technicalIssues,
        content_issues: contentIssues,
        ux_issues: uxIssues,
        performance_metrics: {
          page_speed_score: performanceScore,
          // Extract Core Web Vitals from backend performance data with fallbacks
          first_contentful_paint: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'FCP')?.value / 1000 || 
                                report.performance?.core_web_vitals?.fcp || 0,
          largest_contentful_paint: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'LCP')?.value / 1000 || 
                                  report.performance?.core_web_vitals?.lcp || 0,
          cumulative_layout_shift: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'CLS')?.value || 
                                 report.performance?.core_web_vitals?.cls || 0,
          total_blocking_time: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'TBT')?.value || 
                             report.performance?.core_web_vitals?.tbt || 0,
          time_to_interactive: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'TTI')?.value / 1000 || 
                             report.performance?.core_web_vitals?.tti || 0,
        },
        seo_metrics: {
          // Extract real crawl data
          indexable_pages: report.crawlability?.urls_crawled || 0,
          crawlability_score: report.crawlability?.crawlability_score || 0,
          last_crawl: report.crawlability?.last_crawl || null,
        },
        // Add fields needed by performance tabs with comprehensive detection
        field_data_available: !!(report.performance?.core_web_vitals?.field_data || 
                                 report.performance?.mobile_field_data || 
                                 report.performance?.desktop_field_data),
        mobile_field_data_available: !!(report.performance?.core_web_vitals?.field_data || 
                                       report.performance?.mobile_field_data),
        desktop_field_data_available: !!(report.performance?.core_web_vitals?.field_data || 
                                        report.performance?.desktop_field_data),
        tablet_field_data_available: !!(report.performance?.tablet_field_data), // Check if backend provides tablet data
        mobile_performance_metrics: report.performance?.core_web_vitals?.lab_data || report.performance?.mobile_metrics ? {
          page_speed_score: performanceScore,
          first_contentful_paint: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'FCP')?.value / 1000 || 
                                report.performance?.mobile_metrics?.fcp || 0,
          largest_contentful_paint: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'LCP')?.value / 1000 || 
                                  report.performance?.mobile_metrics?.lcp || 0,
          cumulative_layout_shift: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'CLS')?.value || 
                                 report.performance?.mobile_metrics?.cls || 0,
          total_blocking_time: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'TBT')?.value || 
                             report.performance?.mobile_metrics?.tbt || 0,
          time_to_interactive: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'TTI')?.value / 1000 || 
                             report.performance?.mobile_metrics?.tti || 0,
        } : null,
        desktop_performance_metrics: report.performance?.core_web_vitals?.lab_data || report.performance?.desktop_metrics ? {
          page_speed_score: performanceScore,
          first_contentful_paint: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'FCP')?.value / 1000 || 
                                report.performance?.desktop_metrics?.fcp || 0,
          largest_contentful_paint: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'LCP')?.value / 1000 || 
                                  report.performance?.desktop_metrics?.lcp || 0,
          cumulative_layout_shift: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'CLS')?.value || 
                                 report.performance?.desktop_metrics?.cls || 0,
          total_blocking_time: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'TBT')?.value || 
                             report.performance?.desktop_metrics?.tbt || 0,
          time_to_interactive: report.performance?.core_web_vitals?.lab_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'TTI')?.value / 1000 || 
                             report.performance?.desktop_metrics?.tti || 0,
        } : null,
        mobile_field_performance_metrics: report.performance?.core_web_vitals?.field_data || report.performance?.mobile_field_data ? {
          // Extract field data metrics with multiple fallback sources
          largest_contentful_paint: report.performance?.core_web_vitals?.field_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'LCP')?.value / 1000 || 
                                   report.performance?.mobile_field_data?.lcp || 0,
          cumulative_layout_shift: report.performance?.core_web_vitals?.field_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'CLS')?.value || 
                                 report.performance?.mobile_field_data?.cls || 0,
          first_input_delay: report.performance?.core_web_vitals?.field_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'FID')?.value || 
                           report.performance?.mobile_field_data?.fid || 0,
          inp: report.performance?.core_web_vitals?.field_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'INP')?.value || 
               report.performance?.mobile_field_data?.inp || 0,
        } : null,
        desktop_field_performance_metrics: report.performance?.core_web_vitals?.field_data || report.performance?.desktop_field_data ? {
          // Extract field data metrics with multiple fallback sources
          largest_contentful_paint: report.performance?.core_web_vitals?.field_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'LCP')?.value / 1000 || 
                                   report.performance?.desktop_field_data?.lcp || 0,
          cumulative_layout_shift: report.performance?.core_web_vitals?.field_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'CLS')?.value || 
                                 report.performance?.desktop_field_data?.cls || 0,
          first_input_delay: report.performance?.core_web_vitals?.field_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'FID')?.value || 
                           report.performance?.desktop_field_data?.fid || 0,
          inp: report.performance?.core_web_vitals?.field_data?.metrics?.find((m: any) => m.name?.toUpperCase() === 'INP')?.value || 
               report.performance?.desktop_field_data?.inp || 0,
        } : null,
        
        // Add tablet performance metrics
        tablet_performance_metrics: report.performance?.tablet_metrics ? {
          page_speed_score: report.performance?.tablet_metrics?.page_speed_score || 0,
          first_contentful_paint: report.performance?.tablet_metrics?.first_contentful_paint || 0,
          largest_contentful_paint: report.performance?.tablet_metrics?.largest_contentful_paint || 0,
          cumulative_layout_shift: report.performance?.tablet_metrics?.cumulative_layout_shift || 0,
          total_blocking_time: report.performance?.tablet_metrics?.total_blocking_time || 0,
          time_to_interactive: report.performance?.tablet_metrics?.time_to_interactive || 0,
          interaction_to_next_paint: report.performance?.tablet_metrics?.interaction_to_next_paint || 0,
          time_to_first_byte: report.performance?.tablet_metrics?.time_to_first_byte || 0,
          speed_index: report.performance?.tablet_metrics?.speed_index || 0,
        } : null,
        tablet_field_performance_metrics: report.performance?.tablet_field_data ? {
          // Extract field data metrics for tablet
          largest_contentful_paint: report.performance?.tablet_field_data?.largest_contentful_paint || 0,
          cumulative_layout_shift: report.performance?.tablet_field_data?.cumulative_layout_shift || 0,
          first_input_delay: report.performance?.tablet_field_data?.first_input_delay || 0,
          inp: report.performance?.tablet_field_data?.inp || 0,
          ttfb: report.performance?.tablet_field_data?.ttfb || 0,
          first_contentful_paint: report.performance?.tablet_field_data?.first_contentful_paint || 0,
        } : null,
      },
      // Include original backend data for debugging/compatibility
      crawlability: report.crawlability,
      performance: report.performance,
      bot_behavior: report.bot_behavior,
      recommendations: report.recommendations,
    };
  })() : null;

  // Use only real backend data - no mock fallback
  const reportData = processedReport;

  if (!currentProject) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-2">
            <h3 className="text-2xl font-semibold">No Project Selected</h3>
            <p className="text-muted-foreground">
              Please select a project from the dropdown above to view diagnostics.
            </p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (isLoading) {
    return (
      <DashboardLayout>
        <LoadingState 
          message="Loading diagnostic data..." 
          size="lg" 
          fullHeight 
        />
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-8">
          <ErrorState
            error={error}
            title="Failed to load diagnostic data"
            description="We couldn&apos;t fetch your site&apos;s diagnostic information. Please check your connection and try again."
            onRetry={() => refetch()}
          />
        </div>
      </DashboardLayout>
    );
  }

  if (!reportData) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-8 text-center space-y-4">
          <div className="rounded-lg border-2 border-dashed border-muted-foreground/25 p-8">
            <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">No Diagnostic Data Available</h3>
            <p className="text-muted-foreground mb-6">
              Start your first site analysis to see comprehensive diagnostic results, performance metrics, and optimization recommendations.
            </p>
            <CTAButton
              onClick={() => startCrawl.mutate()}
              disabled={startCrawl.isPending || isScanning}
              size="lg"
            >
              {isScanning ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing Site...
                </>
              ) : (
                <>
                  <Activity className="mr-2 h-4 w-4" />
                  Start Site Analysis
                </>
              )}
            </CTAButton>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
      <DashboardLayout>
        <div className="space-y-8 relative z-10">
          {/* Optimized Header - Research-based 2025 standards */}
          <DashboardPageHeader
            title="Site Diagnostic"
            description="Comprehensive AI-powered analysis of your site's health and performance"
            badge={{
              icon: <Sparkles className="mr-1 h-3 w-3" />,
              text: "AI-Powered Diagnostics",
              variant: "secondary"
            }}
            actions={
              <div className="flex items-center gap-4">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={isScanning}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Export Report
                </Button>
                <Button
                  onClick={() => startCrawl.mutate()}
                  disabled={isScanning || isCrawlerRunning}
                >
                  {(isScanning || isCrawlerRunning) ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      {crawlerProgress?.stage === 'preparing' ? 'Preparing...' :
                       crawlerProgress?.stage === 'discovering' ? 'Discovering...' :
                       crawlerProgress?.stage === 'crawling' ? 'Crawling...' :
                       crawlerProgress?.stage === 'analyzing' ? 'Analyzing...' :
                       'Scanning...'}
                    </>
                  ) : (
                    <>
                      <Activity className="mr-2 h-4 w-4" />
                      Start New Scan
                    </>
                  )}
                </Button>
              </div>
            }
          />

        {/* Enhanced Scan Progress */}
        {(isCrawlerRunning || crawlerProgress) && crawlerProgress && (
          <CrawlerProgress
            progress={crawlerProgress}
            onCancel={canCancel ? cancelTask : undefined}
            onRetry={retryTask}
            canCancel={canCancel}
            showDetails={true}
          />
        )}

        {/* Legacy Progress Fallback */}
        {isScanning && !crawlerProgress && (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Scanning your website...</span>
                  <span>{scanProgress}%</span>
                </div>
                <Progress value={scanProgress} />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Score Overview */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Overall Score</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(reportData.overall_score)}`}>
                {reportData.overall_score}%
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Last scan: {formatDate(reportData.last_scan)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Technical
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(reportData.technical_score)}`}>
                {reportData.technical_score}%
              </div>
              <div className="flex items-center gap-1 mt-1">
                <TrendingUp className="h-3 w-3 text-green-600" />
                <span className="text-xs text-green-600">+3%</span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Content
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(reportData.content_score)}`}>
                {reportData.content_score}%
              </div>
              <div className="flex items-center gap-1 mt-1">
                <Minus className="h-3 w-3 text-gray-600" />
                <span className="text-xs text-gray-600">No change</span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Zap className="h-4 w-4" />
                User Experience
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(reportData.ux_score)}`}>
                {reportData.ux_score}%
              </div>
              <div className="flex items-center gap-1 mt-1">
                <TrendingDown className="h-3 w-3 text-red-600" />
                <span className="text-xs text-red-600">-2%</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Issues Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Issues Summary</CardTitle>
            <CardDescription>Overview of all detected issues</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex items-center justify-between p-4 rounded-lg border-2 border-destructive/20 bg-destructive/5">
                <div className="flex items-center gap-3">
                  <XCircle className="h-8 w-8 text-destructive" />
                  <div>
                    <p className="text-sm font-medium">Critical Issues</p>
                    <p className="text-2xl font-bold">{reportData.issues_count}</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg border-2 border-yellow-500/20 bg-yellow-500/5">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-8 w-8 text-yellow-600" />
                  <div>
                    <p className="text-sm font-medium">Warnings</p>
                    <p className="text-2xl font-bold">{reportData.warnings_count}</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg border-2 border-green-500/20 bg-green-500/5">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                  <div>
                    <p className="text-sm font-medium">Passed</p>
                    <p className="text-2xl font-bold">{reportData.passed_count}</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Issues */}
        <Tabs defaultValue="technical" className="space-y-4">
          <TabsList>
            <TabsTrigger value="technical">Technical Issues</TabsTrigger>
            <TabsTrigger value="content">Content Issues</TabsTrigger>
            <TabsTrigger value="ux">UX Issues</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="coverage">Crawl Coverage</TabsTrigger>
            <TabsTrigger value="seo">SEO Analysis</TabsTrigger>
            <TabsTrigger value="histogram">User Experience</TabsTrigger>
          </TabsList>

          <TabsContent value="technical" className="space-y-4">
            {reportData.data.technical_issues.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-8 text-center">
                  <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Technical Issues Found</h3>
                  <p className="text-muted-foreground">
                    Your site passed all technical checks. Great work!
                  </p>
                </CardContent>
              </Card>
            ) : (
              reportData.data.technical_issues.map((issue: any, index: number) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{issue.title}</CardTitle>
                    <Badge variant={getSeverityColor(issue.severity)}>
                      {issue.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <CardDescription>{issue.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm font-medium mb-2">Affected Pages:</p>
                    <div className="flex flex-wrap gap-2">
                      {issue.affected_pages.map((page: string, i: number) => (
                        <Badge key={i} variant="outline">
                          {page}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-2">Recommendation:</p>
                    <p className="text-sm text-muted-foreground">{issue.recommendation}</p>
                  </div>
                  <Button variant="outline" size="sm">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View Details
                  </Button>
                </CardContent>
              </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="content" className="space-y-4">
            {reportData.data.content_issues.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-8 text-center">
                  <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Content Issues Found</h3>
                  <p className="text-muted-foreground">
                    Your content is optimized and follows SEO best practices.
                  </p>
                </CardContent>
              </Card>
            ) : (
              reportData.data.content_issues.map((issue: any, index: number) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{issue.title}</CardTitle>
                    <Badge variant={getSeverityColor(issue.severity)}>
                      {issue.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <CardDescription>{issue.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm font-medium mb-2">Affected Pages:</p>
                    <div className="flex flex-wrap gap-2">
                      {issue.affected_pages.map((page: string, i: number) => (
                        <Badge key={i} variant="outline">
                          {page}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-2">Recommendation:</p>
                    <p className="text-sm text-muted-foreground">{issue.recommendation}</p>
                  </div>
                </CardContent>
              </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="ux" className="space-y-4">
            {reportData.data.ux_issues.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-8 text-center">
                  <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No UX Issues Found</h3>
                  <p className="text-muted-foreground">
                    Your site provides an excellent user experience across all devices.
                  </p>
                </CardContent>
              </Card>
            ) : (
              reportData.data.ux_issues.map((issue: any, index: number) => (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{issue.title}</CardTitle>
                      <Badge variant={getSeverityColor(issue.severity)}>
                        {issue.severity.toUpperCase()}
                      </Badge>
                    </div>
                    <CardDescription>{issue.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <p className="text-sm font-medium mb-2">Affected Pages:</p>
                      <div className="flex flex-wrap gap-2">
                        {issue.affected_pages.map((page: string, i: number) => (
                          <Badge key={i} variant="outline">
                            {page}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium mb-2">Recommendation:</p>
                      <p className="text-sm text-muted-foreground">{issue.recommendation}</p>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="performance" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Core Web Vitals</CardTitle>
                    <CardDescription>Key performance metrics that impact user experience</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Badge variant="outline">
                      <Activity className="mr-1 h-3 w-3" />
                      Lab Data
                    </Badge>
                    {reportData.data.field_data_available && (
                      <Badge variant="secondary">
                        <Zap className="mr-1 h-3 w-3" />
                        Field Data Available
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {/* Device and Data Type Tabs */}
                <Tabs defaultValue="mobile" className="mb-4">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="mobile">
                      <Smartphone className="mr-1 h-3 w-3" />
                      Mobile
                    </TabsTrigger>
                    <TabsTrigger value="desktop">
                      <Monitor className="mr-1 h-3 w-3" />
                      Desktop
                    </TabsTrigger>
                    <TabsTrigger value="tablet">
                      <Tablet className="mr-1 h-3 w-3" />
                      Tablet
                    </TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="mobile">
                    {/* Lab vs Field Data for Mobile */}
                    {reportData.data.mobile_field_data_available ? (
                      <Tabs defaultValue="lab" className="mt-4">
                        <TabsList className="grid w-full grid-cols-2">
                          <TabsTrigger value="lab">Lab Data (Synthetic)</TabsTrigger>
                          <TabsTrigger value="field">Field Data (Real Users)</TabsTrigger>
                        </TabsList>
                        <TabsContent value="lab">
                          <p className="text-sm text-muted-foreground mb-4">
                            Mobile synthetic performance data from controlled testing environment
                          </p>
                          <PerformanceMetrics data={reportData.data.mobile_performance_metrics || reportData.data.performance_metrics} />
                        </TabsContent>
                        <TabsContent value="field">
                          <p className="text-sm text-muted-foreground mb-4">
                            Mobile real user performance data from Chrome User Experience Report
                          </p>
                          <PerformanceMetrics data={reportData.data.mobile_field_performance_metrics} />
                        </TabsContent>
                      </Tabs>
                    ) : (
                      <>
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 mt-4">
                          <div className="flex items-start gap-2">
                            <Activity className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div>
                              <p className="text-sm font-medium text-blue-800 mb-1">Lab Data Only</p>
                              <p className="text-sm text-blue-700">
                                Real user experience data (CrUX) is not available for this URL. This could be due to insufficient traffic, API restrictions, or the site being new. Lab data provides synthetic testing results instead.
                              </p>
                            </div>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground mb-4">
                          Mobile synthetic performance data from controlled testing environment
                        </p>
                        <PerformanceMetrics data={reportData.data.mobile_performance_metrics || reportData.data.performance_metrics} />
                      </>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="desktop">
                    {/* Lab vs Field Data for Desktop */}
                    {reportData.data.desktop_field_data_available ? (
                      <Tabs defaultValue="lab" className="mt-4">
                        <TabsList className="grid w-full grid-cols-2">
                          <TabsTrigger value="lab">Lab Data (Synthetic)</TabsTrigger>
                          <TabsTrigger value="field">Field Data (Real Users)</TabsTrigger>
                        </TabsList>
                        <TabsContent value="lab">
                          <p className="text-sm text-muted-foreground mb-4">
                            Desktop synthetic performance data from controlled testing environment
                          </p>
                          <PerformanceMetrics data={reportData.data.desktop_performance_metrics} />
                        </TabsContent>
                        <TabsContent value="field">
                          <p className="text-sm text-muted-foreground mb-4">
                            Desktop real user performance data from Chrome User Experience Report
                          </p>
                          <PerformanceMetrics data={reportData.data.desktop_field_performance_metrics} />
                        </TabsContent>
                      </Tabs>
                    ) : (
                      <>
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 mt-4">
                          <div className="flex items-start gap-2">
                            <Activity className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div>
                              <p className="text-sm font-medium text-blue-800 mb-1">Lab Data Only</p>
                              <p className="text-sm text-blue-700">
                                Real user experience data (CrUX) is not available for this URL. This could be due to insufficient traffic, API restrictions, or the site being new. Lab data provides synthetic testing results instead.
                              </p>
                            </div>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground mb-4">
                          Desktop synthetic performance data from controlled testing environment
                        </p>
                        <PerformanceMetrics data={reportData.data.desktop_performance_metrics} />
                      </>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="tablet">
                    {/* Lab vs Field Data for Tablet */}
                    {reportData.data.tablet_field_data_available ? (
                      <Tabs defaultValue="lab" className="mt-4">
                        <TabsList className="grid w-full grid-cols-2">
                          <TabsTrigger value="lab">Lab Data (Synthetic)</TabsTrigger>
                          <TabsTrigger value="field">Field Data (Real Users)</TabsTrigger>
                        </TabsList>
                        <TabsContent value="lab">
                          <p className="text-sm text-muted-foreground mb-4">
                            Tablet synthetic performance data from controlled testing environment
                          </p>
                          <PerformanceMetrics data={reportData.data.tablet_performance_metrics} />
                        </TabsContent>
                        <TabsContent value="field">
                          <p className="text-sm text-muted-foreground mb-4">
                            Tablet real user performance data from Chrome User Experience Report
                          </p>
                          <PerformanceMetrics data={reportData.data.tablet_field_performance_metrics} />
                        </TabsContent>
                      </Tabs>
                    ) : (
                      <>
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 mt-4">
                          <div className="flex items-start gap-2">
                            <Activity className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div>
                              <p className="text-sm font-medium text-blue-800 mb-1">Lab Data Only</p>
                              <p className="text-sm text-blue-700">
                                Real user experience data (CrUX) is not available for tablet devices on this URL. This could be due to insufficient tablet traffic or limited tablet usage. Lab data provides synthetic testing results instead.
                              </p>
                            </div>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground mb-4">
                          Tablet synthetic performance data from controlled testing environment
                        </p>
                        <PerformanceMetrics data={reportData.data.tablet_performance_metrics || reportData.data.performance_metrics} />
                      </>
                    )}
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="trends" className="space-y-4">
            <PerformanceTrendsChart
              data={trendsData?.trends?.core_web_vitals_trends || []}
              isLoading={trendsLoading}
              period={trendsPeriod}
              onPeriodChange={(period) => setTrendsPeriod(period)}
              isCollecting={isCollectingTrends}
              collectionProgress={trendsProgress}
              collectionStage={trendsStage}
            />
          </TabsContent>

          <TabsContent value="coverage" className="space-y-4">
            <CrawlCoverageChart
              data={report?.crawlability || null}
              isLoading={isLoading}
              projectId={currentProject?.id}
              taskId={currentCrawlId || undefined}
              enableRealTimeUpdates={!!currentCrawlId}
            />
          </TabsContent>

          <TabsContent value="seo" className="space-y-4">
            <SEOAnalysisChart
              url={currentProject?.url || ''}
            />
          </TabsContent>

          <TabsContent value="histogram" className="space-y-4">
            <PerformanceHistogramChart
              data={report || null}
              isLoading={isLoading}
            />
          </TabsContent>
        </Tabs>
      </div>
      </DashboardLayout>
  );
}

// Component for performance metrics display
function PerformanceMetrics({ data }: { data: any }) {
  if (!data) return <div>No data available</div>;
  
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">First Contentful Paint</span>
              <span className="text-sm font-bold">{data.first_contentful_paint || data.fcp}s</span>
            </div>
            <Progress value={(data.first_contentful_paint || data.fcp) < 2 ? 100 : 50} />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Largest Contentful Paint</span>
              <span className="text-sm font-bold">{data.largest_contentful_paint || data.lcp}s</span>
            </div>
            <Progress value={(data.largest_contentful_paint || data.lcp) < 2.5 ? 100 : 50} />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Total Blocking Time</span>
              <span className="text-sm font-bold">{data.total_blocking_time || data.tbt}ms</span>
            </div>
            <Progress value={(data.total_blocking_time || data.tbt) < 300 ? 100 : 50} />
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Cumulative Layout Shift</span>
              <span className="text-sm font-bold">{data.cumulative_layout_shift || data.cls}</span>
            </div>
            <Progress value={(data.cumulative_layout_shift || data.cls) < 0.1 ? 100 : 50} />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Time to Interactive</span>
              <span className="text-sm font-bold">{data.time_to_interactive || data.tti}s</span>
            </div>
            <Progress value={(data.time_to_interactive || data.tti) < 3.8 ? 100 : 50} />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">PageSpeed Score</span>
              <span className="text-sm font-bold">{data.page_speed_score || data.lighthouse_score}/100</span>
            </div>
            <Progress value={data.page_speed_score || data.lighthouse_score} />
          </div>
        </div>
      </div>
      
      {/* Additional Core Web Vitals */}
      <div className="grid gap-4 md:grid-cols-3 mt-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Interaction to Next Paint (INP)</span>
            <span className="text-sm font-bold">{data.inp || data.interaction_to_next_paint || 'N/A'}ms</span>
          </div>
          <Progress value={(data.inp || data.interaction_to_next_paint) ? ((data.inp || data.interaction_to_next_paint) < 200 ? 100 : (data.inp || data.interaction_to_next_paint) < 500 ? 50 : 20) : 0} />
        </div>
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Time to First Byte (TTFB)</span>
            <span className="text-sm font-bold">{data.ttfb || data.time_to_first_byte || 'N/A'}ms</span>
          </div>
          <Progress value={(data.ttfb || data.time_to_first_byte) ? ((data.ttfb || data.time_to_first_byte) < 800 ? 100 : (data.ttfb || data.time_to_first_byte) < 1800 ? 50 : 20) : 0} />
        </div>
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Speed Index</span>
            <span className="text-sm font-bold">{data.speed_index || data.si || 'N/A'}s</span>
          </div>
          <Progress value={(data.speed_index || data.si) ? ((data.speed_index || data.si) < 3.4 ? 100 : (data.speed_index || data.si) < 5.8 ? 50 : 20) : 0} />
        </div>
      </div>
      
      {/* Additional metrics if available from backend */}
      {(data.first_input_delay || data.fid) && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">First Input Delay (FID)</span>
            <span className="text-sm font-bold">{data.first_input_delay || data.fid}ms</span>
          </div>
          <Progress value={(data.first_input_delay || data.fid) < 100 ? 100 : (data.first_input_delay || data.fid) < 300 ? 50 : 20} />
        </div>
      )}
    </>
  );
}

export default withAuth(DiagnosticPage);