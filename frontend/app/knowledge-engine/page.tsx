'use client';

import { useState } from 'react';

// Types for Knowledge Engine data structures
interface KnowledgeEntry {
  id?: string;
  entry_id?: string;
  title?: string;
  name?: string;
  category?: string;
  type?: string;
  content?: string;
  description?: string;
  tags?: string[];
  insights?: string[] | Array<{ description?: string; content?: string }>;
  key_insights?: string[] | Array<{ description?: string; content?: string }>;
  created_at?: string;
}

interface KnowledgeCategory {
  name: string;
  count: number;
}

interface OptimizationOpportunity {
  title?: string;
  description?: string;
  content?: string;
}

interface LearningInsight {
  description?: string;
  content?: string;
}

interface IntelligenceData {
  entries?: KnowledgeEntry[];
  knowledge_connections?: KnowledgeEntry[];
  strategic_ledger?: { entries: KnowledgeEntry[] };
  summary?: {
    total_entries?: number;
    categories?: Record<string, number>;
  };
  learning_insights?: Record<string, LearningInsight | string>;
}

interface RecommendationsData {
  recommendations?: Array<any>;
  length?: number;
}

interface AnalyticsData {
  category_distribution?: Record<string, number>;
  total_insights?: number;
  insights_count?: number;
  learning_metrics?: {
    total_insights?: number;
  };
  performance_metrics?: {
    learning_effectiveness?: number;
  };
  learning_score?: number;
  model_effectiveness?: {
    user_satisfaction?: number;
  };
  optimization_opportunities?: OptimizationOpportunity[];
}
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { DashboardPageHeader } from '@/components/layout/dashboard-page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  BookOpen,
  Search,
  Plus,
  Tag,
  Calendar,
  User,
  Link2,
  Brain,
  Lightbulb,
  History,
  TrendingUp,
  FileText,
  MessageSquare,
  Sparkles,
  Share2,
  Download,
  Filter,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { motion } from 'framer-motion';
import { dedupedApi as api } from '@/lib/api-deduped';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { formatDate } from '@/lib/utils';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyState } from '@/components/ui/empty-state';
import { useAutoRefresh } from '@/lib/hooks/use-auto-refresh';

// Type guards for data validation
const isValidKnowledgeEntry = (entry: any): entry is KnowledgeEntry => {
  return entry && (entry.id || entry.entry_id) && (entry.title || entry.name);
};

const isValidOptimizationOpportunity = (opportunity: any): opportunity is OptimizationOpportunity => {
  return opportunity && (opportunity.title || opportunity.description || opportunity.content);
};

