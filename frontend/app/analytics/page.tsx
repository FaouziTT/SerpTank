"use client";

import { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  BarChart3, TrendingUp, Search, FileText, Youtube, Hash, 
  Activity, Target, Users, Globe, ChevronRight, ArrowUp,
  ArrowDown, Minus, Sparkles, Brain, Share2, RefreshCw,
  Calendar, Filter, Download, Loader2, Eye, Plus, ArrowUpRight,
  TrendingDown, Zap, Shield, CheckCircle, AlertCircle, Star,
  Edit, BookOpen, MessageSquare, ArrowRight
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
import { DashboardPageHeader } from "@/components/layout/dashboard-page-header";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { useAnalyticsService, type AnalyticsFilters } from "@/lib/data-access";
import { dedupedApi as api } from "@/lib/api-deduped";
import { Skeleton } from "@/components/ui/skeleton";
import { EntityModal } from "@/components/ui/entity-modal";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useAutoRefresh } from "@/lib/hooks/use-auto-refresh";
import { useWebSocketEvent } from "@/lib/hooks/use-websocket";
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ScatterChart, Scatter, ComposedChart
} from "recharts";
import { formatNumber, formatPercentage, formatDate } from "@/lib/utils";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { AIInsightsPanel } from "@/components/ai-insights-panel";
import { motion } from "framer-motion";

interface AnalyticsModule {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  href: string;
  stats?: {
    label: string;
    value: string | number;
    change?: number;
    trend?: "up" | "down" | "neutral";
  }[];
  status?: "active" | "warning" | "error";
  badge?: string;
}

// Component for competitor overview
function CompetitorOverview({ data, isLoading }: { data: any; isLoading: boolean }) {
  const [addCompetitorOpen, setAddCompetitorOpen] = useState(false);
  const { toast } = useToast();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
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
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const topCompetitors = data.competitors || [];
  const visibilityScore = data.visibility_score || 0;
  const competitorCount = topCompetitors.length;

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Your Visibility Score
            </CardTitle>
            <Eye className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{visibilityScore.toFixed(1)}%</div>
            <Progress value={visibilityScore} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-2">
              Based on top 100 keywords
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Tracked Competitors
            </CardTitle>
            <Users className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{competitorCount}</div>
            <p className="text-xs text-muted-foreground mt-2">
              Active competitor domains
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Market Share
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">24.5%</div>
            <div className="flex items-center space-x-1 text-xs mt-2">
              <TrendingUp className="h-3 w-3 text-green-500" />
              <span className="text-green-500">+2.3%</span>
              <span className="text-muted-foreground">vs last month</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Competitors */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle>Top Competitors</CardTitle>
            <CardDescription>
              Domains competing for your target keywords
            </CardDescription>
          </div>
          <Button
            size="sm"
            onClick={() => setAddCompetitorOpen(true)}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Competitor
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {topCompetitors.map((competitor: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex items-center gap-4">
                  <div className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-full font-semibold text-white",
                    index === 0 ? "bg-yellow-500" : index === 1 ? "bg-gray-400" : index === 2 ? "bg-amber-600" : "bg-muted text-muted-foreground"
                  )}>
                    {index + 1}
                  </div>
                  <div>
                    <p className="font-medium flex items-center gap-2">
                      {competitor.domain}
                      <ArrowUpRight className="h-3 w-3 text-muted-foreground" />
                    </p>
                    <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                      <span>Visibility: {competitor.visibility}%</span>
                      <span>•</span>
                      <span>{competitor.keyword_count} keywords</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium">{competitor.overlap}%</p>
                    <p className="text-xs text-muted-foreground">Keyword overlap</p>
                  </div>
                  <Button variant="outline" size="sm">
                    Analyze
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Add Competitor Modal */}
      <EntityModal
        open={addCompetitorOpen}
        onOpenChange={setAddCompetitorOpen}
        entity="competitor"
        action="create"
        onSuccess={() => {
          toast({
            title: 'Competitor added',
            description: 'The competitor has been added to your tracking list.',
          });
        }}
      />
    </div>
  );
}

