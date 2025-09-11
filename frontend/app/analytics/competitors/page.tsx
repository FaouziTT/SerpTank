'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DetailLayout } from '@/components/layout/detail-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { 
  Search,
  TrendingUp,
  TrendingDown,
  Target,
  Eye,
  RefreshCw,
  Download,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  AlertCircle,
  CheckCircle,
  Users,
  BarChart3,
  Globe,
  Zap,
  Shield,
  Star
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { formatNumber, cn } from '@/lib/utils';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ScatterChart, Scatter } from 'recharts';
import { useToast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import { EntityModal } from '@/components/ui/entity-modal';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

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

  // Get keyword gaps from API data - use empty array if no data
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
      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Keyword Gap Analysis</CardTitle>
              <CardDescription>
                {/* CHANGE: Escaped the apostrophe */}
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
              {keywordGaps.map((gap, index) => (
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

      {/* Opportunity Chart */}
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

  // Get SERP features from API data - use empty array if no data
  const serpFeatures = data?.serp_features || [];

  const radarData = serpFeatures.map(f => ({
    feature: f.feature,
    you: f.you,
    competitors: f.competitors
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        {/* SERP Features Comparison */}
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

        {/* SERP Feature Opportunities */}
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
                {serpFeatures.map((feature, index) => (
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

      {/* Feature Recommendations */}
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

  // Get insights from API data - use empty array if no data
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
      {/* Insights List */}
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
              {insights.map((insight, index) => (
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

      {/* Competitive Strategy */}
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

function CompetitorsAnalyticsPage() {
  const [selectedTimeframe, setSelectedTimeframe] = useState('30d');
  const { currentProject } = useProject();
  const { toast } = useToast();

  // Fetch competitors data
  const { data: competitorsData, isLoading, refetch } = useQuery({
    queryKey: ['competitors', currentProject?.id, selectedTimeframe],
    queryFn: async () => {
      if (!currentProject?.id) return null;
      try {
        const response = await api.serpAnalysis.getCompetitors();
        return response?.data || null;
      } catch (error) {
        console.error('Error fetching competitors data:', error);
        return null;
      }
    },
    enabled: !!currentProject?.id,
  });

  // Use only live API data - no mock fallbacks
  const data = competitorsData || { competitors: [], visibility_score: 0 };

  if (!currentProject) {
    return (
      <DetailLayout
        title="Competitor Analysis"
        breadcrumbs={[
          { label: 'Analytics', href: '/analytics' },
          { label: 'Competitors' },
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
                    Please select a project from the dropdown above to view competitor analysis.
                  </p>
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
      content: <CompetitorOverview data={data} isLoading={isLoading} />,
    },
    {
      id: 'keyword-gap',
      label: 'Keyword Gap',
      icon: Search,
      content: <KeywordGapAnalysis data={data} isLoading={isLoading} />,
    },
    {
      id: 'serp-features',
      label: 'SERP Features',
      icon: Zap,
      content: <SERPFeatures data={data} isLoading={isLoading} />,
    },
    {
      id: 'insights',
      label: 'Insights',
      icon: Target,
      content: <CompetitiveInsights data={data} isLoading={isLoading} />,
    },
  ];

  return (
    <DetailLayout
      title="Competitor Analysis"
      breadcrumbs={[
        { label: 'Analytics', href: '/analytics' },
        { label: 'Competitors' },
      ]}
      actions={[
        {
          label: 'Refresh Data',
          onClick: () => refetch(),
          icon: RefreshCw,
        },
        {
          label: 'Export Report',
          onClick: () => {
            toast({
              title: 'Export started',
              description: 'Your competitor analysis report is being generated.',
            });
          },
          icon: Download,
        },
      ]}
      tabs={tabs}
      metadata={[
        {
          label: 'Status',
          value: 'Active',
          icon: Users,
        },
        {
          label: 'Tracking',
          value: `${data?.competitors?.length || 0} competitors`,
        },
        {
          label: 'Timeframe',
          value: (
            <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
              <SelectTrigger className="w-[140px] h-7">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 Days</SelectItem>
                <SelectItem value="30d">Last 30 Days</SelectItem>
                <SelectItem value="90d">Last 90 Days</SelectItem>
                <SelectItem value="180d">Last 6 Months</SelectItem>
              </SelectContent>
            </Select>
          ),
        },
      ]}
    />
  );
}

export default withAuth(CompetitorsAnalyticsPage);