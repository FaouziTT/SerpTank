"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { 
  Globe, Activity, Settings, ExternalLink, 
  CheckCircle, XCircle, RefreshCw, BarChart3, Search,
  FileText, AlertTriangle, TrendingUp, Clock, Shield,
  Edit, Trash2, Link2, Bug, Zap, Eye, Plus, MoreVertical, Users
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api-client";
import { Site, SiteHealth, CrawlResult, Project, User } from "@/types/api";
import { useAuth } from "@/lib/auth-context";
import { useProject as useProjectContext } from "@/lib/project-context";
import { useToast } from "@/components/ui/use-toast";
import { DetailLayout } from "@/components/layout/detail-layout";
import { EntityModal } from "@/components/ui/entity-modal";
import { ConfirmActionModal } from "@/components/ui/confirm-action-modal";
import { CrawlerLoadingBanner } from "@/components/ui/crawler-loading-banner";
import { useCrawlerStatus } from "@/lib/hooks/use-crawler-status";

// Tab Components
interface AnalysisStatus {
  overall_health?: number;
}

function OverviewTab({ 
  site, 
  siteHealth, 
  crawlerStatus, 
  isCrawlerActive, 
  onDismissCrawler 
}: { 
  site: Site; 
  siteHealth: SiteHealth | null;
  crawlerStatus?: any;
  isCrawlerActive?: boolean;
  onDismissCrawler?: () => void;
}) {
  const healthScore = siteHealth?.overall_score || 0;
  const getHealthColor = (score: number) => {
    if (score >= 90) return "text-green-600";
    if (score >= 70) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-6">
      {isCrawlerActive && crawlerStatus && (
        <CrawlerLoadingBanner
          crawlerStatus={crawlerStatus}
          onDismiss={onDismissCrawler}
          showDismissButton={crawlerStatus.status === 'COMPLETED' || crawlerStatus.status === 'FAILED'}
        />
      )}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Health Score</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getHealthColor(healthScore)}`}>
              {healthScore}%
            </div>
            <Progress value={healthScore} className="mt-2" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pages Indexed</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{siteHealth?.pages_indexed || 0}</div>
            <p className="text-xs text-muted-foreground">Last crawl: {siteHealth?.last_crawl_date || 'Never'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Core Web Vitals</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{siteHealth?.cwv_passing || 0}%</div>
            <p className="text-xs text-muted-foreground">Passing CWV tests</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">SEO Issues</CardTitle>
            <Bug className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{siteHealth?.seo_issues || 0}</div>
            <p className="text-xs text-muted-foreground">Needs attention</p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Site Information</CardTitle>
          <CardDescription>Basic information about your website</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label className="text-sm font-medium">URL</Label>
              <div className="flex items-center gap-2 mt-1">
                <p className="text-sm">{site.url}</p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => window.open(site.url, '_blank')}
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div>
              <Label className="text-sm font-medium">Site Name</Label>
              <p className="text-sm mt-1">{site.name || 'Unnamed Site'}</p>
            </div>
            <div>
              <Label className="text-sm font-medium">Status</Label>
              <div className="mt-1">
                {site.is_active ? (
                  <Badge variant="default"><CheckCircle className="h-3 w-3 mr-1" />Active</Badge>
                ) : (
                  <Badge variant="secondary"><XCircle className="h-3 w-3 mr-1" />Inactive</Badge>
                )}
              </div>
            </div>
            <div>
              <Label className="text-sm font-medium">Project</Label>
              <p className="text-sm mt-1">{site.project?.name || 'No project assigned'}</p>
            </div>
          </div>
          {site.description && (
            <div>
              <Label className="text-sm font-medium">Description</Label>
              <p className="text-sm mt-1 text-muted-foreground">{site.description}</p>
            </div>
          )}
          <Separator />
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label className="text-sm font-medium">Created</Label>
              <p className="text-sm mt-1">{new Date(site.created_at).toLocaleDateString()}</p>
            </div>
            <div>
              <Label className="text-sm font-medium">Last Updated</Label>
              <p className="text-sm mt-1">{new Date(site.updated_at).toLocaleDateString()}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Latest changes and updates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Search className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">SEO audit completed</p>
                <p className="text-xs text-muted-foreground">2 hours ago</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bug className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">3 new issues detected</p>
                <p className="text-xs text-muted-foreground">1 day ago</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <TrendingUp className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Performance improved by 15%</p>
                <p className="text-xs text-muted-foreground">3 days ago</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AnalyticsTab({ site }: { site: Site }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Performance Metrics</CardTitle>
          <CardDescription>SEO and performance analytics for your site</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Analytics data will be displayed here</p>
            <p className="text-sm text-muted-foreground mt-2">
              Connect your Google Analytics and Search Console to view detailed metrics
            </p>
          </div>
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Traffic Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground text-sm">Coming soon...</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Top Keywords</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground text-sm">Coming soon...</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SettingsTab({ site, onUpdate }: { site: Site; onUpdate: () => void }) {
  const [isVerified, setIsVerified] = useState(site.is_verified || false);
  const [crawlEnabled, setCrawlEnabled] = useState(site.crawl_enabled !== false);
  const [crawlFrequency, setCrawlFrequency] = useState<'daily' | 'weekly' | 'monthly'>(site.crawl_frequency || 'weekly');

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Domain Verification</CardTitle>
          <CardDescription>Verify ownership of your domain to access all features</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label>Verification Status</Label>
              <p className="text-sm text-muted-foreground">
                {isVerified ? 'Your domain is verified' : 'Domain verification pending'}
              </p>
            </div>
            {isVerified ? (
              <Badge variant="default"><Shield className="h-3 w-3 mr-1" />Verified</Badge>
            ) : (
              <Badge variant="outline">Not Verified</Badge>
            )}
          </div>
          {!isVerified && (
            <div className="space-y-4 border-t pt-4">
              <p className="text-sm">Choose a verification method:</p>
              <div className="space-y-2">
                <Button variant="outline" className="w-full justify-start">
                  <FileText className="h-4 w-4 mr-2" />
                  HTML File Upload
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Globe className="h-4 w-4 mr-2" />
                  DNS Record
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <FileText className="h-4 w-4 mr-2" />
                  Meta Tag
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Crawl Settings</CardTitle>
          <CardDescription>Configure how we analyze your website</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="crawl-enabled">Enable Crawling</Label>
              <p className="text-sm text-muted-foreground">
                Allow automated crawling of your site
              </p>
            </div>
            <Switch
              id="crawl-enabled"
              checked={crawlEnabled}
              onCheckedChange={(checked) => setCrawlEnabled(checked)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="crawl-frequency">Crawl Frequency</Label>
            <Select value={crawlFrequency} onValueChange={(value) => setCrawlFrequency(value as 'daily' | 'weekly' | 'monthly')}>
              <SelectTrigger id="crawl-frequency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="pt-4">
            <Button>Save Settings</Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
          <CardDescription>Connect external services for enhanced analytics</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded bg-blue-100 flex items-center justify-center">
                <Search className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="font-medium">Google Search Console</p>
                <p className="text-sm text-muted-foreground">View search performance data</p>
              </div>
            </div>
            <Button variant="outline" size="sm">Connect</Button>
          </div>
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded bg-green-100 flex items-center justify-center">
                <BarChart3 className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="font-medium">Google Analytics</p>
                <p className="text-sm text-muted-foreground">Track visitor behavior</p>
              </div>
            </div>
            <Button variant="outline" size="sm">Connect</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function CrawlDataTab({ site }: { site: Site }) {
  const [crawlResults, setCrawlResults] = useState<CrawlResult[]>([]);
  const [loading, setLoading] = useState(false);

  const startCrawl = async () => {
    setLoading(true);
    try {
      await api.diagnostic.startCrawl({ url: site.url });
    } catch (error) {
      console.error("Failed to start crawl:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Crawl Overview</CardTitle>
          <CardDescription>Latest crawl results and discovered issues</CardDescription>
          <div className="flex justify-end">
            <Button onClick={startCrawl} disabled={loading}>
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Crawling...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Start Crawl
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {crawlResults.length === 0 ? (
            <div className="text-center py-8">
              <Bug className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No crawl data available</p>
              <p className="text-sm text-muted-foreground mt-2">
                Start a crawl to analyze your site for SEO issues
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Crawl results would be displayed here */}
            </div>
          )}
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Critical Issues</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">0</div>
            <p className="text-xs text-muted-foreground mt-1">Requires immediate attention</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Warnings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-600">0</div>
            <p className="text-xs text-muted-foreground mt-1">Should be addressed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Notices</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">0</div>
            <p className="text-xs text-muted-foreground mt-1">Optimization opportunities</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SiteDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { currentOrganization: organization } = useProjectContext();
  const { toast } = useToast();
  const [site, setSite] = useState<Site | null>(null);
  const [siteHealth, setSiteHealth] = useState<SiteHealth | null>(null);
  const [loading, setLoading] = useState(true);
  
  const siteId = params.id as string;
  const { crawlerStatus, isActive: isCrawlerActive, dismissStatus } = useCrawlerStatus(siteId);
  
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    url: "",
    name: "",
    description: "",
    project_id: "",
  });
  
  const defaultTab = searchParams.get('tab') || 'overview';

  const fetchSiteData = useCallback(async () => {
    try {
      setLoading(true);
      const [siteResponse, healthResponse] = await Promise.allSettled([
        api.sites.get(siteId),
        api.diagnostic.getSiteHealth(siteId)
      ]);
      
      if (siteResponse.status === 'fulfilled') {
        setSite(siteResponse.value.data);
        setFormData({
          url: siteResponse.value.data.url,
          name: siteResponse.value.data.name || "",
          description: siteResponse.value.data.description || "",
          project_id: siteResponse.value.data.project_id || "",
        });
      } else {
        throw new Error('Failed to fetch site');
      }
      
      if (healthResponse.status === 'fulfilled') {
        setSiteHealth(healthResponse.value.data);
      }
    } catch (error) {
      console.error("Failed to fetch site data:", error);
      toast({
        title: "Error",
        description: "Failed to load site data",
        variant: "destructive",
      });
      router.push("/sites");
    } finally {
      setLoading(false);
    }
  }, [siteId, toast, router]);

  useEffect(() => {
    if (siteId) {
      fetchSiteData();
    }
  }, [siteId, fetchSiteData]);

  const handleEditSite = async () => {
    if (!site) return;
    
    try {
      const response = await api.sites.update(site.id, formData);
      setSite(response.data);
      setEditModalOpen(false);
      toast({
        title: "Success",
        description: "Site updated successfully.",
      });
    } catch (error) {
      console.error("Failed to update site:", error);
      toast({
        title: "Error",
        description: "Failed to update site. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteSite = async () => {
    if (!site) return;
    
    try {
      await api.sites.delete(site.id);
      toast({
        title: "Success",
        description: "Site deleted successfully.",
      });
      router.push("/sites");
    } catch (error) {
      console.error("Failed to delete site:", error);
      toast({
        title: "Error",
        description: "Failed to delete site. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (!site && !loading) {
    return null;
  }

  return (
    <>
      <DetailLayout
        title={site?.name || site?.url || "Loading..."}
        subtitle={site?.description}
        status={site?.is_active ? {
          label: "Active",
          variant: "default" as const
        } : {
          label: "Inactive",
          variant: "secondary" as const
        }}
        breadcrumbs={[
          { label: "Sites", href: "/sites" },
          { label: site?.name || new URL(site?.url || "https://example.com").hostname || "Site" }
        ]}
        actions={[
          {
            label: "Visit Site",
            onClick: () => window.open(site?.url, '_blank'),
            icon: ExternalLink,
            variant: "outline" as const,
          },
          {
            label: "Edit",
            onClick: () => setEditModalOpen(true),
            icon: Edit,
            variant: "outline" as const,
          },
          {
            label: "Delete",
            onClick: () => setDeleteModalOpen(true),
            icon: Trash2,
            variant: "destructive" as const,
          },
        ]}
        tabs={[
          {
            id: "overview",
            label: "Overview",
            icon: Eye,
            content: site ? (
              <OverviewTab 
                site={site} 
                siteHealth={siteHealth} 
                crawlerStatus={crawlerStatus}
                isCrawlerActive={isCrawlerActive}
                onDismissCrawler={dismissStatus}
              />
            ) : null,
          },
          {
            id: "analytics",
            label: "Analytics",
            icon: BarChart3,
            content: site ? <AnalyticsTab site={site} /> : null,
          },
          {
            id: "settings",
            label: "Settings",
            icon: Settings,
            content: site ? <SettingsTab site={site} onUpdate={fetchSiteData} /> : null,
          },
          {
            id: "crawl-data",
            label: "Crawl Data",
            icon: Bug,
            badge: siteHealth?.seo_issues,
            content: site ? <CrawlDataTab site={site} /> : null,
          },
        ]}
        defaultTab="overview"
        loading={loading}
        metadata={site ? [
          {
            label: "Project",
            value: site.project?.name || "No project",
            icon: Shield,
          },
          {
            label: "Added",
            value: new Date(site.created_at).toLocaleDateString(),
            icon: Clock,
          },
        ] : []}
      />

      <EntityModal
        entity="site"
        action="edit"
        open={editModalOpen}
        onOpenChange={(open) => setEditModalOpen(open)}
        title="Edit Site"
        description="Update site information and settings."
        onSubmit={handleEditSite}
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="edit-url">Website URL</Label>
            <Input
              id="edit-url"
              type="url"
              placeholder="https://example.com"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="edit-name">Site Name</Label>
            <Input
              id="edit-name"
              placeholder="My Website"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="edit-description">Description</Label>
            <Textarea
              id="edit-description"
              placeholder="Brief description of the site..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>
        </div>
      </EntityModal>

      <ConfirmActionModal
        open={deleteModalOpen}
        onOpenChange={(open) => setDeleteModalOpen(open)}
        onConfirm={handleDeleteSite}
        type="danger"
        title="Delete Site"
        message={`Are you sure you want to delete ${site?.name || site?.url}? This action cannot be undone and will remove all associated data including: All crawl data and history, Performance metrics, SEO analysis results, and Integration settings.`}
        confirmLabel="Delete Site"
      />
    </>
  );
}

export default function SiteDetailPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div></div>}>
      <SiteDetailPageContent />
    </Suspense>
  );
}