"use client";

import { useState, useEffect, useCallback, Suspense } from "react"; // <-- CHANGE: Imported useCallback
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { 
  FolderOpen, Users, Globe, Settings, Edit, Trash2,
  Plus, UserPlus, Activity, Calendar, Clock, Shield,
  BarChart3, Target, TrendingUp, AlertCircle, MoreVertical,
  Mail, X, CheckCircle, XCircle
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
import { Project, Site, User, ProjectSettings } from "@/types/api";
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
  // Add other properties as needed
}

function OverviewTab({ 
  project, 
  analysisStatus, 
  crawlerStatus, 
  isCrawlerActive, 
  onDismissCrawler 
}: { 
  project: Project; 
  analysisStatus: AnalysisStatus | null;
  crawlerStatus?: any;
  isCrawlerActive?: boolean;
  onDismissCrawler?: () => void;
}) {
  const overallHealth = analysisStatus?.overall_health || 85; // Mock data
  const getHealthColor = (score: number) => {
    if (score >= 90) return "text-green-600";
    if (score >= 70) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-6">
      {/* Crawler Loading Banner */}
      {isCrawlerActive && crawlerStatus && (
        <CrawlerLoadingBanner
          crawlerStatus={crawlerStatus}
          onDismiss={onDismissCrawler}
          showDismissButton={crawlerStatus.status === 'COMPLETED' || crawlerStatus.status === 'FAILED'}
        />
      )}
      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overall Health</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getHealthColor(overallHealth)}`}>
              {overallHealth}%
            </div>
            <Progress value={overallHealth} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sites</CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{project.sites_count || 0}</div>
            <p className="text-xs text-muted-foreground">Active websites</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Team Members</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{project.team_members_count || 0}</div>
            <p className="text-xs text-muted-foreground">Collaborators</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">SEO Score</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">78</div>
            <p className="text-xs text-muted-foreground">Average across sites</p>
          </CardContent>
        </Card>
      </div>

      {/* Project Information */}
      <Card>
        <CardHeader>
          <CardTitle>Project Information</CardTitle>
          <CardDescription>Basic information about your project</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label className="text-sm font-medium">Project Name</Label>
              <p className="text-sm mt-1">{project.name}</p>
            </div>
            <div>
              <Label className="text-sm font-medium">Status</Label>
              <div className="mt-1">
                {project.is_active ? (
                  <Badge variant="default">Active</Badge>
                ) : (
                  <Badge variant="secondary">Inactive</Badge>
                )}
              </div>
            </div>
          </div>
          {project.description && (
            <div>
              <Label className="text-sm font-medium">Description</Label>
              <p className="text-sm mt-1 text-muted-foreground">{project.description}</p>
            </div>
          )}
          <Separator />
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label className="text-sm font-medium">Created</Label>
              <p className="text-sm mt-1">{new Date(project.created_at).toLocaleDateString()}</p>
            </div>
            <div>
              <Label className="text-sm font-medium">Last Updated</Label>
              <p className="text-sm mt-1">{new Date(project.updated_at).toLocaleDateString()}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Latest project updates and changes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Mock activity data */}
            <div className="flex items-center gap-4">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Globe className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">New site added</p>
                <p className="text-xs text-muted-foreground">example.com was added to the project</p>
              </div>
              <p className="text-xs text-muted-foreground">2 hours ago</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Users className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Team member added</p>
                <p className="text-xs text-muted-foreground">John Doe joined the project</p>
              </div>
              <p className="text-xs text-muted-foreground">1 day ago</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <BarChart3 className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">SEO analysis completed</p>
                <p className="text-xs text-muted-foreground">Overall score improved by 5%</p>
              </div>
              <p className="text-xs text-muted-foreground">3 days ago</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SitesTab({ project, onUpdate }: { project: Project; onUpdate: () => void }) {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [addSiteModalOpen, setAddSiteModalOpen] = useState(false);
  const { toast } = useToast();

  // <-- CHANGE: Wrapped in useCallback
  const fetchProjectSites = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.sites.list();
      // Filter sites that belong to this project
      const projectSites = response.data.filter((site: Site) => site.project_id === project.id);
      setSites(projectSites);
    } catch (error) {
      console.error("Failed to fetch project sites:", error);
    } finally {
      setLoading(false);
    }
  }, [project.id]); // project.id is used in the filtering logic

  useEffect(() => {
    fetchProjectSites();
  }, [fetchProjectSites]); // <-- CHANGE: Updated dependency array

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Project Sites</h3>
          <p className="text-sm text-muted-foreground">
            Manage websites associated with this project
          </p>
        </div>
        <Button onClick={() => setAddSiteModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Site
        </Button>
      </div>

      {loading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map((i: number) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-5 bg-muted rounded w-1/3 mb-2"></div>
                <div className="h-4 bg-muted rounded w-1/2"></div>
              </CardHeader>
            </Card>
          ))}
        </div>
      ) : sites.length === 0 ? (
        <Card>
          <CardContent className="text-center py-8">
            <Globe className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No sites yet</h3>
            <p className="text-muted-foreground mb-4">
              Add websites to this project to start monitoring their SEO performance
            </p>
            <Button onClick={() => setAddSiteModalOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Your First Site
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {sites.map((site: Site) => (
            <Card key={site.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Globe className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <CardTitle className="text-base">{site.name || site.url}</CardTitle>
                      <CardDescription>{site.url}</CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {site.is_active ? (
                      <Badge variant="default">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => window.open(`/sites/${site.id}`, '_blank')}>
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => window.open(site.url, '_blank')}>
                          Visit Site
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-destructive">
                          Remove from Project
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function TeamTab({ project, onUpdate }: { project: Project; onUpdate: () => void }) {
  const [teamMembers, setTeamMembers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const { toast } = useToast();

  const fetchTeamMembers = useCallback(async () => {
    try {
      setLoading(true);
      // In a real app, this would be api.projects.getTeam(project.id)
      // For now, we'll mock the data
      setTeamMembers([]);
    } catch (error) {
      console.error("Failed to fetch team members:", error);
    } finally {
      setLoading(false);
    }
  }, []); // project.id will be needed when real API is implemented

  useEffect(() => {
    fetchTeamMembers();
  }, [fetchTeamMembers]);

  const handleInviteMember = async () => {
    try {
      // In a real app: await api.projects.addTeamMember(project.id, { email: inviteEmail, role: inviteRole })
      toast({
        title: "Invitation sent",
        description: `Invitation sent to ${inviteEmail}`,
      });
      setInviteModalOpen(false);
      setInviteEmail("");
      setInviteRole("member");
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send invitation",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Team Members</h3>
          <p className="text-sm text-muted-foreground">
            Manage who has access to this project
          </p>
        </div>
        <Button onClick={() => setInviteModalOpen(true)}>
          <UserPlus className="h-4 w-4 mr-2" />
          Invite Member
        </Button>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i: number) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-muted"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-muted rounded w-1/4 mb-2"></div>
                    <div className="h-3 bg-muted rounded w-1/3"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : teamMembers.length === 0 ? (
        <Card>
          <CardContent className="text-center py-8">
            <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No team members yet</h3>
            <p className="text-muted-foreground mb-4">
              Invite team members to collaborate on this project
            </p>
            <Button onClick={() => setInviteModalOpen(true)}>
              <UserPlus className="h-4 w-4 mr-2" />
              Invite Your First Member
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {teamMembers.map((member: User) => (
            <Card key={member.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <Users className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-medium">{member.name}</p>
                      <p className="text-sm text-muted-foreground">{member.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{member.role}</Badge>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>Change Role</DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive">
                          Remove from Project
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Invite Member Modal */}
      <EntityModal
        entity="team-member"
        action="create"
        open={inviteModalOpen}
        onOpenChange={setInviteModalOpen}
        title="Invite Team Member"
        description="Send an invitation to collaborate on this project"
        onSubmit={handleInviteMember}
        submitLabel="Send Invitation"
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              placeholder="colleague@example.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="role">Role</Label>
            <Select value={inviteRole} onValueChange={setInviteRole}>
              <SelectTrigger id="role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="member">Member</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </EntityModal>
    </div>
  );
}

function SettingsTab({ project, onUpdate }: { project: Project; onUpdate: () => void }) {
  const [settings, setSettings] = useState<ProjectSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleScopes, setGoogleScopes] = useState<string[]>([]);
  const { toast } = useToast();
  const { user } = useAuth();

  // Settings form state
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [crawlFrequency, setCrawlFrequency] = useState("weekly");
  const [alertThreshold, setAlertThreshold] = useState("medium");

  const fetchProjectSettings = useCallback(async () => {
    try {
      setLoading(true);
      // In a real app: const response = await api.projects.getSettings(project.id);
      // For now, we'll use default values
      setNotificationsEnabled(true);
      setCrawlFrequency("weekly");
      setAlertThreshold("medium");
    } catch (error) {
      console.error("Failed to fetch project settings:", error);
    } finally {
      setLoading(false);
    }
  }, []); // project.id will be needed when real API is implemented

  const checkGoogleOAuthStatus = useCallback(async () => {
    try {
      const response = await api.oauth.google.getStatus();
      setGoogleConnected(response.data.connected);
      setGoogleScopes(response.data.scopes || []);
    } catch (error) {
      console.error("Failed to check Google OAuth status:", error);
    }
  }, []); // project.id will be needed when real API is implemented

  useEffect(() => {
    fetchProjectSettings();
    checkGoogleOAuthStatus();
  }, [project.id, fetchProjectSettings, checkGoogleOAuthStatus]);

  const handleConnectGoogle = async () => {
    try {
      const response = await api.oauth.google.authorize({ scopes: 'full' });
      window.location.href = response.data.authorization_url;
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to initiate Google connection",
        variant: "destructive",
      });
    }
  };

  const handleDisconnectGoogle = async () => {
    try {
      await api.oauth.google.revoke();
      setGoogleConnected(false);
      setGoogleScopes([]);
      toast({
        title: "Success",
        description: "Google account disconnected successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to disconnect Google account",
        variant: "destructive",
      });
    }
  };

  const handleSaveSettings = async () => {
    try {
      // In a real app: await api.projects.updateSettings(project.id, settings)
      toast({
        title: "Settings saved",
        description: "Project settings have been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save settings",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
          <CardDescription>Configure basic project settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="notifications">Email Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Receive email updates about project activity
              </p>
            </div>
            <Switch
              id="notifications"
              checked={notificationsEnabled}
              onCheckedChange={setNotificationsEnabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="crawl-frequency">Default Crawl Frequency</Label>
            <Select value={crawlFrequency} onValueChange={setCrawlFrequency}>
              <SelectTrigger id="crawl-frequency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              How often sites in this project should be crawled
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="alert-threshold">Alert Threshold</Label>
            <Select value={alertThreshold} onValueChange={setAlertThreshold}>
              <SelectTrigger id="alert-threshold">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low - All issues</SelectItem>
                <SelectItem value="medium">Medium - Important issues</SelectItem>
                <SelectItem value="high">High - Critical issues only</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              When to receive alerts about SEO issues
            </p>
          </div>

          <div className="pt-4">
            <Button onClick={handleSaveSettings}>Save Settings</Button>
          </div>
        </CardContent>
      </Card>

      {/* Google Account Integration */}
      <Card>
        <CardHeader>
          <CardTitle>Google Account Integration</CardTitle>
          <CardDescription>
            Connect your Google account to enable Search Console and Analytics data
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {googleConnected ? (
            <>
              <div className="flex items-center gap-2 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <div className="flex-1">
                  <p className="font-medium text-green-900 dark:text-green-100">
                    Google Account Connected
                  </p>
                  <p className="text-sm text-green-700 dark:text-green-300">
                    Your Google account is connected and authorized.
                  </p>
                </div>
              </div>
              
              <div className="space-y-2">
                <p className="text-sm font-medium">Authorized Scopes:</p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {googleScopes.includes('https://www.googleapis.com/auth/webmasters.readonly') && (
                    <li className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-green-600" />
                      Search Console (Read-only)
                    </li>
                  )}
                  {googleScopes.includes('https://www.googleapis.com/auth/analytics.readonly') && (
                    <li className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-green-600" />
                      Google Analytics 4 (Read-only)
                    </li>
                  )}
                  {googleScopes.includes('https://www.googleapis.com/auth/userinfo.email') && (
                    <li className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-green-600" />
                      User Email
                    </li>
                  )}
                </ul>
              </div>
              
              <div className="pt-2">
                <Button 
                  variant="destructive" 
                  onClick={handleDisconnectGoogle}
                >
                  <X className="h-4 w-4 mr-2" />
                  Disconnect Google Account
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
                <AlertCircle className="h-5 w-5 text-yellow-600" />
                <div className="flex-1">
                  <p className="font-medium text-yellow-900 dark:text-yellow-100">
                    Google Account Not Connected
                  </p>
                  <p className="text-sm text-yellow-700 dark:text-yellow-300">
                    Connect your Google account to access Search Console and Analytics data.
                  </p>
                </div>
              </div>
              
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  By connecting your Google account, you&apos;ll be able to:
                </p>
                <ul className="text-sm text-muted-foreground space-y-2 ml-4">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">•</span>
                    View Search Console data including search queries, impressions, and clicks
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">•</span>
                    Access Google Analytics 4 data for user behavior and revenue tracking
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">•</span>
                    Track Core Web Vitals and page performance metrics
                  </li>
                </ul>
              </div>
              
              <div className="pt-2">
                <Button onClick={handleConnectGoogle}>
                  <Globe className="h-4 w-4 mr-2" />
                  Connect Google Account
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Settings</CardTitle>
          <CardDescription>Additional project configuration options</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Export Project Data</p>
              <p className="text-sm text-muted-foreground">
                Download all project data in CSV format
              </p>
            </div>
            <Button variant="outline">Export</Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">API Access</p>
              <p className="text-sm text-muted-foreground">
                Generate API keys for programmatic access
              </p>
            </div>
            <Button variant="outline">Manage Keys</Button>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>Irreversible actions for this project</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border border-destructive rounded-lg">
            <div>
              <p className="font-medium">Delete Project</p>
              <p className="text-sm text-muted-foreground">
                Permanently delete this project and all associated data
              </p>
            </div>
            <Button variant="destructive">Delete Project</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ProjectDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { currentOrganization: organization } = useProjectContext();
  const { toast } = useToast();
  const [project, setProject] = useState<Project | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Crawler status integration
  const projectId = params.id as string;
  const { crawlerStatus, isActive: isCrawlerActive, dismissStatus } = useCrawlerStatus(projectId);
  
  // Modal states
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
  });
  
  const defaultTab = searchParams.get('tab') || 'overview';

  // <-- CHANGE: Wrapped in useCallback
  const fetchProjectData = useCallback(async () => {
    try {
      setLoading(true);
      const [projectResponse, analysisResponse] = await Promise.allSettled([
        api.projects.get(projectId),
        api.projects.getAnalysisStatus?.(projectId)
      ]);
      
      if (projectResponse.status === 'fulfilled') {
        setProject(projectResponse.value.data);
        setFormData({
          name: projectResponse.value.data.name,
          description: projectResponse.value.data.description || "",
        });
      } else {
        throw new Error('Failed to fetch project');
      }
      
      if (analysisResponse.status === 'fulfilled') {
        setAnalysisStatus(analysisResponse.value?.data);
      }
    } catch (error) {
      console.error("Failed to fetch project data:", error);
      toast({
        title: "Error",
        description: "Failed to load project data",
        variant: "destructive",
      });
      router.push("/projects");
    } finally {
      setLoading(false);
    }
  }, [projectId, router, toast]);

  useEffect(() => {
    if (projectId) {
      fetchProjectData();
    }
  }, [projectId, fetchProjectData]); // <-- CHANGE: Updated dependency array

  const handleEditProject = async () => {
    if (!project) return;
    
    try {
      const response = await api.projects.update(project.id, formData);
      setProject(response.data);
      setEditModalOpen(false);
      toast({
        title: "Success",
        description: "Project updated successfully.",
      });
    } catch (error) {
      console.error("Failed to update project:", error);
      toast({
        title: "Error",
        description: "Failed to update project. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteProject = async () => {
    if (!project) return;
    
    try {
      await api.projects.delete(project.id);
      toast({
        title: "Success",
        description: "Project deleted successfully.",
      });
      router.push("/projects");
    } catch (error) {
      console.error("Failed to delete project:", error);
      toast({
        title: "Error",
        description: "Failed to delete project. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (!project && !loading) {
    return null;
  }

  return (
    <>
      <DetailLayout
        title={project?.name || "Loading..."}
        subtitle={project?.description}
        status={project?.is_active ? {
          label: "Active",
          variant: "default" as const
        } : {
          label: "Inactive",
          variant: "secondary" as const
        }}
        breadcrumbs={[
          { label: "Projects", href: "/projects" },
          { label: project?.name || "Project" }
        ]}
        actions={[
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
            icon: FolderOpen,
            content: project ? (
              <OverviewTab 
                project={project} 
                analysisStatus={analysisStatus} 
                crawlerStatus={crawlerStatus}
                isCrawlerActive={isCrawlerActive}
                onDismissCrawler={dismissStatus}
              />
            ) : null,
          },
          {
            id: "sites",
            label: "Sites",
            icon: Globe,
            badge: project?.sites_count,
            content: project ? <SitesTab project={project} onUpdate={fetchProjectData} /> : null,
          },
          {
            id: "team",
            label: "Team",
            icon: Users,
            badge: project?.team_members_count,
            content: project ? <TeamTab project={project} onUpdate={fetchProjectData} /> : null,
          },
          {
            id: "settings",
            label: "Settings",
            icon: Settings,
            content: project ? <SettingsTab project={project} onUpdate={fetchProjectData} /> : null,
          },
        ]}
        defaultTab={defaultTab}
        loading={loading}
        metadata={project ? [
          {
            label: "Organization",
            value: organization?.name || "Unknown",
            icon: Shield,
          },
          {
            label: "Created",
            value: new Date(project.created_at).toLocaleDateString(),
            icon: Calendar,
          },
        ] : []}
      />

      {/* Edit Project Modal */}
      <EntityModal
        entity="project"
        action="edit"
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        title="Edit Project"
        description="Update project information."
        onSubmit={handleEditProject}
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="edit-name">Project Name</Label>
            <Input
              id="edit-name"
              placeholder="My SEO Project"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="edit-description">Description</Label>
            <Textarea
              id="edit-description"
              placeholder="Brief description of the project..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>
        </div>
      </EntityModal>

      {/* Delete Confirmation Modal */}
      <ConfirmActionModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        onConfirm={handleDeleteProject}
        type="danger"
        title="Delete Project"
        message={`Are you sure you want to delete ${project?.name}? This action cannot be undone and will remove all project data, sites, team members, configurations, and analytics.`}
        confirmLabel="Delete Project"
      />
    </>
  );
}

export default function ProjectDetailPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div></div>}>
      <ProjectDetailPageContent />
    </Suspense>
  );
}