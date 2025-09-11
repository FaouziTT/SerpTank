'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Users, Mail, Shield, Clock, Calendar, Sparkles, MoreVertical, Crown, Star } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { ListLayout } from '@/components/layout/list-layout';
import { EntityModal, useEntityModal } from '@/components/ui/entity-modal';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { ConfirmActionModal } from '@/components/ui/confirm-action-modal';
import { api } from '@/lib/api-client';
import { OrganizationMember, OrganizationInvitation } from '@/types/api';
import { useAuth } from '@/lib/auth-context';
import { useProject } from '@/lib/project-context';
import { useToast } from '@/components/ui/use-toast';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { motion, useScroll, useTransform } from 'framer-motion';
import { SEOOrb } from '@/components/ui/seo-orb';

interface TeamMemberData {
  email: string;
  role: string;
}

const ROLE_LABELS = {
  owner: 'Owner',
  admin: 'Admin', 
  member: 'Member',
  viewer: 'Viewer'
};

const ROLE_DESCRIPTIONS = {
  owner: 'Full access to all features and billing',
  admin: 'Manage team members and organization settings',
  member: 'Access to most features and projects',
  viewer: 'Read-only access to reports and dashboards'
};

const ROLE_COLORS = {
  owner: 'bg-purple-100 text-purple-800 border-purple-200',
  admin: 'bg-blue-100 text-blue-800 border-blue-200',
  member: 'bg-green-100 text-green-800 border-green-200',
  viewer: 'bg-gray-100 text-gray-800 border-gray-200'
};

