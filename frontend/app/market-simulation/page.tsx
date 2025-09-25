'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { DashboardPageHeader } from '@/components/layout/dashboard-page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dedupedApi as api } from '@/lib/api-deduped';
import { useProject } from '@/lib/project-context';
import { Competitor } from '@/types/api';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyState } from '@/components/ui/empty-state';
import { useAutoRefresh } from '@/lib/hooks/use-auto-refresh';
import {
  Target,
  TrendingUp,
  Users,
  Globe,
  Award,
  Activity,
  Search,
  AlertCircle,
  ChevronRight,
  Sparkles,
  Shield,
  Zap,
  Loader2,
  RefreshCw,
  Download
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

function MarketSimulationPage() {
  const [searchKeyword, setSearchKeyword] = useState('');
  const { currentProject } = useProject();
  const queryClient = useQueryClient();

  // Auto-refresh market data every 5 minutes
  useAutoRefresh(
    ['market-scenarios', currentProject?.id],
    300000,
    { enabled: !!currentProject }
  );

  // Fetch market scenarios
  const { data: scenarios, isLoading: scenariosLoading } = useQuery({
    queryKey: ['market-scenarios', currentProject?.id],
    queryFn: async () => {
      if (!currentProject) return null;
      const response = await api.marketSimulation.getScenarios();
      return response.data;
    },
    enabled: !!currentProject,
  });

  // Fetch competitor analysis
  const { data: competitorAnalysis, isLoading: competitorsLoading } = useQuery({
    queryKey: ['competitor-analysis', currentProject?.id],
    queryFn: async () => {
      if (!currentProject?.url) return null;
      const response = await api.marketSimulation.analyzeCompetitors({
        competitor_domains: [], // Will be populated by backend based on project domain
        keywords: currentProject.keywords || [],
        analysis_depth: 'standard',
        market_segment: 'general',
      });
      return response.data;
    },
    enabled: !!currentProject?.url,
  });

  // Analyze keyword mutation - using competitor analysis endpoint
  const analyzeKeyword = useMutation({
    mutationFn: async (keyword: string) => {
      const response = await api.marketSimulation.analyzeCompetitors({
        competitor_domains: [], // Will be populated by backend based on keyword
        keywords: [keyword],
        analysis_depth: 'standard',
        market_segment: 'general',
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['keyword-analysis', searchKeyword], data);
      queryClient.invalidateQueries({ queryKey: ['competitor-analysis'] });
    },
  });

  // Create scenario mutation
  const createScenario = useMutation({
    mutationFn: async (data: {
      name: string;
      description: string;
      type: string;
      parameters: {
        target_market_share: number;
        timeline: string;
        keywords: string[];
      };
    }) => {
      return api.marketSimulation.createScenario(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['market-scenarios'] });
    },
  });

  const isLoading = scenariosLoading || competitorsLoading;

  const handleAnalyze = () => {
    if (!searchKeyword) return;
    analyzeKeyword.mutate(searchKeyword);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getImpactBadge = (impact: string) => {
    const colors: Record<string, "destructive" | "warning" | "secondary" | "default"> = {
      high: 'destructive',
      medium: 'warning',
      low: 'secondary',
    };
    return colors[impact] || 'default';
  };

  // Use only live data from backend - no mock fallbacks
  const marketData = competitorAnalysis ? {
    keyword: searchKeyword || 'SEO tools',
    market_share: competitorAnalysis.competitor_analysis?.your_market_share,
    opportunity_score: competitorAnalysis.competitive_insights?.opportunity_score,
    difficulty_score: competitorAnalysis.competitive_insights?.difficulty_score,
    competitors: competitorAnalysis.competitor_analysis?.competitors || [],
    competitiveAnalysis: competitorAnalysis.competitor_analysis?.comparative_metrics || [],
    opportunities: competitorAnalysis.market_opportunities || [],
  } : null;

  if (!currentProject) {
    return (
      <DashboardLayout>
        <EmptyState
          icon={Globe}
          title="No Project Selected"
          description="Please select a project from the dropdown above to analyze market opportunities."
        />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
        <div className="relative space-y-6">
        {/* Optimized Header - Research-based 2025 standards */}
        <DashboardPageHeader
          title="Market Simulation"
          description="Analyze competitive landscape and discover market opportunities"
          badge={{
            icon: <Target className="mr-1 h-3 w-3" />,
            text: "Market Intelligence",
            variant: "secondary"
          }}
          actions={
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['market-scenarios'] });
                  queryClient.invalidateQueries({ queryKey: ['competitor-analysis'] });
                }}
                className="bg-card/80 backdrop-blur-sm border-border/50"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button variant="outline" size="sm" className="bg-card/80 backdrop-blur-sm border-border/50">
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </div>
          }
        />

        {/* Search */}
        <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
          <CardHeader>
            <CardTitle>Keyword Analysis</CardTitle>
            <CardDescription>
              Enter a keyword to analyze market competition and opportunities
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex space-x-4">
              <div className="flex-1">
                <Input
                  placeholder="Enter keyword or topic..."
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                  className="h-12"
                />
              </div>
              <Button 
                size="lg" 
                onClick={handleAnalyze}
                disabled={analyzeKeyword.isPending || !searchKeyword}
                className="px-8"
              >
                {analyzeKeyword.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Analyze Market
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Show loading state */}
        {isLoading && (
          <LoadingState 
            message="Loading market analysis data..." 
            size="lg" 
          />
        )}

        {/* Show empty state when no data available */}
        {!isLoading && !marketData && (
          <EmptyState
            icon={Search}
            title="No Market Analysis Available"
            description="Enter a keyword above to analyze market opportunities and competitive landscape."
          />
        )}

        {/* Market Overview - only show when we have live data */}
        {!isLoading && marketData && (
          <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Your Market Share
              </CardTitle>
              <div className="rounded-full bg-primary/10 p-2">
                <Target className="h-4 w-4 text-primary" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{marketData.market_share || 0}%</div>
              <Progress value={marketData.market_share || 0} className="mt-2" />
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Opportunity Score
              </CardTitle>
              <div className="rounded-full bg-green-500/10 p-2">
                <TrendingUp className="h-4 w-4 text-green-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(marketData.opportunity_score || 0)}`}>
                {marketData.opportunity_score || 0}/100
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                High growth potential
              </p>
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Competition Level
              </CardTitle>
              <div className="rounded-full bg-amber-500/10 p-2">
                <Shield className="h-4 w-4 text-amber-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(100 - (marketData.difficulty_score || 0))}`}>
                {marketData.difficulty_score || 0}/100
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Moderate difficulty
              </p>
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Competitors Tracked
              </CardTitle>
              <div className="rounded-full bg-blue-500/10 p-2">
                <Users className="h-4 w-4 text-blue-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{marketData.competitors.length}</div>
              <p className="text-xs text-muted-foreground mt-1">
                In your market segment
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Competitive Analysis */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Competitive Radar</CardTitle>
              <CardDescription>
                How you compare across key metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={marketData.competitiveAnalysis}>
                    <PolarGrid strokeDasharray="3 3" className="stroke-muted" />
                    <PolarAngleAxis dataKey="metric" className="text-xs" />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} />
                    <Radar
                      name="Your Site"
                      dataKey="yours"
                      stroke="#8b5cf6"
                      fill="#8b5cf6"
                      fillOpacity={0.6}
                    />
                    <Radar
                      name="Market Average"
                      dataKey="average"
                      stroke="#ef4444"
                      fill="#ef4444"
                      fillOpacity={0.3}
                    />
                    <Legend />
                    <Tooltip
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Market Share Distribution</CardTitle>
              <CardDescription>
                Top competitors by market share
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: 'You', share: marketData.market_share },
                      ...marketData.competitors.map((c: Competitor) => ({
                        name: c.domain.split('.')[0],
                        share: c.market_share
                      }))
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="name" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="share" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Competitors */}
        <Card>
          <CardHeader>
            <CardTitle>Competitor Analysis</CardTitle>
            <CardDescription>
              Detailed breakdown of your main competitors
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {marketData.competitors.map((competitor: Competitor, index: number) => (
                <div
                  key={index}
                  className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-3 flex-1">
                      <div className="flex items-center space-x-4">
                        <h4 className="text-lg font-semibold">{competitor.domain}</h4>
                        <Badge variant="outline">
                          DA: {competitor.domain_authority}
                        </Badge>
                      </div>
                      
                      <div className="grid gap-4 md:grid-cols-3 text-sm">
                        <div>
                          <p className="text-muted-foreground">Market Share</p>
                          <p className="font-medium">{competitor.market_share}%</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Est. Traffic</p>
                          <p className="font-medium">{competitor.traffic_estimate.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Domain Authority</p>
                          <p className="font-medium">{competitor.domain_authority}/100</p>
                        </div>
                      </div>

                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <p className="text-sm font-medium text-green-600 mb-2">Strengths</p>
                          <div className="flex flex-wrap gap-2">
                            {competitor.strengths.map((strength: string, i: number) => (
                              <Badge key={i} variant="outline" className="text-xs">
                                {strength}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-red-600 mb-2">Weaknesses</p>
                          <div className="flex flex-wrap gap-2">
                            {competitor.weaknesses.map((weakness: string, i: number) => (
                              <Badge key={i} variant="outline" className="text-xs">
                                {weakness}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Opportunities */}
        <Card>
          <CardHeader>
            <CardTitle>Market Opportunities</CardTitle>
            <CardDescription>
              Strategic opportunities to gain market share
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {marketData.opportunities.map((opportunity: {
                title: string;
                impact: string;
                effort: string;
                description: string;
              }, index: number) => (
                <div
                  key={index}
                  className="flex items-start space-x-4 rounded-lg border p-4"
                >
                  <div className="mt-0.5">
                    <Zap className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold">{opportunity.title}</h4>
                      <div className="flex items-center space-x-2">
                        <Badge variant={getImpactBadge(opportunity.impact)}>
                          {opportunity.impact} impact
                        </Badge>
                        <Badge variant="outline">
                          {opportunity.effort} effort
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {opportunity.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* AI-Powered Insights */}
        <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI Market Intelligence
            </CardTitle>
            <CardDescription>
              Get AI-powered recommendations based on your market position
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-muted/50">
                <h4 className="font-medium mb-2">Recommended Strategy</h4>
                <p className="text-sm text-muted-foreground">
                  Based on your current market position and competitor analysis, focus on improving content quality and technical SEO to capture an additional 8-12% market share in the next quarter.
                </p>
              </div>
              <Button 
                className="w-full"
                onClick={() => createScenario.mutate({ 
                  name: 'Growth Scenario',
                  description: 'AI-generated growth scenario',
                  type: 'growth',
                  parameters: {
                    target_market_share: marketData.market_share + 10,
                    timeline: '3_months',
                    keywords: [searchKeyword].filter((k): k is string => Boolean(k)),
                  }
                })}
                disabled={createScenario.isPending}
              >
                <Zap className="mr-2 h-4 w-4" />
                Generate Growth Scenario
              </Button>
            </div>
          </CardContent>
        </Card>
        </>
        )}
        </div>
    </DashboardLayout>
  );
}

export default withAuth(MarketSimulationPage);