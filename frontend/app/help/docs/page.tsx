'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DetailLayout } from '@/components/layout/detail-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  BookOpen,
  Code,
  FileText,
  Search,
  ChevronRight,
  ExternalLink,
  Copy,
  Check,
  Zap,
  Shield,
  Database,
  Globe,
  Terminal,
  Lightbulb,
  PlayCircle,
  GraduationCap,
  Rocket,
  Users,
  BarChart3
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';

// Navigation structure for docs
const docNavigation = [
  {
    title: 'Getting Started',
    icon: Rocket,
    items: [
      { title: 'Introduction', href: '#introduction' },
      { title: 'Quick Start', href: '#quick-start' },
      { title: 'Installation', href: '#installation' },
      { title: 'First Project', href: '#first-project' },
    ],
  },
  {
    title: 'Core Concepts',
    icon: Lightbulb,
    items: [
      { title: 'Projects', href: '#projects' },
      { title: 'Sites', href: '#sites' },
      { title: 'Organizations', href: '#organizations' },
      { title: 'Analytics', href: '#analytics' },
    ],
  },
  {
    title: 'Features',
    icon: Zap,
    items: [
      { title: 'SEO Analysis', href: '#seo-analysis' },
      { title: 'Competitor Tracking', href: '#competitor-tracking' },
      { title: 'Content Optimization', href: '#content-optimization' },
      { title: 'Search Console', href: '#search-console' },
      { title: 'Market Simulation', href: '#market-simulation' },
    ],
  },
  {
    title: 'API Reference',
    icon: Code,
    items: [
      { title: 'Authentication', href: '#api-auth' },
      { title: 'Endpoints', href: '#api-endpoints' },
      { title: 'Rate Limits', href: '#api-rate-limits' },
      { title: 'Error Handling', href: '#api-errors' },
      { title: 'SDKs', href: '#api-sdks' },
    ],
  },
  {
    title: 'Advanced',
    icon: Shield,
    items: [
      { title: 'Security', href: '#security' },
      { title: 'Webhooks', href: '#webhooks' },
      { title: 'Integrations', href: '#integrations' },
      { title: 'Best Practices', href: '#best-practices' },
    ],
  },
];

// API endpoint examples
const apiExamples = [
  {
    method: 'GET',
    endpoint: '/api/v1/projects',
    description: 'List all projects',
    example: `curl -X GET https://api.serptank.com/v1/projects \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
  },
  {
    method: 'POST',
    endpoint: '/api/v1/serp-analysis/analyze-serp',
    description: 'Analyze SERP for a keyword',
    example: `curl -X POST https://api.serptank.com/v1/serp-analysis/analyze-serp \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"keyword": "seo tools", "location": "US"}'`,
  },
  {
    method: 'GET',
    endpoint: '/api/v1/search-console/performance',
    description: 'Get Search Console performance data',
    example: `curl -X GET https://api.serptank.com/v1/search-console/performance \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -G -d "site_url=example.com" -d "days=30"`,
  },
];

function DocsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState('introduction');
  const { toast } = useToast();

  const copyToClipboard = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(id);
    toast({
      title: 'Copied to clipboard',
      description: 'Code snippet copied successfully.',
    });
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const filteredNavigation = docNavigation.map(section => ({
    ...section,
    items: section.items.filter(item =>
      item.title.toLowerCase().includes(searchQuery.toLowerCase())
    ),
  })).filter(section => section.items.length > 0);

  const docsContent = (
    <div className="flex gap-6">
      {/* Sidebar Navigation */}
      <aside className="w-64 flex-shrink-0">
        <div className="sticky top-6 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search docs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <ScrollArea className="h-[calc(100vh-200px)]">
            <nav className="space-y-6">
              {filteredNavigation.map((section) => (
                <div key={section.title}>
                  <div className="flex items-center gap-2 mb-2">
                    <section.icon className="h-4 w-4 text-muted-foreground" />
                    <h4 className="font-medium text-sm">{section.title}</h4>
                  </div>
                  <ul className="space-y-1 ml-6">
                    {section.items.map((item) => (
                      <li key={item.href}>
                        <a
                          href={item.href}
                          onClick={(e) => {
                            e.preventDefault();
                            setActiveSection(item.href.slice(1));
                          }}
                          className={cn(
                            "block py-1 px-2 text-sm rounded hover:bg-muted transition-colors",
                            activeSection === item.href.slice(1) && "bg-muted font-medium"
                          )}
                        >
                          {item.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </nav>
          </ScrollArea>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 max-w-4xl">
        <div className="space-y-8">
          {/* Introduction Section */}
          <section id="introduction" className="space-y-4">
            <div>
              <h1 className="text-3xl font-bold">Welcome to SerpTank Documentation</h1>
              <p className="text-lg text-muted-foreground mt-2">
                Everything you need to know about using SerpTank SEO Dashboard
              </p>
            </div>
            
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <PlayCircle className="h-5 w-5 text-primary" />
                    <CardTitle className="text-base">Quick Start</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Get up and running with SerpTank in 5 minutes
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <GraduationCap className="h-5 w-5 text-primary" />
                    <CardTitle className="text-base">Tutorials</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Step-by-step guides for common tasks
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Code className="h-5 w-5 text-primary" />
                    <CardTitle className="text-base">API Docs</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Complete API reference and examples
                  </p>
                </CardContent>
              </Card>
            </div>
          </section>

          {/* Quick Start Section */}
          <section id="quick-start" className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold">Quick Start Guide</h2>
              <p className="text-muted-foreground mt-1">
                Follow these steps to get started with SerpTank
              </p>
            </div>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Badge className="rounded-full w-6 h-6 p-0 flex items-center justify-center">1</Badge>
                    <CardTitle className="text-lg">Create Your First Organization</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Organizations are the top-level containers for your projects and team members.
                  </p>
                  <div className="bg-muted rounded-lg p-4">
                    <code className="text-sm">
                      Navigate to Organizations → Click &quot;Create Organization&quot; → Enter details → Save
                    </code>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Badge className="rounded-full w-6 h-6 p-0 flex items-center justify-center">2</Badge>
                    <CardTitle className="text-lg">Set Up Your First Project</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Projects contain your sites and all related SEO data.
                  </p>
                  <div className="bg-muted rounded-lg p-4">
                    <code className="text-sm">
                      Go to Projects → &quot;New Project&quot; → Configure settings → Add your website
                    </code>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Badge className="rounded-full w-6 h-6 p-0 flex items-center justify-center">3</Badge>
                    <CardTitle className="text-lg">Connect Your Data Sources</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Connect Google Search Console and Analytics for comprehensive insights.
                  </p>
                  <div className="bg-muted rounded-lg p-4">
                    <code className="text-sm">
                      Settings → Integrations → Connect Google Services → Authorize access
                    </code>
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>

          {/* API Reference Section */}
          <section id="api-endpoints" className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold">API Reference</h2>
              <p className="text-muted-foreground mt-1">
                Complete reference for all SerpTank API endpoints
              </p>
            </div>

            <Tabs defaultValue="rest" className="space-y-4">
              <TabsList>
                <TabsTrigger value="rest">REST API</TabsTrigger>
                <TabsTrigger value="graphql">GraphQL</TabsTrigger>
                <TabsTrigger value="webhooks">Webhooks</TabsTrigger>
              </TabsList>

              <TabsContent value="rest" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Authentication</CardTitle>
                    <CardDescription>
                      All API requests require authentication using an API key
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="bg-muted rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">Header Authentication</span>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => copyToClipboard('Authorization: Bearer YOUR_API_KEY', 'auth-header')}
                          >
                            {copiedCode === 'auth-header' ? (
                              <Check className="h-4 w-4" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                        <code className="text-sm text-muted-foreground">
                          Authorization: Bearer YOUR_API_KEY
                        </code>
                      </div>
                      
                      <p className="text-sm text-muted-foreground">
                        You can generate API keys from your{' '}
                        <a href="/settings" className="text-primary hover:underline">
                          settings page
                        </a>.
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Example Endpoints</CardTitle>
                    <CardDescription>
                      Common API endpoints and usage examples
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6">
                      {apiExamples.map((example, index) => (
                        <div key={index} className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Badge variant={example.method === 'GET' ? 'secondary' : 'default'}>
                              {example.method}
                            </Badge>
                            <code className="text-sm font-medium">{example.endpoint}</code>
                          </div>
                          <p className="text-sm text-muted-foreground">{example.description}</p>
                          <div className="bg-muted rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-muted-foreground">Example Request</span>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => copyToClipboard(example.example, `api-${index}`)}
                              >
                                {copiedCode === `api-${index}` ? (
                                  <Check className="h-3 w-3" />
                                ) : (
                                  <Copy className="h-3 w-3" />
                                )}
                              </Button>
                            </div>
                            <pre className="text-xs overflow-x-auto">
                              <code>{example.example}</code>
                            </pre>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Rate Limits</CardTitle>
                    <CardDescription>
                      API rate limits and best practices
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                          <h4 className="font-medium text-sm">Default Limits</h4>
                          <ul className="space-y-1 text-sm text-muted-foreground">
                            <li>• 1,000 requests per hour</li>
                            <li>• 10,000 requests per day</li>
                            <li>• 100 concurrent requests</li>
                          </ul>
                        </div>
                        <div className="space-y-2">
                          <h4 className="font-medium text-sm">Response Headers</h4>
                          <ul className="space-y-1 text-sm text-muted-foreground">
                            <li>• X-RateLimit-Limit</li>
                            <li>• X-RateLimit-Remaining</li>
                            <li>• X-RateLimit-Reset</li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="graphql" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>GraphQL Endpoint</CardTitle>
                    <CardDescription>
                      Access all SerpTank data through our GraphQL API
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="bg-muted rounded-lg p-4">
                        <code className="text-sm">https://api.serptank.com/graphql</code>
                      </div>
                      <Button>
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Open GraphQL Playground
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="webhooks" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Webhook Events</CardTitle>
                    <CardDescription>
                      Subscribe to real-time events in your SerpTank account
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid gap-2">
                        {[
                          'project.created',
                          'site.analyzed',
                          'ranking.changed',
                          'alert.triggered',
                          'report.generated',
                        ].map((event) => (
                          <div key={event} className="flex items-center justify-between p-3 rounded-lg border">
                            <code className="text-sm">{event}</code>
                            <Badge variant="outline">Event</Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </section>

          {/* Feature Documentation */}
          <section id="features" className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold">Feature Documentation</h2>
              <p className="text-muted-foreground mt-1">
                In-depth guides for all SerpTank features
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Search className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">SEO Analysis</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-3">
                    Comprehensive site audits, technical SEO checks, and optimization recommendations.
                  </p>
                  <Button variant="outline" size="sm">
                    Read More
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">Competitor Analysis</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-3">
                    Track competitors, analyze their strategies, and find opportunities.
                  </p>
                  <Button variant="outline" size="sm">
                    Read More
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">Content Optimization</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-3">
                    AI-powered content analysis, gap detection, and optimization suggestions.
                  </p>
                  <Button variant="outline" size="sm">
                    Read More
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">Analytics & Reporting</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-3">
                    Advanced analytics, custom reports, and data visualization tools.
                  </p>
                  <Button variant="outline" size="sm">
                    Read More
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            </div>
          </section>

          {/* Additional Resources */}
          <section className="space-y-4">
            <div>
              <h2 className="text-2xl font-bold">Additional Resources</h2>
              <p className="text-muted-foreground mt-1">
                More ways to learn and get help
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Database className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="font-medium">API SDKs</h3>
                    <p className="text-sm text-muted-foreground">
                      Official SDKs for Python, Node.js, PHP, and more.
                    </p>
                    <Button variant="link" className="p-0 h-auto">
                      View SDKs →
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Terminal className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="font-medium">CLI Tool</h3>
                    <p className="text-sm text-muted-foreground">
                      Command-line interface for automation and scripting.
                    </p>
                    <Button variant="link" className="p-0 h-auto">
                      Install CLI →
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Globe className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="font-medium">Community</h3>
                    <p className="text-sm text-muted-foreground">
                      Join our community forum for tips and discussions.
                    </p>
                    <Button variant="link" className="p-0 h-auto">
                      Join Community →
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>
        </div>
      </div>
    </div>
  );

  return (
    <DetailLayout
      title="Documentation"
      breadcrumbs={[
        { label: 'Help', href: '/help' },
        { label: 'Documentation' },
      ]}
      tabs={[
        {
          id: 'docs',
          label: 'Documentation',
          icon: BookOpen,
          content: docsContent,
        },
      ]}
    />
  );
}

export default withAuth(DocsPage);