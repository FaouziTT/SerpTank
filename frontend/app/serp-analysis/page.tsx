'use client';

import { useState, useEffect } from 'react';
import { withAuth } from '@/lib/auth-context';
import { motion } from 'framer-motion';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { DashboardPageHeader } from '@/components/layout/dashboard-page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Search,
  Globe,
  TrendingUp,
  Award,
  Link2,
  FileText,
  Image,
  Video,
  ShoppingBag,
  Map,
  MessageSquare,
  Sparkles,
  RefreshCw,
  Download,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  ExternalLink,
  X,
  Target,
  Users,
  Clock,
  Activity
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { notifications } from '@/lib/notification-service';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { truncate } from '@/lib/utils';

interface SERPResult {
  position: number;
  title: string;
  url: string;
  description: string;
  domain: string;
  type: 'organic' | 'featured_snippet' | 'people_also_ask' | 'video' | 'image' | 'shopping' | 'local_pack';
  features?: {
    rating?: number;
    reviews?: number;
    price?: string;
    date?: string;
  };
}

interface SERPOverviewData {
  competition_level: string;
  opportunity_score: number;
  keywords_tracked: number;
  competitors_monitored: number;
  last_analysis: string;
  is_configured: boolean;
  serp_features: {
    featured_snippet: boolean;
    people_also_ask: boolean;
    video_carousel: boolean;
    local_pack: boolean;
    shopping_results: boolean;
    knowledge_panel: boolean;
    site_links: boolean;
  };
  competitor_analysis: {
    top_competitors: Array<{
      domain: string;
      visibility: number;
      keywords: number;
    }>;
    your_position: number;
    your_visibility: number;
  };
  raw?: any;
}

interface SERPDetailData {
  keyword: string;
  location: string;
  device: string;
  search_volume: number;
  keyword_difficulty: number;
  cpc: number;
  analyzed_at: string;
  serp_features: {
    featured_snippet: boolean;
    people_also_ask: boolean;
    video_carousel: boolean;
    image_pack: boolean;
    local_pack: boolean;
    shopping_results: boolean;
    knowledge_panel: boolean;
    site_links: boolean;
  };
  results: SERPResult[];
  competitor_analysis: {
    top_competitors: Array<{
      domain: string;
      visibility: number;
      keywords: number;
    }>;
    your_position: number;
    your_visibility: number;
  };
  opportunities: Array<{
    type: string;
    description: string;
    difficulty: string;
    impact: string;
  }>;
  related_keywords: Array<{
    keyword: string;
    volume: number;
    difficulty: number;
  }>;
}