export default function TeamPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { currentOrganization: organization } = useProject();
  const { toast } = useToast();
  const inviteModal = useEntityModal<TeamMemberData>();
  
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState({
    search: '',
    role: '',
  });
  const [formData, setFormData] = useState<TeamMemberData>({
    email: '',
    role: 'member',
  });

  // Remove member modal state
  const [removeModalOpen, setRemoveModalOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<OrganizationMember | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Parallax and scroll effects
  const { scrollY } = useScroll();
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    if (organization) {
      fetchTeamData();
    }
  }, [organization]);

  const fetchTeamData = async () => {
    if (!organization?.id) {
      console.warn('No organization ID available for team data fetch');
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      console.log('Fetching team data for organization:', organization.id);
      
      const [membersResponse, invitationsResponse] = await Promise.all([
        api.organizations.getMembers(organization.id),
        api.organizations.getInvitations(organization.id)
      ]);
      
      setMembers(membersResponse.data || []);
      setInvitations(invitationsResponse.data || []);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch team data'));
      console.error('Failed to fetch team data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInviteMember = async (data: TeamMemberData) => {
    if (!organization?.id) return;
    
    try {
      await api.organizations.createInvitation(organization.id, data);
      toast({
        title: 'Invitation sent',
        description: `Invitation sent to ${data.email} successfully.`,
      });
      await fetchTeamData();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to send invitation. Please try again.',
        variant: 'destructive',
      });
      throw err;
    }
  };

  const handleUpdateRole = async (memberId: string, newRole: string) => {
    if (!organization?.id) return;
    
    try {
      await api.organizations.updateMemberRole(organization.id, memberId, { role: newRole });
      toast({
        title: 'Role updated',
        description: 'Member role updated successfully.',
      });
      await fetchTeamData();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to update role. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleRemoveMember = async () => {
    if (!organization?.id || !selectedMember) return;
    
    try {
      setSubmitting(true);
      await api.organizations.removeMember(organization.id, selectedMember.user_id);
      toast({
        title: 'Member removed',
        description: 'Team member removed successfully.',
      });
      setRemoveModalOpen(false);
      await fetchTeamData();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to remove member. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevokeInvitation = async (invitationId: string) => {
    try {
      await api.organizations.deleteInvitation(invitationId);
      toast({
        title: 'Invitation revoked',
        description: 'Invitation revoked successfully.',
      });
      await fetchTeamData();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to revoke invitation. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const getInitials = (name: string) => {
    return name.split(' ').map(part => part[0]).join('').toUpperCase().slice(0, 2);
  };

  const getCurrentUserRole = () => {
    return members.find(member => member.user_id === user?.id)?.role || 'viewer';
  };

  const canManageMembers = () => {
    const role = getCurrentUserRole();
    return role === 'owner' || role === 'admin';
  };

  const filteredMembers = members.filter((member: OrganizationMember) => {
    const matchesSearch = !filters.search || 
      member.user?.full_name?.toLowerCase().includes(filters.search.toLowerCase()) ||
      member.user?.email?.toLowerCase().includes(filters.search.toLowerCase());
    
    const matchesRole = !filters.role || member.role === filters.role;
    
    return matchesSearch && matchesRole;
  });

  const roleOptions = [
    { id: 'all', label: 'All Roles', value: '' },
    { id: 'owner', label: 'Owner', value: 'owner' },
    { id: 'admin', label: 'Admin', value: 'admin' },
    { id: 'member', label: 'Member', value: 'member' },
    { id: 'viewer', label: 'Viewer', value: 'viewer' },
  ];

  const sortOptions = [
    { id: 'name', label: 'Name (A-Z)', value: 'name-asc' },
    { id: 'role', label: 'Role', value: 'role' },
    { id: 'joined', label: 'Recently Joined', value: 'joined-desc' },
  ];

  if (!organization) {
    return (
      <div className="min-h-screen bg-background text-foreground relative noise-overlay">
        <DashboardLayout>
          <div className="container mx-auto p-6">
            <Card>
              <CardContent className="text-center py-8">
                <h3 className="text-lg font-semibold mb-2">No Organization Selected</h3>
                <p className="text-muted-foreground mb-4">
                  Please select an organization to manage team members
                </p>
                <Button onClick={() => router.push("/organizations")}>
                  Go to Organizations
                </Button>
              </CardContent>
            </Card>
          </div>
        </DashboardLayout>
      </div>
    );
  }

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
          {/* Enhanced Header */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="flex items-center justify-between"
          >
            <div>
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.1 }}
              >
                <Badge variant="secondary" className="mb-4 animate-slide-up-fade">
                  <Sparkles className="mr-1 h-3 w-3" />
                  Team Management
                </Badge>
              </motion.div>
              
              <motion.h1 
                className="text-5xl sm:text-6xl font-bold tracking-tighter mb-4 leading-[0.9]"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <span className="block">Team</span>
                <span className="block text-gradient-electric">Collaboration</span>
              </motion.h1>
              
              <motion.p 
                className="text-lg sm:text-xl text-muted-foreground leading-relaxed max-w-2xl"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3 }}
              >
                Manage team members, roles, and permissions across your organization
              </motion.p>
            </div>
          </motion.div>

          <ListLayout
            title="Team"
            searchPlaceholder="Search team members..."
            onSearch={(query) => setFilters(prev => ({ ...prev, search: query }))}
            filters={[
              {
                id: 'role',
                label: 'Role',
                type: 'select',
                options: roleOptions,
                placeholder: 'Filter by role',
              },
            ]}
            onFilterChange={(filterId, value) => {
              if (filterId === 'role') {
                setFilters(prev => ({ ...prev, role: value as string }));
              }
            }}
            sortOptions={sortOptions}
            actions={canManageMembers() ? [
              {
                label: 'Invite Member',
                icon: Plus,
                onClick: () => {
                  setFormData({ email: '', role: 'member' });
                  inviteModal.openModal('create');
                },
              } as any,
            ] : []}
            loading={loading}
            error={error}
            onRetry={fetchTeamData}
            totalCount={filteredMembers.length + invitations.length}
            emptyState={{
              icon: Users,
              title: 'No team members found',
              message: filters.search
                ? 'No team members match your search criteria'
                : 'Start building your team by inviting members',
              action: canManageMembers() && !filters.search ? {
                label: 'Invite First Member',
                onClick: () => {
                  setFormData({ email: '', role: 'member' });
                  inviteModal.openModal('create');
                },
              } : undefined,
            }}
          >
            <div className="space-y-6">
              {/* Active Members */}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredMembers.map((member: OrganizationMember, index: number) => (
                  <Card
                    key={member.id}
                    className="hover:shadow-lg transition-all group"
                  >
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div className="flex items-center gap-3 flex-1">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
                            {getInitials(member.user?.full_name || member.user?.email || 'U')}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <CardTitle className="text-base truncate">
                                {member.user?.full_name || member.user?.email}
                              </CardTitle>
                              {member.role === 'owner' && (
                                <Crown className="h-4 w-4 text-yellow-500" />
                              )}
                              {member.user_id === user?.id && (
                                <Badge variant="outline" className="text-xs">You</Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground truncate">
                              {member.user?.email}
                            </p>
                          </div>
                        </div>
                        
                        {canManageMembers() && member.role !== 'owner' && member.user_id !== user?.id && (
                          <div onClick={(e) => e.stopPropagation()}>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                {Object.entries(ROLE_LABELS).map(([roleKey, roleLabel]) => (
                                  roleKey !== 'owner' && roleKey !== member.role && (
                                    <DropdownMenuItem 
                                      key={roleKey}
                                      onClick={() => handleUpdateRole(member.user_id, roleKey)}
                                    >
                                      Change to {roleLabel}
                                    </DropdownMenuItem>
                                  )
                                ))}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem 
                                  className="text-destructive"
                                  onClick={() => {
                                    setSelectedMember(member);
                                    setRemoveModalOpen(true);
                                  }}
                                >
                                  Remove from team
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">Role</span>
                          <Badge 
                            variant="outline" 
                            className={cn("text-xs", ROLE_COLORS[member.role as keyof typeof ROLE_COLORS])}
                          >
                            {ROLE_LABELS[member.role as keyof typeof ROLE_LABELS]}
                          </Badge>
                        </div>
                        
                        <div className="text-xs text-muted-foreground">
                          <p>{ROLE_DESCRIPTIONS[member.role as keyof typeof ROLE_DESCRIPTIONS]}</p>
                        </div>
                        
                        {member.joined_at && (
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Calendar className="h-3 w-3" />
                            <span>Joined {formatDistanceToNow(new Date(member.joined_at), { addSuffix: true })}</span>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Pending Invitations */}
              {invitations.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-4">Pending Invitations</h3>
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {invitations.map((invitation: OrganizationInvitation) => (
                      <Card key={invitation.id} className="border-dashed opacity-75">
                        <CardHeader>
                          <div className="flex justify-between items-start">
                            <div className="flex items-center gap-3 flex-1">
                              <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                                <Mail className="h-5 w-5 text-muted-foreground" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <CardTitle className="text-base truncate">
                                  {invitation.email}
                                </CardTitle>
                                <p className="text-sm text-muted-foreground">
                                  Invitation pending
                                </p>
                              </div>
                            </div>
                            
                            {canManageMembers() && (
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => handleRevokeInvitation(invitation.id)}
                              >
                                Revoke
                              </Button>
                            )}
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-sm text-muted-foreground">Role</span>
                              <Badge variant="secondary">
                                {ROLE_LABELS[invitation.role as keyof typeof ROLE_LABELS]}
                              </Badge>
                            </div>
                            
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              <span>Sent {formatDistanceToNow(new Date(invitation.created_at), { addSuffix: true })}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </ListLayout>
        </div>
      </DashboardLayout>

      {/* Invite Member Modal */}
      <EntityModal
        {...inviteModal}
        onOpenChange={inviteModal.setOpen}
        entity="team member"
        title="Invite Team Member"
        description="Send an invitation to join your organization team."
        onSubmit={() => handleInviteMember(formData)}
        submitLabel="Send Invitation"
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              placeholder="member@example.com"
              value={formData.email}
              onChange={(e) => setFormData(prev => ({ 
                ...prev, 
                email: e.target.value 
              }))}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select
              value={formData.role}
              onValueChange={(value) => setFormData(prev => ({ 
                ...prev, 
                role: value 
              }))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin - Manage team and settings</SelectItem>
                <SelectItem value="member">Member - Access to most features</SelectItem>
                <SelectItem value="viewer">Viewer - Read-only access</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {ROLE_DESCRIPTIONS[formData.role as keyof typeof ROLE_DESCRIPTIONS]}
            </p>
          </div>
        </div>
      </EntityModal>

      {/* Remove Member Confirmation Modal */}
      <ConfirmActionModal
        open={removeModalOpen}
        onOpenChange={setRemoveModalOpen}
        onConfirm={handleRemoveMember}
        type="danger"
        title="Remove Team Member"
        message={`Are you sure you want to remove ${selectedMember?.user?.full_name || selectedMember?.user?.email} from the team? They will lose access to all organization resources.`}
        confirmLabel="Remove Member"
        loading={submitting}
      />
    </div>
  );
}