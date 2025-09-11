'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
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
  AlertCircle
} from 'lucide-react';
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

function SocialMediaPage() {
  const { toast } = useToast();
  const { currentProject } = useProject();
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');

  // Fetch social accounts
  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['social-accounts'],
    queryFn: async () => {
      // Mock data for now
      return [
        {
          id: '1',
          platform: 'twitter' as const,
          username: '@serptankseo',
          connected: true,
          followers: 12500,
          posts: 342,
          engagement_rate: 3.2
        },
        {
          id: '2',
          platform: 'linkedin' as const,
          username: 'serptank-seo',
          connected: true,
          followers: 8200,
          posts: 156,
          engagement_rate: 4.8
        },
        {
          id: '3',
          platform: 'facebook' as const,
          username: 'SerpTankSEO',
          connected: false,
          followers: 0,
          posts: 0,
          engagement_rate: 0
        },
        {
          id: '4',
          platform: 'instagram' as const,
          username: 'serptank.seo',
          connected: false,
          followers: 0,
          posts: 0,
          engagement_rate: 0
        }
      ];
    }
  });

  // Fetch recent posts
  const { data: posts, isLoading: postsLoading } = useQuery({
    queryKey: ['social-posts', selectedPlatform],
    queryFn: async () => {
      // Mock data for now
      return [
        {
          id: '1',
          platform: 'twitter',
          content: 'New blog post: "10 SEO Trends to Watch in 2024" 🚀 Learn how AI is reshaping search...',
          url: 'https://twitter.com/serptankseo/status/123',
          published_at: '2024-01-15T10:30:00Z',
          likes: 45,
          shares: 12,
          comments: 8,
          seo_impact_score: 78
        },
        {
          id: '2',
          platform: 'linkedin',
          content: 'Excited to share our latest case study: How we helped a client increase organic traffic by 250%...',
          url: 'https://linkedin.com/posts/serptank-seo/123',
          published_at: '2024-01-14T14:20:00Z',
          likes: 120,
          shares: 34,
          comments: 22,
          seo_impact_score: 92
        }
      ];
    }
  });

  // Connect account mutation
  const connectAccount = useMutation({
    mutationFn: async (platform: string) => {
      // This would redirect to OAuth flow
      window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/social/${platform}/connect`;
    },
    onSuccess: (_, platform) => {
      toast({
        title: "Redirecting to connect",
        description: `Connecting your ${platform} account...`,
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

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Social Media Integration</h1>
          <p className="text-muted-foreground">
            Connect and analyze your social media presence for SEO insights
          </p>
        </div>

        {/* Connected Accounts */}
        <Card>
          <CardHeader>
            <CardTitle>Connected Accounts</CardTitle>
            <CardDescription>
              Manage your social media connections
            </CardDescription>
          </CardHeader>
          <CardContent>
            {accountsLoading ? (
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
              <div className="text-2xl font-bold">20,700</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-500">+12.5%</span> from last month
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Engagement Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">3.8%</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-500">+0.3%</span> from last month
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Social Traffic</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1,234</div>
              <p className="text-xs text-muted-foreground">
                Visits from social this month
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">SEO Impact</CardTitle>
              <Link2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">85</div>
              <p className="text-xs text-muted-foreground">
                Social SEO score
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
                {postsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    {posts?.map((post) => (
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
              <div className="flex items-start space-x-3">
                <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium">Consistent Posting Schedule</p>
                  <p className="text-sm text-muted-foreground">
                    You&apos;re maintaining a good posting frequency across platforms
                  </p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
                <div>
                  <p className="font-medium">Improve LinkedIn Engagement</p>
                  <p className="text-sm text-muted-foreground">
                    Your LinkedIn posts could benefit from more hashtags and mentions
                  </p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
                <div>
                  <p className="font-medium">Connect Facebook Account</p>
                  <p className="text-sm text-muted-foreground">
                    Facebook can drive significant referral traffic to your site
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

export default withAuth(SocialMediaPage);