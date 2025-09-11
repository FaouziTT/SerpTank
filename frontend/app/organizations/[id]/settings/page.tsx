"use client";

import { useState, useEffect, useCallback } from "react"; // <-- CHANGE: Imported useCallback
import { useRouter, useParams } from "next/navigation";
import { 
  ArrowLeft, Settings, Building2, CreditCard, Link2, 
  AlertTriangle, Save, Trash2, Shield, Bell, Webhook,
  Globe, Database, Key, Users, ExternalLink
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { api } from "@/lib/api-client";
import { Organization } from "@/types/api";
import { useAuth } from "@/lib/auth-context";

export default function OrganizationSettingsPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("general");
  
  // Delete confirmation
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleting, setDeleting] = useState(false);
  
  // Form states
  const [generalForm, setGeneralForm] = useState({
    name: "",
    description: "",
  });
  
  const [notificationSettings, setNotificationSettings] = useState({
    emailAlerts: true,
    weeklyReports: false,
    memberUpdates: true,
    projectAlerts: true,
  });

  const organizationId = params.id as string;

  // <-- CHANGE: Wrapped in useCallback
  const fetchOrganization = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.organizations.get(organizationId);
      const org = response.data;
      
      // Check permissions
      const member = org.members?.find((m: any) => m.user_id === user?.id);
      const role = member?.role;
      
      if (role !== "owner" && role !== "admin") {
        router.push(`/organizations/${organizationId}`);
        return;
      }
      
      setOrganization(org);
      setGeneralForm({
        name: org.name,
        description: org.description || "",
      });
    } catch (error) {
      console.error("Failed to fetch organization:", error);
      router.push("/organizations");
    } finally {
      setLoading(false);
    }
  }, [organizationId, router, user?.id]);

  useEffect(() => {
    if (organizationId) {
      fetchOrganization();
    }
  }, [organizationId, fetchOrganization]); // <-- CHANGE: Added fetchOrganization to dependency array

  const getUserRole = () => {
    if (!organization || !user) return null;
    const member = organization.members?.find((m: any) => m.user_id === user.id);
    return member?.role;
  };

  const isOwner = () => getUserRole() === "owner";

  const handleSaveGeneral = async () => {
    try {
      setSaving(true);
      await api.organizations.update(organizationId, {
        name: generalForm.name.trim(),
        description: generalForm.description.trim() || undefined,
      });
      
      // Update local state
      setOrganization((prev: Organization | null) => prev ? {
        ...prev,
        name: generalForm.name,
        description: generalForm.description,
      } : null);
    } catch (error) {
      console.error("Failed to update organization:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteOrganization = async () => {
    if (deleteConfirmation !== organization?.name) return;

    try {
      setDeleting(true);
      await api.organizations.delete(organizationId);
      router.push("/organizations");
    } catch (error) {
      console.error("Failed to delete organization:", error);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-muted rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            <div className="h-32 bg-muted rounded"></div>
            <div className="h-32 bg-muted rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!organization) {
    return null;
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push(`/organizations/${organizationId}`)}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <Separator orientation="vertical" className="h-6" />
        <div>
          <h1 className="text-2xl font-bold">Organization Settings</h1>
          <p className="text-muted-foreground">{organization.name}</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="billing">Billing & Plans</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
          {isOwner() && <TabsTrigger value="danger">Danger Zone</TabsTrigger>}
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>General Information</CardTitle>
              <CardDescription>
                Update your organization&apos;s basic information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Organization Name</Label>
                <Input
                  id="name"
                  value={generalForm.name}
                  onChange={(e) => setGeneralForm({ ...generalForm, name: e.target.value })}
                  placeholder="Organization name"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={generalForm.description}
                  onChange={(e) => setGeneralForm({ ...generalForm, description: e.target.value })}
                  placeholder="What does your organization do?"
                  rows={4}
                />
              </div>
              
              <Button onClick={handleSaveGeneral} disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Organization ID</CardTitle>
              <CardDescription>
                Unique identifier for API access and integrations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <code className="bg-muted px-4 py-2 rounded flex-1">
                  {organization.id}
                </code>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigator.clipboard.writeText(organization.id)}
                >
                  Copy
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="billing" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Billing & Subscription</CardTitle>
              <CardDescription>
                Manage your organization&apos;s billing and subscription plan
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium">Current Plan</p>
                  <p className="text-sm text-muted-foreground">Professional Plan</p>
                </div>
                <Badge>Active</Badge>
              </div>
              
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium">Billing Period</p>
                  <p className="text-sm text-muted-foreground">Monthly - Next bill on Jan 1, 2025</p>
                </div>
                <p className="font-medium">$99/month</p>
              </div>
              
              <div className="flex gap-2">
                <Button variant="outline">
                  <CreditCard className="h-4 w-4 mr-2" />
                  Update Payment Method
                </Button>
                <Button variant="outline">
                  View Billing History
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Usage & Limits</CardTitle>
              <CardDescription>
                Monitor your organization&apos;s resource usage
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Projects</span>
                  <span>{organization.projects?.length || 0} / 10</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary"
                    style={{ width: `${((organization.projects?.length || 0) / 10) * 100}%` }}
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Team Members</span>
                  <span>{organization.members?.length || 0} / 50</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary"
                    style={{ width: `${((organization.members?.length || 0) / 50) * 100}%` }}
                  />
                </div>
              </div>
              
              <Button variant="outline" className="w-full">
                Upgrade Plan
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="integrations" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Connected Services</CardTitle>
              <CardDescription>
                Manage third-party integrations and API connections
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded bg-blue-100 flex items-center justify-center">
                    <Globe className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium">Google Search Console</p>
                    <p className="text-sm text-muted-foreground">Connected 2 sites</p>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Manage
                </Button>
              </div>
              
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded bg-green-100 flex items-center justify-center">
                    <Database className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium">Google Analytics</p>
                    <p className="text-sm text-muted-foreground">Not connected</p>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Connect
                </Button>
              </div>
              
              <Button className="w-full">
                <Link2 className="h-4 w-4 mr-2" />
                Browse All Integrations
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>API Access</CardTitle>
              <CardDescription>
                Manage API keys for programmatic access
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium">Production API Key</p>
                  <p className="text-sm text-muted-foreground">Last used 2 days ago</p>
                </div>
                <div className="flex items-center gap-2">
                  <code className="text-xs bg-muted px-2 py-1 rounded">...7f8d</code>
                  <Button variant="ghost" size="sm">
                    <Key className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              <Button variant="outline" className="w-full">
                <Key className="h-4 w-4 mr-2" />
                Generate New API Key
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Email Notifications</CardTitle>
              <CardDescription>
                Configure how and when you receive email notifications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="font-medium">Email Alerts</p>
                  <p className="text-sm text-muted-foreground">
                    Receive alerts for critical issues and updates
                  </p>
                </div>
                <Switch
                  checked={notificationSettings.emailAlerts}
                  onCheckedChange={(checked: boolean) => 
                    setNotificationSettings({ ...notificationSettings, emailAlerts: checked })
                  }
                />
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="font-medium">Weekly Reports</p>
                  <p className="text-sm text-muted-foreground">
                    Get a weekly summary of your organization&apos;s activity
                  </p>
                </div>
                <Switch
                  checked={notificationSettings.weeklyReports}
                  onCheckedChange={(checked: boolean) => 
                    setNotificationSettings({ ...notificationSettings, weeklyReports: checked })
                  }
                />
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="font-medium">Member Updates</p>
                  <p className="text-sm text-muted-foreground">
                    Notifications about team member changes
                  </p>
                </div>
                <Switch
                  checked={notificationSettings.memberUpdates}
                  onCheckedChange={(checked: boolean) => 
                    setNotificationSettings({ ...notificationSettings, memberUpdates: checked })
                  }
                />
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="font-medium">Project Alerts</p>
                  <p className="text-sm text-muted-foreground">
                    Updates about project performance and issues
                  </p>
                </div>
                <Switch
                  checked={notificationSettings.projectAlerts}
                  onCheckedChange={(checked: boolean) => 
                    setNotificationSettings({ ...notificationSettings, projectAlerts: checked })
                  }
                />
              </div>
              
              <Button className="w-full">
                Save Notification Preferences
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Webhook Notifications</CardTitle>
              <CardDescription>
                Send real-time updates to your own systems
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full">
                <Webhook className="h-4 w-4 mr-2" />
                Configure Webhooks
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>
                Configure security policies for your organization
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Two-Factor Authentication</p>
                    <p className="text-sm text-muted-foreground">
                      Require 2FA for all organization members
                    </p>
                  </div>
                </div>
                <Switch />
              </div>
              
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">SSO (Single Sign-On)</p>
                    <p className="text-sm text-muted-foreground">
                      Configure SAML or OAuth SSO
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Configure
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Data & Privacy</CardTitle>
              <CardDescription>
                Manage data retention and privacy settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button variant="outline" className="w-full">
                <Database className="h-4 w-4 mr-2" />
                Export Organization Data
              </Button>
              <Button variant="outline" className="w-full">
                View Data Processing Agreement
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {isOwner() && (
          <TabsContent value="danger" className="space-y-6">
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-destructive">Danger Zone</CardTitle>
                <CardDescription>
                  Irreversible actions that affect your entire organization
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 border border-destructive rounded-lg space-y-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
                    <div className="space-y-2 flex-1">
                      <p className="font-medium">Delete Organization</p>
                      <p className="text-sm text-muted-foreground">
                        Once you delete an organization, there is no going back. 
                        All projects, data, and team member access will be permanently removed.
                      </p>
                      <Button
                        variant="destructive"
                        onClick={() => setShowDeleteDialog(true)}
                      >
                        Delete This Organization
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Organization</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently delete the
              organization and all associated data.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>
                Type <strong>{organization.name}</strong> to confirm
              </Label>
              <Input
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                placeholder="Type organization name"
              />
            </div>
            
            <div className="bg-destructive/10 text-destructive p-4 rounded-lg text-sm">
              <p className="font-medium mb-2">This will delete:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>All projects in this organization</li>
                <li>All team member access</li>
                <li>All data and analytics</li>
                <li>All integrations and API keys</li>
              </ul>
            </div>
          </div>
          
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowDeleteDialog(false);
                setDeleteConfirmation("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteOrganization}
              disabled={deleteConfirmation !== organization.name || deleting}
            >
              {deleting ? "Deleting..." : "Delete Organization"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}