function SERPAnalysisPage() {
  const [keyword, setKeyword] = useState('');
  const [location, setLocation] = useState('United States');
  const [device, setDevice] = useState('desktop');
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { currentProject } = useProject();
  const queryClient = useQueryClient();

  // Fetch SERP overview data
  const { data: overviewData, isLoading: isOverviewLoading, error: overviewError, refetch: refetchOverview } = useQuery({
    queryKey: ['serp-overview', currentProject?.id],
    queryFn: async () => {
      if (!currentProject) return null;
      const response = await api.serpAnalysis.getOverview();
      return response.data;
    },
    enabled: !!currentProject,
  });

  // Fetch competitors data
  const { data: competitorsData, isLoading: isCompetitorsLoading, error: competitorsError, refetch: refetchCompetitors } = useQuery({
    queryKey: ['serp-competitors', currentProject?.id],
    queryFn: async () => {
      if (!currentProject) return null;
      const response = await api.serpAnalysis.getCompetitors();
      return response.data;
    },
    enabled: !!currentProject,
  });

  // Progressive analysis stages
  const analysisStages = [
    { stage: 'Initializing search...', progress: 10 },
    { stage: 'Fetching SERP data...', progress: 25 },
    { stage: 'Analyzing competition...', progress: 45 },
    { stage: 'Processing SERP features...', progress: 65 },
    { stage: 'Calculating metrics...', progress: 80 },
    { stage: 'Generating insights...', progress: 95 },
    { stage: 'Analysis complete!', progress: 100 }
  ];

  // Simulate progressive analysis
  const simulateAnalysisProgress = async () => {
    setIsAnalyzing(true);
    setAnalysisProgress(0);
    setCurrentStage('');

    for (const { stage, progress } of analysisStages) {
      setCurrentStage(stage);
      setAnalysisProgress(progress);
      await new Promise(resolve => setTimeout(resolve, 800));
    }
  };

  // Analyze keyword mutation
  const analyzeKeyword = useMutation({
    mutationFn: async (queryData: { keyword: string; location: string; device: string }) => {
      if (!currentProject) throw new Error('No project selected');
      
      // Start progress simulation
      await simulateAnalysisProgress();
      
      return api.serpAnalysis.analyzeSERP({
        keyword: queryData.keyword,
        location: queryData.location,
        device: queryData.device,
      });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['serp-overview'] });
      queryClient.invalidateQueries({ queryKey: ['serp-competitors'] });
      notifications.success('Analysis complete', 'SERP data has been analyzed successfully');
      setKeyword('');
      setIsAnalyzing(false);
      setAnalysisProgress(0);
      setCurrentStage('');
    },
    onError: (error) => {
      notifications.handleApiError(error, 'Failed to analyze keyword');
      setIsAnalyzing(false);
      setAnalysisProgress(0);
      setCurrentStage('');
    },
  });

  const isLoading = isOverviewLoading || isCompetitorsLoading;
  const error = overviewError || competitorsError;
  const refetch = () => {
    refetchOverview();
    refetchCompetitors();
  };
  
  // Transform backend data to match frontend expectations
  const transformedData = (() => {
    if (!overviewData && !competitorsData) return null;
    
    const overview = overviewData || {};
    const competitors = competitorsData || [];
    
    return {
      // Overview metrics
      competition_level: overview.competition_level || 'medium',
      opportunity_score: overview.opportunity_score || 0,
      keywords_tracked: overview.keywords_tracked || 0,
      competitors_monitored: overview.competitors_monitored || 0,
      last_analysis: overview.last_analysis || new Date().toISOString(),
      is_configured: overview.is_configured !== false,
      
      // SERP features summary
      serp_features: {
        featured_snippet: overview.organic_results > 0,
        people_also_ask: overview.organic_results > 3,
        video_carousel: overview.video_results > 0,
        local_pack: overview.local_results > 0,
        shopping_results: overview.paid_results > 0,
        knowledge_panel: false,
        site_links: false,
      },
      
      // Competitor data
      competitor_analysis: {
        top_competitors: competitors.slice(0, 5).map((comp: any) => ({
          domain: comp.domain,
          visibility: comp.visibility_score || 0,
          keywords: comp.tracked_keywords || 0,
        })),
        your_position: 0, // Would need project domain to calculate
        your_visibility: 0,
      },
      
      // Include raw data
      raw: {
        overview: overviewData,
        competitors: competitorsData,
      },
    };
  })();
  
  const serpData = transformedData;

  const handleAnalyze = () => {
    if (!keyword.trim()) {
      notifications.error('No keyword', 'Please enter a keyword to analyze.');
      return;
    }
    analyzeKeyword.mutate({ keyword, location, device });
  };

  // Mock data for overview display
  const mockOverviewData: SERPOverviewData = {
    competition_level: 'high',
    opportunity_score: 75,
    keywords_tracked: 156,
    competitors_monitored: 12,
    last_analysis: new Date().toISOString(),
    is_configured: true,
    serp_features: {
      featured_snippet: true,
      people_also_ask: true,
      video_carousel: true,
      local_pack: false,
      shopping_results: false,
      knowledge_panel: true,
      site_links: true,
    },
    competitor_analysis: {
      top_competitors: [
        { domain: 'competitor1.com', visibility: 82, keywords: 15420 },
        { domain: 'competitor2.com', visibility: 78, keywords: 12890 },
        { domain: 'competitor3.com', visibility: 71, keywords: 10234 },
      ],
      your_position: 8,
      your_visibility: 45,
    },
  };
  
  // Mock data for detail display
  const mockDetailData: SERPDetailData = {
    keyword: 'best seo tools',
    location: 'United States',
    device: 'desktop',
    search_volume: 12100,
    keyword_difficulty: 72,
    cpc: 8.45,
    analyzed_at: '2024-01-15T14:30:00Z',
    
    serp_features: {
      featured_snippet: true,
      people_also_ask: true,
      video_carousel: true,
      image_pack: false,
      local_pack: false,
      shopping_results: false,
      knowledge_panel: true,
      site_links: true,
    },
    
    results: [
      {
        position: 1,
        title: 'Best SEO Tools in 2024: Complete Guide',
        url: 'https://example.com/best-seo-tools',
        domain: 'example.com',
        description: 'Discover the top SEO tools for 2024. Compare features, pricing, and find the perfect tool for your needs...',
        type: 'featured_snippet' as const,
      },
      {
        position: 2,
        title: '15 Best SEO Tools to Boost Your Rankings',
        url: 'https://competitor1.com/seo-tools',
        domain: 'competitor1.com',
        description: 'Looking for the best SEO tools? We tested 50+ tools and found the top 15 that deliver real results...',
        type: 'organic' as const,
      },
      {
        position: 3,
        title: 'SEO Tools Comparison: Which One is Right for You?',
        url: 'https://competitor2.com/seo-tools-comparison',
        domain: 'competitor2.com',
        description: 'Compare the best SEO tools side by side. Features, pricing, pros and cons - everything you need to know...',
        type: 'organic' as const,
      },
    ] as SERPResult[],
    
    competitor_analysis: {
      top_competitors: [
        { domain: 'competitor1.com', visibility: 82, keywords: 15420 },
        { domain: 'competitor2.com', visibility: 78, keywords: 12890 },
        { domain: 'competitor3.com', visibility: 71, keywords: 10234 },
      ],
      your_position: 8,
      your_visibility: 45,
    },
    
    opportunities: [
      {
        type: 'featured_snippet',
        description: 'Target featured snippet by adding structured Q&A content',
        difficulty: 'medium',
        impact: 'high',
      },
      {
        type: 'people_also_ask',
        description: 'Create content answering related questions',
        difficulty: 'easy',
        impact: 'medium',
      },
      {
        type: 'schema_markup',
        description: 'Implement FAQ and HowTo schema for rich results',
        difficulty: 'easy',
        impact: 'high',
      },
    ],
    
    related_keywords: [
      { keyword: 'free seo tools', volume: 8900, difficulty: 45 },
      { keyword: 'seo tools for small business', volume: 2400, difficulty: 38 },
      { keyword: 'seo audit tools', volume: 3600, difficulty: 52 },
      { keyword: 'keyword research tools', volume: 6500, difficulty: 48 },
    ],
  };

  const data = serpData || mockOverviewData;
  const detailData = null as SERPDetailData | null;  // We'll populate this when user analyzes a keyword

  const getTypeColor = (type: string) => {
    const colors = {
      featured_snippet: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
      people_also_ask: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
      video: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
      local_pack: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
      organic: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400',
    };
    return colors[type as keyof typeof colors] || colors.organic;
  };

  const getDifficultyColor = (difficulty: number) => {
    if (difficulty < 30) return 'text-green-600';
    if (difficulty < 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (!currentProject) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-2">
            <h3 className="text-2xl font-semibold">No Project Selected</h3>
            <p className="text-muted-foreground">
              Please select a project from the dropdown above to analyze SERP.
            </p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (isLoading) {
    return (
      <DashboardLayout>
        <LoadingState message="Loading SERP analysis..." size="lg" fullHeight />
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-8">
          <ErrorState
            error={error}
            title="Failed to load SERP data"
            description="We couldn't fetch SERP analysis. Please try again."
            onRetry={() => {
              queryClient.invalidateQueries({ queryKey: ['serp-overview'] });
              queryClient.invalidateQueries({ queryKey: ['serp-competitors'] });
            }}
          />
        </div>
      </DashboardLayout>
    );
  }
  
  // Check if SERP analysis is configured
  if (serpData && !serpData.is_configured) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">SERP Analysis</h1>
            <p className="text-muted-foreground">
              Analyze search engine results and competitor rankings
            </p>
          </div>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-amber-500/10 p-3">
                  <AlertCircle className="h-6 w-6 text-amber-500" />
                </div>
                <div>
                  <CardTitle>SERP Analysis Configuration Required</CardTitle>
                  <CardDescription>
                    Configure your SERP API credentials to enable search result analysis
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                SERP analysis requires either SerpAPI or Google Programmable Search API credentials. 
                Please configure your API keys in the environment settings.
              </p>
              <div className="flex gap-3">
                <Button variant="outline" asChild>
                  <a href="https://serpapi.com" target="_blank" rel="noopener noreferrer">
                    Learn about SerpAPI
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </a>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
        <div className="relative space-y-6">
        {/* Optimized Header - Research-based 2025 standards */}
        <DashboardPageHeader
          title="SERP Analysis"
          description="Analyze search engine results and competitor rankings"
          badge={{
            icon: <Search className="mr-1 h-3 w-3" />,
            text: "SERP Intelligence",
            variant: "secondary"
          }}
          actions={
            <div className="flex items-center gap-4">
              <Button variant="outline" onClick={() => refetch()} size="sm" className="bg-card/80 backdrop-blur-sm border-border/50">
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
              <Button variant="outline" size="sm" className="bg-card/80 backdrop-blur-sm border-border/50">
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </div>
          }
        />

        {/* Keyword Analysis */}
        <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Analyze SERP
              {isAnalyzing && (
                <Badge variant="secondary" className="animate-pulse">
                  <Activity className="h-3 w-3 mr-1" />
                  Analyzing
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              {isAnalyzing 
                ? currentStage || 'Processing keyword analysis...'
                : 'Enter a keyword to analyze search results and competition'
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Analysis Progress */}
              {isAnalyzing && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-blue-800">{currentStage}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {Math.round(analysisProgress)}%
                      </Badge>
                    </div>
                  </div>
                  <Progress value={analysisProgress} className="h-2 mb-3" />
                  
                  {/* Analysis stages indicator */}
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className={`text-center p-2 rounded ${analysisProgress >= 25 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                      SERP Fetch
                    </div>
                    <div className={`text-center p-2 rounded ${analysisProgress >= 65 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                      Competition Analysis
                    </div>
                    <div className={`text-center p-2 rounded ${analysisProgress >= 95 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                      Insights Generation
                    </div>
                  </div>
                </div>
              )}
              
              <div className="flex gap-2">
                <Input
                  placeholder="Enter keyword..."
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAnalyze()}
                  className="flex-1"
                  disabled={isAnalyzing}
                />
                <Select value={location} onValueChange={setLocation} disabled={isAnalyzing}>
                  <SelectTrigger className="w-[200px]">
                    <Globe className="mr-2 h-4 w-4" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="United States">United States</SelectItem>
                    <SelectItem value="United Kingdom">United Kingdom</SelectItem>
                    <SelectItem value="Canada">Canada</SelectItem>
                    <SelectItem value="Australia">Australia</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={device} onValueChange={setDevice} disabled={isAnalyzing}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="desktop">Desktop</SelectItem>
                    <SelectItem value="mobile">Mobile</SelectItem>
                  </SelectContent>
                </Select>
                <Button 
                  onClick={handleAnalyze}
                  disabled={!keyword.trim() || isAnalyzing}
                  className="gradient-primary"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      Analyze
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Overview Metrics */}
        {data && (
          <>
            <div className="grid gap-4 md:grid-cols-4">
            <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Competition Level
                </CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold capitalize">{data.competition_level}</div>
                <p className="text-xs text-muted-foreground">Overall market competition</p>
              </CardContent>
            </Card>
            
            <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Opportunity Score
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.opportunity_score}%</div>
                <p className="text-xs text-muted-foreground">SEO opportunity potential</p>
              </CardContent>
            </Card>
            
            <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Keywords Tracked
                </CardTitle>
                <Search className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.keywords_tracked}</div>
                <p className="text-xs text-muted-foreground">Active keyword monitoring</p>
              </CardContent>
            </Card>
            
            <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Competitors
                </CardTitle>
                <Users className="h-4 w-4 text-amber-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.competitors_monitored}</div>
                <p className="text-xs text-muted-foreground">Monitored competitors</p>
              </CardContent>
            </Card>
          </div>
          
          {/* Top Competitors Overview */}
          {data.competitor_analysis?.top_competitors?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Top Competitors</CardTitle>
                <CardDescription>
                  Leading domains in your market space
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.competitor_analysis.top_competitors.map((competitor: any, index: number) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-4 rounded-lg border hover:border-primary/20 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="rounded-full bg-primary/10 p-2">
                          <Globe className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{competitor.domain}</p>
                          <p className="text-xs text-muted-foreground">
                            {competitor.keywords.toLocaleString()} keywords
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <p className="text-sm font-medium">Visibility</p>
                          <p className="text-2xl font-bold">{competitor.visibility}%</p>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => analyzeKeyword.mutate({ 
                            keyword: competitor.domain, 
                            location, 
                            device 
                          })}
                        >
                          Analyze
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
          </>
        )}
        
        {detailData && (
          <>
            {/* Keyword-specific Metrics */}
            <div className="grid gap-4 md:grid-cols-4">
              <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Search Volume
                  </CardTitle>
                  <Search className="h-4 w-4 text-primary" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{detailData.search_volume.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">Monthly searches</p>
                </CardContent>
              </Card>

              <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Keyword Difficulty
                  </CardTitle>
                  <Award className="h-4 w-4 text-yellow-500" />
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${getDifficultyColor(detailData.keyword_difficulty)}`}>
                    {detailData.keyword_difficulty}/100
                  </div>
                  <p className="text-xs text-muted-foreground">Competition level</p>
                </CardContent>
              </Card>

              <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    CPC
                  </CardTitle>
                  <TrendingUp className="h-4 w-4 text-green-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${detailData.cpc.toFixed(2)}</div>
                  <p className="text-xs text-muted-foreground">Cost per click</p>
                </CardContent>
              </Card>

              <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Your Position
                  </CardTitle>
                  <Globe className="h-4 w-4 text-blue-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {data.competitor_analysis.your_position > 0 ? `#${data.competitor_analysis.your_position}` : 'Not ranking'}
                  </div>
                  <p className="text-xs text-muted-foreground">Current ranking</p>
                </CardContent>
              </Card>
            </div>

            {/* SERP Features */}
            <Card>
              <CardHeader>
                <CardTitle>SERP Features</CardTitle>
                <CardDescription>
                  Special features present in search results
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-4">
                  {Object.entries(data.serp_features).map(([feature, present]) => {
                    const icons = {
                      featured_snippet: FileText,
                      people_also_ask: MessageSquare,
                      video_carousel: Video,
                      image_pack: Image,
                      local_pack: Map,
                      shopping_results: ShoppingBag,
                      knowledge_panel: Globe,
                      site_links: Link2,
                    };
                    const Icon = icons[feature as keyof typeof icons] || Globe;
                    
                    return (
                      <div
                        key={feature}
                        className={`flex items-center gap-3 p-3 rounded-lg border ${
                          present ? 'border-primary/20 bg-primary/5' : 'border-muted opacity-50'
                        }`}
                      >
                        <Icon className={`h-5 w-5 ${present ? 'text-primary' : 'text-muted-foreground'}`} />
                        <div className="flex-1">
                          <p className="text-sm font-medium capitalize">
                            {feature.replace(/_/g, ' ')}
                          </p>
                        </div>
                        {present ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <X className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Search Results */}
            <Tabs defaultValue="results" className="space-y-4">
              <TabsList>
                <TabsTrigger value="results">Search Results</TabsTrigger>
                <TabsTrigger value="competitors">Competitors</TabsTrigger>
                <TabsTrigger value="opportunities">Opportunities</TabsTrigger>
                <TabsTrigger value="related">Related Keywords</TabsTrigger>
              </TabsList>

              <TabsContent value="results" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Top 10 Results for &quot;{detailData.keyword}&quot;</CardTitle>
                    <CardDescription>
                      Current search engine results page
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {detailData.results.map((result: any) => (
                        <div
                          key={result.position}
                          className="flex items-start gap-4 p-4 rounded-lg border hover:border-primary/20 transition-colors"
                        >
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold">
                            {result.position}
                          </div>
                          <div className="flex-1 space-y-2">
                            <div className="flex items-start justify-between">
                              <div className="space-y-1">
                                <h4 className="font-semibold text-primary hover:underline cursor-pointer">
                                  {result.title}
                                </h4>
                                <p className="text-sm text-green-600 flex items-center gap-1">
                                  {result.domain}
                                  <ExternalLink className="h-3 w-3" />
                                </p>
                              </div>
                              <Badge className={getTypeColor(result.type)}>
                                {result.type.replace(/_/g, ' ')}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {truncate(result.description, 150)}
                            </p>
                            {result.features && (
                              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                {result.features.rating && (
                                  <span>⭐ {result.features.rating}</span>
                                )}
                                {result.features.reviews && (
                                  <span>{result.features.reviews} reviews</span>
                                )}
                                {result.features.price && (
                                  <span>{result.features.price}</span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="competitors" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Top Competitors</CardTitle>
                    <CardDescription>
                      Domains ranking for similar keywords
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {data.competitor_analysis.top_competitors.map((competitor: any) => (
                        <div
                          key={competitor.domain}
                          className="flex items-center justify-between p-4 rounded-lg border"
                        >
                          <div>
                            <p className="font-semibold">{competitor.domain}</p>
                            <p className="text-sm text-muted-foreground">
                              Ranking for {competitor.keywords.toLocaleString()} keywords
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-2xl font-bold">{competitor.visibility}%</p>
                            <p className="text-xs text-muted-foreground">Visibility score</p>
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
                    <CardTitle>Ranking Opportunities</CardTitle>
                    <CardDescription>
                      Actionable insights to improve your rankings
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {detailData.opportunities.map((opportunity: any, index: number) => (
                        <div
                          key={index}
                          className="flex items-start gap-4 p-4 rounded-lg border"
                        >
                          <div className="rounded-full p-2 bg-primary/10">
                            <Sparkles className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold capitalize">
                              {opportunity.type.replace(/_/g, ' ')}
                            </h4>
                            <p className="text-sm text-muted-foreground mt-1">
                              {opportunity.description}
                            </p>
                            <div className="flex items-center gap-2 mt-2">
                              <Badge variant={opportunity.difficulty === 'easy' ? 'default' : 'warning'}>
                                {opportunity.difficulty} difficulty
                              </Badge>
                              <Badge variant={opportunity.impact === 'high' ? 'default' : 'secondary'}>
                                {opportunity.impact} impact
                              </Badge>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="related" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Related Keywords</CardTitle>
                    <CardDescription>
                      Similar keywords you could target
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {detailData.related_keywords.map((kw: any, index: number) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 rounded-lg border hover:border-primary/20 transition-colors cursor-pointer"
                        >
                          <div>
                            <p className="font-medium">{kw.keyword}</p>
                            <p className="text-xs text-muted-foreground">
                              {kw.volume.toLocaleString()} monthly searches
                            </p>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <p className={`text-sm font-medium ${getDifficultyColor(kw.difficulty)}`}>
                                KD: {kw.difficulty}
                              </p>
                            </div>
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </>
        )}
        </div>
      </div>
    </DashboardLayout>
  );
}

export default withAuth(SERPAnalysisPage);