function KnowledgeEnginePage() {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [generateTopic, setGenerateTopic] = useState<string>('');
  const { currentProject } = useProject();
  const queryClient = useQueryClient();

  // Auto-refresh intelligence data every 10 minutes
  useAutoRefresh(
    ['competitive-intelligence'],
    600000,
    { enabled: !!currentProject }
  );

  // Fetch competitive intelligence
  const { data: intelligence, isLoading: intelligenceLoading } = useQuery<IntelligenceData | null>({
    queryKey: ['competitive-intelligence'],
    queryFn: async (): Promise<IntelligenceData | null> => {
      try {
        // Use project domain as default competitor domain for analysis
        const defaultDomains = currentProject?.domain ? [currentProject.domain] : ['example.com'];
        const response = await api.knowledgeEngine.getCompetitiveIntelligence(defaultDomains);
        return response.data as IntelligenceData;
      } catch (error) {
        console.error('Failed to fetch competitive intelligence:', error);
        return null;
      }
    },
    enabled: !!currentProject,
  });

  // Fetch personalized recommendations
  const { data: recommendations, isLoading: recommendationsLoading } = useQuery<RecommendationsData | null>({
    queryKey: ['personalized-recommendations'],
    queryFn: async (): Promise<RecommendationsData | null> => {
      try {
        const response = await api.knowledgeEngine.getPersonalizedRecommendations();
        return response.data as RecommendationsData;
      } catch (error) {
        console.error('Failed to fetch recommendations:', error);
        return null;
      }
    },
    enabled: !!currentProject,
  });

  // Fetch learning analytics
  const { data: analytics, isLoading: analyticsLoading } = useQuery<AnalyticsData | null>({
    queryKey: ['learning-analytics'],
    queryFn: async (): Promise<AnalyticsData | null> => {
      try {
        const response = await api.knowledgeEngine.getLearningAnalytics();
        return response.data as AnalyticsData;
      } catch (error) {
        console.error('Failed to fetch learning analytics:', error);
        return null;
      }
    },
    enabled: !!currentProject,
  });

  // Generate intelligence mutation
  const generateIntelligence = useMutation<any, Error, string>({
    mutationFn: async (topic: string) => {
      // Transform frontend request to match backend expectations
      const response = await api.knowledgeEngine.generateIntelligence({
        analysis_type: 'strategic',
        data_sources: ['competitive', 'market', 'performance'],
        focus_areas: [topic],
        time_horizon: 'quarterly',
        include_predictions: true,
        learning_mode: true,
      });
      return response.data;
    },
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['competitive-intelligence'] });
      setGenerateTopic('');
    },
  });

  // Knowledge synthesis mutation
  const synthesizeKnowledge = useMutation<any, Error, string>({
    mutationFn: async (query: string) => {
      const sources = [
        intelligence,
        recommendations,
        analytics,
      ].filter(Boolean);

      const response = await api.knowledgeEngine.synthesizeKnowledge({
        sources,
        query,
      });
      return response.data;
    },
  });

  const isLoading = intelligenceLoading || recommendationsLoading || analyticsLoading;

  // Get live data from backend
  const getKnowledgeEntries = (): KnowledgeEntry[] => {
    const allEntries = [
      ...(intelligence?.entries || []),
      ...(intelligence?.knowledge_connections || []),
      ...(intelligence?.strategic_ledger?.entries || [])
    ];
    return allEntries.filter(isValidKnowledgeEntry);
  };

  const getKnowledgeCategories = (): KnowledgeCategory[] => {
    if (analytics?.category_distribution) {
      return Object.entries(analytics.category_distribution).map(([name, count]) => ({ name, count: count as number }));
    }
    if (intelligence?.summary?.categories) {
      return Object.entries(intelligence.summary.categories).map(([name, count]) => ({ name, count: count as number }));
    }
    return [];
  };

  const getTotalEntries = (): number => {
    return intelligence?.summary?.total_entries ||
           analytics?.total_insights ||
           intelligence?.entries?.length ||
           0;
  };

  if (!currentProject) {
    return (
      <DashboardLayout>
        <EmptyState
          icon={Brain}
          title="No Project Selected"
          description="Please select a project from the dropdown above to access the knowledge engine."
        />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
        <div className="relative space-y-6">
        {/* Optimized Header - Research-based 2025 standards */}
        <DashboardPageHeader
          title="Knowledge Engine"
          description="AI-powered competitive intelligence and strategic insights"
          badge={{
            icon: <Brain className="mr-1 h-3 w-3" />,
            text: "AI-Powered Intelligence",
            variant: "secondary"
          }}
          actions={
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['competitive-intelligence'] });
                  queryClient.invalidateQueries({ queryKey: ['personalized-recommendations'] });
                  queryClient.invalidateQueries({ queryKey: ['learning-analytics'] });
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

        {/* Stats - Use real data if available */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Intelligence Items
              </CardTitle>
              <BookOpen className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {getTotalEntries()}
              </div>
              <p className="text-xs text-muted-foreground">
                Knowledge base entries
              </p>
            </CardContent>
          </Card>
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Insights Generated
              </CardTitle>
              <Lightbulb className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analytics?.insights_count || analytics?.learning_metrics?.total_insights || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                AI-powered insights
              </p>
            </CardContent>
          </Card>
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Recommendations
              </CardTitle>
              <User className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {recommendations?.recommendations?.length || recommendations?.length || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                Personalized for you
              </p>
            </CardContent>
          </Card>
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Learning Score
              </CardTitle>
              <History className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-lg font-bold">
                {analytics?.performance_metrics?.learning_effectiveness ||
                 analytics?.learning_score ||
                 (analytics?.model_effectiveness?.user_satisfaction ? Math.round(analytics.model_effectiveness.user_satisfaction * 100) : 0)}%
              </div>
              <p className="text-xs text-muted-foreground">
                Knowledge utilization
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Search and Filter */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search knowledge base..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <Button
                onClick={() => {
                  if (searchQuery) {
                    synthesizeKnowledge.mutate(searchQuery);
                  }
                }}
                disabled={!searchQuery || synthesizeKnowledge.isPending}
              >
                {synthesizeKnowledge.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Synthesizing...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Search & Synthesize
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Show loading state */}
        {isLoading && (
          <LoadingState 
            message="Loading knowledge engine data..." 
            size="lg" 
          />
        )}

        {/* Main Content */}
        <div className="grid gap-6 md:grid-cols-3">
          {/* Categories Sidebar */}
          <Card className="md:col-span-1">
            <CardHeader>
              <CardTitle>Categories</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Button
                  variant={selectedCategory === 'all' ? 'secondary' : 'ghost'}
                  className="w-full justify-between"
                  onClick={() => setSelectedCategory('all')}
                >
                  <span>All Categories</span>
                  <Badge variant="secondary">{getTotalEntries()}</Badge>
                </Button>
                {getKnowledgeCategories().map((category) => (
                  <Button
                    key={category.name}
                    variant={selectedCategory === category.name ? 'secondary' : 'ghost'}
                    className="w-full justify-between"
                    onClick={() => setSelectedCategory(category.name)}
                  >
                    <span>{category.name}</span>
                    <Badge variant="secondary">{category.count as React.ReactNode}</Badge>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Knowledge Entries */}
          <div className="md:col-span-2 space-y-4">
            <Tabs defaultValue="recent" className="space-y-4">
              <TabsList>
                <TabsTrigger value="recent">Recent</TabsTrigger>
                <TabsTrigger value="popular">Popular</TabsTrigger>
                <TabsTrigger value="insights">Key Insights</TabsTrigger>
              </TabsList>

              <TabsContent value="recent" className="space-y-4">
                {getKnowledgeEntries().length > 0 ? (
                  getKnowledgeEntries().map((entry: KnowledgeEntry, index: number) => (
                    <Card key={entry.id || entry.entry_id || index} className="hover:shadow-lg transition-shadow">
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div>
                            <CardTitle className="text-lg">{entry.title || entry.name || 'Knowledge Entry'}</CardTitle>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge variant="secondary">{entry.category || entry.type || 'General'}</Badge>
                              <span className="text-xs text-muted-foreground">
                                {entry.created_at ? formatDate(entry.created_at) : 'Recently'}
                              </span>
                            </div>
                          </div>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm">
                              <Share2 className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Link2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground mb-4">
                          {(entry.content || entry.description || 'No content available').substring(0, 150)}...
                        </p>

                        {entry.tags && entry.tags.length > 0 && (
                          <div className="flex flex-wrap gap-2 mb-4">
                            {entry.tags.map((tag: string, i: number) => (
                              <Badge key={i} variant="outline" className="text-xs">
                                #{tag}
                              </Badge>
                            ))}
                          </div>
                        )}

                        {(entry.insights || entry.key_insights) && (
                          <div className="rounded-lg bg-primary/5 p-3">
                            <p className="text-xs font-medium mb-2 flex items-center gap-1">
                              <Lightbulb className="h-3 w-3" />
                              Key Insights
                            </p>
                            <ul className="space-y-1">
                              {(entry.insights || entry.key_insights || []).map((insight: string | { description?: string; content?: string }, i: number) => (
                                <li key={i} className="text-xs text-muted-foreground">
                                  • {typeof insight === 'string' ? insight : (insight as { description?: string; content?: string })?.description || (insight as { description?: string; content?: string })?.content || 'No insight'}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))
                ) : (
                  <EmptyState
                    icon={Brain}
                    title="No Knowledge Entries"
                    description="Generate intelligence or create strategic entries to populate your knowledge base."
                  />
                )}
              </TabsContent>

              <TabsContent value="insights" className="space-y-4">
                <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Brain className="h-5 w-5 text-primary" />
                      AI-Generated Insights
                    </CardTitle>
                    <CardDescription>
                      Patterns and trends discovered from your knowledge base
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {analytics?.optimization_opportunities?.map((opportunity: OptimizationOpportunity, index: number) => (
                        <div key={index} className="rounded-lg border p-4">
                          <h4 className="font-semibold mb-2 flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-green-500" />
                            {opportunity.title || 'Optimization Opportunity'}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {opportunity.description || opportunity.content || 'No description available'}
                          </p>
                        </div>
                      )) || intelligence?.learning_insights && Object.entries(intelligence.learning_insights).map(([key, insight]: [string, LearningInsight | string], index: number) => (
                        <div key={index} className="rounded-lg border p-4">
                          <h4 className="font-semibold mb-2 flex items-center gap-2">
                            <MessageSquare className="h-4 w-4 text-blue-500" />
                            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {typeof insight === 'string' ? insight : (insight as LearningInsight)?.description || 'No insight available'}
                          </p>
                        </div>
                      )) || (
                        <div className="rounded-lg border p-4">
                          <h4 className="font-semibold mb-2 flex items-center gap-2">
                            <Sparkles className="h-4 w-4 text-primary" />
                            No AI Insights Available
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            Generate intelligence or run analytics to get AI-powered insights and recommendations.
                          </p>
                        </div>
                      )}
                    </div>
                    
                    {/* Generate Intelligence */}
                    <div className="mt-6 p-4 rounded-lg bg-primary/5 border border-primary/20">
                      <h4 className="font-semibold mb-3 flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-primary" />
                        Generate New Intelligence
                      </h4>
                      <div className="flex gap-2">
                        <Input
                          placeholder="Enter a topic to analyze..."
                          value={generateTopic}
                          onChange={(e) => setGenerateTopic(e.target.value)}
                          onKeyPress={(e) => {
                            if (e.key === 'Enter' && generateTopic) {
                              generateIntelligence.mutate(generateTopic);
                            }
                          }}
                        />
                        <Button
                          onClick={() => {
                            if (generateTopic) {
                              generateIntelligence.mutate(generateTopic);
                            }
                          }}
                          disabled={!generateTopic || generateIntelligence.isPending}
                        >
                          {generateIntelligence.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Brain className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>

            {/* Synthesis Results */}
            {synthesizeKnowledge.data && (
              <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
                <CardHeader>
                  <CardTitle>Knowledge Synthesis Results</CardTitle>
                  <CardDescription>
                    AI-synthesized insights based on your query
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="prose dark:prose-invert max-w-none">
                    {synthesizeKnowledge.data.synthesis || synthesizeKnowledge.data}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
        </div>
    </DashboardLayout>
  );
}

export default withAuth(KnowledgeEnginePage);