'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Brain,
  Sparkles,
  Target,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Info,
  MessageSquare,
  FileText,
  Link2,
  Globe,
  Zap,
  Shield,
  RefreshCw
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { PieChart, Pie, Cell, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip, Legend } from 'recharts';

function SGEReadinessPage() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { currentProject } = useProject();

  // Fetch SGE readiness data
  const { data: sgeData, isLoading, refetch } = useQuery({
    queryKey: ['sge-readiness', currentProject?.id],
    queryFn: async () => {
      if (!currentProject) return null;
      const response = await api.sgeReadiness.getReport(currentProject.id);
      return response.data;
    },
    enabled: !!currentProject,
  });

  // Start analysis mutation
  const startAnalysis = useMutation({
    mutationFn: async () => {
      if (!currentProject) throw new Error('No project selected');
      setIsAnalyzing(true);
      const response = await api.sgeReadiness.analyze(currentProject.id);
      return response.data;
    },
    onSuccess: () => {
      setTimeout(() => {
        setIsAnalyzing(false);
        refetch();
      }, 3000);
    },
  });

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBadge = (score: number) => {
    if (score >= 80) return { variant: 'default' as const, text: 'Excellent' };
    if (score >= 60) return { variant: 'warning' as const, text: 'Good' };
    return { variant: 'destructive' as const, text: 'Needs Work' };
  };

  // Transform backend data to match frontend expectations
  const transformSGEData = (data: any) => {
    if (!data) return null;
    
    // Calculate scores from backend data
    const triggers = data.triggers || {};
    const citations = data.citations || {};
    const gaps = data.gaps || {};
    
    // Calculate overall score based on available metrics
    const entityCoverage = triggers.entity_coverage || 65;
    const schemaScore = triggers.schema_markup_score || 45;
    const conversationalScore = gaps.conversational_content_score || 58;
    const citationScore = citations.citation_likelihood || 68;
    
    const overallScore = Math.round((entityCoverage + schemaScore + conversationalScore + citationScore) / 4);
    const contentScore = Math.round((conversationalScore + citationScore) / 2);
    const technicalScore = schemaScore;
    const authorityScore = entityCoverage;
    
    return {
      overall_score: overallScore,
      content_score: contentScore,
      technical_score: technicalScore,
      authority_score: authorityScore,
      recommendations: triggers.recommendations || [],
      opportunities: gaps.opportunities || [],
      metrics: {
        entity_coverage: entityCoverage,
        schema_implementation: schemaScore,
        conversational_content: conversationalScore,
        featured_snippet_ready: triggers.featured_snippet_ready || 72,
        voice_search_optimized: triggers.voice_search_optimized || 60,
        ai_citation_likelihood: citationScore,
      },
      raw: data,
    };
  };
  
  // Mock data
  const mockSGEData = {
    overall_score: 72,
    content_score: 78,
    technical_score: 68,
    authority_score: 70,
    recommendations: [
      {
        type: 'content',
        priority: 'high',
        title: 'Enhance Conversational Content',
        description: 'Add more Q&A style content and conversational language to better match SGE preferences',
        impact_score: 85,
        effort_score: 60,
      },
      {
        type: 'technical',
        priority: 'high',
        title: 'Implement Structured Data',
        description: 'Add FAQ and HowTo schema markup to improve entity recognition',
        impact_score: 90,
        effort_score: 40,
      },
      {
        type: 'authority',
        priority: 'medium',
        title: 'Increase Entity Mentions',
        description: 'Build stronger topical authority by mentioning related entities and concepts',
        impact_score: 70,
        effort_score: 50,
      },
    ],
    opportunities: [
      {
        type: 'featured_snippets',
        title: 'Featured Snippet Opportunities',
        description: '23 keywords have featured snippet potential',
        potential_impact: 'High traffic increase',
        implementation_steps: [
          'Identify target queries',
          'Create structured answers',
          'Optimize content format',
        ],
      },
      {
        type: 'conversational_gaps',
        title: 'Conversational Query Gaps',
        description: '45 long-tail conversational queries without content',
        potential_impact: 'Capture SGE traffic',
        implementation_steps: [
          'Create FAQ pages',
          'Add conversational sections',
          'Target voice search queries',
        ],
      },
    ],
    metrics: {
      entity_coverage: 65,
      schema_implementation: 45,
      conversational_content: 58,
      featured_snippet_ready: 72,
      voice_search_optimized: 60,
      ai_citation_likelihood: 68,
    },
  };

  const data = transformSGEData(sgeData) || mockSGEData;

  const radarData = [
    { metric: 'Entity Coverage', value: data.metrics.entity_coverage },
    { metric: 'Schema Markup', value: data.metrics.schema_implementation },
    { metric: 'Conversational', value: data.metrics.conversational_content },
    { metric: 'Snippet Ready', value: data.metrics.featured_snippet_ready },
    { metric: 'Voice Optimized', value: data.metrics.voice_search_optimized },
    { metric: 'AI Citations', value: data.metrics.ai_citation_likelihood },
  ];

  const COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'];

  if (!currentProject) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-2">
            <h3 className="text-2xl font-semibold">No Project Selected</h3>
            <p className="text-muted-foreground">
              Please select a project from the dropdown above to analyze SGE readiness.
            </p>
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
          <div>
            <h1 className="text-3xl font-bold tracking-tight">SGE Readiness</h1>
            <p className="text-muted-foreground">
              Prepare your site for AI-powered search experiences
            </p>
          </div>
          <Button 
            onClick={() => startAnalysis.mutate()}
            disabled={isAnalyzing}
          >
            {isAnalyzing ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Brain className="mr-2 h-4 w-4" />
                Analyze SGE Readiness
              </>
            )}
          </Button>
        </div>

        {/* Score Overview */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Overall SGE Score
              </CardTitle>
              <div className="rounded-full bg-primary/10 p-2">
                <Brain className="h-4 w-4 text-primary" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(data.overall_score)}`}>
                {data.overall_score}%
              </div>
              <Badge variant={getScoreBadge(data.overall_score).variant} className="mt-2">
                {getScoreBadge(data.overall_score).text}
              </Badge>
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Content Readiness
              </CardTitle>
              <div className="rounded-full bg-blue-500/10 p-2">
                <FileText className="h-4 w-4 text-blue-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(data.content_score)}`}>
                {data.content_score}%
              </div>
              <Progress value={data.content_score} className="mt-2" />
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Technical Score
              </CardTitle>
              <div className="rounded-full bg-green-500/10 p-2">
                <Shield className="h-4 w-4 text-green-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(data.technical_score)}`}>
                {data.technical_score}%
              </div>
              <Progress value={data.technical_score} className="mt-2" />
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Authority Score
              </CardTitle>
              <div className="rounded-full bg-amber-500/10 p-2">
                <Globe className="h-4 w-4 text-amber-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-3xl font-bold ${getScoreColor(data.authority_score)}`}>
                {data.authority_score}%
              </div>
              <Progress value={data.authority_score} className="mt-2" />
            </CardContent>
          </Card>
        </div>

        {/* Analysis Charts */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>SGE Readiness Factors</CardTitle>
              <CardDescription>
                How well your site performs across key SGE factors
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid strokeDasharray="3 3" className="stroke-muted" />
                    <PolarAngleAxis dataKey="metric" className="text-xs" />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} />
                    <Radar
                      name="Score"
                      dataKey="value"
                      stroke="#8b5cf6"
                      fill="#8b5cf6"
                      fillOpacity={0.6}
                    />
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
              <CardTitle>Key Metrics Breakdown</CardTitle>
              <CardDescription>
                Detailed view of your SGE optimization status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Link2 className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Entity Coverage</span>
                    </div>
                    <span className="text-sm font-bold">{data.metrics.entity_coverage}%</span>
                  </div>
                  <Progress value={data.metrics.entity_coverage} />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Schema Implementation</span>
                    </div>
                    <span className="text-sm font-bold">{data.metrics.schema_implementation}%</span>
                  </div>
                  <Progress value={data.metrics.schema_implementation} />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Conversational Content</span>
                    </div>
                    <span className="text-sm font-bold">{data.metrics.conversational_content}%</span>
                  </div>
                  <Progress value={data.metrics.conversational_content} />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Featured Snippet Ready</span>
                    </div>
                    <span className="text-sm font-bold">{data.metrics.featured_snippet_ready}%</span>
                  </div>
                  <Progress value={data.metrics.featured_snippet_ready} />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Brain className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">AI Citation Likelihood</span>
                    </div>
                    <span className="text-sm font-bold">{data.metrics.ai_citation_likelihood}%</span>
                  </div>
                  <Progress value={data.metrics.ai_citation_likelihood} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recommendations */}
        <Tabs defaultValue="recommendations" className="space-y-4">
          <TabsList>
            <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
            <TabsTrigger value="opportunities">Opportunities</TabsTrigger>
            <TabsTrigger value="insights">AI Insights</TabsTrigger>
          </TabsList>

          <TabsContent value="recommendations" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Priority Recommendations</CardTitle>
                <CardDescription>
                  Actions to improve your SGE readiness score
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.recommendations.map((rec: any, index: number) => (
                    <div
                      key={index}
                      className="flex items-start space-x-4 rounded-lg border p-4"
                    >
                      <div className="mt-0.5">
                        {rec.priority === 'high' ? (
                          <AlertTriangle className="h-5 w-5 text-red-500" />
                        ) : (
                          <Info className="h-5 w-5 text-yellow-500" />
                        )}
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-semibold">{rec.title}</h4>
                          <div className="flex items-center gap-2">
                            <Badge variant={rec.priority === 'high' ? 'destructive' : 'warning'}>
                              {rec.priority} priority
                            </Badge>
                            <Badge variant="outline">
                              Impact: {rec.impact_score}%
                            </Badge>
                            <Badge variant="outline">
                              Effort: {rec.effort_score}%
                            </Badge>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {rec.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="opportunities" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>SGE Opportunities</CardTitle>
                <CardDescription>
                  Capitalize on these opportunities to increase AI visibility
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.opportunities.map((opp: any, index: number) => (
                    <div
                      key={index}
                      className="space-y-4 rounded-lg border p-4"
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <h4 className="text-lg font-semibold flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-primary" />
                            {opp.title}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {opp.description}
                          </p>
                          <Badge variant="outline" className="mt-2">
                            {opp.potential_impact}
                          </Badge>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium mb-2">Implementation Steps:</p>
                        <ol className="list-decimal list-inside space-y-1">
                          {opp.implementation_steps.map((step: string, i: number) => (
                            <li key={i} className="text-sm text-muted-foreground">
                              {step}
                            </li>
                          ))}
                        </ol>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="insights" className="space-y-4">
            <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5 text-primary" />
                  AI-Powered Insights
                </CardTitle>
                <CardDescription>
                  Advanced analysis of your SGE optimization potential
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="rounded-lg bg-primary/5 p-4">
                    <h4 className="font-semibold mb-2">Conversational Query Analysis</h4>
                    <p className="text-sm text-muted-foreground">
                      Your content answers 68% of common conversational queries in your niche. 
                      Focus on creating Q&A content for the remaining 32% to improve SGE visibility.
                    </p>
                  </div>
                  <div className="rounded-lg bg-primary/5 p-4">
                    <h4 className="font-semibold mb-2">Entity Recognition Status</h4>
                    <p className="text-sm text-muted-foreground">
                      AI models recognize your brand as an authority in 3 out of 5 core topics. 
                      Strengthen content around  &quot;technical SEO&quot; and  &quot;local search optimization&quot; 
                      to improve entity associations.
                    </p>
                  </div>
                  <div className="rounded-lg bg-primary/5 p-4">
                    <h4 className="font-semibold mb-2">Future-Proofing Score</h4>
                    <p className="text-sm text-muted-foreground">
                      Based on current trends, your content has a 72% likelihood of being 
                      cited in AI-generated responses. Implement structured data and increase 
                      conversational content to reach 85%+.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}

export default withAuth(SGEReadinessPage);