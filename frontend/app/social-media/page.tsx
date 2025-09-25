'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { DashboardPageHeader } from '@/components/layout/dashboard-page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/components/ui/use-toast';
import {
  Twitter,
  Facebook,
  Instagram,
  Linkedin,
  TrendingUp,
  Users,
  MessageSquare,
  Share2,
  Calendar,
  BarChart3,
  Link2,
  Settings,
  Loader2,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  Download
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { useProject } from '@/lib/project-context';

interface SocialAccount {
  id: string;
  platform: 'twitter' | 'facebook' | 'instagram' | 'linkedin';
  username: string;
  connected: boolean;
  followers: number;
  posts: number;
  engagement_rate: number;
}

interface SocialPost {
  id: string;
  platform: string;
  content: string;
  url: string;
  published_at: string;
  likes: number;
  shares: number;
  comments: number;
  seo_impact_score: number;
}

// Helper function to transform dashboard data to accounts format
function transformDashboardToAccounts(dashboard: any): SocialAccount[] {
  const accounts: SocialAccount[] = [];

  if (dashboard.platforms) {
    Object.entries(dashboard.platforms).forEach(([platform, data]: [string, any]) => {
      const isConnected = data.status === 'active';
      accounts.push({
        id: platform,
        platform: platform as 'twitter' | 'facebook' | 'instagram' | 'linkedin',
        username: data.page_name || data.company_name || `@${platform}`,
        connected: isConnected,
        followers: data.followers || 0,
        posts: data.posts || 0,
        engagement_rate: data.engagement_rate || data.engagement || 0
      });
    });
  }

  // Add common platforms if not present
  const platformDefaults = [
    { platform: 'twitter', username: '@yourhandle' },
    { platform: 'facebook', username: 'Your Page' },
    { platform: 'instagram', username: '@yourhandle' },
    { platform: 'linkedin', username: 'Your Company' }
  ];

  platformDefaults.forEach(({ platform, username }) => {
    if (!accounts.find(acc => acc.platform === platform)) {
      accounts.push({
        id: platform,
        platform: platform as any,
        username,
        connected: false,
        followers: 0,
        posts: 0,
        engagement_rate: 0
      });
    }
  });

  return accounts;
}

// Helper function to extract recent posts from dashboard data
function extractRecentPosts(dashboard: any, selectedPlatform: string): SocialPost[] {
  const posts: SocialPost[] = [];

  if (!dashboard.platforms) return posts;

  Object.entries(dashboard.platforms).forEach(([platform, data]: [string, any]) => {
    if (selectedPlatform !== 'all' && platform !== selectedPlatform) return;
    if (data.status !== 'active') return;

    // Extract Facebook posts
    if (platform === 'facebook' && data.top_posts) {
      data.top_posts.forEach((post: any, index: number) => {
        posts.push({
          id: `fb-${index}`,
          platform: 'facebook',
          content: post.message || post.story || 'Facebook post content',
          url: post.permalink_url || `https://facebook.com/post/${post.id}`,
          published_at: post.created_time || new Date().toISOString(),
          likes: post.likes_count || 0,
          shares: post.shares_count || 0,
          comments: post.comments_count || 0,
          seo_impact_score: calculateSeoImpactScore(post)
        });
      });
    }

    // Extract LinkedIn updates
    if (platform === 'linkedin' && data.recent_updates) {
      data.recent_updates.forEach((update: any, index: number) => {
        posts.push({
          id: `li-${index}`,
          platform: 'linkedin',
          content: update.text || update.content || 'LinkedIn update content',
          url: update.url || `https://linkedin.com/posts/${update.id}`,
          published_at: update.published_at || new Date().toISOString(),
          likes: update.like_count || 0,
          shares: update.share_count || 0,
          comments: update.comment_count || 0,
          seo_impact_score: calculateSeoImpactScore(update)
        });
      });
    }

    // Extract Twitter mentions as posts
    if (platform === 'twitter' && dashboard.brand_mentions?.platforms?.twitter?.mentions) {
      dashboard.brand_mentions.platforms.twitter.mentions.slice(0, 5).forEach((mention: any, index: number) => {
        posts.push({
          id: `tw-${index}`,
          platform: 'twitter',
          content: mention.text || 'Twitter mention',
          url: mention.url || `https://twitter.com/status/${mention.id}`,
          published_at: mention.created_at || new Date().toISOString(),
          likes: mention.metrics?.like_count || 0,
          shares: mention.metrics?.retweet_count || 0,
          comments: mention.metrics?.reply_count || 0,
          seo_impact_score: calculateSeoImpactScore(mention)
        });
      });
    }
  });

  return posts.sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime());
}

