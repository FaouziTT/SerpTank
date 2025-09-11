"use client";

import { useState, useEffect, useCallback } from "react"; // <-- CHANGE: Imported useCallback
import { useRouter, useParams } from "next/navigation";
import { 
  ArrowLeft, Users, UserPlus, MoreVertical, Shield, 
  ChevronDown, Search, Mail 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { Organization, OrganizationMember } from "@/types/api";
import { useAuth } from "@/lib/auth-context";

type MemberRole = "owner" | "admin" | "member";

export default function OrganizationMembersPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedMember, setSelectedMember] = useState<OrganizationMember | null>(null);
  const [showRoleDialog, setShowRoleDialog] = useState(false);
  const [showRemoveDialog, setShowRemoveDialog] = useState(false);
  const [newRole, setNewRole] = useState<MemberRole>("member");
  const [updating, setUpdating] = useState(false);

  const organizationId = params.id as string;

  // <-- CHANGE: Wrapped function in useCallback and moved it above useEffect
  const fetchOrganizationData = useCallback(async () => {
    try {
      setLoading(true);
      const [orgResponse, membersResponse] = await Promise.all([
        api.organizations.get(organizationId),
        api.organizations.getMembers(organizationId),
      ]);
      
      setOrganization(orgResponse.data);
      setMembers(membersResponse.data);
    } catch (error) {
      console.error("Failed to fetch organization data:", error);
      router.push("/organizations");
    } finally {
      setLoading(false);
    }
  }, [organizationId, router]);

  useEffect(() => {
    if (organizationId) {
      fetchOrganizationData();
    }
  }, [organizationId, fetchOrganizationData]); // <-- CHANGE: Added fetchOrganizationData to dependency array

  const getUserRole = () => {
    if (!organization || !user) return null;
    const member = organization.members?.find(m => m.user_id === user.id);
    return member?.role;
  };

  const canManageMembers = () => {
    const role = getUserRole();
    return role === "owner" || role === "admin";
  };

  const canUpdateRole = (member: OrganizationMember) => {
    const userRole = getUserRole();
    // Owners can update anyone except themselves
    // Admins can update members but not owners or other admins
    if (userRole === "owner") {
      return member.user_id !== user?.id;
    }
    if (userRole === "admin") {
      return member.role === "member";
    }
    return false;
  };

  const canRemoveMember = (member: OrganizationMember) => {
    const userRole = getUserRole();
    // Can't remove yourself or the owner
    if (member.user_id === user?.id || member.role === "owner") {
      return false;
    }
    // Owners can remove anyone
    if (userRole === "owner") {
      return true;
    }
    // Admins can only remove members
    if (userRole === "admin") {
      return member.role === "member";
    }
    return false;
  };

  const handleUpdateRole = async () => {
    if (!selectedMember) return;

    try {
      setUpdating(true);
      await api.organizations.updateMemberRole(
        organizationId,
        selectedMember.user_id,
        { role: newRole }
      );
      
      // Update local state
      setMembers(members.map(m => 
        m.id === selectedMember.id ? { ...m, role: newRole } : m
      ));
      
      setShowRoleDialog(false);
      setSelectedMember(null);
    } catch (error) {
      console.error("Failed to update member role:", error);
    } finally {
      setUpdating(false);
    }
  };

  const handleRemoveMember = async () => {
    if (!selectedMember) return;

    try {
      setUpdating(true);
      await api.organizations.removeMember(
        organizationId,
        selectedMember.user_id
      );
      
      // Update local state
      setMembers(members.filter(m => m.id !== selectedMember.id));
      
      setShowRemoveDialog(false);
      setSelectedMember(null);
    } catch (error) {
      console.error("Failed to remove member:", error);
    } finally {
      setUpdating(false);
    }
  };

  const filteredMembers = members.filter(member =>
    member.user?.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    member.user?.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case "owner":
        return "default";
      case "admin":
        return "secondary";
      default:
        return "outline";
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-muted rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-muted rounded"></div>
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
            <h1 className="text-2xl font-bold">Organization Members</h1>
            <p className="text-muted-foreground">{organization.name}</p>
          </div>
        </div>
        
        {canManageMembers() && (
          <Button
            onClick={() => router.push(`/organizations/${organizationId}/invitations`)}
          >
            <UserPlus className="h-4 w-4 mr-2" />
            Invite Members
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Members ({members.length})</CardTitle>
          <CardDescription>
            Manage who has access to this organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search members by name or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          <div className="space-y-4">
            {filteredMembers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No members found matching your search
              </div>
            ) : (
              filteredMembers.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                      <Users className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">
                        {member.user?.full_name || member.user?.email}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {member.user?.email}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Badge variant={getRoleBadgeVariant(member.role)}>
                      {member.role === "owner" && <Shield className="h-3 w-3 mr-1" />}
                      {member.role}
                    </Badge>
                    
                    {canManageMembers() && (canUpdateRole(member) || canRemoveMember(member)) && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          {canUpdateRole(member) && (
                            <DropdownMenuItem
                              onClick={() => {
                                setSelectedMember(member);
                                setNewRole(member.role as MemberRole);
                                setShowRoleDialog(true);
                              }}
                            >
                              Change Role
                            </DropdownMenuItem>
                          )}
                          {canRemoveMember(member) && (
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => {
                                setSelectedMember(member);
                                setShowRemoveDialog(true);
                              }}
                            >
                              Remove from Organization
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Change Role Dialog */}
      <Dialog open={showRoleDialog} onOpenChange={setShowRoleDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Member Role</DialogTitle>
            <DialogDescription>
              Update the role for {selectedMember?.user?.full_name || selectedMember?.user?.email}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>New Role</Label>
              <Select value={newRole} onValueChange={(value) => setNewRole(value as MemberRole)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="member">Member</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  {getUserRole() === "owner" && (
                    <SelectItem value="owner">Owner</SelectItem>
                  )}
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground">
                {newRole === "owner" && "Owners have full control over the organization"}
                {newRole === "admin" && "Admins can manage projects and invite members"}
                {newRole === "member" && "Members can view and contribute to projects"}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRoleDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateRole} disabled={updating}>
              {updating ? "Updating..." : "Update Role"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove Member Dialog */}
      <Dialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Member</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove {selectedMember?.user?.full_name || selectedMember?.user?.email} from this organization?
            </DialogDescription>
          </DialogHeader>
          <p className="text-sm text-muted-foreground py-4">
            This action cannot be undone. The member will lose access to all projects in this organization.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRemoveDialog(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleRemoveMember} 
              disabled={updating}
            >
              {updating ? "Removing..." : "Remove Member"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}