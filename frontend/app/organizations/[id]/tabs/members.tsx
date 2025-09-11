'use client';

import { useState, useEffect, useCallback } from 'react'; // <-- CHANGE: Imported useCallback
import { Users, UserPlus, MoreVertical, Shield, Mail } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { EntityModal, useEntityModal } from '@/components/ui/entity-modal';
import { ConfirmActionModal } from '@/components/ui/confirm-action-modal';
import { api } from '@/lib/api-client';
import { OrganizationMember } from '@/types/api';
import { useToast } from '@/components/ui/use-toast';

interface OrganizationMembersProps {
  organizationId: string;
  currentUserRole: string | null;
  onUpdate: () => void;
}

export function OrganizationMembers({ organizationId, currentUserRole, onUpdate }: OrganizationMembersProps) {
  const { toast } = useToast();
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [memberToRemove, setMemberToRemove] = useState<OrganizationMember | null>(null);
  const inviteModal = useEntityModal<{ email: string; role: string }>();
  
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [inviteFormData, setInviteFormData] = useState({ email: '', role: 'member' });

  // <-- CHANGE: Wrapped in useCallback
  const fetchMembers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.organizations.getMembers(organizationId);
      setMembers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch members:', error);
    } finally {
      setLoading(false);
    }
  }, [organizationId]);
  
  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]); // <-- CHANGE: Updated dependency array

  const canManageMembers = currentUserRole === 'owner' || currentUserRole === 'admin';

  const handleInvite = async (data: { email: string; role: string }) => {
    try {
      await api.organizations.createInvitation(organizationId, {
        email: data.email,
        role: data.role as 'admin' | 'member',
      });
      toast({
        title: 'Invitation sent',
        description: `An invitation has been sent to ${data.email}`,
      });
      onUpdate();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to send invitation. Please try again.',
        variant: 'destructive',
      });
      throw error;
    }
  };

  const handleRemoveMember = (member: OrganizationMember) => {
    setMemberToRemove(member);
    setConfirmModalOpen(true);
  };

  const confirmRemoveMember = async () => {
    if (!memberToRemove) return;
    try {
      await api.organizations.removeMember(organizationId, memberToRemove.user_id);
      toast({
        title: 'Member removed',
        description: 'The member has been removed from the organization.',
      });
      fetchMembers();
      onUpdate();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to remove member. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setConfirmModalOpen(false);
      setMemberToRemove(null);
    }
  };

  const filteredMembers = members.filter(member =>
    member.user?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    member.user?.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex-1 max-w-sm">
            <Input
              placeholder="Search members..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          {canManageMembers && (
            <Button onClick={() => inviteModal.openModal('create', { email: '', role: 'member' })}>
              <UserPlus className="h-4 w-4 mr-2" />
              Invite Member
            </Button>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Organization Members</CardTitle>
            <CardDescription>
              Manage members and their roles within the organization
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : filteredMembers.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground">
                {searchTerm ? 'No members match your search' : 'No members found'}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredMembers.map(member => (
                  <div key={member.user_id} className="flex items-center justify-between p-3 rounded-lg border">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                        <Users className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div>
                        <div className="font-medium">{member.user?.name || 'Unnamed User'}</div>
                        <div className="text-sm text-muted-foreground">{member.user?.email || 'No email'}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={member.role === 'owner' ? 'default' : 'secondary'}>
                        <Shield className="h-3 w-3 mr-1" />
                        {member.role}
                      </Badge>
                      {canManageMembers && member.role !== 'owner' && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem 
                              onClick={() => handleRemoveMember(member)}
                              className="text-destructive"
                            >
                              Remove Member
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <EntityModal
        {...inviteModal}
        onOpenChange={inviteModal.setOpen}
        entity="invitation"
        action="create"
        title="Invite Member"
        description="Send an invitation to join this organization"
        onSubmit={() => handleInvite(inviteFormData)}
        submitLabel="Send Invitation"
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="invite-email">Email Address</Label>
            <Input
              id="invite-email"
              type="email"
              placeholder="colleague@example.com"
              value={inviteFormData.email}
              onChange={(e) => setInviteFormData(prev => ({ 
                ...prev, 
                email: e.target.value 
              }))}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="invite-role">Role</Label>
            <Select
              value={inviteFormData.role}
              onValueChange={(value) => setInviteFormData(prev => ({ 
                ...prev, 
                role: value 
              }))}
            >
              <SelectTrigger id="invite-role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="member">Member</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </EntityModal>

      <ConfirmActionModal
        open={confirmModalOpen}
        onOpenChange={setConfirmModalOpen}
        title="Remove Member"
        message={`Are you sure you want to remove ${memberToRemove?.user?.name || memberToRemove?.user?.email} from the organization?`}
        onConfirm={confirmRemoveMember}
        type="warning"
        confirmLabel="Remove"
      />
    </>
  );
}