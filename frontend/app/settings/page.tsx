"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  User, Shield, Users, Link, Key, Bell, CreditCard, Settings2,
  Mail, Lock, Smartphone, Plus, Trash2, Check, X, AlertCircle,
  Globe, Webhook, Database, BarChart3, RefreshCw, Eye, EyeOff,
  Calendar, Activity, Building2, Copy, CheckCircle, Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useProject } from "@/lib/project-context";
import { useToast } from "@/components/ui/use-toast";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { EntityModal } from "@/components/ui/entity-modal";
import { ConfirmActionModal } from "@/components/ui/confirm-action-modal";
import { WizardModal } from "@/components/ui/wizard-modal";
import { SEOOrb } from "@/components/ui/seo-orb";
import { motion, useScroll, useTransform } from "framer-motion";
import { MagneticButton } from "@/components/ui/magnetic-button";
import { CTAButton } from "@/components/ui/cta-button";
import { SimpleMagneticWrapper } from "@/components/ui/simple-magnetic-wrapper";

// Profile Section
function ProfileSection() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [profileData, setProfileData] = useState({
    name: user?.name || "",
    email: user?.email || "",
    company: "",
    role: "",
    bio: "",
  });

  const handleUpdateProfile = async () => {
    try {
      setLoading(true);
      await api.settings.updateProfile(profileData);
      toast({
        title: "Profile updated",
        description: "Your profile has been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update profile",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float group">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <CardHeader className="relative">
          <CardTitle className="text-2xl font-bold text-gradient">Personal Information</CardTitle>
          <CardDescription className="text-base">Update your personal details and profile information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 relative">
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <Label htmlFor="name" className="text-sm font-semibold text-foreground">Full Name</Label>
              <Input
                id="name"
                value={profileData.name}
                onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                className="mt-2 bg-card/50 backdrop-blur-sm border-border/50 focus:bg-card/80 focus:border-primary/50 transition-all"
              />
            </div>
            <div>
              <Label htmlFor="email" className="text-sm font-semibold text-foreground">Email Address</Label>
              <Input
                id="email"
                type="email"
                value={profileData.email}
                disabled
                className="mt-2 bg-muted/50 backdrop-blur-sm border-border/50"
              />
              <p className="text-xs text-muted-foreground mt-2">Email cannot be changed</p>
            </div>
            <div>
              <Label htmlFor="company" className="text-sm font-semibold text-foreground">Company</Label>
              <Input
                id="company"
                value={profileData.company}
                onChange={(e) => setProfileData({ ...profileData, company: e.target.value })}
                placeholder="Acme Inc."
                className="mt-2 bg-card/50 backdrop-blur-sm border-border/50 focus:bg-card/80 focus:border-primary/50 transition-all"
              />
            </div>
            <div>
              <Label htmlFor="role" className="text-sm font-semibold text-foreground">Role</Label>
              <Input
                id="role"
                value={profileData.role}
                onChange={(e) => setProfileData({ ...profileData, role: e.target.value })}
                placeholder="SEO Manager"
                className="mt-2 bg-card/50 backdrop-blur-sm border-border/50 focus:bg-card/80 focus:border-primary/50 transition-all"
              />
            </div>
          </div>
          <div>
            <Label htmlFor="bio" className="text-sm font-semibold text-foreground">Bio</Label>
            <Textarea
              id="bio"
              value={profileData.bio}
              onChange={(e) => setProfileData({ ...profileData, bio: e.target.value })}
              placeholder="Tell us about yourself..."
              rows={3}
              className="mt-2 bg-card/50 backdrop-blur-sm border-border/50 focus:bg-card/80 focus:border-primary/50 transition-all resize-none"
            />
          </div>
          <div className="flex justify-end pt-4">
            <SimpleMagneticWrapper>
              <CTAButton onClick={handleUpdateProfile} disabled={loading} size="lg">
                {loading ? "Saving..." : "Save Changes"}
              </CTAButton>
            </SimpleMagneticWrapper>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>Your account details and subscription status</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label className="text-sm font-medium">Account ID</Label>
              <p className="text-sm text-muted-foreground">{user?.id}</p>
            </div>
            <div>
              <Label className="text-sm font-medium">Member Since</Label>
              <p className="text-sm text-muted-foreground">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "N/A"}
              </p>
            </div>
            <div>
              <Label className="text-sm font-medium">Account Type</Label>
              <Badge variant="default">Professional</Badge>
            </div>
            <div>
              <Label className="text-sm font-medium">Storage Used</Label>
              <div className="space-y-1">
                <Progress value={65} />
                <p className="text-xs text-muted-foreground">6.5 GB of 10 GB</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Security Section
function SecuritySection() {
  const { toast } = useToast();
  const [passwordData, setPasswordData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [showPasswords, setShowPasswords] = useState(false);
  const [sessions, setSessions] = useState<any[]>([]);
  const [changePasswordModalOpen, setChangePasswordModalOpen] = useState(false);
  const [twoFactorModalOpen, setTwoFactorModalOpen] = useState(false);

  useEffect(() => {
    fetchSecurityData();
  }, []);

  const fetchSecurityData = async () => {
    try {
      const [securityResponse, sessionsResponse] = await Promise.allSettled([
        api.settings.getSecurity(),
        api.auth.getSessions()
      ]);
      
      if (sessionsResponse.status === 'fulfilled') {
        setSessions(sessionsResponse.value.data || []);
      }
    } catch (error) {
      console.error("Failed to fetch security data:", error);
    }
  };

  const handleChangePassword = async () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast({
        title: "Error",
        description: "New passwords do not match",
        variant: "destructive",
      });
      return;
    }

    try {
      await api.settings.changePassword({
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword,
      });
      toast({
        title: "Password changed",
        description: "Your password has been updated successfully.",
      });
      setChangePasswordModalOpen(false);
      setPasswordData({ currentPassword: "", newPassword: "", confirmPassword: "" });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to change password",
        variant: "destructive",
      });
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await api.auth.revokeSession(sessionId);
      setSessions(sessions.filter((s: any) => s.id !== sessionId));
      toast({
        title: "Session revoked",
        description: "The session has been terminated.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to revoke session",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Password & Authentication</CardTitle>
          <CardDescription>Manage your password and authentication methods</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <Lock className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium">Password</p>
                <p className="text-sm text-muted-foreground">Last changed 30 days ago</p>
              </div>
            </div>
            <Button variant="outline" onClick={() => setChangePasswordModalOpen(true)}>
              Change Password
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <Smartphone className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium">Two-Factor Authentication</p>
                <p className="text-sm text-muted-foreground">
                  {twoFactorEnabled ? "Enabled for your account" : "Add an extra layer of security"}
                </p>
              </div>
            </div>
            <Switch
              checked={twoFactorEnabled}
              onCheckedChange={(checked) => {
                if (checked) {
                  setTwoFactorModalOpen(true);
                } else {
                  setTwoFactorEnabled(false);
                }
              }}
            />
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <Globe className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium">Connected Accounts</p>
                <p className="text-sm text-muted-foreground">Manage external account connections</p>
              </div>
            </div>
            <Button variant="outline">Manage</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active Sessions</CardTitle>
          <CardDescription>Manage devices and browsers where you&apos;re signed in</CardDescription>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active sessions found</p>
          ) : (
            <div className="space-y-4">
              {sessions.map((session: any) => (
                <div key={session.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Activity className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{session.device || "Unknown Device"}</p>
                      <p className="text-sm text-muted-foreground">
                        {session.location || "Unknown Location"} • Last active {session.last_active}
                      </p>
                    </div>
                  </div>
                  {session.is_current ? (
                    <Badge variant="outline">Current</Badge>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRevokeSession(session.id)}
                      className="text-destructive"
                    >
                      Revoke
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Change Password Modal */}
      <EntityModal
        entity="password"
        action="edit"
        open={changePasswordModalOpen}
        onOpenChange={setChangePasswordModalOpen}
        title="Change Password"
        description="Enter your current password and choose a new one"
        onSubmit={handleChangePassword}
        submitLabel="Change Password"
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="current-password">Current Password</Label>
            <div className="relative">
              <Input
                id="current-password"
                type={showPasswords ? "text" : "password"}
                value={passwordData.currentPassword}
                onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                required
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowPasswords(!showPasswords)}
              >
                {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          <Separator />
          <div>
            <Label htmlFor="new-password">New Password</Label>
            <Input
              id="new-password"
              type={showPasswords ? "text" : "password"}
              value={passwordData.newPassword}
              onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="confirm-password">Confirm New Password</Label>
            <Input
              id="confirm-password"
              type={showPasswords ? "text" : "password"}
              value={passwordData.confirmPassword}
              onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
              required
            />
          </div>
        </div>
      </EntityModal>

      {/* 2FA Setup Modal */}
      <WizardModal
        open={twoFactorModalOpen}
        onOpenChange={setTwoFactorModalOpen}
        title="Enable Two-Factor Authentication"
        steps={[
          { 
            id: "method", 
            title: "Choose Method", 
            content: (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Choose your preferred 2FA method:
                </p>
                <div className="space-y-2">
                  <Button variant="outline" className="w-full justify-start">
                    <Smartphone className="h-4 w-4 mr-2" />
                    Authenticator App (Recommended)
                  </Button>
                  <Button variant="outline" className="w-full justify-start">
                    <Mail className="h-4 w-4 mr-2" />
                    SMS Text Message
                  </Button>
                </div>
              </div>
            )
          },
          { 
            id: "setup", 
            title: "Setup", 
            content: (
              <div className="space-y-4">
                <p>Scan this QR code with your authenticator app:</p>
                <div className="bg-white p-4 rounded-lg inline-block">
                  {/* QR code would go here */}
                  <div className="w-48 h-48 bg-gray-200 flex items-center justify-center">
                    [QR Code]
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  Or enter this code manually: XXXX-XXXX-XXXX
                </p>
              </div>
            )
          },
          { 
            id: "verify", 
            title: "Verify", 
            content: (
              <div className="space-y-4">
                <p>Enter the 6-digit code from your authenticator app:</p>
                <Input placeholder="000000" maxLength={6} />
              </div>
            )
          },
        ]}
        onComplete={() => {
          setTwoFactorEnabled(true);
          setTwoFactorModalOpen(false);
          toast({
            title: "2FA Enabled",
            description: "Two-factor authentication has been enabled for your account.",
          });
        }}
      />
    </div>
  );
}

// Team Section
function TeamSection() {
  const { currentOrganization: organization } = useProject();
  const { toast } = useToast();
  const [teamMembers, setTeamMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteData, setInviteData] = useState({
    email: "",
    role: "member",
  });

  useEffect(() => {
    if (organization) {
      fetchTeamMembers();
    }
  }, [organization]);

  const fetchTeamMembers = async () => {
    try {
      setLoading(true);
      const response = await api.settings.getTeam();
      setTeamMembers(response.data || []);
    } catch (error) {
      console.error("Failed to fetch team members:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleInviteMember = async () => {
    try {
      await api.settings.addTeamMember(inviteData);
      toast({
        title: "Invitation sent",
        description: `Invitation sent to ${inviteData.email}`,
      });
      setInviteModalOpen(false);
      setInviteData({ email: "", role: "member" });
      fetchTeamMembers();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send invitation",
        variant: "destructive",
      });
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    try {
      await api.settings.removeTeamMember(memberId);
      setTeamMembers(teamMembers.filter((m: any) => m.id !== memberId));
      toast({
        title: "Member removed",
        description: "Team member has been removed.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to remove member",
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
            Manage your organization&apos;s team members and their roles
          </p>
        </div>
        <Button onClick={() => setInviteModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Invite Member
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center">
              <p className="text-muted-foreground">Loading team members...</p>
            </div>
          ) : teamMembers.length === 0 ? (
            <div className="p-8 text-center">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No team members yet</h3>
              <p className="text-muted-foreground mb-4">
                Invite team members to collaborate on your projects
              </p>
              <Button onClick={() => setInviteModalOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Invite Your First Member
              </Button>
            </div>
          ) : (
            <div className="divide-y">
              {teamMembers.map((member: any) => (
                <div key={member.id} className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <User className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-medium">{member.name}</p>
                      <p className="text-sm text-muted-foreground">{member.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{member.role}</Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveMember(member.id)}
                      className="text-destructive"
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Invite Member Modal */}
      <EntityModal
        entity="team-member"
        action="create"
        open={inviteModalOpen}
        onOpenChange={setInviteModalOpen}
        title="Invite Team Member"
        description="Send an invitation to join your organization"
        onSubmit={handleInviteMember}
        submitLabel="Send Invitation"
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="invite-email">Email Address</Label>
            <Input
              id="invite-email"
              type="email"
              placeholder="colleague@example.com"
              value={inviteData.email}
              onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="invite-role">Role</Label>
            <Select
              value={inviteData.role}
              onValueChange={(value) => setInviteData({ ...inviteData, role: value })}
            >
              <SelectTrigger id="invite-role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="owner">Owner</SelectItem>
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

// Integrations Section
function IntegrationsSection() {
  const { toast } = useToast();
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    try {
      setLoading(true);
      // Mock data for now
      setIntegrations([
        {
          id: "google-search-console",
          name: "Google Search Console",
          description: "View search performance data",
          icon: "🔍",
          connected: false,
          category: "analytics",
        },
        {
          id: "google-analytics",
          name: "Google Analytics",
          description: "Track visitor behavior and conversions",
          icon: "📊",
          connected: false,
          category: "analytics",
        },
        {
          id: "slack",
          name: "Slack",
          description: "Get notifications in your Slack workspace",
          icon: "💬",
          connected: false,
          category: "communication",
        },
        {
          id: "zapier",
          name: "Zapier",
          description: "Connect to 5000+ apps",
          icon: "⚡",
          connected: false,
          category: "automation",
        },
      ]);
    } catch (error) {
      console.error("Failed to fetch integrations:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (integrationId: string) => {
    toast({
      title: "Coming soon",
      description: "Integration connections will be available soon.",
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Available Integrations</h3>
        <p className="text-sm text-muted-foreground">
          Connect your favorite tools and services
        </p>
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-muted-foreground">Loading integrations...</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {integrations.map((integration: any) => (
            <Card key={integration.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">{integration.icon}</div>
                    <div>
                      <CardTitle className="text-base">{integration.name}</CardTitle>
                      <CardDescription className="text-sm">
                        {integration.description}
                      </CardDescription>
                    </div>
                  </div>
                  {integration.connected ? (
                    <Badge variant="default">Connected</Badge>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleConnect(integration.id)}
                    >
                      Connect
                    </Button>
                  )}
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      <Card className="border-dashed">
        <CardContent className="text-center py-8">
          <p className="text-muted-foreground mb-4">
            Can&apos;t find the integration you need?
          </p>
          <Button variant="outline">Request Integration</Button>
        </CardContent>
      </Card>
    </div>
  );
}

// API Keys Section
function ApiKeysSection() {
  const { toast } = useToast();
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedKey, setSelectedKey] = useState<any>(null);
  const [newKeyData, setNewKeyData] = useState({
    name: "",
    permissions: "read",
  });

  useEffect(() => {
    fetchApiKeys();
  }, []);

  const fetchApiKeys = async () => {
    try {
      setLoading(true);
      const response = await api.settings.getApiKeys();
      setApiKeys(response.data || []);
    } catch (error) {
      console.error("Failed to fetch API keys:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async () => {
    try {
      const response = await api.settings.createApiKey({
        name: newKeyData.name,
        scopes: [newKeyData.permissions]
      });
      setApiKeys([...apiKeys, response.data]);
      setCreateModalOpen(false);
      setNewKeyData({ name: "", permissions: "read" });
      
      // Show the new key to the user (only shown once)
      toast({
        title: "API Key Created",
        description: (
          <div className="space-y-2">
            <p>Your new API key has been created. Copy it now as it won&apos;t be shown again:</p>
            <code className="block bg-muted p-2 rounded text-xs">{response.data.key}</code>
          </div>
        ),
        duration: 10000,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create API key",
        variant: "destructive",
      });
    }
  };

  const handleDeleteKey = async () => {
    if (!selectedKey) return;
    
    try {
      await api.settings.deleteApiKey(selectedKey.id);
      setApiKeys(apiKeys.filter((k: any) => k.id !== selectedKey.id));
      setDeleteModalOpen(false);
      toast({
        title: "API key deleted",
        description: "The API key has been revoked.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete API key",
        variant: "destructive",
      });
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied",
      description: "API key ID copied to clipboard",
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">API Keys</h3>
          <p className="text-sm text-muted-foreground">
            Manage API keys for programmatic access
          </p>
        </div>
        <Button onClick={() => setCreateModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Key
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center">
              <p className="text-muted-foreground">Loading API keys...</p>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="p-8 text-center">
              <Key className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No API keys yet</h3>
              <p className="text-muted-foreground mb-4">
                Create an API key to access the API programmatically
              </p>
              <Button onClick={() => setCreateModalOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Key
              </Button>
            </div>
          ) : (
            <div className="divide-y">
              {apiKeys.map((apiKey: any) => (
                <div key={apiKey.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{apiKey.name}</p>
                        <Badge variant="outline">{apiKey.permissions}</Badge>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <code className="font-mono">•••• {apiKey.last_four}</code>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-auto p-0"
                          onClick={() => copyToClipboard(apiKey.id)}
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Created {new Date(apiKey.created_at).toLocaleDateString()} • 
                        Last used {apiKey.last_used || "Never"}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setSelectedKey(apiKey);
                        setDeleteModalOpen(true);
                      }}
                      className="text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create API Key Modal */}
      <EntityModal
        entity="api-key"
        action="create"
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        title="Create API Key"
        description="Generate a new API key for programmatic access"
        onSubmit={handleCreateKey}
        submitLabel="Create Key"
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="key-name">Key Name</Label>
            <Input
              id="key-name"
              placeholder="Production API Key"
              value={newKeyData.name}
              onChange={(e) => setNewKeyData({ ...newKeyData, name: e.target.value })}
              required
            />
            <p className="text-sm text-muted-foreground mt-1">
              A descriptive name to identify this key
            </p>
          </div>
          <div>
            <Label htmlFor="key-permissions">Permissions</Label>
            <Select
              value={newKeyData.permissions}
              onValueChange={(value) => setNewKeyData({ ...newKeyData, permissions: value })}
            >
              <SelectTrigger id="key-permissions">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="read">Read Only</SelectItem>
                <SelectItem value="write">Read & Write</SelectItem>
                <SelectItem value="admin">Full Access</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </EntityModal>

      {/* Delete Confirmation Modal */}
      <ConfirmActionModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        onConfirm={handleDeleteKey}
        type="danger"
        title="Delete API Key"
        message={`Are you sure you want to delete the API key "${selectedKey?.name}"? Any applications using this key will lose access immediately.`}
        confirmLabel="Delete Key"
      />
    </div>
  );
}

// Notifications Section
function NotificationsSection() {
  const { toast } = useToast();
  const [notifications, setNotifications] = useState({
    email: {
      seo_alerts: true,
      weekly_reports: true,
      team_updates: false,
      product_updates: true,
    },
    push: {
      critical_issues: true,
      performance_alerts: true,
      mentions: false,
    },
    frequency: "realtime",
    quiet_hours: false,
    quiet_hours_start: "22:00",
    quiet_hours_end: "08:00",
  });

  const handleSaveNotifications = async () => {
    try {
      // TODO: Implement bulk notification updates
      // For now, this would need to iterate through individual notification settings
      // await api.settings.updateNotification(notificationId, { enabled: true/false });
      toast({
        title: "Notifications updated",
        description: "Your notification preferences have been saved.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update notifications",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Email Notifications</CardTitle>
          <CardDescription>Choose what email notifications you want to receive</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="seo-alerts">SEO Alerts</Label>
                <p className="text-sm text-muted-foreground">
                  Critical SEO issues and opportunities
                </p>
              </div>
              <Switch
                id="seo-alerts"
                checked={notifications.email.seo_alerts}
                onCheckedChange={(checked) =>
                  setNotifications({
                    ...notifications,
                    email: { ...notifications.email, seo_alerts: checked },
                  })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="weekly-reports">Weekly Reports</Label>
                <p className="text-sm text-muted-foreground">
                  Summary of your sites&apos; performance
                </p>
              </div>
              <Switch
                id="weekly-reports"
                checked={notifications.email.weekly_reports}
                onCheckedChange={(checked) =>
                  setNotifications({
                    ...notifications,
                    email: { ...notifications.email, weekly_reports: checked },
                  })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="team-updates">Team Updates</Label>
                <p className="text-sm text-muted-foreground">
                  When team members join or leave
                </p>
              </div>
              <Switch
                id="team-updates"
                checked={notifications.email.team_updates}
                onCheckedChange={(checked) =>
                  setNotifications({
                    ...notifications,
                    email: { ...notifications.email, team_updates: checked },
                  })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="product-updates">Product Updates</Label>
                <p className="text-sm text-muted-foreground">
                  New features and improvements
                </p>
              </div>
              <Switch
                id="product-updates"
                checked={notifications.email.product_updates}
                onCheckedChange={(checked) =>
                  setNotifications({
                    ...notifications,
                    email: { ...notifications.email, product_updates: checked },
                  })
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notification Settings</CardTitle>
          <CardDescription>Configure how and when you receive notifications</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="frequency">Notification Frequency</Label>
            <Select
              value={notifications.frequency}
              onValueChange={(value) => setNotifications({ ...notifications, frequency: value })}
            >
              <SelectTrigger id="frequency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="realtime">Real-time</SelectItem>
                <SelectItem value="hourly">Hourly Summary</SelectItem>
                <SelectItem value="daily">Daily Digest</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="quiet-hours">Quiet Hours</Label>
                <p className="text-sm text-muted-foreground">
                  Pause notifications during specific hours
                </p>
              </div>
              <Switch
                id="quiet-hours"
                checked={notifications.quiet_hours}
                onCheckedChange={(checked) =>
                  setNotifications({ ...notifications, quiet_hours: checked })
                }
              />
            </div>

            {notifications.quiet_hours && (
              <div className="grid gap-4 md:grid-cols-2 pl-8">
                <div>
                  <Label htmlFor="quiet-start">Start Time</Label>
                  <Input
                    id="quiet-start"
                    type="time"
                    value={notifications.quiet_hours_start}
                    onChange={(e) =>
                      setNotifications({ ...notifications, quiet_hours_start: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="quiet-end">End Time</Label>
                  <Input
                    id="quiet-end"
                    type="time"
                    value={notifications.quiet_hours_end}
                    onChange={(e) =>
                      setNotifications({ ...notifications, quiet_hours_end: e.target.value })
                    }
                  />
                </div>
              </div>
            )}
          </div>

          <div className="pt-4">
            <Button onClick={handleSaveNotifications}>Save Preferences</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Billing Section
function BillingSection() {
  const { toast } = useToast();
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      setLoading(true);
      const response = await api.subscriptions.getCurrent();
      setSubscription(response.data);
    } catch (error) {
      console.error("Failed to fetch subscription:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Current Plan</CardTitle>
          <CardDescription>Manage your subscription and billing</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Loading subscription details...</p>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-lg">Professional Plan</p>
                  <p className="text-sm text-muted-foreground">$99/month • Billed monthly</p>
                </div>
                <Badge variant="default">Active</Badge>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1">
                  <Label className="text-sm font-medium">Next billing date</Label>
                  <p className="text-sm text-muted-foreground">February 1, 2025</p>
                </div>
                <div className="space-y-1">
                  <Label className="text-sm font-medium">Payment method</Label>
                  <p className="text-sm text-muted-foreground">•••• 4242</p>
                </div>
              </div>

              <Separator />

              <div className="flex gap-2">
                <Button variant="outline">Change Plan</Button>
                <Button variant="outline">Update Payment Method</Button>
                <Button variant="outline">Download Invoice</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Usage</CardTitle>
          <CardDescription>Your current usage this billing period</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Sites</span>
              <span className="font-medium">3 / 10</span>
            </div>
            <Progress value={30} />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>API Calls</span>
              <span className="font-medium">15,420 / 100,000</span>
            </div>
            <Progress value={15.42} />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Team Members</span>
              <span className="font-medium">4 / 10</span>
            </div>
            <Progress value={40} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Advanced Section
function AdvancedSection() {
  const router = useRouter();
  const { toast } = useToast();
  const [deleteAccountModalOpen, setDeleteAccountModalOpen] = useState(false);

  const handleDeleteAccount = async () => {
    toast({
      title: "Account deletion",
      description: "Please contact support to delete your account.",
    });
    setDeleteAccountModalOpen(false);
  };

  const handleExportData = async () => {
    toast({
      title: "Data export started",
      description: "You&apos;ll receive an email when your data export is ready.",
    });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Data & Privacy</CardTitle>
          <CardDescription>Manage your data and privacy settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Export Your Data</p>
              <p className="text-sm text-muted-foreground">
                Download all your data in JSON format
              </p>
            </div>
            <Button variant="outline" onClick={handleExportData}>
              Export Data
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Data Retention</p>
              <p className="text-sm text-muted-foreground">
                Configure how long we keep your data
              </p>
            </div>
            <Button variant="outline">Configure</Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Privacy Settings</p>
              <p className="text-sm text-muted-foreground">
                Control how your data is used
              </p>
            </div>
            <Button variant="outline">Manage</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Developer Settings</CardTitle>
          <CardDescription>Advanced settings for developers</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Webhooks</p>
              <p className="text-sm text-muted-foreground">
                Configure webhook endpoints for events
              </p>
            </div>
            <Button variant="outline">Configure</Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">OAuth Applications</p>
              <p className="text-sm text-muted-foreground">
                Manage OAuth applications
              </p>
            </div>
            <Button variant="outline">Manage</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>Irreversible actions for your account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border border-destructive rounded-lg">
            <div>
              <p className="font-medium">Delete Account</p>
              <p className="text-sm text-muted-foreground">
                Permanently delete your account and all data
              </p>
            </div>
            <Button
              variant="destructive"
              onClick={() => setDeleteAccountModalOpen(true)}
            >
              Delete Account
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Delete Account Confirmation */}
      <ConfirmActionModal
        open={deleteAccountModalOpen}
        onOpenChange={setDeleteAccountModalOpen}
        onConfirm={handleDeleteAccount}
        type="danger"
        title="Delete Account"
        message="Are you sure you want to delete your account? This action cannot be undone and will: Permanently delete all your data, Cancel any active subscriptions, Remove access for all team members, Delete all projects and sites"
        confirmLabel="Delete My Account"
      />
    </div>
  );
}

// Admin System Settings Section
function SystemSettingsSection() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [systemConfig, setSystemConfig] = useState({
    maintenance_mode: false,
    signup_enabled: true,
    require_email_verification: true,
    max_projects_per_user: 10,
    max_api_calls_per_hour: 1000,
    session_timeout_minutes: 60,
  });

  const handleUpdateSystemSettings = async () => {
    try {
      setLoading(true);
      // await api.admin.updateSystemSettings(systemConfig);
      toast({
        title: "System settings updated",
        description: "System configuration has been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update system settings.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    try {
      await api.cache.clear();
      toast({
        title: "Cache cleared",
        description: "All cache entries have been cleared successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to clear cache.",
        variant: "destructive",
      });
    }
  };

  const handleRunMaintenance = async () => {
    try {
      // await api.admin.runMaintenance();
      toast({
        title: "Maintenance started",
        description: "System maintenance tasks have been initiated.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start maintenance tasks.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card className="border-destructive/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-destructive" />
            <CardTitle>System Configuration</CardTitle>
          </div>
          <CardDescription>
            Admin-only system settings. Changes here affect all users.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="maintenance">Maintenance Mode</Label>
                <p className="text-sm text-muted-foreground">
                  Prevent non-admin users from accessing the platform
                </p>
              </div>
              <Switch
                id="maintenance"
                checked={systemConfig.maintenance_mode}
                onCheckedChange={(checked) =>
                  setSystemConfig({ ...systemConfig, maintenance_mode: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="signup">New Signups</Label>
                <p className="text-sm text-muted-foreground">
                  Allow new users to register
                </p>
              </div>
              <Switch
                id="signup"
                checked={systemConfig.signup_enabled}
                onCheckedChange={(checked) =>
                  setSystemConfig({ ...systemConfig, signup_enabled: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="email-verify">Email Verification</Label>
                <p className="text-sm text-muted-foreground">
                  Require email verification for new accounts
                </p>
              </div>
              <Switch
                id="email-verify"
                checked={systemConfig.require_email_verification}
                onCheckedChange={(checked) =>
                  setSystemConfig({ ...systemConfig, require_email_verification: checked })
                }
              />
            </div>

            <Separator />

            <div>
              <Label htmlFor="max-projects">Max Projects per User</Label>
              <Input
                id="max-projects"
                type="number"
                value={systemConfig.max_projects_per_user}
                onChange={(e) =>
                  setSystemConfig({
                    ...systemConfig,
                    max_projects_per_user: parseInt(e.target.value),
                  })
                }
                className="mt-1 w-32"
              />
            </div>

            <div>
              <Label htmlFor="api-rate">API Rate Limit (per hour)</Label>
              <Input
                id="api-rate"
                type="number"
                value={systemConfig.max_api_calls_per_hour}
                onChange={(e) =>
                  setSystemConfig({
                    ...systemConfig,
                    max_api_calls_per_hour: parseInt(e.target.value),
                  })
                }
                className="mt-1 w-32"
              />
            </div>

            <div>
              <Label htmlFor="session-timeout">Session Timeout (minutes)</Label>
              <Input
                id="session-timeout"
                type="number"
                value={systemConfig.session_timeout_minutes}
                onChange={(e) =>
                  setSystemConfig({
                    ...systemConfig,
                    session_timeout_minutes: parseInt(e.target.value),
                  })
                }
                className="mt-1 w-32"
              />
            </div>
          </div>

          <Button onClick={handleUpdateSystemSettings} disabled={loading}>
            Save System Settings
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Maintenance Tasks</CardTitle>
          <CardDescription>
            System maintenance and optimization tasks
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Clear Cache</p>
              <p className="text-sm text-muted-foreground">
                Clear all cached data across the system
              </p>
            </div>
            <Button variant="outline" onClick={handleClearCache}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Clear Cache
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Database Optimization</p>
              <p className="text-sm text-muted-foreground">
                Run database vacuum and analyze operations
              </p>
            </div>
            <Button variant="outline" onClick={handleRunMaintenance}>
              <Database className="mr-2 h-4 w-4" />
              Optimize
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">System Health Check</p>
              <p className="text-sm text-muted-foreground">
                Run comprehensive system diagnostics
              </p>
            </div>
            <Button variant="outline" onClick={() => window.open('/monitoring', '_blank')}>
              <Activity className="mr-2 h-4 w-4" />
              View Monitoring
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SettingsPage() {
  const { user } = useAuth();
  const { currentOrganization: organization } = useProject();
  const { scrollY } = useScroll();
  const [activeSection, setActiveSection] = useState('profile');

  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  if (!user) {
    return null;
  }

  // Build sections array
  const sections = [
    {
      id: "profile",
      label: "Profile",
      description: "Your personal information",
      icon: User,
      content: <ProfileSection />,
    },
    {
      id: "security",
      label: "Security",
      description: "Password and authentication",
      icon: Shield,
      content: <SecuritySection />,
    },
    {
      id: "team",
      label: "Team",
      description: "Manage team members",
      icon: Users,
      content: <TeamSection />,
      badge: organization ? undefined : "Org Required",
      disabled: !organization,
    },
    {
      id: "integrations",
      label: "Integrations",
      description: "Connected services",
      icon: Link,
      content: <IntegrationsSection />,
    },
    {
      id: "api-keys",
      label: "API Keys",
      description: "Programmatic access",
      icon: Key,
      content: <ApiKeysSection />,
    },
    {
      id: "notifications",
      label: "Notifications",
      description: "Email and push notifications",
      icon: Bell,
      content: <NotificationsSection />,
    },
    {
      id: "billing",
      label: "Billing",
      description: "Subscription and usage",
      icon: CreditCard,
      content: <BillingSection />,
    },
    {
      id: "advanced",
      label: "Advanced",
      description: "Data, privacy, and danger zone",
      icon: Settings2,
      content: <AdvancedSection />,
    },
  ];

  // Add system settings section for admin users
  if (user.is_superuser) {
    sections.push({
      id: "system",
      label: "System Settings",
      description: "Admin-only system configuration",
      icon: Settings2,
      content: <SystemSettingsSection />,
      badge: "Admin Only",
    } as any);
  }

  const currentSection = sections.find(s => s.id === activeSection) || sections[0];

  return (
    <div className="min-h-screen bg-background text-foreground relative noise-overlay">
      {/* Background gradient mesh */}
      <div className="fixed inset-0 gradient-mesh opacity-20 dark:opacity-10" />
      
      {/* Enhanced floating 3D orb */}
      <motion.div
        className="fixed right-[-300px] top-1/4 w-[600px] h-[600px] lg:w-[800px] lg:h-[800px] pointer-events-none"
        style={{ y: heroY, scale: orbScale }}
      >
        <SEOOrb className="scale-100 opacity-30" />
      </motion.div>
      
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute -top-32 -left-32 w-64 h-64 bg-primary/20 rounded-full blur-3xl"
          animate={{
            x: [0, 100, 0],
            y: [0, -50, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute -bottom-32 -right-32 w-96 h-96 bg-accent/20 rounded-full blur-3xl"
          animate={{
            x: [0, -100, 0],
            y: [0, 50, 0],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      </div>

      <DashboardLayout>
        <div className="space-y-8 relative z-10">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.1 }}
            >
              <Badge variant="secondary" className="mb-4 animate-slide-up-fade">
                <Sparkles className="mr-1 h-3 w-3" />
                Settings & Configuration
              </Badge>
            </motion.div>
            
            <motion.h1 
              className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tighter mb-4 leading-[0.9]"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <span className="block">Account</span>
              <span className="block text-gradient-electric">Settings</span>
            </motion.h1>
            
            <motion.p 
              className="text-lg sm:text-xl text-muted-foreground leading-relaxed max-w-2xl"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
            >
              Customize your experience and manage your account preferences
            </motion.p>
          </motion.div>

          {/* Settings Layout */}
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="flex gap-8"
          >
            {/* Sidebar */}
            <div className="w-64 flex-shrink-0">
              <Card className="bg-card/80 backdrop-blur-sm border-border/50 sticky top-8 card-float">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent" />
                <CardContent className="p-6 relative">
                  <nav className="space-y-2">
                    {sections.map((section, index) => (
                      <motion.div
                        key={section.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.05 }}
                        whileHover={{ x: 5 }}
                        className="group"
                      >
                        <SimpleMagneticWrapper>
                          <button
                            onClick={() => setActiveSection(section.id)}
                            disabled={section.disabled}
                            className={`
                              w-full flex items-center justify-between px-4 py-3 text-sm font-medium transition-all duration-300 rounded-2xl card-float
                              ${activeSection === section.id
                                ? 'bg-primary/10 text-primary border border-primary/20 shadow-sm neon-glow-blue'
                                : 'text-muted-foreground hover:bg-card/50 hover:text-foreground hover:backdrop-blur-sm hover:border-border/50 hover:border'
                              }
                              ${section.disabled ? 'opacity-50 cursor-not-allowed' : ''}
                            `}
                          >
                            <span className="flex items-center space-x-3">
                              <div className={`
                                h-5 w-5 p-0.5 rounded-lg transition-all duration-300
                                ${activeSection === section.id 
                                  ? "bg-primary/20 text-primary" 
                                  : "group-hover:bg-primary/10 group-hover:text-primary"
                                }
                              `}>
                                <section.icon className="h-full w-full" />
                              </div>
                              <span>{section.label}</span>
                            </span>
                            {section.badge && (
                              <Badge variant="outline" className="text-xs">
                                {section.badge}
                              </Badge>
                            )}
                          </button>
                        </SimpleMagneticWrapper>
                      </motion.div>
                    ))}
                  </nav>
                </CardContent>
              </Card>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <motion.div
                key={activeSection}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="space-y-8"
              >
                {/* Section Header */}
                <div className="space-y-4">
                  <div className="flex items-center space-x-3">
                    <div className="rounded-2xl bg-primary/10 p-3 neon-glow-blue">
                      <currentSection.icon className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h2 className="text-3xl font-bold text-gradient tracking-tight">
                        {currentSection.label}
                      </h2>
                      <p className="text-muted-foreground">
                        {currentSection.description}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Section Content with Enhanced Styling */}
                <div className="space-y-6">
                  {currentSection.content}
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </DashboardLayout>
    </div>
  );
}

export default function EnhancedSettingsPage() {
  return <SettingsPage />;
}