// Component for keyword gap analysis
function KeywordGapAnalysis({ data, isLoading }: { data: any; isLoading: boolean }) {
  const [selectedCompetitor, setSelectedCompetitor] = useState<string>('all');

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[300px] w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  const keywordGaps = data?.keyword_gaps || [];

  const getOpportunityColor = (opportunity: string) => {
    switch (opportunity) {
      case 'high': return 'text-green-500';
      case 'medium': return 'text-yellow-500';
      case 'low': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getOpportunityBadge = (opportunity: string) => {
    switch (opportunity) {
      case 'high': return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'low': return 'bg-red-500/10 text-red-500 border-red-500/20';
      default: return '';
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Keyword Gap Analysis</CardTitle>
              <CardDescription>
                Keywords your competitors rank for that you don&apos;t
              </CardDescription>
            </div>
            <Select value={selectedCompetitor} onValueChange={setSelectedCompetitor}>
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Competitors</SelectItem>
                <SelectItem value="competitor1.com">competitor1.com</SelectItem>
                <SelectItem value="competitor2.com">competitor2.com</SelectItem>
                <SelectItem value="competitor3.com">competitor3.com</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {keywordGaps.length === 0 ? (
            <div className="text-center py-8">
              <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No keyword gap data available</p>
              <p className="text-sm text-muted-foreground mt-1">
                Run a competitor analysis to see keyword opportunities
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {keywordGaps.map((gap: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex-1">
                  <p className="font-medium">{gap.keyword}</p>
                  <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                    <span>Volume: {formatNumber(gap.volume)}</span>
                    <span>•</span>
                    <span>Difficulty: {gap.difficulty}/100</span>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-center">
                    <p className="text-sm font-medium">{gap.competitor_rank}</p>
                    <p className="text-xs text-muted-foreground">Competitor</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium">{gap.your_rank}</p>
                    <p className="text-xs text-muted-foreground">You</p>
                  </div>
                  <Badge className={getOpportunityBadge(gap.opportunity)}>
                    {gap.opportunity} opportunity
                  </Badge>
                  <Button size="sm">
                    Target Keyword
                  </Button>
                </div>
              </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Keyword Opportunity Distribution</CardTitle>
          <CardDescription>
            Potential keywords by difficulty and search volume
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis 
                  dataKey="difficulty" 
                  name="Difficulty" 
                  domain={[0, 100]}
                  className="text-xs"
                />
                <YAxis 
                  dataKey="volume" 
                  name="Search Volume"
                  className="text-xs"
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Scatter 
                  name="Keywords" 
                  data={keywordGaps} 
                  fill="#8b5cf6"
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Component for SERP features
function SERPFeatures({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          {[...Array(2)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-[200px] w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const serpFeatures = data?.serp_features || [];

  const radarData = serpFeatures.map((f: any) => ({
    feature: f.feature,
    you: f.you,
    competitors: f.competitors
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>SERP Features Comparison</CardTitle>
            <CardDescription>
              Your presence vs competitors in SERP features
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid strokeDasharray="3 3" className="stroke-muted" />
                  <PolarAngleAxis dataKey="feature" className="text-xs" />
                  <PolarRadiusAxis className="text-xs" />
                  <Radar 
                    name="You" 
                    dataKey="you" 
                    stroke="#8b5cf6" 
                    fill="#8b5cf6" 
                    fillOpacity={0.6} 
                  />
                  <Radar 
                    name="Competitors" 
                    dataKey="competitors" 
                    stroke="#ef4444" 
                    fill="#ef4444" 
                    fillOpacity={0.6} 
                  />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>SERP Feature Opportunities</CardTitle>
            <CardDescription>
              Features where you can improve visibility
            </CardDescription>
          </CardHeader>
          <CardContent>
            {serpFeatures.length === 0 ? (
              <div className="text-center py-8">
                <Zap className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No SERP features data available</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Run SERP analysis to see feature opportunities
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {serpFeatures.map((feature: any, index: number) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{feature.feature}</span>
                    <span className="text-sm text-muted-foreground">
                      {feature.opportunity} opportunities
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <Progress 
                        value={(feature.you / (feature.you + feature.competitors)) * 100} 
                        className="h-2"
                      />
                    </div>
                    <span className="text-xs font-medium w-12 text-right">
                      {feature.you}%
                    </span>
                  </div>
                </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>SERP Feature Recommendations</CardTitle>
          <CardDescription>
            Actionable insights to capture more SERP features
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 rounded-lg border border-green-500/20 bg-green-500/5">
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">Target Featured Snippets</p>
                <p className="text-sm text-muted-foreground mt-1">
                  You have 16 keyword opportunities for featured snippets. Focus on question-based keywords
                  and format content with clear, concise answers.
                </p>
                <Button size="sm" className="mt-2">
                  View Opportunities
                </Button>
              </div>
            </div>
            
            <div className="flex items-start gap-4 p-4 rounded-lg border border-yellow-500/20 bg-yellow-500/5">
              <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">Improve People Also Ask Coverage</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Competitors dominate PAA boxes. Create FAQ sections and expand content depth
                  to capture these opportunities.
                </p>
                <Button size="sm" variant="outline" className="mt-2">
                  Learn More
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Component for competitive insights
function CompetitiveInsights({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const insights = data?.insights || [];

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'opportunity': return <Target className="h-5 w-5 text-green-500" />;
      case 'threat': return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'trend': return <TrendingUp className="h-5 w-5 text-blue-500" />;
      case 'win': return <Star className="h-5 w-5 text-yellow-500" />;
      default: return <Zap className="h-5 w-5 text-gray-500" />;
    }
  };

  const getImpactBadge = (impact: string) => {
    switch (impact) {
      case 'high': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'low': return 'bg-green-500/10 text-green-500 border-green-500/20';
      default: return '';
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Competitive Intelligence</CardTitle>
          <CardDescription>
            AI-powered insights and recommendations
          </CardDescription>
        </CardHeader>
        <CardContent>
          {insights.length === 0 ? (
            <div className="text-center py-8">
              <Target className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No competitive insights available</p>
              <p className="text-sm text-muted-foreground mt-1">
                Add competitors to get AI-powered insights and recommendations
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {insights.map((insight: any, index: number) => (
              <div key={index} className="flex items-start gap-4 p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                {getInsightIcon(insight.type)}
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{insight.title}</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {insight.description}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-sm">
                        <span className="text-muted-foreground">
                          {insight.keywords} keywords affected
                        </span>
                        <span className="text-muted-foreground">•</span>
                        <span className="text-muted-foreground">
                          {insight.traffic_potential} potential traffic
                        </span>
                      </div>
                    </div>
                    <Badge className={getImpactBadge(insight.impact)}>
                      {insight.impact} impact
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <Button size="sm">
                      Take Action
                    </Button>
                    <Button size="sm" variant="outline">
                      View Details
                    </Button>
                  </div>
                </div>
              </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recommended Strategy</CardTitle>
          <CardDescription>
            Based on competitive analysis and market trends
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-5 w-5 text-primary" />
                <span className="font-medium">Defensive Strategy</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Protect your strong positions in local SEO and technical guides. 
                Increase content depth and freshness to maintain rankings.
              </p>
            </div>
            
            <div className="p-4 rounded-lg bg-blue-500/5 border border-blue-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Target className="h-5 w-5 text-blue-500" />
                <span className="font-medium">Offensive Strategy</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Target high-opportunity keywords in enterprise and reporting categories.
                Focus on featured snippets and video content creation.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AnalyticsHubPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { currentProject, organizations } = useProject();
  const organization = organizations?.[0]; // Get first organization from project context
  const { toast } = useToast();
  const queryClient = useQueryClient();

// Component for content performance overview
function ContentPerformanceOverview({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-6">
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
            <Skeleton className="h-[300px] w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Use live data from API or default to empty state
  const metrics = {
    total_pages: data?.metrics?.total_pages || 0,
    optimized_pages: data?.metrics?.optimized_pages || 0,
    avg_content_score: data?.metrics?.avg_content_score || 0,
    traffic_from_content: data?.metrics?.traffic_from_content || 0,
    pages_change: data?.metrics?.pages_change || 0,
    optimization_rate: data?.metrics?.optimization_rate || 0,
    score_change: data?.metrics?.score_change || 0,
    traffic_change: data?.metrics?.traffic_change || 0
  };

  // Use performance data from API or empty array
  const performanceTrend = data?.performance_trend || [];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Pages
            </CardTitle>
            <FileText className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.total_pages}</div>
            <div className="flex items-center space-x-1 text-xs">
              <TrendingUp className="h-3 w-3 text-green-500" />
              <span className="text-green-500">+{metrics.pages_change}%</span>
              <span className="text-muted-foreground">from last month</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Optimization Rate
            </CardTitle>
            <Zap className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.optimization_rate}%</div>
            <Progress value={metrics.optimization_rate} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {metrics.optimized_pages} of {metrics.total_pages} pages
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Content Score
            </CardTitle>
            <Star className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.avg_content_score}/100</div>
            <div className="flex items-center space-x-1 text-xs">
              <TrendingUp className="h-3 w-3 text-green-500" />
              <span className="text-green-500">+{metrics.score_change}</span>
              <span className="text-muted-foreground">points improvement</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Content Traffic
            </CardTitle>
            <Eye className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(metrics.traffic_from_content)}</div>
            <div className="flex items-center space-x-1 text-xs">
              <TrendingUp className="h-3 w-3 text-green-500" />
              <span className="text-green-500">+{metrics.traffic_change}%</span>
              <span className="text-muted-foreground">vs previous period</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Content Performance Trend</CardTitle>
          <CardDescription>
            Traffic and conversions from content over time
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={performanceTrend}>
                <defs>
                  <linearGradient id="colorTraffic" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorConversions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="month" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="traffic"
                  stroke="#8b5cf6"
                  fillOpacity={1}
                  fill="url(#colorTraffic)"
                />
                <Area
                  type="monotone"
                  dataKey="conversions"
                  stroke="#10b981"
                  fillOpacity={1}
                  fill="url(#colorConversions)"
                  yAxisId="right"
                />
                <YAxis yAxisId="right" orientation="right" className="text-xs" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Top Performing Content</CardTitle>
          <CardDescription>
            Your best performing pages by traffic and engagement
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {(data?.top_performing_content || []).length === 0 ? (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No content performance data available</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Content analysis will show here once data is collected
                </p>
              </div>
            ) : (
              (data?.top_performing_content || []).map((page: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex-1">
                  <p className="font-medium">{page.title}</p>
                  <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                    <span>{formatNumber(page.traffic)} visits</span>
                    <span>•</span>
                    <span>Score: {page.score}/100</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {page.trend === 'up' && <TrendingUp className="h-4 w-4 text-green-500" />}
                  {page.trend === 'down' && <TrendingDown className="h-4 w-4 text-red-500" />}
                  <Button size="sm" variant="outline">
                    View Details
                  </Button>
                </div>
              </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Component for content gap analysis
function ContentGapAnalysis({ data, isLoading, error }: { data: any; isLoading: boolean; error?: any }) {
  const [createBriefOpen, setCreateBriefOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show error state if there was an error or no data
  if (error || (!data && !isLoading)) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-orange-500" />
            Content Gap Analysis Unavailable
          </CardTitle>
          <CardDescription>
            We're having trouble analyzing content gaps right now. Please try again later.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-sm text-muted-foreground mb-4">
              Content gap analysis requires active content monitoring and competitor data.
            </p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Use content gaps from API or empty array
  const contentGaps = data?.content_gaps || [];

  const getOpportunityColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle>Content Gap Opportunities</CardTitle>
            <CardDescription>
              High-value topics missing from your content strategy
            </CardDescription>
          </div>
          <Button
            size="sm"
            onClick={() => setCreateBriefOpen(true)}
          >
            <Plus className="mr-2 h-4 w-4" />
            Create Brief
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {contentGaps.length === 0 ? (
              <div className="text-center py-8">
                <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No content gaps identified</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Content gap analysis will show opportunities once data is available
                </p>
              </div>
            ) : (
              contentGaps.map((gap: any, index: number) => (
              <div key={index} className="p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium">{gap.topic}</p>
                    <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                      <span>Volume: {formatNumber(gap.search_volume)}</span>
                      <span>•</span>
                      <span>Difficulty: {gap.difficulty}/100</span>
                      <span>•</span>
                      <span>{gap.competitors_covering} competitors</span>
                    </div>
                    <div className="mt-2">
                      <Badge variant="secondary">{gap.suggested_format}</Badge>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={cn("text-2xl font-bold", getOpportunityColor(gap.opportunity_score))}>
                      {gap.opportunity_score}
                    </div>
                    <p className="text-xs text-muted-foreground">Opportunity Score</p>
                    <Button size="sm" className="mt-2">
                      Create Content
                    </Button>
                  </div>
                </div>
              </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recommended Topic Clusters</CardTitle>
          <CardDescription>
            Group related content for topical authority
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-4 rounded-lg border">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="h-5 w-5 text-primary" />
                <h4 className="font-medium">Technical SEO Cluster</h4>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Core Web Vitals Guide</span>
                  <Badge variant="secondary" className="text-xs">Pillar</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Page Speed Optimization</span>
                  <CheckCircle className="h-4 w-4 text-green-500" />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Mobile SEO Best Practices</span>
                  <AlertCircle className="h-4 w-4 text-yellow-500" />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Structured Data Implementation</span>
                  <Plus className="h-4 w-4 text-muted-foreground" />
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg border">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="h-5 w-5 text-primary" />
                <h4 className="font-medium">Local SEO Cluster</h4>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Local SEO Complete Guide</span>
                  <Badge variant="secondary" className="text-xs">Pillar</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Google My Business Optimization</span>
                  <CheckCircle className="h-4 w-4 text-green-500" />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Local Link Building</span>
                  <CheckCircle className="h-4 w-4 text-green-500" />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Review Management Strategy</span>
                  <Plus className="h-4 w-4 text-muted-foreground" />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <EntityModal
        open={createBriefOpen}
        onOpenChange={setCreateBriefOpen}
        entity="content-brief"
        action="create"
        onSuccess={() => {
          setCreateBriefOpen(false);
        }}
      />
    </div>
  );
}

// Component for content optimization
function ContentOptimization({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-32 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Use optimization tasks from API or empty array
  const optimizationTasks = data?.optimization_tasks || [];

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'low': return 'bg-green-500/10 text-green-500 border-green-500/20';
      default: return '';
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Content Optimization Queue</CardTitle>
          <CardDescription>
            Pages with the highest optimization potential
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {optimizationTasks.length === 0 ? (
              <div className="text-center py-8">
                <Zap className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No optimization tasks available</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Content optimization opportunities will appear once analysis is complete
                </p>
              </div>
            ) : (
              optimizationTasks.map((task: any, index: number) => (
              <div key={index} className="p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-medium">{task.title}</p>
                    <p className="text-sm text-muted-foreground">{task.page}</p>
                  </div>
                  <Badge className={getPriorityColor(task.priority)}>
                    {task.priority} priority
                  </Badge>
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Content Score</span>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{task.current_score}</span>
                        <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        <span className="text-sm font-medium text-green-500">{task.potential_score}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="w-full bg-secondary rounded-full h-2 relative">
                    <div 
                      className="bg-primary h-2 rounded-full absolute left-0 top-0"
                      style={{ width: `${task.current_score}%` }}
                    />
                    <div 
                      className="bg-primary/30 h-2 rounded-full absolute left-0 top-0"
                      style={{ width: `${task.potential_score}%` }}
                    />
                  </div>
                  
                  <div className="flex flex-wrap gap-2 mt-2">
                    {task.issues.map((issue: string, i: number) => (
                      <Badge key={i} variant="outline" className="text-xs">
                        {issue}
                      </Badge>
                    ))}
                  </div>
                  
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-sm text-green-500 font-medium">
                      {task.estimated_impact}
                    </span>
                    <Button size="sm">
                      <Edit className="mr-2 h-3 w-3" />
                      Optimize Now
                    </Button>
                  </div>
                </div>
              </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Wins</CardTitle>
            <CardDescription>
              Easy optimizations with high impact
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Add FAQ Schema</p>
                  <p className="text-xs text-muted-foreground">
                    12 pages missing FAQ schema markup
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Update Meta Descriptions</p>
                  <p className="text-xs text-muted-foreground">
                    8 pages with truncated descriptions
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Optimize Images</p>
                  <p className="text-xs text-muted-foreground">
                    23 images over 100KB need compression
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Content Health Score</CardTitle>
            <CardDescription>
              Overall content quality metrics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-center">
                <div className="relative w-32 h-32">
                  <svg className="w-32 h-32 transform -rotate-90">
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke="currentColor"
                      strokeWidth="12"
                      fill="none"
                      className="text-secondary"
                    />
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke="currentColor"
                      strokeWidth="12"
                      fill="none"
                      strokeDasharray={`${2 * Math.PI * 56}`}
                      strokeDashoffset={`${2 * Math.PI * 56 * (1 - 0.78)}`}
                      className="text-primary transition-all duration-500"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-2xl font-bold">78</div>
                      <div className="text-xs text-muted-foreground">Score</div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Readability</span>
                  <span className="font-medium">85/100</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>SEO Optimization</span>
                  <span className="font-medium">72/100</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>User Engagement</span>
                  <span className="font-medium">79/100</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Component for SGE readiness
function SGEReadiness({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[200px] w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Use SGE data from API or defaults
  const sgeMetrics = {
    overall_readiness: data?.sge_metrics?.overall_readiness || 0,
    conversational_content: data?.sge_metrics?.conversational_content || 0,
    structured_data: data?.sge_metrics?.structured_data || 0,
    entity_coverage: data?.sge_metrics?.entity_coverage || 0,
    citation_worthy: data?.sge_metrics?.citation_worthy || 0,
  };

  // Use conversational gaps from API or empty array
  const conversationalGaps = data?.conversational_gaps || [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>SGE Readiness Dashboard</CardTitle>
          <CardDescription>
            How well your content is optimized for Search Generative Experience
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <div className="flex items-center justify-center mb-4">
                <div className="relative w-40 h-40">
                  <svg className="w-40 h-40 transform -rotate-90">
                    <circle
                      cx="80"
                      cy="80"
                      r="70"
                      stroke="currentColor"
                      strokeWidth="12"
                      fill="none"
                      className="text-secondary"
                    />
                    <circle
                      cx="80"
                      cy="80"
                      r="70"
                      stroke="currentColor"
                      strokeWidth="12"
                      fill="none"
                      strokeDasharray={`${2 * Math.PI * 70}`}
                      strokeDashoffset={`${2 * Math.PI * 70 * (1 - sgeMetrics.overall_readiness / 100)}`}
                      className="text-primary transition-all duration-500"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-3xl font-bold">{sgeMetrics.overall_readiness}%</div>
                      <div className="text-sm text-muted-foreground">SGE Ready</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Conversational Content</span>
                  <span className="text-sm font-medium">{sgeMetrics.conversational_content}%</span>
                </div>
                <Progress value={sgeMetrics.conversational_content} />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Structured Data</span>
                  <span className="text-sm font-medium">{sgeMetrics.structured_data}%</span>
                </div>
                <Progress value={sgeMetrics.structured_data} />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Entity Coverage</span>
                  <span className="text-sm font-medium">{sgeMetrics.entity_coverage}%</span>
                </div>
                <Progress value={sgeMetrics.entity_coverage} />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Citation Worthy</span>
                  <span className="text-sm font-medium">{sgeMetrics.citation_worthy}%</span>
                </div>
                <Progress value={sgeMetrics.citation_worthy} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Conversational Content Gaps</CardTitle>
          <CardDescription>
            Questions your content should answer for SGE
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {conversationalGaps.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No conversational gaps identified</p>
                <p className="text-sm text-muted-foreground mt-1">
                  SGE analysis will identify content gaps once data is available
                </p>
              </div>
            ) : (
              conversationalGaps.map((gap: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg border">
                <div className="flex items-center gap-3">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{gap.question}</span>
                </div>
                <div className="flex items-center gap-2">
                  {gap.status === 'covered' && (
                    <Badge variant="secondary" className="bg-green-500/10 text-green-500">
                      Covered
                    </Badge>
                  )}
                  {gap.status === 'partial' && (
                    <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-500">
                      Partial
                    </Badge>
                  )}
                  {gap.status === 'missing' && (
                    <Badge variant="secondary" className="bg-red-500/10 text-red-500">
                      Missing
                    </Badge>
                  )}
                  {gap.status !== 'covered' && (
                    <Button size="sm" variant="outline">
                      Add Answer
                    </Button>
                  )}
                </div>
              </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>SGE Optimization Recommendations</CardTitle>
          <CardDescription>
            Actions to improve your SGE visibility
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-4 rounded-lg border border-primary/20 bg-primary/5">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-5 w-5 text-primary" />
                <h4 className="font-medium">Enhance Conversational Tone</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Rewrite technical content to be more conversational and question-focused.
                Focus on natural language patterns.
              </p>
            </div>
            
            <div className="p-4 rounded-lg border border-blue-500/20 bg-blue-500/5">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="h-5 w-5 text-blue-500" />
                <h4 className="font-medium">Add Entity Markup</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Implement Person, Organization, and Product schema to help Google understand
                your content entities.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// SEO Analytics Components
function SEOMetrics({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[...Array(5)].map((_, i) => (
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
    );
  }

  const seoData = {
    overallScore: data?.overall_score || 0,
    scoreChange: data?.score_change || 0,
    totalKeywords: data?.total_keywords || 0,
    keywordsChange: data?.keywords_change || 0,
    avgPosition: data?.avg_position || 0,
    positionChange: data?.position_change || 0,
    organicTraffic: data?.organic_traffic || 0,
    trafficChange: data?.traffic_change || 0,
    visibility: data?.visibility || 0,
    visibilityChange: data?.visibility_change || 0
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

  return (
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
  );
}

function SEOPerformanceChart({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[400px] w-full" />
        </CardContent>
      </Card>
    );
  }

  const performanceTrend = data?.performance_trend || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance Trend</CardTitle>
        <CardDescription>
          SEO visibility and organic traffic over time
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[400px]">
          {performanceTrend.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <TrendingUp className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No performance data available</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Performance trends will show here once data is collected
                </p>
              </div>
            </div>
          ) : (
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
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SEOKeywordDistribution({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

  const keywordDistribution = data?.keyword_distribution || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Keyword Distribution</CardTitle>
        <CardDescription>Keywords by ranking position</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          {keywordDistribution.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No keyword distribution data available</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Keyword rankings will show here once analysis is complete
                </p>
              </div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={keywordDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {keywordDistribution.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SEOHealthIssues({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const healthIssues = data?.health_issues || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>SEO Health Issues</CardTitle>
        <CardDescription>Critical issues affecting performance</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {healthIssues.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-4" />
              <p className="text-muted-foreground">No critical SEO issues detected</p>
              <p className="text-sm text-muted-foreground mt-1">
                Your site appears to be in good SEO health
              </p>
            </div>
          ) : (
            healthIssues.map((issue: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <AlertCircle className={`h-5 w-5 ${
                    issue.priority === 'high' ? 'text-red-500' :
                    issue.priority === 'medium' ? 'text-yellow-500' : 'text-blue-500'
                  }`} />
                  <div>
                    <p className="font-medium">{issue.title}</p>
                    <p className="text-sm text-muted-foreground">{issue.affected_pages} pages affected</p>
                  </div>
                </div>
                <Badge variant={
                  issue.priority === 'high' ? 'destructive' :
                  issue.priority === 'medium' ? 'warning' : 'secondary'
                }>
                  {issue.priority}
                </Badge>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SEOTopPages({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const topPages = data?.top_pages || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Performing Pages</CardTitle>
        <CardDescription>Pages driving the most organic traffic</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {topPages.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No page performance data available</p>
              <p className="text-sm text-muted-foreground mt-1">
                Top performing pages will show here once data is collected
              </p>
            </div>
          ) : (
            topPages.map((page: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex-1">
                  <p className="font-medium">{page.url}</p>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                    <span>Traffic: {page.traffic?.toLocaleString()}</span>
                    <span>Keywords: {page.keywords}</span>
                    <span>CTR: {page.ctr}%</span>
                    <span>Avg Position: {page.position}</span>
                  </div>
                </div>
                <Button variant="ghost" size="sm">
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SEOCompetitorComparison({ data, isLoading }: { data: any; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const competitorComparison = data?.competitor_comparison || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Competitor Comparison</CardTitle>
        <CardDescription>How you stack up against the competition</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {competitorComparison.length === 0 ? (
            <div className="text-center py-8">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No competitor comparison data available</p>
              <p className="text-sm text-muted-foreground mt-1">
                Competitor analysis will show here once configured
              </p>
            </div>
          ) : (
            competitorComparison.map((comp: any, index: number) => (
              <div key={index} className={`p-4 border rounded-lg ${
                comp.is_current_site ? "bg-primary/5 border-primary" : ""
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <p className="font-medium">{comp.competitor}</p>
                  {comp.is_current_site && (
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
                    <p className="font-medium">{comp.keywords?.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Avg Position</p>
                    <p className="font-medium">{comp.avgPosition}</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

  const [activeTab, setActiveTab] = useState("overview");
  const [dateRange, setDateRange] = useState({ start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), end: new Date() });
  const [selectedMetric, setSelectedMetric] = useState("traffic");
  const [isExporting, setIsExporting] = useState(false);
  const [showAIInsights, setShowAIInsights] = useState(false);
  
  // Parallax and scroll effects
  
  // Use the new analytics service
  const analyticsService = useAnalyticsService();

  // Auto-refresh analytics data every 5 minutes
  useAutoRefresh(
    ['analytics-data', currentProject?.id],
    300000,
    { enabled: !!currentProject }
  );

  // Listen for real-time analytics updates
  useWebSocketEvent('analytics_update', (data) => {
    if (data.project_id === currentProject?.id) {
      queryClient.invalidateQueries({ queryKey: ['analytics-data'] });
      toast({
        title: "Analytics Updated",
        description: "New data is available",
      });
    }
  }, [currentProject?.id, queryClient, toast]);

  // Handle unhandled promise rejections
  useEffect(() => {
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      if (event.reason?.name === 'AxiosError') {
        const url = event.reason?.config?.url || '';
        if (url.includes('analytics') || url.includes('content-workflow') || url.includes('gap-analysis')) {
          console.warn('Analytics/Content API error handled:', event.reason.message);
          event.preventDefault(); // Prevent the error from being logged as uncaught
          return;
        }
      }
    };

    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, []);

  // Create analytics filters
  const analyticsFilters: AnalyticsFilters = {
    dateRange,
    metrics: ['impressions', 'clicks', 'ctr', 'position'],
    country: 'US', // Could be made configurable
  };

  // Fetch data from individual APIs using established patterns
  const { data: searchConsoleData, isLoading: isSearchConsoleLoading, refetch } = useQuery({
    queryKey: ['search-console', currentProject?.id, dateRange],
    queryFn: async () => {
      try {
        return await api.searchConsole.getDashboard({
          days: Math.ceil((dateRange.end.getTime() - dateRange.start.getTime()) / (1000 * 60 * 60 * 24))
        });
      } catch (error) {
        console.warn('Search Console dashboard error:', error);
        return { data: null };
      }
    },
    enabled: !!currentProject,
    retry: false,
    throwOnError: false
  });

  const { data: contentData, isLoading: isContentLoading } = useQuery({
    queryKey: ['content-workflow', currentProject?.id],
    queryFn: async () => {
      try {
        return await api.contentWorkflow.getPerformanceTracking();
      } catch (error) {
        console.warn('Content workflow performance tracking error:', error);
        return { data: null };
      }
    },
    enabled: !!currentProject,
    retry: false,
    throwOnError: false
  });

  // Fetch content gap analysis - requires POST with specific parameters
  const { data: contentGapsData, isLoading: isGapsLoading, error: gapsError } = useQuery({
    queryKey: ['content-gaps', currentProject?.id],
    queryFn: async () => {
      try {
        return await api.contentWorkflow.gapAnalysis({
          primary_keywords: ['SEO', 'digital marketing', 'content optimization'],
          competitor_domains: ['example.com', 'competitor.com'],
          content_categories: ['blog', 'guides', 'resources'],
          analysis_depth: 'standard',
          include_trending_topics: true
        });
      } catch (error) {
        console.warn('Content gaps analysis error:', error);
        return { data: null };
      }
    },
    enabled: !!currentProject,
    retry: false,
    refetchOnWindowFocus: false,
    throwOnError: false
  });

  // Fetch SGE readiness data - requires topic query parameter
  const { data: sgeData, isLoading: isSgeLoading, error: sgeError } = useQuery({
    queryKey: ['sge-readiness', currentProject?.id], 
    queryFn: async () => {
      try {
        return await api.sgeReadiness.getConversationalGaps('SEO');
      } catch (error) {
        console.warn('SGE readiness analysis error:', error);
        return { data: null };
      }
    },
    enabled: !!currentProject,
    retry: false,
    refetchOnWindowFocus: false,
    throwOnError: false
  });

  const { data: serpData, isLoading: isSerpLoading, error: serpError } = useQuery({
    queryKey: ['serp-analysis', currentProject?.id],
    queryFn: async () => {
      try {
        return await api.serpAnalysis.getCompetitors();
      } catch (error) {
        console.warn('SERP competitors analysis error:', error);
        return { data: null };
      }
    },
    enabled: !!currentProject,
    retry: false,
    refetchOnWindowFocus: false,
    throwOnError: false
  });

  // Fetch SERP features data for competitors tab
  const { data: serpFeaturesData, isLoading: isSerpFeaturesLoading } = useQuery({
    queryKey: ['serp-features', currentProject?.id],
    queryFn: async () => {
      try {
        return await api.serpAnalysis.getFeatures();
      } catch (error) {
        console.warn('SERP features analysis error:', error);
        return { data: null };
      }
    },
    enabled: !!currentProject,
    retry: false,
    refetchOnWindowFocus: false,
    throwOnError: false
  });

  // Fetch SEO overview data
  const { data: seoOverviewData, isLoading: isSeoLoading } = useQuery({
    queryKey: ['seo-overview', currentProject?.id],
    queryFn: async () => {
      try {
        return await api.serpAnalysis.getOverview();
      } catch (error) {
        console.warn('SEO overview analysis error:', error);
        return { data: null };
      }
    },
    enabled: !!currentProject,
    retry: false,
    refetchOnWindowFocus: false,
    throwOnError: false
  });

  // Google Trends - External link instead of scraping for legal compliance
  const trendsData = null;
  const isTrendsLoading = false;

  // Combined loading and error states
  const isLoading = isSearchConsoleLoading || isContentLoading || isSerpLoading || isTrendsLoading;
  const error = null; // Individual queries handle their own errors
  
  // Combine all data into analyticsData format for backward compatibility
  const analyticsData = useMemo(() => {
    if (isLoading || !searchConsoleData) return null;
    
    return {
      searchConsole: searchConsoleData?.data?.performance ? {
        metrics: {
          impressions: searchConsoleData.data.performance.total_impressions || 0,
          clicks: searchConsoleData.data.performance.total_clicks || 0,
          ctr: searchConsoleData.data.performance.average_ctr || 0,
          position: searchConsoleData.data.performance.average_position || 0,
          impressions_change: 0, // TODO: Calculate from historical data
          clicks_change: 0,
          ctr_change: 0,
          position_change: 0
        },
        keywords: searchConsoleData.data.top_queries?.slice(0, 10).map((q: any) => ({
          keyword: q.query,
          clicks: q.clicks,
          impressions: q.impressions,
          ctr: q.ctr,
          position: q.position
        })) || [],
        daily_data: searchConsoleData.data.performance.daily_breakdown || [],
        last_sync: new Date().toISOString()
      } : null,
      content: contentData?.data ? {
        total_pages: contentData.data.total_briefs || 0,
        average_score: contentData.data.average_seo_score || 0,
        score_change: 0, // TODO: Calculate from historical data
        top_performing: [],
        optimization_opportunities: []
      } : null,
      competitors: serpData?.data ? {
        competitors: serpData.data.competitors || [],
        keyword_overlap: 0,
        market_share: 0
      } : null,
      trends: null, // Removed Google Trends for legal compliance
      lastUpdated: new Date().toISOString()
    };
  }, [searchConsoleData, contentData, serpData, trendsData, isLoading]);

  // Export analytics mutation
  const exportAnalytics = useMutation({
    mutationFn: async (params: { projectId: string; filters: any; format: string }) => {
      if (!analyticsData) throw new Error('No analytics data available');
      
      // Create CSV content from analytics data
      const csvLines = [
        'SerpTank Analytics Export',
        `Generated: ${new Date().toISOString()}`,
        '',
        'Search Console Metrics',
        'Metric,Value',
        `Impressions,${analyticsData.searchConsole?.metrics?.impressions || 0}`,
        `Clicks,${analyticsData.searchConsole?.metrics?.clicks || 0}`,
        `CTR,${analyticsData.searchConsole?.metrics?.ctr || 0}%`,
        `Position,${analyticsData.searchConsole?.metrics?.position || 0}`,
        '',
      ];
      
      if (analyticsData.searchConsole?.keywords?.length) {
        csvLines.push('Top Keywords');
        csvLines.push('Keyword,Clicks,Impressions,CTR,Position');
        analyticsData.searchConsole.keywords.slice(0, 10).forEach((keyword: any) => {
          csvLines.push(`"${keyword.keyword}",${keyword.clicks},${keyword.impressions},${keyword.ctr}%,${keyword.position}`);
        });
      }
      
      const csvContent = csvLines.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      
      // Download file
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `analytics-${currentProject?.id}-${Date.now()}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      return blob;
    },
    onSuccess: () => {
      toast({
        title: "Export Complete",
        description: "Analytics data has been exported successfully.",
      });
    },
    onError: (error) => {
      toast({
        title: "Export Failed",
        description: "Failed to export analytics data. Please try again.",
        variant: "destructive",
      });
    }
  });

  // Generate analytics modules with real data
  const analyticsModules: AnalyticsModule[] = useMemo(() => {
    const modules = [
      {
        id: "seo",
        title: "SEO Overview",
        description: "Comprehensive SEO performance metrics and insights",
        icon: Search,
        href: "#seo",
        stats: [
          { 
            label: "Avg. Position", 
            value: analyticsData?.searchConsole?.metrics?.position?.toFixed(1) || "--", 
            change: analyticsData?.searchConsole?.metrics?.position_change || 0, 
            trend: (analyticsData?.searchConsole?.metrics?.position_change || 0) < 0 ? "up" as const : "down" as const
          },
          { 
            label: "Total Keywords", 
            value: formatNumber(analyticsData?.searchConsole?.keywords?.length || 0), 
            change: 0, // TODO: Calculate from historical data
            trend: "neutral" as const
          },
          { 
            label: "Visibility Score", 
            value: analyticsData?.searchConsole?.metrics ? `${Math.min(100, Math.max(0, 100 - (analyticsData.searchConsole.metrics.position || 100)))}%` : "--", 
            change: 0,
            trend: "neutral" as const
          }
        ],
        status: "active" as const,
        badge: "Core"
      },
      {
        id: "search-console",
        title: "Search Console",
        description: "Google Search Console data and performance tracking",
        icon: Activity,
        href: "/search-console",
        stats: [
          { 
            label: "Impressions", 
            value: formatNumber(analyticsData?.searchConsole?.metrics?.impressions || 0), 
            change: analyticsData?.searchConsole?.metrics?.impressions_change || 0, 
            trend: (analyticsData?.searchConsole?.metrics?.impressions_change || 0) > 0 ? "up" as const : "down" as const
          },
          { 
            label: "Clicks", 
            value: formatNumber(analyticsData?.searchConsole?.metrics?.clicks || 0), 
            change: analyticsData?.searchConsole?.metrics?.clicks_change || 0, 
            trend: (analyticsData?.searchConsole?.metrics?.clicks_change || 0) > 0 ? "up" as const : "down" as const
          },
          { 
            label: "CTR", 
            value: `${(analyticsData?.searchConsole?.metrics?.ctr || 0).toFixed(1)}%`, 
            change: analyticsData?.searchConsole?.metrics?.ctr_change || 0, 
            trend: (analyticsData?.searchConsole?.metrics?.ctr_change || 0) > 0 ? "up" as const : "neutral" as const
          }
        ],
        status: "active" as const
      },
      {
        id: "competitors",
        title: "Competitor Analysis",
        description: "Track and analyze competitor performance",
        icon: Users,
        href: "#competitors",
        stats: [
          { 
            label: "Tracked Competitors", 
            value: formatNumber(analyticsData?.competitors?.competitors?.length || 0), 
            change: 0, 
            trend: "neutral" as const
          },
          { 
            label: "Keyword Overlap", 
            value: `${(analyticsData?.competitors?.keyword_overlap || 0).toFixed(0)}%`, 
            change: 0, 
            trend: "neutral" as const
          },
          { 
            label: "Gap Opportunities", 
            value: "--", // TODO: Implement gap analysis
            change: 0, 
            trend: "neutral" as const
          }
        ],
        status: analyticsData?.competitors ? "active" as const : "warning" as const
      },
      {
        id: "content",
        title: "Content Analytics",
        description: "Content performance and optimization insights",
        icon: FileText,
        href: "#content",
        stats: [
          { 
            label: "Total Pages", 
            value: formatNumber(analyticsData?.content?.total_pages || 0), 
            change: 0, 
            trend: "neutral" as const
          },
          { 
            label: "Avg. Score", 
            value: (analyticsData?.content?.average_score || 0).toString(), 
            change: analyticsData?.content?.score_change || 0, 
            trend: (analyticsData?.content?.score_change || 0) > 0 ? "up" as const : "neutral" as const
          },
          { 
            label: "Optimized", 
            value: "--", // TODO: Calculate optimization percentage
            change: 0, 
            trend: "neutral" as const
          }
        ],
        status: "active" as const,
        badge: "AI-Powered"
      },
      {
        id: "trends",
        title: "Google Trends",
        description: "Access Google Trends for search interest analysis",
        icon: TrendingUp,
        href: "https://trends.google.com",
        stats: [
          { 
            label: "External Tool", 
            value: "Available", 
            change: 0, 
            trend: "neutral" as const
          },
          { 
            label: "Search Trends", 
            value: "Real-time", 
            change: 0, 
            trend: "neutral" as const
          },
          { 
            label: "Data Range", 
            value: "5+ Years", 
            change: 0, 
            trend: "neutral" as const
          }
        ],
        status: "active" as const,
        badge: "External"
      },
      {
        id: "sge",
        title: "SGE Readiness",
        description: "AI search readiness and optimization",
        icon: Sparkles,
        href: "/sge-readiness",
        stats: [
          { 
            label: "SGE Score", 
            value: "--", // TODO: Implement SGE scoring
            change: 0, 
            trend: "neutral" as const
          },
          { 
            label: "AI Citations", 
            value: "--", 
            change: 0, 
            trend: "neutral" as const
          },
          { 
            label: "Coverage", 
            value: "--", 
            change: 0, 
            trend: "neutral" as const
          }
        ],
        status: "warning" as const,
        badge: "New"
      }
    ];
    
    return modules;
  }, [analyticsData]);

  const getTrendIcon = (trend?: "up" | "down" | "neutral") => {
    switch (trend) {
      case "up":
        return <ArrowUp className="h-3 w-3 text-green-500" />;
      case "down":
        return <ArrowDown className="h-3 w-3 text-red-500" />;
      default:
        return <Minus className="h-3 w-3 text-gray-500" />;
    }
  };

  const getStatusColor = (status?: "active" | "warning" | "error") => {
    switch (status) {
      case "warning":
        return "bg-yellow-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-green-500";
    }
  };

  // Calculate overview metrics from real data
  const overviewMetrics = useMemo(() => {
    if (!analyticsData) {
      return [
        { title: "Overall SEO Health", value: "--", unit: "%", change: 0, trend: "neutral" as const },
        { title: "Total Traffic", value: "--", unit: "visits", change: 0, trend: "neutral" as const },
        { title: "Keyword Rankings", value: "--", unit: "keywords", change: 0, trend: "neutral" as const },
        { title: "Content Score", value: "--", unit: "/100", change: 0, trend: "neutral" as const },
      ];
    }

    const clicks = analyticsData.searchConsole?.metrics?.clicks || 0;
    const previousClicks = (analyticsData.searchConsole?.metrics as any)?.previous_clicks || clicks;
    const clicksChange = previousClicks > 0 ? ((clicks - previousClicks) / previousClicks) * 100 : 0;

    const keywords = analyticsData.searchConsole?.keywords?.length || 0;
    const avgPosition = analyticsData.searchConsole?.metrics?.position || 0;
    const positionChange = analyticsData.searchConsole?.metrics?.position_change || 0;

    const contentScore = analyticsData.content?.average_score || 0;
    const contentChange = analyticsData.content?.score_change || 0;

    const healthScore = Math.round(
      (100 - avgPosition) * 0.3 + // Position score (30%)
      (contentScore) * 0.3 + // Content score (30%)
      (Math.min(keywords / 10, 100)) * 0.2 + // Keyword coverage (20%)
      (Math.min(clicks / 1000, 100)) * 0.2 // Traffic score (20%)
    );

    return [
      {
        title: "Overall SEO Health",
        value: healthScore.toString(),
        unit: "%",
        change: 5,
        trend: "up" as const,
        description: "Based on 15 key metrics"
      },
      {
        title: "Total Traffic",
        value: formatNumber(clicks),
        unit: "clicks",
        change: clicksChange,
        trend: (clicksChange > 0 ? "up" : clicksChange < 0 ? "down" : "neutral") as "up" | "down" | "neutral",
        description: "Last 30 days"
      },
      {
        title: "Keyword Rankings",
        value: formatNumber(keywords),
        unit: "keywords",
        change: Math.abs(positionChange),
        trend: (positionChange < 0 ? "up" : positionChange > 0 ? "down" : "neutral") as "up" | "down" | "neutral",
        description: "In top 100 positions"
      },
      {
        title: "Content Score",
        value: contentScore.toString(),
        unit: "/100",
        change: contentChange,
        trend: (contentChange > 0 ? "up" : contentChange < 0 ? "down" : "neutral") as "up" | "down" | "neutral",
        description: "Average across all pages"
      }
    ];
  }, [analyticsData]);

  if (!currentProject) {
    return (
      <DashboardLayout>
        <EmptyState
          icon={BarChart3}
          title="No Project Selected"
          description="Please select a project from the dropdown above to view analytics."
        />
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <ErrorState
          error={error}
          title="Failed to load analytics"
          description="We couldn't fetch your analytics data. Please try again."
          onRetry={() => refetch()}
        />
      </DashboardLayout>
    );
  }

  return (
      <DashboardLayout>
        <div className="space-y-8 relative z-10">
        {/* Optimized Header - Research-based 2025 standards */}
        <DashboardPageHeader
          title="Analytics Hub"
          description="Unified analytics and AI-powered insights across all your SEO data"
          badge={{
            icon: <Sparkles className="mr-1 h-3 w-3" />,
            text: "Analytics Intelligence",
            variant: "secondary"
          }}
          actions={
            <div className="flex items-center gap-2">
              <DateRangePicker
                value={dateRange}
                onChange={setDateRange}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (currentProject?.id) {
                    exportAnalytics.mutate({
                      projectId: currentProject.id,
                      filters: analyticsFilters,
                      format: 'csv',
                    });
                  }
                }}
                disabled={exportAnalytics.isPending}
              >
                {exportAnalytics.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Export
              </Button>
              <Button
                size="sm"
                onClick={() => setShowAIInsights(true)}
              >
                <Brain className="h-4 w-4 mr-2" />
                AI Insights
              </Button>
            </div>
          }
        />

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="seo">SEO</TabsTrigger>
            <TabsTrigger value="content">Content</TabsTrigger>
            <TabsTrigger value="competitors">Competitors</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {isLoading ? (
              <LoadingState message="Loading analytics data..." size="lg" />
            ) : (
              <>
                {/* Key Metrics */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  {overviewMetrics.map((metric) => (
                    <Card key={metric.title} className="metric-card">
                      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                          {metric.title}
                        </CardTitle>
                        <div className="flex items-center text-xs">
                          {getTrendIcon(metric.trend)}
                          <span className={
                            metric.trend === "up" ? "text-green-500" : 
                            metric.trend === "down" ? "text-red-500" : 
                            "text-gray-500"
                          }>
                            {metric.change !== 0 && Math.abs(metric.change).toFixed(1)}%
                          </span>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold transition-all duration-300">
                          {metric.value}
                          <span className="text-sm font-normal text-muted-foreground ml-1">
                            {metric.unit}
                          </span>
                        </div>
                        {'description' in metric && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {metric.description}
                          </p>
                        )}
                        <Progress 
                          value={metric.value === "--" ? 0 : Math.min(parseInt(metric.value) || 0, 100)} 
                          className="mt-2 h-1"
                        />
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Interactive Charts */}
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Traffic Trend Chart */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Traffic Trend</CardTitle>
                      <CardDescription>
                        Clicks and impressions over time
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[300px]">
                        {analyticsData?.searchConsole?.daily_data ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={analyticsData.searchConsole.daily_data}>
                              <defs>
                                <linearGradient id="colorClicks" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                                </linearGradient>
                                <linearGradient id="colorImpressions" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                              <XAxis dataKey="date" className="text-xs" />
                              <YAxis className="text-xs" />
                              <Tooltip 
                                contentStyle={{ 
                                  backgroundColor: 'hsl(var(--card))',
                                  border: '1px solid hsl(var(--border))',
                                  borderRadius: '8px'
                                }}
                              />
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
                                stroke="#3b82f6"
                                fillOpacity={1}
                                fill="url(#colorImpressions)"
                              />
                            </AreaChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="flex items-center justify-center h-full text-muted-foreground">
                            No data available
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Keyword Performance Chart */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Top Keywords Performance</CardTitle>
                      <CardDescription>
                        Position and clicks by keyword
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[300px]">
                        {analyticsData?.searchConsole?.keywords ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={analyticsData.searchConsole.keywords.slice(0, 10)}>
                              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                              <XAxis dataKey="keyword" className="text-xs" angle={-45} textAnchor="end" height={80} />
                              <YAxis yAxisId="left" className="text-xs" />
                              <YAxis yAxisId="right" orientation="right" className="text-xs" />
                              <Tooltip 
                                contentStyle={{ 
                                  backgroundColor: 'hsl(var(--card))',
                                  border: '1px solid hsl(var(--border))',
                                  borderRadius: '8px'
                                }}
                              />
                              <Bar yAxisId="left" dataKey="clicks" fill="#8b5cf6" />
                              <Line yAxisId="right" type="monotone" dataKey="position" stroke="#f59e0b" strokeWidth={2} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="flex items-center justify-center h-full text-muted-foreground">
                            No keyword data available
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Analytics Modules Grid */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {analyticsModules.map((module) => {
                    const Icon = module.icon;
                    return (
                      <Card
                        key={module.id}
                        className="hover:shadow-lg transition-shadow cursor-pointer"
                        onClick={() => {
                          if (module.href.startsWith('http')) {
                            window.open(module.href, '_blank');
                          } else if (module.href.startsWith('#')) {
                            // Handle tab switching for internal tabs
                            const tabName = module.href.substring(1);
                            setActiveTab(tabName);
                          } else {
                            router.push(module.href);
                          }
                        }}
                      >
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="p-2 bg-primary/10 rounded-lg">
                                <Icon className="h-5 w-5 text-primary" />
                              </div>
                              <div>
                                <CardTitle className="text-base flex items-center gap-2">
                                  {module.title}
                                  {module.badge && (
                                    <Badge variant="secondary" className="text-xs">
                                      {module.badge}
                                    </Badge>
                                  )}
                                </CardTitle>
                                <CardDescription className="text-xs mt-1">
                                  {module.description}
                                </CardDescription>
                              </div>
                            </div>
                            <div className={`h-2 w-2 rounded-full ${getStatusColor(module.status)}`} />
                          </div>
                        </CardHeader>
                        <CardContent>
                          {module.stats && (
                            <div className="space-y-2">
                              {module.stats.map((stat, index) => (
                                <div key={index} className="flex items-center justify-between text-sm">
                                  <span className="text-muted-foreground">{stat.label}</span>
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">{stat.value}</span>
                                    {stat.change !== undefined && (
                                      <div className="flex items-center">
                                        {getTrendIcon(stat.trend)}
                                        <span className={`text-xs ${
                                          stat.trend === "up" ? "text-green-500" : 
                                          stat.trend === "down" ? "text-red-500" : 
                                          "text-gray-500"
                                        }`}>
                                          {Math.abs(stat.change)}%
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="w-full mt-4 justify-between"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (module.href.startsWith('http')) {
                                window.open(module.href, '_blank');
                              } else if (module.href.startsWith('#')) {
                                // Handle tab switching for internal tabs
                                const tabName = module.href.substring(1);
                                setActiveTab(tabName);
                              } else {
                                router.push(module.href);
                              }
                            }}
                          >
                            {module.href.startsWith('http') ? 'Open External' : 'View Details'}
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </>
            )}

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>Common analytics tasks and reports</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 md:grid-cols-4">
                  <Button variant="outline" size="sm" onClick={() => setActiveTab("seo")}>
                    <Search className="h-4 w-4 mr-2" />
                    SEO Analysis
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setActiveTab("content")}>
                    <FileText className="h-4 w-4 mr-2" />
                    Content Audit
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setActiveTab("competitors")}>
                    <Users className="h-4 w-4 mr-2" />
                    Competitor Report
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => window.open('https://trends.google.com', '_blank')}>
                    <TrendingUp className="h-4 w-4 mr-2" />
                    Google Trends
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* SEO Tab */}
          <TabsContent value="seo">
            <Tabs defaultValue="performance" className="space-y-6">
              <div className="space-y-6">
                {/* SEO Metrics */}
                <SEOMetrics 
                  data={seoOverviewData?.data} 
                  isLoading={isSeoLoading} 
                />
                
                <TabsList className="grid w-full grid-cols-5">
                  <TabsTrigger value="performance">Performance</TabsTrigger>
                  <TabsTrigger value="keywords">Keywords</TabsTrigger>
                  <TabsTrigger value="pages">Pages</TabsTrigger>
                  <TabsTrigger value="competitors">Competitors</TabsTrigger>
                  <TabsTrigger value="opportunities">Opportunities</TabsTrigger>
                </TabsList>

                <TabsContent value="performance" className="space-y-4">
                  <SEOPerformanceChart 
                    data={seoOverviewData?.data} 
                    isLoading={isSeoLoading} 
                  />
                  
                  <div className="grid gap-4 md:grid-cols-2">
                    <SEOKeywordDistribution 
                      data={seoOverviewData?.data} 
                      isLoading={isSeoLoading} 
                    />
                    <SEOHealthIssues 
                      data={seoOverviewData?.data} 
                      isLoading={isSeoLoading} 
                    />
                  </div>
                </TabsContent>

                <TabsContent value="keywords">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="text-center py-12">
                        <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <h3 className="text-lg font-semibold mb-2">Keywords Analysis</h3>
                        <p className="text-muted-foreground mb-4">
                          Detailed keyword rankings, search volume, and opportunity analysis
                        </p>
                        <Button onClick={() => setActiveTab("competitors")}>
                          <Search className="h-4 w-4 mr-2" />
                          View Competitor Analysis
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="pages">
                  <SEOTopPages 
                    data={seoOverviewData?.data} 
                    isLoading={isSeoLoading} 
                  />
                </TabsContent>

                <TabsContent value="competitors">
                  <SEOCompetitorComparison 
                    data={seoOverviewData?.data} 
                    isLoading={isSeoLoading} 
                  />
                </TabsContent>

                <TabsContent value="opportunities">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="text-center py-12">
                        <Zap className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <h3 className="text-lg font-semibold mb-2">SEO Opportunities</h3>
                        <p className="text-muted-foreground mb-4">
                          AI-powered recommendations to improve your SEO performance
                        </p>
                        <Button onClick={() => setActiveTab("content")}>
                          <Sparkles className="h-4 w-4 mr-2" />
                          View Content Opportunities
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </div>
            </Tabs>
          </TabsContent>

          {/* Content Tab */}
          <TabsContent value="content">
            <Tabs defaultValue="performance" className="space-y-6">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="performance">Performance</TabsTrigger>
                <TabsTrigger value="gap-analysis">Gap Analysis</TabsTrigger>
                <TabsTrigger value="optimization">Optimization</TabsTrigger>
                <TabsTrigger value="sge-readiness">SGE Readiness</TabsTrigger>
              </TabsList>
              
              <TabsContent value="performance">
                <ContentPerformanceOverview 
                  data={contentData?.data} 
                  isLoading={isContentLoading} 
                />
              </TabsContent>
              
              <TabsContent value="gap-analysis">
                <ContentGapAnalysis 
                  data={contentGapsData?.data} 
                  isLoading={isGapsLoading}
                  error={gapsError} 
                />
              </TabsContent>
              
              <TabsContent value="optimization">
                <ContentOptimization 
                  data={contentData?.data} 
                  isLoading={isContentLoading} 
                />
              </TabsContent>
              
              <TabsContent value="sge-readiness">
                <SGEReadiness 
                  data={sgeData?.data} 
                  isLoading={isSgeLoading} 
                />
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* Competitors Tab */}
          <TabsContent value="competitors">
            <Tabs defaultValue="overview" className="space-y-6">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="keyword-gap">Keyword Gap</TabsTrigger>
                <TabsTrigger value="serp-features">SERP Features</TabsTrigger>
                <TabsTrigger value="insights">Insights</TabsTrigger>
              </TabsList>
              
              <TabsContent value="overview">
                <CompetitorOverview 
                  data={serpData || { competitors: [], visibility_score: 0 }} 
                  isLoading={isSerpLoading} 
                />
              </TabsContent>
              
              <TabsContent value="keyword-gap">
                <KeywordGapAnalysis 
                  data={serpData || { keyword_gaps: [] }} 
                  isLoading={isSerpLoading} 
                />
              </TabsContent>
              
              <TabsContent value="serp-features">
                <SERPFeatures 
                  data={serpFeaturesData || serpData || { serp_features: [] }} 
                  isLoading={isSerpFeaturesLoading || isSerpLoading} 
                />
              </TabsContent>
              
              <TabsContent value="insights">
                <CompetitiveInsights 
                  data={serpData || { insights: [] }} 
                  isLoading={isSerpLoading} 
                />
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* Trends Tab */}
          <TabsContent value="trends">
            <Card>
              <CardHeader>
                <CardTitle>Google Trends Integration</CardTitle>
                <CardDescription>
                  Access Google Trends data to analyze search interest and trending topics
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="text-center">
                    <TrendingUp className="h-16 w-16 mx-auto text-primary mb-4" />
                    <h3 className="text-xl font-semibold mb-2">Analyze Search Trends</h3>
                    <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
                      Google Trends shows the popularity of search terms over time. Use it to understand 
                      seasonal patterns, compare keywords, discover rising topics, and analyze regional 
                      search interest to optimize your SEO strategy.
                    </p>
                  </div>
                  
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <h4 className="font-medium flex items-center gap-2">
                        <Search className="h-4 w-4" />
                        What you can discover:
                      </h4>
                      <ul className="space-y-2 text-sm text-muted-foreground">
                        <li>• Search volume trends over time</li>
                        <li>• Seasonal patterns and cycles</li>
                        <li>• Regional search interest</li>
                        <li>• Related queries and topics</li>
                        <li>• Rising and declining trends</li>
                        <li>• Keyword comparison data</li>
                      </ul>
                    </div>
                    
                    <div className="space-y-4">
                      <h4 className="font-medium flex items-center gap-2">
                        <Target className="h-4 w-4" />
                        Use cases for SEO:
                      </h4>
                      <ul className="space-y-2 text-sm text-muted-foreground">
                        <li>• Content planning and timing</li>
                        <li>• Keyword research and validation</li>
                        <li>• Market trend analysis</li>
                        <li>• Competitor research</li>
                        <li>• Campaign timing optimization</li>
                        <li>• Geographic targeting insights</li>
                      </ul>
                    </div>
                  </div>
                  
                  <div className="text-center pt-4">
                    <Button 
                      size="lg" 
                      onClick={() => window.open('https://trends.google.com', '_blank')}
                      className="mr-4"
                    >
                      <Globe className="h-4 w-4 mr-2" />
                      Open Google Trends
                    </Button>
                    <Button 
                      variant="outline" 
                      size="lg"
                      onClick={() => window.open('https://trends.google.com/trends/explore', '_blank')}
                    >
                      <BarChart3 className="h-4 w-4 mr-2" />
                      Explore Trends
                    </Button>
                  </div>
                  
                  <div className="bg-muted/50 rounded-lg p-4 mt-6">
                    <p className="text-sm text-muted-foreground">
                      <strong>Pro Tip:</strong> Use Google Trends alongside SerpTank's keyword analysis 
                      to identify trending topics in your niche and create timely, relevant content that 
                      captures search interest.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* AI Insights Modal */}
        <Dialog open={showAIInsights} onOpenChange={setShowAIInsights}>
          <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-primary" />
                AI Insights & Analytics
              </DialogTitle>
              <DialogDescription>
                Get AI-powered insights and recommendations based on your analytics data
              </DialogDescription>
            </DialogHeader>
            <AIInsightsPanel className="border-0 shadow-none" />
          </DialogContent>
        </Dialog>
        </div>
      </DashboardLayout>
  );
}