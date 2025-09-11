'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DetailLayout } from '@/components/layout/detail-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  FileText,
  TrendingUp,
  TrendingDown,
  Target,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Download,
  Plus,
  Edit,
  Eye,
  Star,
  BarChart3,
  BookOpen,
  Zap,
  MessageSquare,
  Brain,
  Search,
  ArrowRight
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { formatNumber, cn } from '@/lib/utils';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart, RadialBarChart, RadialBar, PieChart, Pie, Cell } from 'recharts';
import { useToast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import { EntityModal } from '@/components/ui/entity-modal';

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

  // Mock data for content metrics
  const metrics = {
    total_pages: 156,
    optimized_pages: 89,
    avg_content_score: 78,
    traffic_from_content: 45230,
    pages_change: 12,
    optimization_rate: 57,
    score_change: 5,
    traffic_change: 18.5
  };

  const performanceTrend = Array.from({ length: 12 }, (_, i) => ({
    month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i],
    traffic: Math.floor(Math.random() * 10000) + 35000,
    conversions: Math.floor(Math.random() * 500) + 200,
    score: Math.floor(Math.random() * 20) + 70
  }));

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
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

      {/* Performance Chart */}
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

      {/* Top Performing Content */}
      <Card>
        <CardHeader>
          <CardTitle>Top Performing Content</CardTitle>
          <CardDescription>
            Your best performing pages by traffic and engagement
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { title: 'Complete SEO Guide 2024', traffic: 12450, score: 95, trend: 'up' },
              { title: 'Technical SEO Checklist', traffic: 9870, score: 92, trend: 'up' },
              { title: 'Local SEO Strategy Guide', traffic: 8230, score: 88, trend: 'stable' },
              { title: 'Content Optimization Tips', traffic: 7560, score: 85, trend: 'down' },
              { title: 'Link Building Strategies', traffic: 6890, score: 82, trend: 'up' },
            ].map((page, index) => (
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
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Component for content gap analysis
function ContentGapAnalysis({ data, isLoading }: { data: any; isLoading: boolean }) {
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

  const contentGaps = [
    {
      topic: 'Voice Search Optimization',
      search_volume: 8900,
      difficulty: 45,
      opportunity_score: 92,
      competitors_covering: 3,
      suggested_format: 'Comprehensive Guide',
    },
    {
      topic: 'AI in SEO Strategy',
      search_volume: 12300,
      difficulty: 68,
      opportunity_score: 88,
      competitors_covering: 5,
      suggested_format: 'Research Report',
    },
    {
      topic: 'E-commerce SEO Checklist',
      search_volume: 6700,
      difficulty: 38,
      opportunity_score: 85,
      competitors_covering: 2,
      suggested_format: 'Interactive Checklist',
    },
    {
      topic: 'International SEO Guide',
      search_volume: 4500,
      difficulty: 52,
      opportunity_score: 78,
      competitors_covering: 4,
      suggested_format: 'Step-by-Step Tutorial',
    },
    {
      topic: 'SEO for SaaS Companies',
      search_volume: 3200,
      difficulty: 41,
      opportunity_score: 75,
      competitors_covering: 2,
      suggested_format: 'Case Study',
    },
  ];

  const getOpportunityColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="space-y-6">
      {/* Content Gaps */}
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
            {contentGaps.map((gap, index) => (
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
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Topic Clusters */}
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

      {/* Create Brief Modal */}
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

  const optimizationTasks = [
    {
      page: '/blog/seo-guide-2024',
      title: 'Complete SEO Guide 2024',
      current_score: 72,
      potential_score: 95,
      issues: ['Missing schema markup', 'Thin content sections', 'No FAQ section'],
      priority: 'high',
      estimated_impact: '+2,500 monthly visits',
    },
    {
      page: '/resources/keyword-research',
      title: 'Keyword Research Tutorial',
      current_score: 68,
      potential_score: 88,
      issues: ['Outdated examples', 'Missing video content', 'Poor internal linking'],
      priority: 'medium',
      estimated_impact: '+1,200 monthly visits',
    },
    {
      page: '/tools/rank-tracker',
      title: 'Rank Tracker Tool Page',
      current_score: 75,
      potential_score: 90,
      issues: ['No social proof', 'Missing comparison table', 'Weak CTA'],
      priority: 'medium',
      estimated_impact: '+800 monthly visits',
    },
    {
      page: '/case-studies/ecommerce-seo',
      title: 'E-commerce SEO Case Study',
      current_score: 82,
      potential_score: 94,
      issues: ['No data visualizations', 'Missing methodology section'],
      priority: 'low',
      estimated_impact: '+500 monthly visits',
    },
  ];

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
      {/* Optimization Opportunities */}
      <Card>
        <CardHeader>
          <CardTitle>Content Optimization Queue</CardTitle>
          <CardDescription>
            Pages with the highest optimization potential
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {optimizationTasks.map((task, index) => (
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
                    {task.issues.map((issue, i) => (
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
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Optimization Tips */}
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

  const sgeMetrics = {
    overall_readiness: 72,
    conversational_content: 65,
    structured_data: 88,
    entity_coverage: 78,
    citation_worthy: 45,
  };

  const conversationalGaps = [
    { question: 'What is the best SEO strategy for small businesses?', status: 'missing', priority: 'high' },
    { question: 'How do I improve my website loading speed?', status: 'partial', priority: 'medium' },
    { question: 'What are the latest Google algorithm updates?', status: 'covered', priority: 'low' },
    { question: 'How to do keyword research for local SEO?', status: 'missing', priority: 'high' },
    { question: 'What is the difference between SEO and SEM?', status: 'covered', priority: 'low' },
  ];

  return (
    <div className="space-y-6">
      {/* SGE Readiness Score */}
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

      {/* Conversational Gaps */}
      <Card>
        <CardHeader>
          <CardTitle>Conversational Content Gaps</CardTitle>
          <CardDescription>
            Questions your content should answer for SGE
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {conversationalGaps.map((gap, index) => (
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
            ))}
          </div>
        </CardContent>
      </Card>

      {/* SGE Optimization Tips */}
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

function ContentAnalyticsPage() {
  const { currentProject } = useProject();
  const { toast } = useToast();

  // Fetch content performance data
  const { data: performanceData, isLoading, refetch } = useQuery({
    queryKey: ['content-performance', currentProject?.id],
    queryFn: async () => {
      if (!currentProject?.id) return null;
      const response = await api.contentWorkflow.getPerformanceTracking();
      return response.data;
    },
    enabled: !!currentProject?.id,
  });

  const mockData = {};
  const data = performanceData || mockData;

  if (!currentProject) {
    return (
      <DetailLayout
        title="Content Analytics"
        breadcrumbs={[
          { label: 'Analytics', href: '/analytics' },
          { label: 'Content' },
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
                    Please select a project from the dropdown above to view content analytics.
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
      id: 'performance',
      label: 'Performance',
      icon: BarChart3,
      content: <ContentPerformanceOverview data={data} isLoading={isLoading} />,
    },
    {
      id: 'gap-analysis',
      label: 'Gap Analysis',
      icon: Search,
      content: <ContentGapAnalysis data={data} isLoading={isLoading} />,
    },
    {
      id: 'optimization',
      label: 'Optimization',
      icon: Zap,
      content: <ContentOptimization data={data} isLoading={isLoading} />,
    },
    {
      id: 'sge-readiness',
      label: 'SGE Readiness',
      icon: Brain,
      content: <SGEReadiness data={data} isLoading={isLoading} />,
    },
  ];

  return (
    <DetailLayout
      title="Content Analytics"
      breadcrumbs={[
        { label: 'Analytics', href: '/analytics' },
        { label: 'Content' },
      ]}
      actions={[
        {
          label: 'Refresh Data',
          onClick: () => refetch(),
          icon: RefreshCw,
        },
        {
          label: 'Create Brief',
          onClick: () => {
            toast({
              title: 'Opening brief creator',
              description: 'Create a new content brief based on analytics.',
            });
          },
          icon: Plus,
        },
        {
          label: 'Export Report',
          onClick: () => {
            toast({
              title: 'Export started',
              description: 'Your content analytics report is being generated.',
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
          icon: BookOpen,
        },
        {
          label: 'Analyzing',
          value: `${currentProject.name} content`,
        },
      ]}
    />
  );
}

export default withAuth(ContentAnalyticsPage);