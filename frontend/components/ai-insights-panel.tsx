'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { 
  Sparkles, 
  Brain, 
  TrendingUp, 
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Info,
  Target,
  Lightbulb,
  MessageSquare,
  RefreshCw,
  Loader2,
  Send,
  ThumbsUp,
  ThumbsDown,
  Bookmark
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dedupedApi as api } from '@/lib/api-deduped';
import { useProject } from '@/lib/project-context';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { formatDate } from '@/lib/utils';
import { notifications } from '@/lib/notification-service';

interface Insight {
  id: string;
  type: 'opportunity' | 'risk' | 'trend' | 'recommendation';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  impact: string;
  confidence: number;
  category: string;
  data_points: any[];
  created_at: string;
  actions?: {
    label: string;
    action: string;
  }[];
}

interface AIInsightsPanelProps {
  className?: string;
}

const insightIcons = {
  opportunity: TrendingUp,
  risk: AlertTriangle,
  trend: TrendingDown,
  recommendation: Lightbulb,
};

const priorityColors = {
  high: 'destructive',
  medium: 'default',
  low: 'secondary',
};

export function AIInsightsPanel({ className }: AIInsightsPanelProps) {
  const { currentProject } = useProject();
  const queryClient = useQueryClient();
  const [selectedTab, setSelectedTab] = useState('insights');
  const [customQuery, setCustomQuery] = useState('');
  const [feedbackSent, setFeedbackSent] = useState<Record<string, boolean>>({});

  // Fetch AI insights
  const { data: insights, isLoading: insightsLoading, error: insightsError } = useQuery({
    queryKey: ['ai-insights', currentProject?.id],
    queryFn: async () => {
      if (!currentProject) return [];
      try {
        const response = await api.knowledgeEngine.getPersonalizedRecommendations();
        return response.data || [];
      } catch (error) {
        console.error('Failed to fetch insights:', error);
        return [];
      }
    },
    enabled: !!currentProject,
    refetchInterval: 300000, // Refresh every 5 minutes
  });

  // Generate custom insights
  const generateInsight = useMutation({
    mutationFn: async (query: string) => {
      const response = await api.knowledgeEngine.generateIntelligence({
        topic: query,
        context: {
          project_id: currentProject?.id,
          domain: currentProject?.url,
        },
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['ai-insights'] });
      notifications.success('Insight Generated', 'New AI insight has been added');
      setCustomQuery('');
    },
    onError: (error) => {
      notifications.error('Generation Failed', 'Could not generate insight');
    },
  });

  // Submit feedback
  const submitFeedback = useMutation({
    mutationFn: async ({ insightId, feedback }: { insightId: string; feedback: 'positive' | 'negative' }) => {
      return api.knowledgeEngine.submitLearningFeedback({
        feedback_type: 'insight_feedback',
        content: {
          insight_id: insightId,
          feedback,
          project_id: currentProject?.id,
        },
      });
    },
    onSuccess: (_, variables) => {
      setFeedbackSent(prev => ({ ...prev, [variables.insightId]: true }));
      notifications.success('Feedback Sent', 'Thank you for your feedback!');
    },
  });

  const getInsightIcon = (type: string) => {
    const Icon = insightIcons[type as keyof typeof insightIcons] || Info;
    return Icon;
  };

  const getPriorityColor = (priority: string): "default" | "destructive" | "outline" | "secondary" => {
    return (priorityColors[priority as keyof typeof priorityColors] || 'secondary') as any;
  };

  const handleGenerateInsight = () => {
    if (customQuery.trim()) {
      generateInsight.mutate(customQuery);
    }
  };

  if (!currentProject) {
    return null;
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              AI Insights Panel
            </CardTitle>
            <CardDescription>
              AI-powered insights and recommendations for your SEO strategy
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['ai-insights'] })}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={selectedTab} onValueChange={setSelectedTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="insights">Insights</TabsTrigger>
            <TabsTrigger value="generator">Generator</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          {/* Insights Tab */}
          <TabsContent value="insights" className="space-y-4">
            {insightsLoading ? (
              <LoadingState message="Loading AI insights..." />
            ) : insightsError ? (
              <ErrorState
                error={insightsError}
                title="Failed to load insights"
                description="Could not fetch AI insights"
              />
            ) : (
              <div className="space-y-4">
                {insights?.length === 0 ? (
                  <div className="text-center py-8">
                    <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">
                      No insights available yet. Generate some insights to get started.
                    </p>
                  </div>
                ) : (
                  insights?.map((insight: Insight) => {
                    const Icon = getInsightIcon(insight.type);
                    return (
                      <Card key={insight.id} className="border-l-4 border-l-primary">
                        <CardHeader className="pb-3">
                          <div className="flex items-start justify-between">
                            <div className="flex items-start gap-3">
                              <div className="p-2 bg-primary/10 rounded-lg">
                                <Icon className="h-4 w-4 text-primary" />
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <h4 className="font-semibold">{insight.title}</h4>
                                  <Badge variant={getPriorityColor(insight.priority)}>
                                    {insight.priority}
                                  </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground mb-2">
                                  {insight.description}
                                </p>
                                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                  <span>{insight.category}</span>
                                  <span>Confidence: {Math.round(insight.confidence * 100)}%</span>
                                  <span>{formatDate(insight.created_at)}</span>
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-1">
                              {!feedbackSent[insight.id] && (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => submitFeedback.mutate({ insightId: insight.id, feedback: 'positive' })}
                                  >
                                    <ThumbsUp className="h-3 w-3" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => submitFeedback.mutate({ insightId: insight.id, feedback: 'negative' })}
                                  >
                                    <ThumbsDown className="h-3 w-3" />
                                  </Button>
                                </>
                              )}
                              <Button variant="ghost" size="sm">
                                <Bookmark className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent className="pt-0">
                          <Progress value={insight.confidence * 100} className="mb-3" />
                          {insight.impact && (
                            <p className="text-sm">
                              <strong>Impact:</strong> {insight.impact}
                            </p>
                          )}
                          {insight.actions && insight.actions.length > 0 && (
                            <div className="mt-3 flex gap-2">
                              {insight.actions.map((action, index) => (
                                <Button key={index} variant="outline" size="sm">
                                  {action.label}
                                </Button>
                              ))}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })
                )}
              </div>
            )}
          </TabsContent>

          {/* Generator Tab */}
          <TabsContent value="generator" className="space-y-4">
            <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Generate Custom Insight
                </CardTitle>
                <CardDescription>
                  Ask AI to analyze specific aspects of your SEO strategy
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Textarea
                    placeholder="What would you like insights about? e.g., 'Analyze my content performance for the last month' or 'What are the biggest SEO opportunities?'"
                    value={customQuery}
                    onChange={(e) => setCustomQuery(e.target.value)}
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={handleGenerateInsight}
                      disabled={!customQuery.trim() || generateInsight.isPending}
                      className="flex-1"
                    >
                      {generateInsight.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Send className="mr-2 h-4 w-4" />
                          Generate Insight
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Quick prompts */}
                <div className="mt-4 space-y-2">
                  <p className="text-sm font-medium">Quick prompts:</p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      'Content gaps analysis',
                      'Competitor opportunities',
                      'Technical SEO issues',
                      'Keyword strategy review',
                      'Page speed optimization',
                    ].map((prompt) => (
                      <Button
                        key={prompt}
                        variant="outline"
                        size="sm"
                        onClick={() => setCustomQuery(prompt)}
                      >
                        {prompt}
                      </Button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Insights Generated</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{insights?.length || 0}</div>
                  <p className="text-xs text-muted-foreground">This month</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Avg. Confidence</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {insights?.length > 0 
                      ? Math.round((insights.reduce((acc: number, insight: Insight) => acc + insight.confidence, 0) / insights.length) * 100)
                      : 0
                    }%
                  </div>
                  <p className="text-xs text-muted-foreground">AI confidence</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Action Items</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {insights?.reduce((acc: number, insight: Insight) => acc + (insight.actions?.length || 0), 0) || 0}
                  </div>
                  <p className="text-xs text-muted-foreground">Recommended actions</p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}