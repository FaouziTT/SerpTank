'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  Youtube,
  TrendingUp,
  Users,
  Eye,
  ThumbsUp,
  MessageSquare,
  PlayCircle,
  Calendar,
  BarChart3,
  Activity,
  Sparkles,
  RefreshCw,
  Download,
  Link2,
  Clock,
  Award
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { notifications } from '@/lib/notification-service';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { formatNumber, formatDate } from '@/lib/utils';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

function YouTubeAnalysisPage() {
  const [channelUrl, setChannelUrl] = useState('');
  const { currentProject } = useProject();

  // Fetch YouTube analytics - disabled by default until channel is specified
  const { data: analyticsData, isLoading, error, refetch } = useQuery({
    queryKey: ['youtube-analytics', currentProject?.id],
    queryFn: async () => {
      return null; // No default channel to analyze
    },
    enabled: false, // Disabled until user specifies a channel
  });

  // Analyze channel mutation
  const analyzeChannel = useMutation({
    mutationFn: async (channelId: string) => {
      if (!currentProject) throw new Error('No project selected');
      const response = await api.youtube.getChannelInfo({ channel_id: channelId });
      // Handle backend response structure
      if (response.data?.success === false) {
        throw new Error(response.data.error || 'Failed to analyze channel');
      }
      return response.data?.data || response.data;
    },
    onSuccess: () => {
      refetch();
      notifications.success('Analysis complete', 'YouTube channel data has been fetched.');
      setChannelUrl('');
    },
    onError: (error) => {
      notifications.handleApiError(error, 'Failed to analyze channel');
    },
  });

  const handleAnalyze = () => {
    if (!channelUrl.trim()) {
      notifications.error('No channel URL', 'Please enter a YouTube channel URL.');
      return;
    }
    
    // Extract channel ID from URL
    const channelId = channelUrl.includes('@') 
      ? channelUrl.split('@')[1].split('/')[0]
      : channelUrl.split('/channel/')[1]?.split('/')[0] || channelUrl;
    
    analyzeChannel.mutate(channelId);
  };

  // Mock data for demonstration
  const mockData = {
    channel: {
      id: 'UC_x5XG1OV2P6uZZ5FSM9Ttw',
      title: 'Google for Developers',
      description: 'The Google Developers channel features talks...',
      subscriber_count: 2340000,
      video_count: 5678,
      view_count: 892340000,
      created_at: '2007-08-23T00:00:00Z',
      thumbnail_url: 'https://yt3.googleusercontent.com/...',
      custom_url: '@GoogleDevelopers',
    },
    recent_videos: [
      {
        id: 'abc123',
        title: 'What\'s new in Web Development',
        views: 125000,
        likes: 8900,
        comments: 456,
        duration: 'PT15M32S',
        published_at: '2024-01-10T18:00:00Z',
        engagement_rate: 7.5,
      },
      {
        id: 'def456',
        title: 'Building with AI: A Developer\'s Guide',
        views: 98000,
        likes: 7200,
        comments: 389,
        duration: 'PT22M18S',
        published_at: '2024-01-08T18:00:00Z',
        engagement_rate: 7.8,
      },
      {
        id: 'ghi789',
        title: 'Chrome DevTools Tips and Tricks',
        views: 156000,
        likes: 12300,
        comments: 678,
        duration: 'PT18M45S',
        published_at: '2024-01-05T18:00:00Z',
        engagement_rate: 8.3,
      },
    ],
    performance_trends: [
      { date: '2024-01-09', views: 245000, subscribers: 2200 },
      { date: '2024-01-10', views: 268000, subscribers: 2350 },
      { date: '2024-01-11', views: 289000, subscribers: 2450 },
      { date: '2024-01-12', views: 256000, subscribers: 2300 },
      { date: '2024-01-13', views: 198000, subscribers: 1800 },
      { date: '2024-01-14', views: 205000, subscribers: 1950 },
      { date: '2024-01-15', views: 312000, subscribers: 2800 },
    ],
    content_categories: [
      { category: 'Web Development', videos: 156, percentage: 35 },
      { category: 'Mobile Development', videos: 98, percentage: 22 },
      { category: 'AI/ML', videos: 89, percentage: 20 },
      { category: 'Cloud Computing', videos: 67, percentage: 15 },
      { category: 'Other', videos: 36, percentage: 8 },
    ],
    seo_opportunities: [
      {
        type: 'title_optimization',
        title: 'Optimize Video Titles',
        description: '23 videos could benefit from keyword-rich titles',
        impact: 'high',
        videos_affected: 23,
      },
      {
        type: 'description_enhancement',
        title: 'Enhance Descriptions',
        description: '45 videos have descriptions under 200 characters',
        impact: 'medium',
        videos_affected: 45,
      },
      {
        type: 'thumbnail_consistency',
        title: 'Improve Thumbnails',
        description: 'Inconsistent thumbnail style across recent videos',
        impact: 'medium',
        videos_affected: 12,
      },
    ],
    competitor_comparison: {
      subscriber_growth: '+12.5%',
      view_rate: '+8.3%',
      engagement_rate: '+2.1%',
      upload_frequency: '-15%',
    },
  };

  // Transform backend data to match frontend expectations
  const transformYouTubeData = (data: any) => {
    if (!data) return null;
    
    // If data has the expected structure, return as is
    if (data.channel && data.recent_videos) {
      return data;
    }
    
    // Transform backend response to match frontend structure
    return {
      channel: data.channel || data,
      recent_videos: data.recent_videos || [],
      performance_trends: data.performance_trends || mockData.performance_trends,
      content_categories: data.content_categories || mockData.content_categories,
      seo_opportunities: data.seo_opportunities || mockData.seo_opportunities,
      competitor_comparison: data.competitor_comparison || mockData.competitor_comparison,
    };
  };
  
  const data = transformYouTubeData(analyticsData) || mockData;
  const COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];

  if (!currentProject) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-2">
            <h3 className="text-2xl font-semibold">No Project Selected</h3>
            <p className="text-muted-foreground">
              Please select a project from the dropdown above to analyze YouTube channels.
            </p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (isLoading) {
    return (
      <DashboardLayout>
        <LoadingState message="Loading YouTube analytics..." size="lg" fullHeight />
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-8">
          <ErrorState
            error={error}
            title="Failed to load analytics"
            description="We couldn't fetch YouTube analytics data. Please try again."
            onRetry={() => refetch()}
          />
        </div>
      </DashboardLayout>
    );
  }

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'text-red-600';
      case 'medium':
        return 'text-yellow-600';
      default:
        return 'text-green-600';
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">YouTube Analytics</h1>
            <p className="text-muted-foreground">
              Analyze YouTube channels and optimize video SEO
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Export Report
            </Button>
          </div>
        </div>

        {/* Channel Input */}
        <Card className="border-red-500/20 bg-gradient-to-br from-card to-red-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Youtube className="h-5 w-5 text-red-500" />
              Analyze YouTube Channel
            </CardTitle>
            <CardDescription>
              Enter a YouTube channel URL to analyze its performance and SEO
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="https://youtube.com/@channelname or channel ID"
                value={channelUrl}
                onChange={(e) => setChannelUrl(e.target.value)}
                className="flex-1"
              />
              <Button 
                onClick={handleAnalyze}
                disabled={!channelUrl.trim() || analyzeChannel.isPending}
                className="gradient-primary"
              >
                {analyzeChannel.isPending ? (
                  <>
                    <Sparkles className="mr-2 h-4 w-4 animate-pulse" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Analyze Channel
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {data.channel && (
          <>
            {/* Channel Overview */}
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center">
                      <Youtube className="h-8 w-8 text-red-500" />
                    </div>
                    <div>
                      <CardTitle className="text-2xl">{data.channel.title}</CardTitle>
                      <CardDescription className="flex items-center gap-2 mt-1">
                        <Link2 className="h-3 w-3" />
                        {data.channel.custom_url}
                      </CardDescription>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    Created {formatDate(data.channel.created_at)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Subscribers</p>
                    <p className="text-2xl font-bold">{formatNumber(data.channel.subscriber_count)}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Views</p>
                    <p className="text-2xl font-bold">{formatNumber(data.channel.view_count)}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Videos</p>
                    <p className="text-2xl font-bold">{formatNumber(data.channel.video_count)}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Avg Views/Video</p>
                    <p className="text-2xl font-bold">
                      {formatNumber(Math.round(data.channel.view_count / data.channel.video_count))}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Performance Trends */}
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Performance Trends</CardTitle>
                  <CardDescription>
                    Daily views and subscriber growth
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={data.performance_trends}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis 
                          dataKey="date" 
                          className="text-xs"
                          tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        />
                        <YAxis yAxisId="left" className="text-xs" />
                        <YAxis yAxisId="right" orientation="right" className="text-xs" />
                        <Tooltip
                          contentStyle={{ 
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px'
                          }}
                        />
                        <Legend />
                        <Line
                          yAxisId="left"
                          type="monotone"
                          dataKey="views"
                          stroke="#8b5cf6"
                          strokeWidth={2}
                          dot={false}
                          name="Views"
                        />
                        <Line
                          yAxisId="right"
                          type="monotone"
                          dataKey="subscribers"
                          stroke="#10b981"
                          strokeWidth={2}
                          dot={false}
                          name="New Subscribers"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Content Categories</CardTitle>
                  <CardDescription>
                    Distribution of video content by category
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={data.content_categories}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ category, percentage }) => `${category} (${percentage}%)`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="videos"
                        >
                          {data.content_categories.map((entry: any, index: number) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Recent Videos Performance */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Videos Performance</CardTitle>
                <CardDescription>
                  Analyze the performance of recently published videos
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.recent_videos.map((video: any) => (
                    <div key={video.id} className="flex items-start justify-between p-4 rounded-lg border">
                      <div className="flex-1 space-y-2">
                        <h4 className="font-semibold">{video.title}</h4>
                        <div className="flex items-center gap-6 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Eye className="h-3 w-3" />
                            {formatNumber(video.views)} views
                          </span>
                          <span className="flex items-center gap-1">
                            <ThumbsUp className="h-3 w-3" />
                            {formatNumber(video.likes)} likes
                          </span>
                          <span className="flex items-center gap-1">
                            <MessageSquare className="h-3 w-3" />
                            {formatNumber(video.comments)} comments
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {video.duration.replace('PT', '').replace('M', 'm ').replace('S', 's')}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Progress value={video.engagement_rate * 10} className="w-32 h-2" />
                          <span className="text-xs font-medium">{video.engagement_rate}% engagement</span>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {formatDate(video.published_at)}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* SEO Opportunities */}
            <Card>
              <CardHeader>
                <CardTitle>SEO Opportunities</CardTitle>
                <CardDescription>
                  Recommendations to improve video visibility and rankings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.seo_opportunities.map((opportunity: any, index: number) => (
                    <div key={index} className="flex items-start gap-4 p-4 rounded-lg border">
                      <div className={`rounded-full p-2 bg-primary/10`}>
                        <Sparkles className={`h-5 w-5 ${getImpactColor(opportunity.impact)}`} />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold">{opportunity.title}</h4>
                        <p className="text-sm text-muted-foreground mt-1">
                          {opportunity.description}
                        </p>
                        <div className="flex items-center gap-4 mt-2">
                          <Badge variant={opportunity.impact === 'high' ? 'destructive' : 'secondary'}>
                            {opportunity.impact} impact
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            {opportunity.videos_affected} videos affected
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Competitor Comparison */}
            <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="h-5 w-5 text-primary" />
                  Performance vs Competitors
                </CardTitle>
                <CardDescription>
                  How your channel compares to similar channels in your niche
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Subscriber Growth</p>
                    <p className={`text-2xl font-bold ${data.competitor_comparison.subscriber_growth.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                      {data.competitor_comparison.subscriber_growth}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">View Rate</p>
                    <p className={`text-2xl font-bold ${data.competitor_comparison.view_rate.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                      {data.competitor_comparison.view_rate}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Engagement Rate</p>
                    <p className={`text-2xl font-bold ${data.competitor_comparison.engagement_rate.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                      {data.competitor_comparison.engagement_rate}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Upload Frequency</p>
                    <p className={`text-2xl font-bold ${data.competitor_comparison.upload_frequency.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                      {data.competitor_comparison.upload_frequency}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}

export default withAuth(YouTubeAnalysisPage);