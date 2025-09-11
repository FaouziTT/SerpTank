'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DetailLayout } from '@/components/layout/detail-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  TrendingUp,
  TrendingDown,
  Globe,
  Youtube,
  Twitter,
  Facebook,
  Instagram,
  Linkedin,
  RefreshCw,
  Download,
  Search,
  BarChart3,
  Play,
  Users,
  MessageCircle,
  Heart,
  Share2,
  MapPin,
  Calendar,
  Zap,
  Eye
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { formatNumber, cn } from '@/lib/utils';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart, PieChart, Pie, Cell } from 'recharts';
import { useToast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';

// Component for Google Trends
function GoogleTrendsTab({ data, isLoading }: { data: any; isLoading: boolean }) {
  const [searchTerm, setSearchTerm] = useState('');

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
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

  // Mock data for Google Trends
  const trendingKeywords = [
    { keyword: 'AI SEO tools', trend: 85, change: 42, volume: 12500 },
    { keyword: 'voice search optimization', trend: 72, change: 28, volume: 8900 },
    { keyword: 'SGE impact on SEO', trend: 68, change: 156, volume: 6200 },
    { keyword: 'local SEO 2024', trend: 65, change: 15, volume: 15400 },
    { keyword: 'video SEO strategy', trend: 61, change: 32, volume: 9800 },
  ];

  const interestOverTime = Array.from({ length: 12 }, (_, i) => ({
    month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i],
    'AI SEO': Math.floor(Math.random() * 30) + 70,
    'voice search': Math.floor(Math.random() * 25) + 50,
    'local SEO': Math.floor(Math.random() * 20) + 60,
  }));

  const regionalData = [
    { region: 'United States', interest: 100, flag: '🇺🇸' },
    { region: 'United Kingdom', interest: 89, flag: '🇬🇧' },
    { region: 'Canada', interest: 78, flag: '🇨🇦' },
    { region: 'Australia', interest: 72, flag: '🇦🇺' },
    { region: 'India', interest: 65, flag: '🇮🇳' },
  ];

  return (
    <div className="space-y-6">
      {/* Search Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search for trending topics..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button>
              Search Trends
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Trending Keywords */}
      <Card>
        <CardHeader>
          <CardTitle>Trending Keywords</CardTitle>
          <CardDescription>
            Rising search terms in your industry
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {trendingKeywords.map((keyword, index) => (
              <div key={index} className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex-1">
                  <p className="font-medium">{keyword.keyword}</p>
                  <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                    <span>Volume: {formatNumber(keyword.volume)}</span>
                    <span>•</span>
                    <span>Trend score: {keyword.trend}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <TrendingUp className="h-4 w-4 text-green-500" />
                    <span className="text-sm font-medium text-green-500">+{keyword.change}%</span>
                  </div>
                  <Button size="sm" variant="outline">
                    Track Keyword
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Interest Over Time */}
        <Card>
          <CardHeader>
            <CardTitle>Interest Over Time</CardTitle>
            <CardDescription>
              Search trend patterns throughout the year
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={interestOverTime}>
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
                  <Line type="monotone" dataKey="AI SEO" stroke="#8b5cf6" strokeWidth={2} />
                  <Line type="monotone" dataKey="voice search" stroke="#06b6d4" strokeWidth={2} />
                  <Line type="monotone" dataKey="local SEO" stroke="#10b981" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Regional Interest */}
        <Card>
          <CardHeader>
            <CardTitle>Regional Interest</CardTitle>
            <CardDescription>
              Geographic distribution of search interest
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {regionalData.map((region, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{region.flag}</span>
                      <span className="font-medium">{region.region}</span>
                    </div>
                    <span className="text-sm font-medium">{region.interest}%</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div 
                      className="bg-primary h-2 rounded-full transition-all duration-500"
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
      <Card>
        <CardHeader>
          <CardTitle>Related Queries</CardTitle>
          <CardDescription>
            Discover related search terms and questions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 md:grid-cols-2">
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground">Rising Queries</h4>
              {[
                'ChatGPT SEO optimization',
                'SGE search results',
                'AI content detection',
                'Zero click searches 2024',
              ].map((query, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded border">
                  <span className="text-sm">{query}</span>
                  <Badge variant="secondary" className="text-xs">
                    +{Math.floor(Math.random() * 200 + 50)}%
                  </Badge>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground">Top Questions</h4>
              {[
                'How to optimize for SGE?',
                'What is E-E-A-T in SEO?',
                'Is AI content bad for SEO?',
                'How to do local SEO in 2024?',
              ].map((query, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded border">
                  <span className="text-sm">{query}</span>
                  <Button size="sm" variant="ghost" className="h-7 text-xs">
                    Create Content
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Component for YouTube Analytics
function YouTubeAnalyticsTab({ data, isLoading }: { data: any; isLoading: boolean }) {
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

  // Mock data for YouTube
  const trendingVideos = [
    {
      title: 'SEO in 2024: Complete Guide',
      channel: 'Digital Marketing Pro',
      views: 245000,
      likes: 12500,
      comments: 890,
      published: '2 weeks ago',
      thumbnail: '🎥',
    },
    {
      title: 'Google SGE Explained',
      channel: 'SEO News Daily',
      views: 189000,
      likes: 9200,
      comments: 567,
      published: '5 days ago',
      thumbnail: '📺',
    },
    {
      title: 'Local SEO Masterclass',
      channel: 'Marketing Academy',
      views: 156000,
      likes: 8900,
      comments: 445,
      published: '1 month ago',
      thumbnail: '🎬',
    },
    {
      title: 'AI Tools for SEO',
      channel: 'Tech SEO Guide',
      views: 134000,
      likes: 7600,
      comments: 390,
      published: '3 weeks ago',
      thumbnail: '📹',
    },
  ];

  const channelMetrics = {
    total_videos: 145,
    total_views: 2340000,
    avg_engagement: 5.8,
    subscriber_growth: 12.5,
  };

  const performanceData = Array.from({ length: 7 }, (_, i) => ({
    day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
    views: Math.floor(Math.random() * 5000) + 10000,
    engagement: Math.floor(Math.random() * 10) + 5,
  }));

  return (
    <div className="space-y-6">
      {/* Channel Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Videos
            </CardTitle>
            <Play className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{channelMetrics.total_videos}</div>
            <p className="text-xs text-muted-foreground">
              Analyzed videos
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Views
            </CardTitle>
            <Eye className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(channelMetrics.total_views)}</div>
            <p className="text-xs text-muted-foreground">
              Across all videos
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg Engagement
            </CardTitle>
            <Heart className="h-4 w-4 text-pink-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{channelMetrics.avg_engagement}%</div>
            <p className="text-xs text-muted-foreground">
              Likes & comments rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Growth Rate
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">+{channelMetrics.subscriber_growth}%</div>
            <p className="text-xs text-muted-foreground">
              Monthly growth
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Trending Videos */}
      <Card>
        <CardHeader>
          <CardTitle>Trending Videos in Your Niche</CardTitle>
          <CardDescription>
            Top performing videos related to your keywords
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {trendingVideos.map((video, index) => (
              <div key={index} className="flex items-start gap-4 p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="text-4xl">{video.thumbnail}</div>
                <div className="flex-1">
                  <p className="font-medium">{video.title}</p>
                  <p className="text-sm text-muted-foreground">{video.channel} • {video.published}</p>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <span className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      {formatNumber(video.views)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Heart className="h-3 w-3" />
                      {formatNumber(video.likes)}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageCircle className="h-3 w-3" />
                      {formatNumber(video.comments)}
                    </span>
                  </div>
                </div>
                <Button size="sm" variant="outline">
                  Analyze
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Performance Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Video Performance Trends</CardTitle>
          <CardDescription>
            Views and engagement over the past week
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="day" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Legend />
                <Bar dataKey="views" fill="#ff0000" radius={[8, 8, 0, 0]} />
                <Bar dataKey="engagement" fill="#8b5cf6" radius={[8, 8, 0, 0]} yAxisId="right" />
                <YAxis yAxisId="right" orientation="right" className="text-xs" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Video SEO Opportunities */}
      <Card>
        <CardHeader>
          <CardTitle>Video SEO Opportunities</CardTitle>
          <CardDescription>
            Optimize your video content for better visibility
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-4 rounded-lg border border-green-500/20 bg-green-500/5">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-5 w-5 text-green-500" />
                <h4 className="font-medium">Create Video Responses</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                5 trending topics in your niche have high video demand but low competition.
                Create video content to capture this traffic.
              </p>
              <Button size="sm" className="mt-3">
                View Topics
              </Button>
            </div>
            
            <div className="p-4 rounded-lg border border-blue-500/20 bg-blue-500/5">
              <div className="flex items-center gap-2 mb-2">
                <Youtube className="h-5 w-5 text-red-500" />
                <h4 className="font-medium">Optimize Existing Videos</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                12 of your videos are missing key SEO elements like timestamps,
                chapters, and optimized descriptions.
              </p>
              <Button size="sm" variant="outline" className="mt-3">
                Fix Issues
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Component for Social Media Insights
function SocialMediaInsightsTab({ data, isLoading }: { data: any; isLoading: boolean }) {
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
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Mock data for social media
  const socialMetrics = {
    total_mentions: 1234,
    sentiment_score: 78,
    engagement_rate: 4.5,
    share_of_voice: 23,
  };

  const platformDistribution = [
    { name: 'Twitter', value: 35, color: '#1DA1F2', icon: Twitter },
    { name: 'LinkedIn', value: 28, color: '#0077B5', icon: Linkedin },
    { name: 'Facebook', value: 20, color: '#1877F2', icon: Facebook },
    { name: 'Instagram', value: 17, color: '#E4405F', icon: Instagram },
  ];

  const brandMentions = [
    {
      platform: 'Twitter',
      author: '@marketingguru',
      content: 'Just discovered @YourBrand SEO tools - game changer for local businesses!',
      engagement: 145,
      sentiment: 'positive',
      time: '2 hours ago',
    },
    {
      platform: 'LinkedIn',
      author: 'Sarah Johnson',
      content: 'Great insights from the team at YourBrand on the latest SEO trends.',
      engagement: 89,
      sentiment: 'positive',
      time: '5 hours ago',
    },
    {
      platform: 'Facebook',
      author: 'Digital Marketing Group',
      content: 'Anyone tried YourBrand for technical SEO audits? Looking for recommendations.',
      engagement: 67,
      sentiment: 'neutral',
      time: '1 day ago',
    },
    {
      platform: 'Instagram',
      author: '@seo_tips_daily',
      content: 'New blog post about SEO tools featuring @YourBrand #SEO #DigitalMarketing',
      engagement: 234,
      sentiment: 'positive',
      time: '2 days ago',
    },
  ];

  const sentimentData = [
    { sentiment: 'Positive', count: 78, color: '#10b981' },
    { sentiment: 'Neutral', count: 18, color: '#6b7280' },
    { sentiment: 'Negative', count: 4, color: '#ef4444' },
  ];

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-500';
      case 'neutral': return 'text-gray-500';
      case 'negative': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getSentimentBadge = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'neutral': return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
      case 'negative': return 'bg-red-500/10 text-red-500 border-red-500/20';
      default: return '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Social Metrics Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Brand Mentions
            </CardTitle>
            <MessageCircle className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(socialMetrics.total_mentions)}</div>
            <div className="flex items-center space-x-1 text-xs">
              <TrendingUp className="h-3 w-3 text-green-500" />
              <span className="text-green-500">+23%</span>
              <span className="text-muted-foreground">from last month</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Sentiment Score
            </CardTitle>
            <Heart className="h-4 w-4 text-pink-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{socialMetrics.sentiment_score}%</div>
            <p className="text-xs text-muted-foreground">
              Positive sentiment
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Engagement Rate
            </CardTitle>
            <Users className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{socialMetrics.engagement_rate}%</div>
            <p className="text-xs text-muted-foreground">
              Average across platforms
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Share of Voice
            </CardTitle>
            <Share2 className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{socialMetrics.share_of_voice}%</div>
            <p className="text-xs text-muted-foreground">
              In your industry
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Platform Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Platform Distribution</CardTitle>
            <CardDescription>
              Where your brand is being mentioned
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={platformDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {platformDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Sentiment Analysis */}
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Analysis</CardTitle>
            <CardDescription>
              How people feel about your brand
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {sentimentData.map((item, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{item.sentiment}</span>
                    <span className="text-sm text-muted-foreground">{item.count}%</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-3">
                    <div 
                      className="h-3 rounded-full transition-all duration-500"
                      style={{ 
                        width: `${item.count}%`,
                        backgroundColor: item.color 
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-4 rounded-lg bg-green-500/5 border border-green-500/20">
              <p className="text-sm">
                <span className="font-medium text-green-500">Great sentiment!</span> Your brand
                perception is very positive across social media platforms.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Mentions */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Brand Mentions</CardTitle>
          <CardDescription>
            Latest social media mentions and conversations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {brandMentions.map((mention, index) => (
              <div key={index} className="flex items-start gap-4 p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="mt-1">
                  {mention.platform === 'Twitter' && <Twitter className="h-5 w-5 text-[#1DA1F2]" />}
                  {mention.platform === 'LinkedIn' && <Linkedin className="h-5 w-5 text-[#0077B5]" />}
                  {mention.platform === 'Facebook' && <Facebook className="h-5 w-5 text-[#1877F2]" />}
                  {mention.platform === 'Instagram' && <Instagram className="h-5 w-5 text-[#E4405F]" />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <p className="font-medium text-sm">{mention.author}</p>
                    <Badge className={getSentimentBadge(mention.sentiment)}>
                      {mention.sentiment}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{mention.content}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                    <span>{mention.time}</span>
                    <span>•</span>
                    <span>{mention.engagement} engagements</span>
                  </div>
                </div>
                <Button size="sm" variant="outline">
                  Respond
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Social SEO Tips */}
      <Card>
        <CardHeader>
          <CardTitle>Social SEO Opportunities</CardTitle>
          <CardDescription>
            Leverage social signals for better SEO performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-4 rounded-lg border border-blue-500/20 bg-blue-500/5">
              <div className="flex items-center gap-2 mb-2">
                <Share2 className="h-5 w-5 text-blue-500" />
                <h4 className="font-medium">Increase Social Shares</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Your top content has low social share rates. Add social sharing buttons
                and create shareable quotes to boost distribution.
              </p>
            </div>
            
            <div className="p-4 rounded-lg border border-purple-500/20 bg-purple-500/5">
              <div className="flex items-center gap-2 mb-2">
                <Users className="h-5 w-5 text-purple-500" />
                <h4 className="font-medium">Build Brand Authority</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Engage with industry conversations on LinkedIn and Twitter to establish
                thought leadership and earn quality backlinks.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TrendsAnalyticsPage() {
  const [selectedPlatform, setSelectedPlatform] = useState('all');
  const { currentProject } = useProject();
  const { toast } = useToast();

  // Fetch trends data
  const { data: trendsData, isLoading, refetch } = useQuery({
    queryKey: ['trends-analytics', currentProject?.id, selectedPlatform],
    queryFn: async () => {
      if (!currentProject?.id) return null;
      
      // Fetch data based on selected platform
      if (selectedPlatform === 'google' || selectedPlatform === 'all') {
        const googleTrends = await api.googleTrends.getTrendingKeywords();
      }
      if (selectedPlatform === 'youtube' || selectedPlatform === 'all') {
        const youtubeData = await api.youtube.getTrendingVideos();
      }
      if (selectedPlatform === 'social' || selectedPlatform === 'all') {
        const socialData = await api.socialMedia.getUnifiedDashboard();
      }
      
      return {}; // Return combined data
    },
    enabled: !!currentProject?.id,
  });

  const mockData = {};
  const data = trendsData || mockData;

  if (!currentProject) {
    return (
      <DetailLayout
        title="Trends Analytics"
        breadcrumbs={[
          { label: 'Analytics', href: '/analytics' },
          { label: 'Trends' },
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
                    Please select a project from the dropdown above to view trends analytics.
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
      id: 'google-trends',
      label: 'Google Trends',
      icon: Globe,
      content: <GoogleTrendsTab data={data} isLoading={isLoading} />,
    },
    {
      id: 'youtube',
      label: 'YouTube',
      icon: Youtube,
      content: <YouTubeAnalyticsTab data={data} isLoading={isLoading} />,
    },
    {
      id: 'social-media',
      label: 'Social Media',
      icon: Users,
      content: <SocialMediaInsightsTab data={data} isLoading={isLoading} />,
    },
  ];

  return (
    <DetailLayout
      title="Trends Analytics"
      breadcrumbs={[
        { label: 'Analytics', href: '/analytics' },
        { label: 'Trends' },
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
              description: 'Your trends analytics report is being generated.',
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
          icon: TrendingUp,
        },
        {
          label: 'Tracking',
          value: `${currentProject.name} across all platforms`,
        },
      ]}
    />
  );
}

export default withAuth(TrendsAnalyticsPage);