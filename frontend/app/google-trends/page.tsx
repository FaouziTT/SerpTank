'use client';

import { useState, useEffect } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  TrendingUp,
  TrendingDown,
  Search,
  Calendar,
  Globe,
  Sparkles,
  Download,
  RefreshCw,
  PlusCircle,
  X,
  BarChart3,
  LineChart,
  MapPin,
  Users,
  Zap,
  Clock,
  Activity
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { notifications } from '@/lib/notification-service';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { LineChart as RechartsLineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';

function GoogleTrendsPage() {
  const [keywords, setKeywords] = useState<string[]>(['']);
  const [currentKeyword, setCurrentKeyword] = useState('');
  const [timeRange, setTimeRange] = useState('90d');
  const [region, setRegion] = useState('US');
  const [batchProgress, setBatchProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedKeywords, setProcessedKeywords] = useState<string[]>([]);
  const { currentProject } = useProject();

  // Fetch trends data
  const { data: trendsData, isLoading, error, refetch } = useQuery({
    queryKey: ['google-trends', currentProject?.id, keywords, timeRange, region],
    queryFn: async () => {
      if (!currentProject) return null;
      const validKeywords = keywords.filter(k => k.trim());
      if (validKeywords.length === 0) return null;
      
      // Convert array to comma-separated string as backend expects
      const response = await api.googleTrends.getKeywordTrends({ 
        keywords: validKeywords.join(','),
        timeframe: timeRange,
        geo: region
      });
      return response.data;
    },
    enabled: !!currentProject && keywords.some(k => k.trim()),
  });

  // Simulate batch processing for keywords
  const simulateBatchProcessing = async (keywordList: string[]) => {
    setIsProcessing(true);
    setBatchProgress(0);
    setProcessedKeywords([]);
    setCurrentStage('Initializing batch analysis...');

    const totalKeywords = keywordList.length;
    
    for (let i = 0; i < totalKeywords; i++) {
      const keyword = keywordList[i];
      const progress = ((i + 1) / totalKeywords) * 100;
      
      setCurrentStage(`Processing "${keyword}"...`);
      setBatchProgress(Math.round(progress * 0.8)); // Use 80% for processing
      setProcessedKeywords(prev => [...prev, keyword]);
      
      // Simulate API call time
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000));
    }

    // Final processing stages
    setCurrentStage('Aggregating trend data...');
    setBatchProgress(85);
    await new Promise(resolve => setTimeout(resolve, 800));

    setCurrentStage('Calculating insights...');
    setBatchProgress(95);
    await new Promise(resolve => setTimeout(resolve, 600));

    setCurrentStage('Analysis complete!');
    setBatchProgress(100);
  };

  // Analyze keywords mutation
  const analyzeKeywords = useMutation({
    mutationFn: async (keywordList: string[]) => {
      if (!currentProject) throw new Error('No project selected');
      
      // Start batch processing simulation
      await simulateBatchProcessing(keywordList);
      
      // Convert array to comma-separated string as backend expects
      return api.googleTrends.getKeywordTrends({ 
        keywords: keywordList.join(','),
        timeframe: timeRange,
        geo: region
      });
    },
    onSuccess: () => {
      refetch();
      notifications.success('Analysis complete', 'Google Trends data has been analyzed successfully');
      setIsProcessing(false);
      setBatchProgress(0);
      setCurrentStage('');
      setProcessedKeywords([]);
    },
    onError: (error) => {
      notifications.handleApiError(error, 'Failed to analyze keywords');
      setIsProcessing(false);
      setBatchProgress(0);
      setCurrentStage('');
      setProcessedKeywords([]);
    },
  });

  const handleAddKeyword = () => {
    if (currentKeyword.trim() && !keywords.includes(currentKeyword.trim())) {
      setKeywords([...keywords.filter((k: string) => k), currentKeyword.trim()]);
      setCurrentKeyword('');
    }
  };

  const handleRemoveKeyword = (index: number) => {
    setKeywords(keywords.filter((_, i) => i !== index));
  };

  const handleAnalyze = () => {
    const validKeywords = keywords.filter((k: string) => k.trim());
    if (validKeywords.length === 0) {
      notifications.error('No keywords', 'Please add at least one keyword to analyze.');
      return;
    }
    analyzeKeywords.mutate(validKeywords);
  };

  // Mock data for demonstration
  const mockData = {
    keywords: ['seo tools', 'keyword research', 'backlink checker'],
    time_range: '90d',
    region: 'US',
    trend_data: [
      { date: '2024-10-15', 'seo tools': 75, 'keyword research': 62, 'backlink checker': 45 },
      { date: '2024-10-22', 'seo tools': 78, 'keyword research': 65, 'backlink checker': 48 },
      { date: '2024-10-29', 'seo tools': 82, 'keyword research': 68, 'backlink checker': 52 },
      { date: '2024-11-05', 'seo tools': 79, 'keyword research': 70, 'backlink checker': 50 },
      { date: '2024-11-12', 'seo tools': 85, 'keyword research': 72, 'backlink checker': 55 },
      { date: '2024-11-19', 'seo tools': 88, 'keyword research': 75, 'backlink checker': 58 },
      { date: '2024-11-26', 'seo tools': 90, 'keyword research': 78, 'backlink checker': 60 },
      { date: '2024-12-03', 'seo tools': 87, 'keyword research': 76, 'backlink checker': 57 },
      { date: '2024-12-10', 'seo tools': 92, 'keyword research': 80, 'backlink checker': 62 },
      { date: '2024-12-17', 'seo tools': 95, 'keyword research': 82, 'backlink checker': 65 },
    ],
    related_queries: {
      'seo tools': [
        { query: 'best seo tools 2024', value: 100 },
        { query: 'free seo tools', value: 85 },
        { query: 'seo audit tools', value: 72 },
        { query: 'ahrefs vs semrush', value: 68 },
      ],
      'keyword research': [
        { query: 'keyword research tools', value: 95 },
        { query: 'how to do keyword research', value: 82 },
        { query: 'keyword difficulty', value: 75 },
        { query: 'long tail keywords', value: 70 },
      ],
    },
    regional_data: [
      { region: 'California', interest: 95 },
      { region: 'New York', interest: 88 },
      { region: 'Texas', interest: 82 },
      { region: 'Florida', interest: 78 },
      { region: 'Illinois', interest: 75 },
    ],
    rising_topics: [
      { topic: 'AI SEO tools', growth: '+250%', category: 'Technology' },
      { topic: 'Voice search optimization', growth: '+180%', category: 'Search' },
      { topic: 'Core Web Vitals', growth: '+150%', category: 'Technical' },
      { topic: 'SGE optimization', growth: '+120%', category: 'AI' },
    ],
  };

  const data = trendsData || mockData;

  if (!currentProject) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-2">
            <h3 className="text-2xl font-semibold">No Project Selected</h3>
            <p className="text-muted-foreground">
              Please select a project from the dropdown above to analyze Google Trends.
            </p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (isLoading) {
    return (
      <DashboardLayout>
        <LoadingState message="Loading Google Trends data..." size="lg" fullHeight />
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-8">
          <ErrorState
            error={error}
            title="Failed to load trends data"
            description="We couldn't fetch Google Trends data. Please try again."
            onRetry={() => refetch()}
          />
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
            <h1 className="text-3xl font-bold tracking-tight">Google Trends</h1>
            <p className="text-muted-foreground">
              Analyze search trends and discover rising topics
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

        {/* Keyword Input */}
        <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Analyze Keywords
              {isProcessing && (
                <Badge variant="secondary" className="animate-pulse">
                  <Activity className="h-3 w-3 mr-1" />
                  Processing
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              {isProcessing 
                ? currentStage || 'Processing keyword batch analysis...'
                : 'Add up to 5 keywords to compare their search trends'
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Batch Processing Progress */}
              {isProcessing && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-blue-800">{currentStage}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {Math.round(batchProgress)}%
                      </Badge>
                    </div>
                  </div>
                  <Progress value={batchProgress} className="h-2 mb-3" />
                  
                  {/* Keyword processing status */}
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-blue-800">
                      Processing {keywords.filter(k => k).length} keywords:
                    </p>
                    <div className="grid grid-cols-1 gap-2">
                      {keywords.filter(k => k).map((keyword, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm">
                          {processedKeywords.includes(keyword) ? (
                            <div className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                              <span className="text-white text-xs">✓</span>
                            </div>
                          ) : currentStage.includes(keyword) ? (
                            <div className="w-4 h-4 rounded-full bg-blue-500 animate-pulse"></div>
                          ) : (
                            <div className="w-4 h-4 rounded-full bg-gray-300"></div>
                          )}
                          <span className={processedKeywords.includes(keyword) ? 'text-green-700' : 
                                         currentStage.includes(keyword) ? 'text-blue-700' : 'text-gray-500'}>
                            {keyword}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              
              <div className="flex gap-2">
                <Input
                  placeholder="Enter keyword..."
                  value={currentKeyword}
                  onChange={(e) => setCurrentKeyword(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddKeyword()}
                  className="flex-1"
                  disabled={isProcessing}
                />
                <Button 
                  onClick={handleAddKeyword}
                  disabled={!currentKeyword.trim() || keywords.filter((k: string) => k).length >= 5 || isProcessing}
                >
                  <PlusCircle className="mr-2 h-4 w-4" />
                  Add
                </Button>
              </div>

              {keywords.filter((k: string) => k).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {keywords.filter((k: string) => k).map((keyword: string, index: number) => (
                    <Badge key={index} variant="secondary" className="px-3 py-1">
                      {keyword}
                      {!isProcessing && (
                        <button
                          onClick={() => handleRemoveKeyword(index)}
                          className="ml-2 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      )}
                    </Badge>
                  ))}
                </div>
              )}

              <div className="flex gap-4">
                <Select value={timeRange} onValueChange={setTimeRange} disabled={isProcessing}>
                  <SelectTrigger className="w-[180px]">
                    <Calendar className="mr-2 h-4 w-4" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7d">Last 7 days</SelectItem>
                    <SelectItem value="30d">Last 30 days</SelectItem>
                    <SelectItem value="90d">Last 90 days</SelectItem>
                    <SelectItem value="12m">Last 12 months</SelectItem>
                    <SelectItem value="5y">Last 5 years</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={region} onValueChange={setRegion} disabled={isProcessing}>
                  <SelectTrigger className="w-[180px]">
                    <Globe className="mr-2 h-4 w-4" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="US">United States</SelectItem>
                    <SelectItem value="GB">United Kingdom</SelectItem>
                    <SelectItem value="CA">Canada</SelectItem>
                    <SelectItem value="AU">Australia</SelectItem>
                    <SelectItem value="GLOBAL">Worldwide</SelectItem>
                  </SelectContent>
                </Select>

                <Button 
                  onClick={handleAnalyze}
                  disabled={keywords.filter((k: string) => k).length === 0 || isProcessing}
                  className="gradient-primary"
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      Analyze Trends
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Trends Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Search Interest Over Time</CardTitle>
            <CardDescription>
              Relative search volume (0-100) for tracked keywords
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsLineChart data={data.trend_data}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis 
                    dataKey="date" 
                    className="text-xs"
                    tickFormatter={(value: string) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis className="text-xs" />
                  <Tooltip
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                    labelFormatter={(value: string) => new Date(value).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                  />
                  <Legend />
                  {data.keywords.map((keyword: string, index: number) => (
                    <Line
                      key={keyword}
                      type="monotone"
                      dataKey={keyword}
                      stroke={['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'][index % 4]}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 6 }}
                    />
                  ))}
                </RechartsLineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Additional Insights */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Rising Topics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-yellow-500" />
                Rising Topics
              </CardTitle>
              <CardDescription>
                Trending topics with significant growth
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.rising_topics.map((topic: any, index: number) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-lg border">
                    <div>
                      <p className="font-medium">{topic.topic}</p>
                      <p className="text-xs text-muted-foreground">{topic.category}</p>
                    </div>
                    <Badge variant="default" className="font-mono">
                      <TrendingUp className="mr-1 h-3 w-3" />
                      {topic.growth}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Regional Interest */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-blue-500" />
                Regional Interest
              </CardTitle>
              <CardDescription>
                Search interest by region
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.regional_data.map((region: any, index: number) => (
                  <div key={index} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{region.region}</span>
                      <span className="text-sm text-muted-foreground">{region.interest}%</span>
                    </div>
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${region.interest}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Related Queries */}
        <Tabs defaultValue={data.keywords[0]} className="space-y-4">
          <TabsList>
            {data.keywords.map((keyword: string) => (
              <TabsTrigger key={keyword} value={keyword}>
                {keyword}
              </TabsTrigger>
            ))}
          </TabsList>

          {data.keywords.map((keyword: string) => (
            <TabsContent key={keyword} value={keyword}>
              <Card>
                <CardHeader>
                  <CardTitle>Related Queries for &quot;{keyword}&quot;</CardTitle>
                  <CardDescription>
                    Top search queries related to this keyword
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 md:grid-cols-2">
                    {data.related_queries[keyword]?.map((query: any, index: number) => (
                      <div key={index} className="flex items-center justify-between p-3 rounded-lg border">
                        <span className="text-sm">{query.query}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-secondary rounded-full h-2">
                            <div
                              className="bg-primary h-2 rounded-full"
                              style={{ width: `${query.value}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium w-12 text-right">{query.value}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </DashboardLayout>
  );
}

export default withAuth(GoogleTrendsPage);