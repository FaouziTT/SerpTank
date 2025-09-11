'use client';

import { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Globe, 
  Search, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  BarChart3,
  Activity,
  TreePine,
  RefreshCw,
  Clock
} from 'lucide-react';
import { useCrawlerProgress } from '@/lib/hooks/use-crawler-progress';

interface CrawlCoverageData {
  indexable_pages: number;
  non_indexable_pages: number;
  crawl_depth_distribution: Record<string, number>;
  content_type_distribution: Record<string, number>;
  status_code_distribution: Record<string, number>;
  total_pages?: number;
  crawlability_score?: number;
  status?: string;
  issues?: Array<{
    title?: string;
    type?: string;
    description?: string;
    message?: string;
    severity?: string;
  }>;
  recommendations?: Array<{
    title?: string;
    type?: string;
    description?: string;
    message?: string;
    priority?: string;
  }>;
}

interface CrawlCoverageChartProps {
  data: CrawlCoverageData | null;
  isLoading?: boolean;
  className?: string;
  projectId?: string;
  taskId?: string;
  enableRealTimeUpdates?: boolean;
}

const COLORS = {
  indexable: '#10b981',
  nonIndexable: '#ef4444',
  depth: ['#3b82f6', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899', '#84cc16'],
};

export function CrawlCoverageChart({ 
  data, 
  isLoading, 
  className = '', 
  projectId,
  taskId,
  enableRealTimeUpdates = false 
}: CrawlCoverageChartProps) {
  const [crawlProgress, setCrawlProgress] = useState<any>(null);
  const [isRealTimeActive, setIsRealTimeActive] = useState(false);

  // Real-time crawler progress for live updates
  const { 
    progress, 
    isRunning: isCrawlerRunning 
  } = useCrawlerProgress({
    taskId: enableRealTimeUpdates ? taskId : undefined,
    projectId: enableRealTimeUpdates ? projectId : undefined,
    autoRefresh: enableRealTimeUpdates
  });

  // Update real-time state when crawler is running
  useEffect(() => {
    if (enableRealTimeUpdates && progress && isCrawlerRunning) {
      setIsRealTimeActive(true);
      setCrawlProgress(progress);
    } else if (!isCrawlerRunning) {
      setIsRealTimeActive(false);
      setCrawlProgress(null);
    }
  }, [enableRealTimeUpdates, progress, isCrawlerRunning]);
  if (isLoading || isRealTimeActive) {
    return (
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Crawl Coverage Analysis
                {isRealTimeActive && (
                  <Badge variant="secondary" className="animate-pulse">
                    <Activity className="h-3 w-3 mr-1" />
                    Live Updates
                  </Badge>
                )}
              </CardTitle>
              <CardDescription>
                {isRealTimeActive 
                  ? `Live crawl in progress - ${crawlProgress?.stage || 'analyzing'}`
                  : 'Loading crawl coverage data...'
                }
              </CardDescription>
            </div>
            {isRealTimeActive && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {Math.round(crawlProgress?.percentage || 0)}%
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isRealTimeActive && crawlProgress ? (
            <div className="space-y-6">
              {/* Real-time progress section */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-blue-800">
                    {crawlProgress.stage === 'discovering' ? 'Discovering Pages...' :
                     crawlProgress.stage === 'crawling' ? 'Analyzing Pages...' :
                     crawlProgress.stage === 'processing' ? 'Processing Results...' :
                     'Crawl Progress'}
                  </span>
                  <span className="text-blue-700 font-bold">
                    {Math.round(crawlProgress.percentage)}%
                  </span>
                </div>
                <Progress value={crawlProgress.percentage} className="h-2 mb-3" />
                
                {/* Live stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {crawlProgress.details?.pagesDiscovered !== undefined && (
                    <div className="text-center p-2 bg-white rounded border">
                      <p className="text-lg font-bold text-blue-600">
                        {crawlProgress.details.pagesDiscovered}
                      </p>
                      <p className="text-xs text-blue-600">Discovered</p>
                    </div>
                  )}
                  {crawlProgress.details?.pagesCrawled !== undefined && (
                    <div className="text-center p-2 bg-white rounded border">
                      <p className="text-lg font-bold text-green-600">
                        {crawlProgress.details.pagesCrawled}
                      </p>
                      <p className="text-xs text-green-600">Crawled</p>
                    </div>
                  )}
                  {crawlProgress.details?.pagesAnalyzed !== undefined && (
                    <div className="text-center p-2 bg-white rounded border">
                      <p className="text-lg font-bold text-purple-600">
                        {crawlProgress.details.pagesAnalyzed}
                      </p>
                      <p className="text-xs text-purple-600">Analyzed</p>
                    </div>
                  )}
                  {crawlProgress.details?.errors !== undefined && crawlProgress.details.errors > 0 && (
                    <div className="text-center p-2 bg-white rounded border">
                      <p className="text-lg font-bold text-red-600">
                        {crawlProgress.details.errors}
                      </p>
                      <p className="text-xs text-red-600">Errors</p>
                    </div>
                  )}
                </div>
                
                {/* Current URL being processed */}
                {crawlProgress.details?.currentUrl && (
                  <div className="mt-3 p-2 bg-white rounded border">
                    <p className="text-xs font-medium mb-1">Currently analyzing:</p>
                    <p className="text-xs text-muted-foreground truncate font-mono">
                      {crawlProgress.details.currentUrl}
                    </p>
                  </div>
                )}
              </div>
              
              {/* Placeholder skeleton for chart area during crawl */}
              <div className="grid gap-4 md:grid-cols-2">
                <Skeleton className="h-[300px]" />
                <Skeleton className="h-[300px]" />
              </div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <Skeleton className="h-[300px]" />
              <Skeleton className="h-[300px]" />
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Crawl Coverage
          </CardTitle>
          <CardDescription>No crawl data available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            <Activity className="h-8 w-8 mr-2" />
            <span>Run a crawl to see coverage data</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Check if we have indexability data (rich analysis) vs basic crawl data
  const hasRichData = data.indexable_pages !== undefined && data.non_indexable_pages !== undefined;
  
  if (!hasRichData && data.status !== "COMPLETED") {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Crawl Coverage Analysis
          </CardTitle>
          <CardDescription>Crawl completed, analysis in progress...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            <RefreshCw className="h-8 w-8 mr-2 animate-spin" />
            <span>Analyzing crawled pages for indexability insights</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const totalPages = data.indexable_pages + data.non_indexable_pages;
  const indexabilityPercentage = totalPages > 0 ? Math.round((data.indexable_pages / totalPages) * 100) : 0;

  // Prepare data for pie chart
  const indexabilityData = [
    { name: 'Indexable', value: data.indexable_pages, color: COLORS.indexable },
    { name: 'Non-Indexable', value: data.non_indexable_pages, color: COLORS.nonIndexable },
  ];

  // Prepare crawl depth data
  const crawlDepthData = Object.entries(data.crawl_depth_distribution || {})
    .map(([depth, count]) => ({
      depth: `Depth ${depth}`,
      count: count,
    }))
    .sort((a, b) => parseInt(a.depth.split(' ')[1]) - parseInt(b.depth.split(' ')[1]));

  // Prepare status code data
  const statusCodeData = Object.entries(data.status_code_distribution || {})
    .map(([code, count]) => ({
      code: code,
      count: count,
      status: getStatusCodeCategory(parseInt(code)),
    }))
    .sort((a, b) => parseInt(a.code) - parseInt(b.code));

  // Prepare content type data
  const contentTypeData = Object.entries(data.content_type_distribution || {})
    .map(([type, count]) => ({
      type: type,
      count: count,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8); // Show top 8 content types

  function getStatusCodeCategory(code: number): string {
    if (code >= 200 && code < 300) return 'success';
    if (code >= 300 && code < 400) return 'redirect';
    if (code >= 400 && code < 500) return 'client-error';
    if (code >= 500) return 'server-error';
    return 'other';
  }

  function getStatusColor(status: string): string {
    switch (status) {
      case 'success': return '#10b981';
      case 'redirect': return '#f59e0b';
      case 'client-error': return '#ef4444';
      case 'server-error': return '#dc2626';
      default: return '#6b7280';
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-5 w-5" />
          Crawl Coverage Analysis
        </CardTitle>
        <CardDescription>
          Analysis of {totalPages.toLocaleString()} crawled pages and their indexability
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="indexability" className="space-y-4">
          <TabsList>
            <TabsTrigger value="indexability">Indexability</TabsTrigger>
            <TabsTrigger value="depth">Crawl Depth</TabsTrigger>
            <TabsTrigger value="status">Status Codes</TabsTrigger>
            <TabsTrigger value="content">Content Types</TabsTrigger>
            <TabsTrigger value="insights">SEO Insights</TabsTrigger>
          </TabsList>

          <TabsContent value="indexability" className="space-y-4">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Summary Stats */}
              <div className="space-y-4">
                <div className="grid gap-4">
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="h-8 w-8 text-green-600" />
                      <div>
                        <p className="text-sm font-medium">Indexable Pages</p>
                        <p className="text-2xl font-bold">{data.indexable_pages.toLocaleString()}</p>
                      </div>
                    </div>
                    <Badge variant="default" className="bg-green-100 text-green-800">
                      {indexabilityPercentage}%
                    </Badge>
                  </div>
                  
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <XCircle className="h-8 w-8 text-red-600" />
                      <div>
                        <p className="text-sm font-medium">Non-Indexable Pages</p>
                        <p className="text-2xl font-bold">{data.non_indexable_pages.toLocaleString()}</p>
                      </div>
                    </div>
                    <Badge variant="destructive">
                      {100 - indexabilityPercentage}%
                    </Badge>
                  </div>
                </div>

                {/* Indexability Score */}
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Indexability Score</span>
                    <span className="text-sm font-bold">{indexabilityPercentage}%</span>
                  </div>
                  <Progress value={indexabilityPercentage} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1">
                    Higher is better - aim for 80%+ indexable pages
                  </p>
                </div>

                {data.crawlability_score && (
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Crawlability Score</span>
                      <span className="text-sm font-bold">{data.crawlability_score}/100</span>
                    </div>
                    <Progress value={data.crawlability_score} className="h-2" />
                    <p className="text-xs text-muted-foreground mt-1">
                      Overall technical SEO health
                    </p>
                  </div>
                )}
              </div>

              {/* Pie Chart */}
              <div className="flex items-center justify-center">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={indexabilityData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={120}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {indexabilityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => [value.toLocaleString(), 'Pages']} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="depth" className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <TreePine className="h-4 w-4" />
                  Crawl Depth Distribution
                </CardTitle>
                <CardDescription>
                  Number of pages found at each crawl depth level
                </CardDescription>
              </CardHeader>
              <CardContent>
                {crawlDepthData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={crawlDepthData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="depth" />
                      <YAxis />
                      <Tooltip formatter={(value: number) => [value.toLocaleString(), 'Pages']} />
                      <Bar dataKey="count" fill="#3b82f6" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                    <span>No depth distribution data available</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="status" className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Status Code Distribution
                </CardTitle>
                <CardDescription>
                  HTTP status codes encountered during crawling
                </CardDescription>
              </CardHeader>
              <CardContent>
                {statusCodeData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={statusCodeData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="code" />
                      <YAxis />
                      <Tooltip formatter={(value: number) => [value.toLocaleString(), 'Pages']} />
                      <Bar dataKey="count" fill="#10b981" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                    <span>No status code data available</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="content" className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Content Type Distribution</CardTitle>
                <CardDescription>
                  Types of content discovered during crawling
                </CardDescription>
              </CardHeader>
              <CardContent>
                {contentTypeData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={contentTypeData} layout="horizontal">
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis dataKey="type" type="category" width={120} />
                      <Tooltip formatter={(value: number) => [value.toLocaleString(), 'Pages']} />
                      <Bar dataKey="count" fill="#8b5cf6" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                    <span>No content type data available</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="insights" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Technical Issues */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                    Technical Issues
                  </CardTitle>
                  <CardDescription>
                    SEO issues discovered during crawl analysis
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {data.issues && data.issues.length > 0 ? (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                      {data.issues.slice(0, 10).map((issue: any, index: number) => (
                        <div key={index} className="p-3 border rounded-lg bg-orange-50 border-orange-200">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-medium text-orange-800 text-sm">
                                {issue.title || issue.type || 'Technical Issue'}
                              </p>
                              <p className="text-orange-700 text-xs mt-1">
                                {issue.description || issue.message || 'Issue detected during crawl analysis'}
                              </p>
                              {issue.severity && (
                                <Badge 
                                  variant={issue.severity === 'Critical' ? 'destructive' : 
                                          issue.severity === 'High' ? 'secondary' : 'outline'}
                                  className="mt-2 text-xs"
                                >
                                  {issue.severity}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                      <CheckCircle className="h-8 w-8 mr-2 text-green-500" />
                      <span>No technical issues detected</span>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Recommendations */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Search className="h-4 w-4 text-blue-500" />
                    SEO Recommendations
                  </CardTitle>
                  <CardDescription>
                    Automated recommendations to improve crawlability
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {data.recommendations && data.recommendations.length > 0 ? (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                      {data.recommendations.slice(0, 10).map((rec: any, index: number) => (
                        <div key={index} className="p-3 border rounded-lg bg-blue-50 border-blue-200">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-medium text-blue-800 text-sm">
                                {rec.title || rec.type || 'SEO Recommendation'}
                              </p>
                              <p className="text-blue-700 text-xs mt-1">
                                {rec.description || rec.message || 'Recommendation to improve SEO performance'}
                              </p>
                              {rec.priority && (
                                <Badge 
                                  variant={rec.priority === 'High' ? 'default' : 'outline'}
                                  className="mt-2 text-xs"
                                >
                                  {rec.priority} Priority
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                      <CheckCircle className="h-8 w-8 mr-2 text-green-500" />
                      <span>No specific recommendations at this time</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}