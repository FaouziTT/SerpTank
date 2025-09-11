"use client";

import { useState, useEffect, useCallback } from "react"; // <-- CHANGE: Imported useCallback
import { useRouter, useParams } from "next/navigation";
import { 
  ArrowLeft, Mail, UserPlus, Copy, Trash2, Clock, 
  CheckCircle, XCircle, Send, RefreshCw 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api-client";
import { Organization, OrganizationInvitation, OrganizationMember } from "@/types/api";
import { useAuth } from "@/lib/auth-context";

type InvitationRole = "admin" | "member";

export default function OrganizationInvitationsPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [sending, setSending] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  
  const [inviteForm, setInviteForm] = useState({
    email: "",
    role: "member" as InvitationRole,
  });
  const [inviteError, setInviteError] = useState<string | null>(null);

  const organizationId = params.id as string;

  // <-- CHANGE: Wrapped fetchData in useCallback
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [orgResponse, invitationsResponse] = await Promise.all([
        api.organizations.get(organizationId),
        api.organizations.getInvitations(organizationId),
      ]);
      
      // Check permissions
      const org = orgResponse.data;
      const member = org.members?.find((m: OrganizationMember) => m.user_id === user?.id);
      const role = member?.role;
      
      if (role !== "owner" && role !== "admin") {
        router.push(`/organizations/${organizationId}`);
        return;
      }
      
      setOrganization(org);
      setInvitations(invitationsResponse.data);
    } catch (error) {
      console.error("Failed to fetch data:", error);
      router.push("/organizations");
    } finally {
      setLoading(false);
    }
  }, [organizationId, router, user?.id]);

  useEffect(() => {
    if (organizationId) {
      fetchData();
    }
  }, [organizationId, fetchData]); // <-- CHANGE: Added fetchData to dependency array

  const handleSendInvitation = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteError(null);

    if (!inviteForm.email.trim()) {
      setInviteError("Email is required");
      return;
    }

    try {
      setSending(true);
      const response = await api.organizations.createInvitation(organizationId, {
        email: inviteForm.email.trim(),
        role: inviteForm.role,
      });
      
      // Add new invitation to the list
      setInvitations([response.data, ...invitations]);
      
      // Reset form and close dialog
      setInviteForm({ email: "", role: "member" });
      setShowInviteDialog(false);
    } catch (error) {
      console.error("Failed to send invitation:", error);
      setInviteError(
        (error as any)?.response?.data?.detail || 
        "Failed to send invitation. Please try again."
      );
    } finally {
      setSending(false);
    }
  };

  const handleDeleteInvitation = async (invitationId: string) => {
    try {
      setDeleting(invitationId);
      await api.organizations.deleteInvitation(invitationId);
      
      // Remove from local state
      setInvitations(invitations.filter((inv) => inv.id !== invitationId));
    } catch (error) {
      console.error("Failed to delete invitation:", error);
    } finally {
      setDeleting(null);
    }
  };

  const copyInvitationLink = (invitation: OrganizationInvitation) => {
    // In a real app, you would construct the invitation link
    const inviteLink = `${window.location.origin}/organizations/invitations/${invitation.id}/accept`;
    navigator.clipboard.writeText(inviteLink);
    setCopiedId(invitation.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
      case "accepted":
        return <Badge variant="default"><CheckCircle className="h-3 w-3 mr-1" />Accepted</Badge>;
      case "expired":
        return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Expired</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-muted rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3].map((i: number) => (
              <div key={i} className="h-24 bg-muted rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!organization) {
    return null;
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
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
            <h1 className="text-2xl font-bold">Invitations</h1>
            <p className="text-muted-foreground">{organization.name}</p>
          </div>
        </div>
        
        <Button onClick={() => setShowInviteDialog(true)}>
          <Mail className="h-4 w-4 mr-2" />
          Send Invitation
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Pending Invitations</CardTitle>
            <CardDescription>
              {/* CHANGE: Escaped apostrophe */}
              Invitations that haven&apos;t been accepted yet
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {invitations.filter((inv: OrganizationInvitation) => inv.status === "pending").length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Mail className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No pending invitations</p>
                </div>
              ) : (
                invitations
                  .filter((inv: OrganizationInvitation) => inv.status === "pending")
                  .map((invitation: OrganizationInvitation) => (
                    <div
                      key={invitation.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="space-y-1">
                        <p className="font-medium">{invitation.email}</p>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Badge variant="outline">{invitation.role}</Badge>
                          <span>•</span>
                          <span>Expires {formatDate(invitation.expires_at)}</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => copyInvitationLink(invitation)}
                        >
                          {copiedId === invitation.id ? (
                            <>
                              <CheckCircle className="h-4 w-4 mr-1" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="h-4 w-4 mr-1" />
                              Copy Link
                            </>
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteInvitation(invitation.id)}
                          disabled={deleting === invitation.id}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Invitation History</CardTitle>
            <CardDescription>
              All sent invitations and their status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {invitations.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Send className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No invitations sent yet</p>
                </div>
              ) : (
                invitations.map((invitation: OrganizationInvitation) => (
                  <div
                    key={invitation.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="space-y-1">
                      <p className="font-medium">{invitation.email}</p>
                      <div className="flex items-center gap-2 text-sm">
                        {getStatusBadge(invitation.status || 'pending')}
                        <span className="text-muted-foreground">
                          Sent {formatDate(invitation.created_at)}
                        </span>
                      </div>
                    </div>
                    
                    <Badge variant="outline">{invitation.role}</Badge>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Invitation Guidelines</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>Invitations expire after 7 days if not accepted</li>
            {/* CHANGE: Escaped apostrophe */}
            <li>Users need to create an account if they don&apos;t have one</li>
            <li>Invited members will have access to all organization projects</li>
            <li>You can resend invitations by creating a new one</li>
          </ul>
        </CardContent>
      </Card>

      {/* Send Invitation Dialog */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent>
          <form onSubmit={handleSendInvitation}>
            <DialogHeader>
              <DialogTitle>Send Invitation</DialogTitle>
              <DialogDescription>
                Invite a new member to join {organization.name}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="colleague@example.com"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                  disabled={sending}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select
                  value={inviteForm.role}
                  onValueChange={(value) => setInviteForm({ ...inviteForm, role: value as InvitationRole })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="member">Member</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground">
                  {inviteForm.role === "admin" 
                    ? "Admins can manage projects and invite members"
                    : "Members can view and contribute to projects"}
                </p>
              </div>
              
              {inviteError && (
                <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
                  {inviteError}
                </div>
              )}
            </div>
            
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowInviteDialog(false)}
                disabled={sending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={sending}>
                {sending ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Send Invitation
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}