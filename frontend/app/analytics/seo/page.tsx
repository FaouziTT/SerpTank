"use client";

import { useState, useEffect, useCallback } from "react"; // <-- CHANGE #1: Imported useCallback
import { useRouter } from "next/navigation";
import { 
  Search, TrendingUp, Target, AlertCircle, ChevronRight,
  ArrowUp, ArrowDown, Minus, BarChart3, PieChart, Activity,
  Globe, FileText, Users, Zap, Calendar, Download
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { useAuth } from "@/lib/auth-context";
import { useProject } from "@/lib/project-context";
import { useToast } from "@/components/ui/use-toast";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { api } from "@/lib/api-client";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Legend
} from "recharts";

export default function SEOAnalyticsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { currentProject } = useProject();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ start: new Date(), end: new Date() });
  const [selectedSite, setSelectedSite] = useState<string>("all");
  
  // Mock data - would come from API
  const [seoData, setSeoData] = useState({
    overallScore: 85,
    scoreChange: 5,
    totalKeywords: 1234,
    keywordsChange: 12,
    avgPosition: 15.2,
    positionChange: -2.3,
    organicTraffic: 125000,
    trafficChange: 18.5,
    visibility: 78,
    visibilityChange: 8.2
  });

  const performanceTrend = [
    { date: "Jan", visibility: 65, traffic: 95000, keywords: 980 },
    { date: "Feb", visibility: 68, traffic: 102000, keywords: 1050 },
    { date: "Mar", visibility: 72, traffic: 108000, keywords: 1120 },
    { date: "Apr", visibility: 70, traffic: 112000, keywords: 1180 },
    { date: "May", visibility: 75, traffic: 118000, keywords: 1220 },
    { date: "Jun", visibility: 78, traffic: 125000, keywords: 1234 }
  ];

  const keywordDistribution = [
    { name: "Top 3", value: 234, color: "#10b981" },
    { name: "Top 10", value: 456, color: "#3b82f6" },
    { name: "Top 20", value: 312, color: "#8b5cf6" },
    { name: "Top 50", value: 189, color: "#f59e0b" },
    { name: "50+", value: 43, color: "#ef4444" }
  ];

  const topPages = [
    { url: "/blog/seo-guide", traffic: 12500, keywords: 45, ctr: 8.2, position: 4.5 },
    { url: "/products", traffic: 8900, keywords: 78, ctr: 6.5, position: 8.2 },
    { url: "/about", traffic: 6700, keywords: 23, ctr: 5.8, position: 12.3 },
    { url: "/blog/keyword-research", traffic: 5400, keywords: 34, ctr: 9.1, position: 3.2 },
    { url: "/services", traffic: 4200, keywords: 56, ctr: 4.2, position: 15.7 }
  ];

  const competitorComparison = [
    { competitor: "competitor1.com", visibility: 82, keywords: 1456, avgPosition: 12.3 },
    { competitor: "competitor2.com", visibility: 75, keywords: 1123, avgPosition: 14.8 },
    { competitor: "yoursite.com", visibility: 78, keywords: 1234, avgPosition: 15.2 },
    { competitor: "competitor3.com", visibility: 68, keywords: 987, avgPosition: 18.5 }
  ];

  // <-- CHANGE #2: Moved function above useEffect and wrapped in useCallback
  const fetchSEOData = useCallback(async () => {
    try {
      setLoading(true);
      // In real implementation, this would call the API
      // const data = await api.serpAnalysis.getOverview({ projectId: currentProject?.id });
      setTimeout(() => {
        setLoading(false);
      }, 1000);
    } catch (error) {
      console.error("Failed to fetch SEO data:", error);
      toast({
        title: "Error",
        description: "Failed to load SEO analytics",
        variant: "destructive"
      });
      setLoading(false);
    }
  }, [toast]); // currentProject will be needed when real API is implemented (line 98)

  useEffect(() => {
    fetchSEOData();
  }, [fetchSEOData]); // <-- CHANGE #3: Updated useEffect to depend on the memoized function

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

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push("/analytics")}
                className="px-0"
              >
                Analytics Hub
              </Button>
              <ChevronRight className="h-4 w-4" />
              <span>SEO Analytics</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight">SEO Analytics</h1>
            <p className="text-muted-foreground">
              Comprehensive search engine optimization performance analysis
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Select value={selectedSite} onValueChange={setSelectedSite}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select site" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sites</SelectItem>
                <SelectItem value="site1">example.com</SelectItem>
                <SelectItem value="site2">blog.example.com</SelectItem>
              </SelectContent>
            </Select>
            <DateRangePicker value={dateRange} onChange={(range) => setDateRange(range)} />
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">SEO Score</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{seoData.overallScore}/100</div>
              <div className="flex items-center text-xs">
                {getChangeIcon(seoData.scoreChange)}
                <span className={getChangeColor(seoData.scoreChange)}>
                  {Math.abs(seoData.scoreChange)} points
                </span>
              </div>
              <Progress value={seoData.overallScore} className="mt-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Keywords</CardTitle>
              <Search className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{seoData.totalKeywords.toLocaleString()}</div>
              <div className="flex items-center text-xs">
                {getChangeIcon(seoData.keywordsChange)}
                <span className={getChangeColor(seoData.keywordsChange)}>
                  {Math.abs(seoData.keywordsChange)}%
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg. Position</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{seoData.avgPosition.toFixed(1)}</div>
              <div className="flex items-center text-xs">
                {getChangeIcon(-seoData.positionChange)}
                <span className={getChangeColor(-seoData.positionChange)}>
                  {Math.abs(seoData.positionChange)} positions
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Organic Traffic</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(seoData.organicTraffic / 1000).toFixed(0)}K
              </div>
              <div className="flex items-center text-xs">
                {getChangeIcon(seoData.trafficChange)}
                <span className={getChangeColor(seoData.trafficChange)}>
                  {Math.abs(seoData.trafficChange)}%
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Visibility</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{seoData.visibility}%</div>
              <div className="flex items-center text-xs">
                {getChangeIcon(seoData.visibilityChange)}
                <span className={getChangeColor(seoData.visibilityChange)}>
                  {Math.abs(seoData.visibilityChange)}%
                </span>
              </div>
              <Progress value={seoData.visibility} className="mt-2" />
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="performance" className="space-y-4">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="keywords">Keywords</TabsTrigger>
            <TabsTrigger value="pages">Pages</TabsTrigger>
            <TabsTrigger value="competitors">Competitors</TabsTrigger>
            <TabsTrigger value="opportunities">Opportunities</TabsTrigger>
          </TabsList>

          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Performance Trend</CardTitle>
                <CardDescription>
                  SEO visibility and organic traffic over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[400px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={performanceTrend}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="date" className="text-xs" />
                      <YAxis yAxisId="left" className="text-xs" />
                      <YAxis yAxisId="right" orientation="right" className="text-xs" />
                      <Tooltip />
                      <Legend />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="visibility"
                        stroke="#8b5cf6"
                        strokeWidth={2}
                        name="Visibility %"
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="traffic"
                        stroke="#10b981"
                        strokeWidth={2}
                        name="Organic Traffic"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Keyword Distribution</CardTitle>
                  <CardDescription>Keywords by ranking position</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <RechartsPieChart>
                        <Pie
                          data={keywordDistribution}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={100}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {keywordDistribution.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </RechartsPieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>SEO Health Issues</CardTitle>
                  <CardDescription>Critical issues affecting performance</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <AlertCircle className="h-5 w-5 text-red-500" />
                        <div>
                          <p className="font-medium">Missing Meta Descriptions</p>
                          <p className="text-sm text-muted-foreground">23 pages affected</p>
                        </div>
                      </div>
                      <Badge variant="destructive">High</Badge>
                    </div>
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <AlertCircle className="h-5 w-5 text-yellow-500" />
                        <div>
                          <p className="font-medium">Duplicate Title Tags</p>
                          <p className="text-sm text-muted-foreground">12 pages affected</p>
                        </div>
                      </div>
                      <Badge variant="warning">Medium</Badge>
                    </div>
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <AlertCircle className="h-5 w-5 text-blue-500" />
                        <div>
                          <p className="font-medium">Long Page Load Time</p>
                          <p className="text-sm text-muted-foreground">8 pages affected</p>
                        </div>
                      </div>
                      <Badge>Low</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Keywords Tab */}
          <TabsContent value="keywords">
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-12">
                  <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Keywords Analysis Coming Soon</h3>
                  <p className="text-muted-foreground mb-4">
                    Detailed keyword rankings, search volume, and opportunity analysis
                  </p>
                  <Button onClick={() => router.push("/serp-analysis")}>
                    View SERP Analysis
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Pages Tab */}
          <TabsContent value="pages">
            <Card>
              <CardHeader>
                <CardTitle>Top Performing Pages</CardTitle>
                <CardDescription>Pages driving the most organic traffic</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topPages.map((page, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium">{page.url}</p>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                          <span>Traffic: {page.traffic.toLocaleString()}</span>
                          <span>Keywords: {page.keywords}</span>
                          <span>CTR: {page.ctr}%</span>
                          <span>Avg Position: {page.position}</span>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Competitors Tab */}
          <TabsContent value="competitors">
            <Card>
              <CardHeader>
                <CardTitle>Competitor Comparison</CardTitle>
                <CardDescription>How you stack up against the competition</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {competitorComparison.map((comp, index) => (
                    <div key={index} className={`p-4 border rounded-lg ${
                      comp.competitor === "yoursite.com" ? "bg-primary/5 border-primary" : ""
                    }`}>
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-medium">{comp.competitor}</p>
                        {comp.competitor === "yoursite.com" && (
                          <Badge>You</Badge>
                        )}
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Visibility</p>
                          <p className="font-medium">{comp.visibility}%</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Keywords</p>
                          <p className="font-medium">{comp.keywords.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Avg Position</p>
                          <p className="font-medium">{comp.avgPosition}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Opportunities Tab */}
          <TabsContent value="opportunities">
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-12">
                  <Zap className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">SEO Opportunities</h3>
                  <p className="text-muted-foreground mb-4">
                    AI-powered recommendations to improve your SEO performance
                  </p>
                  <Button onClick={() => router.push("/sge-readiness")}>
                    View SGE Recommendations
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}