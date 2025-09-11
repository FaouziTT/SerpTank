'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
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
import { dedupedApi as api } from '@/lib/api-deduped';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { formatDate } from '@/lib/utils';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyState } from '@/components/ui/empty-state';
import { useAutoRefresh } from '@/lib/hooks/use-auto-refresh';

function KnowledgeEnginePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [generateTopic, setGenerateTopic] = useState('');
  const { currentProject } = useProject();
  const queryClient = useQueryClient();

  // Auto-refresh intelligence data every 10 minutes
  useAutoRefresh(
    ['competitive-intelligence'],
    600000,
    { enabled: !!currentProject }
  );

  // Fetch competitive intelligence
  const { data: intelligence, isLoading: intelligenceLoading } = useQuery({
    queryKey: ['competitive-intelligence'],
    queryFn: async () => {
      try {
        const response = await api.knowledgeEngine.getCompetitiveIntelligence();
        return response.data;
      } catch (error) {
        console.error('Failed to fetch competitive intelligence:', error);
        return null;
      }
    },
    enabled: !!currentProject,
  });

  // Fetch personalized recommendations
  const { data: recommendations, isLoading: recommendationsLoading } = useQuery({
    queryKey: ['personalized-recommendations'],
    queryFn: async () => {
      try {
        const response = await api.knowledgeEngine.getPersonalizedRecommendations();
        return response.data;
      } catch (error) {
        console.error('Failed to fetch recommendations:', error);
        return null;
      }
    },
    enabled: !!currentProject,
  });

  // Fetch learning analytics
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['learning-analytics'],
    queryFn: async () => {
      try {
        const response = await api.knowledgeEngine.getLearningAnalytics();
        return response.data;
      } catch (error) {
        console.error('Failed to fetch learning analytics:', error);
        return null;
      }
    },
    enabled: !!currentProject,
  });

  // Generate intelligence mutation
  const generateIntelligence = useMutation({
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
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['competitive-intelligence'] });
      setGenerateTopic('');
    },
  });

  // Knowledge synthesis mutation
  const synthesizeKnowledge = useMutation({
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

  // Mock data
  const mockKnowledge = {
    entries: [
      {
        id: '1',
        title: 'Core Web Vitals Optimization Strategy',
        category: 'Technical SEO',
        tags: ['performance', 'CWV', 'page speed'],
        content: 'Comprehensive guide on optimizing Core Web Vitals...',
        insights: [
          'LCP improvements led to 15% better rankings',
          'Mobile performance is critical for user retention',
        ],
        created_at: '2024-01-10T10:00:00Z',
      },
      {
        id: '2',
        title: 'Content Clustering Best Practices',
        category: 'Content Strategy',
        tags: ['content', 'clustering', 'topical authority'],
        content: 'How to build topical authority through content clusters...',
        insights: [
          'Topic clusters improved organic traffic by 40%',
          'Internal linking is key to cluster success',
        ],
        created_at: '2024-01-12T14:00:00Z',
      },
      {
        id: '3',
        title: 'Local SEO Checklist 2024',
        category: 'Local SEO',
        tags: ['local', 'GMB', 'citations'],
        content: 'Complete checklist for local SEO optimization...',
        insights: [
          'GMB optimization drives 70% of local traffic',
          'Review management is crucial for rankings',
        ],
        created_at: '2024-01-14T09:00:00Z',
      },
    ],
    categories: [
      { name: 'Technical SEO', count: 24 },
      { name: 'Content Strategy', count: 18 },
      { name: 'Local SEO', count: 12 },
      { name: 'Link Building', count: 8 },
      { name: 'Analytics', count: 15 },
    ],
    insights: {
      total_entries: 156,
      total_insights: 412,
      contributors: 8,
      last_updated: '2024-01-15T16:00:00Z',
    },
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
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Knowledge Engine</h1>
            <p className="text-muted-foreground">
              AI-powered competitive intelligence and strategic insights
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['competitive-intelligence'] });
                queryClient.invalidateQueries({ queryKey: ['personalized-recommendations'] });
                queryClient.invalidateQueries({ queryKey: ['learning-analytics'] });
              }}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

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
                {intelligence?.entries?.length || intelligence?.items?.length || analytics?.total_entries || mockKnowledge.insights.total_entries}
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
                {analytics?.insights_count || mockKnowledge.insights.total_insights}
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
                {analytics?.performance_metrics?.learning_effectiveness || analytics?.learning_score || 85}%
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
                  <Badge variant="secondary">{mockKnowledge.insights.total_entries}</Badge>
                </Button>
                {mockKnowledge.categories.map((category) => (
                  <Button
                    key={category.name}
                    variant={selectedCategory === category.name ? 'secondary' : 'ghost'}
                    className="w-full justify-between"
                    onClick={() => setSelectedCategory(category.name)}
                  >
                    <span>{category.name}</span>
                    <Badge variant="secondary">{category.count}</Badge>
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
                {mockKnowledge.entries.map((entry) => (
                  <Card key={entry.id} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-lg">{entry.title}</CardTitle>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="secondary">{entry.category}</Badge>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(entry.created_at)}
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
                        {entry.content.substring(0, 150)}...
                      </p>
                      
                      <div className="flex flex-wrap gap-2 mb-4">
                        {entry.tags.map((tag, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            #{tag}
                          </Badge>
                        ))}
                      </div>

                      {entry.insights.length > 0 && (
                        <div className="rounded-lg bg-primary/5 p-3">
                          <p className="text-xs font-medium mb-2 flex items-center gap-1">
                            <Lightbulb className="h-3 w-3" />
                            Key Insights
                          </p>
                          <ul className="space-y-1">
                            {entry.insights.map((insight, i) => (
                              <li key={i} className="text-xs text-muted-foreground">
                                • {insight}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
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
                      <div className="rounded-lg border p-4">
                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                          <TrendingUp className="h-4 w-4 text-green-500" />
                          Performance Patterns
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          Content optimized using insights from the knowledge base shows 
                          35% better performance on average. Technical SEO improvements 
                          have the highest correlation with ranking improvements.
                        </p>
                      </div>
                      
                      <div className="rounded-lg border p-4">
                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-blue-500" />
                          Common Themes
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          Your team frequently documents insights about: page speed optimization (18%), 
                          content quality (15%), and user experience (12%). Consider creating 
                          standardized processes for these areas.
                        </p>
                      </div>

                      <div className="rounded-lg border p-4">
                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-primary" />
                          Knowledge Gaps
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          Limited documentation found for: video SEO, voice search optimization, 
                          and international SEO. These areas represent opportunities for 
                          knowledge expansion.
                        </p>
                      </div>
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