// Helper function to calculate SEO impact score
function calculateSeoImpactScore(post: any): number {
  const likes = post.likes_count || post.like_count || post.metrics?.like_count || 0;
  const shares = post.shares_count || post.share_count || post.metrics?.retweet_count || 0;
  const comments = post.comments_count || post.comment_count || post.metrics?.reply_count || 0;

  // Simple scoring algorithm
  const engagementScore = (likes * 1) + (shares * 3) + (comments * 2);
  const score = Math.min(100, Math.max(0, Math.round(engagementScore / 10)));

  return score;
}

function SocialMediaPage() {
  const { toast } = useToast();
  const { currentProject } = useProject();
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');

  // Fetch unified social dashboard data
  const { data: socialDashboard, isLoading: dashboardLoading, error: dashboardError } = useQuery({
    queryKey: ['social-dashboard', currentProject?.url, currentProject?.name],
    queryFn: async () => {
      if (!currentProject?.url || !currentProject?.name) return null;

      const domain = new URL(currentProject.url).hostname;
      const response = await api.socialMedia.getUnifiedDashboard();

      // Handle backend response structure
      if (response.data?.success === false) {
        throw new Error(response.data.error || 'Failed to fetch social dashboard');
      }

      return response.data?.data || response.data;
    },
    enabled: !!currentProject?.url && !!currentProject?.name,
  });

  // Transform dashboard data to accounts format for compatibility
  const accounts = socialDashboard ? transformDashboardToAccounts(socialDashboard) : [];

  // Extract recent posts from social dashboard data
  const posts = socialDashboard ? extractRecentPosts(socialDashboard, selectedPlatform) : [];

  // Extract brand mentions for recent activity
  const { data: brandMentions, isLoading: mentionsLoading } = useQuery({
    queryKey: ['brand-mentions', currentProject?.name],
    queryFn: async () => {
      if (!currentProject?.name) return null;

      const response = await api.socialMedia.getBrandMentions({
        brand: currentProject.name,
        platforms: ['twitter', 'facebook', 'linkedin']
      });

      if (response.data?.success === false) {
        throw new Error(response.data.error || 'Failed to fetch brand mentions');
      }

      return response.data?.data || response.data;
    },
    enabled: !!currentProject?.name,
  });

  // Connect account mutation
  const connectAccount = useMutation({
    mutationFn: async (platform: string) => {
      if (!currentProject) throw new Error('No project selected');

      // Add social media credential through project settings
      const response = await api.settings.project.addSocialMedia(currentProject.id, {
        platform,
        credentials: {} // OAuth flow would be handled separately
      });

      return response.data;
    },
    onSuccess: (_, platform) => {
      toast({
        title: "Connection initiated",
        description: `${platform} account connection has been initiated. Please complete the OAuth flow.`,
      });
      // Refresh the dashboard data
      // refetch();
    },
    onError: (error) => {
      toast({
        title: "Connection failed",
        description: `Failed to connect ${platform} account. Please try again.`,
        variant: "destructive"
      });
    }
  });

  // Disconnect account mutation
  const disconnectAccount = useMutation({
    mutationFn: async (accountId: string) => {
      // Social media disconnect would be implemented through project settings
      return api.settings.project.deleteSocialMedia(currentProject?.id || '', accountId);
    },
    onSuccess: () => {
      toast({
        title: "Account disconnected",
        description: "Social media account has been disconnected.",
      });
    }
  });

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'twitter': return <Twitter className="h-5 w-5" />;
      case 'facebook': return <Facebook className="h-5 w-5" />;
      case 'instagram': return <Instagram className="h-5 w-5" />;
      case 'linkedin': return <Linkedin className="h-5 w-5" />;
      default: return <Share2 className="h-5 w-5" />;
    }
  };

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'twitter': return 'text-blue-400';
      case 'facebook': return 'text-blue-600';
      case 'instagram': return 'text-pink-600';
      case 'linkedin': return 'text-blue-700';
      default: return 'text-gray-600';
    }
  };

  if (!currentProject) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <div className="text-center space-y-2">
            <h3 className="text-2xl font-semibold">No Project Selected</h3>
            <p className="text-muted-foreground">
              Please select a project from the dropdown above to view social media analytics.
            </p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
        <div className="space-y-6">
        {/* Optimized Header - Research-based 2025 standards */}
        <DashboardPageHeader
          title="Social Media"
          description="Connect and analyze your social media presence for SEO insights"
          badge={{
            icon: <Share2 className="mr-1 h-3 w-3" />,
            text: "Social Intelligence",
            variant: "secondary"
          }}
          actions={
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
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

        {/* Connected Accounts */}
        <Card>
          <CardHeader>
            <CardTitle>Connected Accounts</CardTitle>
            <CardDescription>
              Manage your social media connections
            </CardDescription>
          </CardHeader>
          <CardContent>
            {dashboardLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {accounts?.map((account) => (
                  <div
                    key={account.id}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
                    <div className="flex items-center space-x-4">
                      <div className={getPlatformColor(account.platform)}>
                        {getPlatformIcon(account.platform)}
                      </div>
                      <div>
                        <p className="font-medium capitalize">{account.platform}</p>
                        <p className="text-sm text-muted-foreground">
                          {account.connected ? account.username : 'Not connected'}
                        </p>
                        {account.connected && (
                          <div className="mt-1 flex items-center space-x-4 text-xs text-muted-foreground">
                            <span>{account.followers.toLocaleString()} followers</span>
                            <span>{account.posts} posts</span>
                            <span>{account.engagement_rate}% engagement</span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div>
                      {account.connected ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => disconnectAccount.mutate(account.id)}
                        >
                          Disconnect
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => connectAccount.mutate(account.platform)}
                        >
                          Connect
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Analytics Overview */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Followers</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {socialDashboard?.summary?.total_followers?.toLocaleString() || '0'}
              </div>
              <p className="text-xs text-muted-foreground">
                Total across all platforms
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Engagement Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {socialDashboard?.summary?.total_engagement
                  ? `${(socialDashboard.summary.total_engagement / 100).toFixed(1)}%`
                  : '0%'
                }
              </div>
              <p className="text-xs text-muted-foreground">
                Average engagement rate
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Brand Mentions</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {socialDashboard?.summary?.total_mentions || brandMentions?.summary?.total_mentions || '0'}
              </div>
              <p className="text-xs text-muted-foreground">
                Mentions this month
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Social Health</CardTitle>
              <Link2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {Math.round(socialDashboard?.summary?.social_health_score || 0)}
              </div>
              <p className="text-xs text-muted-foreground">
                Social media health score
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Recent Posts */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Posts & SEO Impact</CardTitle>
            <CardDescription>
              Track how your social content impacts SEO
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="all" className="space-y-4">
              <TabsList>
                <TabsTrigger value="all" onClick={() => setSelectedPlatform('all')}>
                  All Platforms
                </TabsTrigger>
                <TabsTrigger value="twitter" onClick={() => setSelectedPlatform('twitter')}>
                  Twitter
                </TabsTrigger>
                <TabsTrigger value="linkedin" onClick={() => setSelectedPlatform('linkedin')}>
                  LinkedIn
                </TabsTrigger>
                <TabsTrigger value="facebook" onClick={() => setSelectedPlatform('facebook')}>
                  Facebook
                </TabsTrigger>
                <TabsTrigger value="instagram" onClick={() => setSelectedPlatform('instagram')}>
                  Instagram
                </TabsTrigger>
              </TabsList>
              <TabsContent value={selectedPlatform} className="space-y-4">
                {dashboardLoading || mentionsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                ) : posts.length > 0 ? (
                  <div className="space-y-4">
                    {posts.map((post) => (
                      <div key={post.id} className="rounded-lg border p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 space-y-2">
                            <div className="flex items-center space-x-2">
                              <div className={getPlatformColor(post.platform)}>
                                {getPlatformIcon(post.platform)}
                              </div>
                              <span className="text-sm text-muted-foreground">
                                {new Date(post.published_at).toLocaleDateString()}
                              </span>
                              <Badge variant={post.seo_impact_score > 80 ? 'default' : 'secondary'}>
                                SEO Score: {post.seo_impact_score}
                              </Badge>
                            </div>
                            <p className="text-sm">{post.content}</p>
                            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                              <span className="flex items-center">
                                <MessageSquare className="mr-1 h-3 w-3" />
                                {post.comments}
                              </span>
                              <span className="flex items-center">
                                <Share2 className="mr-1 h-3 w-3" />
                                {post.shares}
                              </span>
                              <span className="flex items-center">
                                <TrendingUp className="mr-1 h-3 w-3" />
                                {post.likes}
                              </span>
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(post.url, '_blank')}
                          >
                            View Post
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <MessageSquare className="h-12 w-12 text-muted-foreground mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No Recent Posts</h3>
                    <p className="text-muted-foreground">
                      {selectedPlatform === 'all'
                        ? 'No recent social media activity found. Connect your accounts to see posts.'
                        : `No recent ${selectedPlatform} activity found. Make sure your ${selectedPlatform} account is connected.`
                      }
                    </p>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Social SEO Recommendations */}
        <Card>
          <CardHeader>
            <CardTitle>Social SEO Recommendations</CardTitle>
            <CardDescription>
              Optimize your social media for better SEO impact
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {socialDashboard?.recommendations?.length > 0 ? (
                socialDashboard.recommendations.map((recommendation: string, index: number) => (
                  <div key={index} className="flex items-start space-x-3">
                    <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
                    <div>
                      <p className="font-medium">Recommendation {index + 1}</p>
                      <p className="text-sm text-muted-foreground">
                        {recommendation}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <>
                  {/* Default recommendations based on connected accounts */}
                  {accounts.filter(acc => acc.connected).length > 0 && (
                    <div className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                      <div>
                        <p className="font-medium">Social Accounts Connected</p>
                        <p className="text-sm text-muted-foreground">
                          You have {accounts.filter(acc => acc.connected).length} social media account(s) connected
                        </p>
                      </div>
                    </div>
                  )}

                  {socialDashboard?.summary?.social_health_score && socialDashboard.summary.social_health_score < 50 && (
                    <div className="flex items-start space-x-3">
                      <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
                      <div>
                        <p className="font-medium">Improve Social Health Score</p>
                        <p className="text-sm text-muted-foreground">
                          Your social media health score is below 50. Focus on increasing engagement and followers.
                        </p>
                      </div>
                    </div>
                  )}

                  {accounts.filter(acc => !acc.connected).length > 0 && (
                    <div className="flex items-start space-x-3">
                      <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
                      <div>
                        <p className="font-medium">Connect More Platforms</p>
                        <p className="text-sm text-muted-foreground">
                          Connect {accounts.filter(acc => !acc.connected).map(acc => acc.platform).join(', ')} to expand your social presence
                        </p>
                      </div>
                    </div>
                  )}

                  {(!socialDashboard?.summary?.total_mentions || socialDashboard.summary.total_mentions < 10) && (
                    <div className="flex items-start space-x-3">
                      <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
                      <div>
                        <p className="font-medium">Increase Brand Visibility</p>
                        <p className="text-sm text-muted-foreground">
                          Low brand mentions detected. Consider running social media campaigns to increase awareness.
                        </p>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </CardContent>
        </Card>
        </div>
    </DashboardLayout>
  );
}

export default withAuth(SocialMediaPage);