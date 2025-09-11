"use client";

import { useState, useEffect, useCallback, useMemo } from "react"; // <-- CHANGE: Imported useCallback and useMemo
import { useRouter, useParams } from "next/navigation";
import { 
  FileText, Download, Share2, Calendar, Clock, Printer,
  Mail, Settings, ChevronLeft, TrendingUp, TrendingDown,
  ArrowUp, ArrowDown, Minus, RefreshCw, Filter, Target, Search
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/use-toast";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

interface ReportData {
  id: string;
  name: string;
  description?: string;
  type: string;
  generated_at: string;
  period: {
    start: string;
    end: string;
  };
  summary: {
    totalTraffic: number;
    trafficChange: number;
    avgPosition: number;
    positionChange: number;
    totalKeywords: number;
    keywordsChange: number;
    conversionRate: number;
    conversionChange: number;
  };
  sections: {
    overview: any;
    traffic: any;
    keywords: any;
    performance: any;
  };
}

export default function ReportDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const { toast } = useToast();
  const reportId = params.id as string;
  
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<ReportData | null>(null);
  const [dateRange, setDateRange] = useState({ 
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), 
    end: new Date() 
  });
  const [refreshing, setRefreshing] = useState(false);

  // Mock data - wrapped in useMemo to prevent recreation on every render
  const mockReport: ReportData = useMemo(() => ({
    id: reportId,
    name: "Weekly SEO Performance Report",
    description: "Comprehensive SEO metrics and rankings analysis",
    type: "seo",
    generated_at: new Date().toISOString(),
    period: {
      start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      end: new Date().toISOString()
    },
    summary: {
      totalTraffic: 125000,
      trafficChange: 12.5,
      avgPosition: 15.2,
      positionChange: -2.3,
      totalKeywords: 1234,
      keywordsChange: 8.7,
      conversionRate: 3.2,
      conversionChange: 0.5
    },
    sections: {
      overview: {},
      traffic: {
        chart: [
          { date: "Mon", organic: 15000, direct: 8000, referral: 3000 },
          { date: "Tue", organic: 16500, direct: 7500, referral: 3200 },
          { date: "Wed", organic: 18000, direct: 8200, referral: 3500 },
          { date: "Thu", organic: 17500, direct: 8000, referral: 3300 },
          { date: "Fri", organic: 19000, direct: 8500, referral: 3800 },
          { date: "Sat", organic: 14000, direct: 6000, referral: 2500 },
          { date: "Sun", organic: 13000, direct: 5500, referral: 2200 }
        ],
        sources: [
          { name: "Organic Search", value: 65, color: "#10b981" },
          { name: "Direct", value: 25, color: "#3b82f6" },
          { name: "Referral", value: 8, color: "#8b5cf6" },
          { name: "Social", value: 2, color: "#f59e0b" }
        ]
      },
      keywords: {
        top: [
          { keyword: "seo tools", position: 3, volume: 12000, change: -1 },
          { keyword: "website analysis", position: 5, volume: 8000, change: 2 },
          { keyword: "keyword research", position: 8, volume: 15000, change: 0 },
          { keyword: "competitor analysis", position: 12, volume: 6000, change: -3 },
          { keyword: "seo audit", position: 15, volume: 9000, change: 1 }
        ],
        distribution: [
          { range: "1-3", count: 125, percentage: 10 },
          { range: "4-10", count: 345, percentage: 28 },
          { range: "11-20", count: 432, percentage: 35 },
          { range: "21-50", count: 234, percentage: 19 },
          { range: "51-100", count: 98, percentage: 8 }
        ]
      },
      performance: {
        metrics: [
          { metric: "Page Load Time", value: 2.3, unit: "s", change: -0.5, benchmark: 3.0 },
          { metric: "First Contentful Paint", value: 1.2, unit: "s", change: -0.2, benchmark: 1.8 },
          { metric: "Time to Interactive", value: 3.5, unit: "s", change: -0.8, benchmark: 3.8 },
          { metric: "Cumulative Layout Shift", value: 0.05, unit: "", change: -0.02, benchmark: 0.1 }
        ]
      }
    }
  }), [reportId]); // Memoized with reportId dependency

  // <-- CHANGE: Wrapped in useCallback
  const fetchReport = useCallback(async () => {
    try {
      setLoading(true);
      // In real implementation, this would call the API
      // const response = await api.reports.get(reportId);
      setTimeout(() => {
        setReport(mockReport);
        setLoading(false);
      }, 1000);
    } catch (error) {
      console.error("Failed to fetch report:", error);
      toast({
        title: "Error",
        description: "Failed to load report",
        variant: "destructive"
      });
      setLoading(false);
    }
  }, [toast, mockReport]); // mockReport contains reportId data

  useEffect(() => {
    fetchReport();
  }, [fetchReport]); // <-- CHANGE: Updated dependency array

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      // Regenerate report with latest data
      await fetchReport();
      toast({
        title: "Report refreshed",
        description: "Report has been updated with the latest data",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to refresh report",
        variant: "destructive"
      });
    } finally {
      setRefreshing(false);
    }
  };

  const handleDownload = async (format: "pdf" | "csv" | "xlsx") => {
    try {
      // In real implementation, this would call the API
      // const response = await api.reports.download(reportId, format);
      toast({
        title: "Download started",
        description: `Downloading report as ${format.toUpperCase()}`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to download report",
        variant: "destructive"
      });
    }
  };

  const handleShare = async () => {
    try {
      const url = `${window.location.origin}/reports/${reportId}`;
      await navigator.clipboard.writeText(url);
      toast({
        title: "Link copied",
        description: "Report link has been copied to clipboard",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to copy link",
        variant: "destructive"
      });
    }
  };

  const getChangeIcon = (change: number) => {
    if (change > 0) return <ArrowUp className="h-4 w-4 text-green-500" />;
    if (change < 0) return <ArrowDown className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-gray-500" />;
  };

  const getChangeColor = (change: number) => {
    if (change > 0) return "text-green-500";
    if (change < 0) return "text-red-500";
    return "text-gray-500";
  };

  if (loading || !report) {
    return (
      <DashboardLayout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-muted rounded w-1/3"></div>
          <div className="grid gap-4 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardHeader>
                  <div className="h-4 bg-muted rounded w-1/2"></div>
                </CardHeader>
                <CardContent>
                  <div className="h-8 bg-muted rounded w-3/4"></div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push("/reports")}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Back to Reports
            </Button>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">{report.name}</h1>
              {report.description && (
                <p className="text-muted-foreground">{report.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <DateRangePicker value={dateRange} onChange={(range) => setDateRange(range)} />
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleShare}
            >
              <Share2 className="h-4 w-4 mr-2" />
              Share
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm">
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleDownload('pdf')}>
                  Download as PDF
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleDownload('csv')}>
                  Download as CSV
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleDownload('xlsx')}>
                  Download as Excel
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Report Info */}
        <Card>
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <span className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Period: {new Date(report.period.start).toLocaleDateString()} - {new Date(report.period.end).toLocaleDateString()}
              </span>
              <span className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Generated: {new Date(report.generated_at).toLocaleString()}
              </span>
            </div>
            <Badge variant="outline">
              <FileText className="h-3 w-3 mr-1" />
              {report.type.toUpperCase()} Report
            </Badge>
          </CardContent>
        </Card>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Traffic</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(report.summary.totalTraffic / 1000).toFixed(0)}K
              </div>
              <div className="flex items-center text-xs">
                {getChangeIcon(report.summary.trafficChange)}
                <span className={getChangeColor(report.summary.trafficChange)}>
                  {Math.abs(report.summary.trafficChange)}%
                </span>
                <span className="text-muted-foreground ml-1">vs last period</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg. Position</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{report.summary.avgPosition}</div>
              <div className="flex items-center text-xs">
                {getChangeIcon(-report.summary.positionChange)}
                <span className={getChangeColor(-report.summary.positionChange)}>
                  {Math.abs(report.summary.positionChange)}
                </span>
                <span className="text-muted-foreground ml-1">positions</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Keywords</CardTitle>
              <Search className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{report.summary.totalKeywords}</div>
              <div className="flex items-center text-xs">
                {getChangeIcon(report.summary.keywordsChange)}
                <span className={getChangeColor(report.summary.keywordsChange)}>
                  {Math.abs(report.summary.keywordsChange)}%
                </span>
                <span className="text-muted-foreground ml-1">change</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{report.summary.conversionRate}%</div>
              <div className="flex items-center text-xs">
                {getChangeIcon(report.summary.conversionChange)}
                <span className={getChangeColor(report.summary.conversionChange)}>
                  {Math.abs(report.summary.conversionChange)}%
                </span>
                <span className="text-muted-foreground ml-1">points</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Report Content */}
        <Tabs defaultValue="traffic" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="traffic">Traffic Analysis</TabsTrigger>
            <TabsTrigger value="keywords">Keyword Performance</TabsTrigger>
            <TabsTrigger value="performance">Site Performance</TabsTrigger>
            <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
          </TabsList>

          {/* Traffic Analysis Tab */}
          <TabsContent value="traffic" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Traffic Overview</CardTitle>
                <CardDescription>Website traffic breakdown by source</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[400px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={report.sections.traffic.chart}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="date" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="organic"
                        stackId="1"
                        stroke="#10b981"
                        fill="#10b981"
                        fillOpacity={0.6}
                      />
                      <Area
                        type="monotone"
                        dataKey="direct"
                        stackId="1"
                        stroke="#3b82f6"
                        fill="#3b82f6"
                        fillOpacity={0.6}
                      />
                      <Area
                        type="monotone"
                        dataKey="referral"
                        stackId="1"
                        stroke="#8b5cf6"
                        fill="#8b5cf6"
                        fillOpacity={0.6}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Traffic Sources</CardTitle>
                  <CardDescription>Distribution of traffic by source</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={report.sections.traffic.sources}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={100}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {report.sections.traffic.sources.map((entry: any, index: number) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Top Landing Pages</CardTitle>
                  <CardDescription>Pages with the most traffic</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {[
                      { page: "/blog/seo-guide", visits: 12500, bounce: 32 },
                      { page: "/products", visits: 8900, bounce: 45 },
                      { page: "/", visits: 7500, bounce: 38 },
                      { page: "/about", visits: 4200, bounce: 25 },
                      { page: "/contact", visits: 2100, bounce: 55 }
                    ].map((page, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium">{page.page}</p>
                          <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span>{page.visits.toLocaleString()} visits</span>
                            <span>{page.bounce}% bounce rate</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Keywords Tab */}
          <TabsContent value="keywords" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Top Performing Keywords</CardTitle>
                <CardDescription>Keywords driving the most traffic</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {report.sections.keywords.top.map((keyword: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium">{keyword.keyword}</p>
                        <p className="text-sm text-muted-foreground">
                          Search volume: {keyword.volume.toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-medium">#{keyword.position}</p>
                          <div className="flex items-center text-xs">
                            {getChangeIcon(-keyword.change)}
                            <span className={getChangeColor(-keyword.change)}>
                              {Math.abs(keyword.change)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Keyword Distribution</CardTitle>
                <CardDescription>Keywords by ranking position</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={report.sections.keywords.distribution}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="range" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip />
                      <Bar dataKey="count" fill="#8b5cf6" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Core Web Vitals</CardTitle>
                <CardDescription>Key performance metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {report.sections.performance.metrics.map((metric: any, index: number) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{metric.metric}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-bold">
                            {metric.value}{metric.unit}
                          </span>
                          <div className="flex items-center text-xs">
                            {getChangeIcon(-metric.change)}
                            <span className={getChangeColor(-metric.change)}>
                              {Math.abs(metric.change)}{metric.unit}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="relative">
                        <Progress 
                          value={(metric.value / metric.benchmark) * 100} 
                          className="h-2"
                        />
                        <div 
                          className="absolute top-0 h-2 w-0.5 bg-foreground"
                          style={{ left: '100%' }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Benchmark: {metric.benchmark}{metric.unit}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Recommendations Tab */}
          <TabsContent value="recommendations">
            <Card>
              <CardHeader>
                <CardTitle>Actionable Recommendations</CardTitle>
                <CardDescription>
                  Based on your report data, here are some recommendations to improve performance
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    {
                      title: "Improve Page Load Speed",
                      description: "Your average page load time is above the recommended threshold. Consider optimizing images and reducing JavaScript bundle size.",
                      priority: "high",
                      impact: "high"
                    },
                    {
                      title: "Target Long-tail Keywords",
                      description: "You have strong rankings for competitive terms. Focus on long-tail keywords to capture more specific search intent.",
                      priority: "medium",
                      impact: "medium"
                    },
                    {
                      title: "Enhance Mobile Experience",
                      description: "Mobile traffic is growing but has higher bounce rates. Optimize for mobile users with responsive design improvements.",
                      priority: "high",
                      impact: "high"
                    },
                    {
                      title: "Build More Quality Backlinks",
                      description: "Your domain authority could be improved. Focus on earning high-quality backlinks from relevant websites.",
                      priority: "medium",
                      impact: "medium"
                    }
                  ].map((rec, index) => (
                    <div key={index} className="p-4 border rounded-lg space-y-2">
                      <div className="flex items-start justify-between">
                        <h4 className="font-medium">{rec.title}</h4>
                        <div className="flex gap-2">
                          <Badge variant={rec.priority === "high" ? "destructive" : "secondary"}>
                            {rec.priority} priority
                          </Badge>
                          <Badge variant={rec.impact === "high" ? "default" : "outline"}>
                            {rec.impact} impact
                          </Badge>
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground">{rec.description}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}