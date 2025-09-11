'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { 
  Building2, Users, FolderOpen, Mail, Shield, Settings,
  Activity, Calendar, UserPlus, Trash2, Edit, Link2,
  Clock, CheckCircle, XCircle, AlertCircle
} from 'lucide-react';
import { DetailLayout } from '@/components/layout/detail-layout';
import { EntityModal, useEntityModal } from '@/components/ui/entity-modal';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { api } from '@/lib/api-client';
import { Organization, Project, OrganizationMember, OrganizationInvitation, AuditLog } from '@/types/api';
import { useAuth } from '@/lib/auth-context';
import { useToast } from '@/components/ui/use-toast';
import { formatDistanceToNow, format } from 'date-fns';
import { ErrorBoundary } from '@/components/error-boundary';
import { LoadingBoundary } from '@/components/loading-boundary';
import { ConfirmActionModal } from '@/components/ui/confirm-action-modal';

// Tab Components
import { OrganizationOverview } from './tabs/overview';
import { OrganizationMembers } from './tabs/members';
import { OrganizationInvitations } from './tabs/invitations';
import { OrganizationAuditLogs } from './tabs/audit-logs';
import { OrganizationSettings } from './tabs/settings';

interface EditOrganizationData {
  name: string;
  description: string;
}

export default function OrganizationDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const { toast } = useToast();
  const editModal = useEntityModal<EditOrganizationData>();
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [confirmModalData, setConfirmModalData] = useState<{ title: string; message: string; onConfirm: () => void } | null>(null);
  
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [editFormData, setEditFormData] = useState<EditOrganizationData>({
    name: '',
    description: '',
  });
  
  const organizationId = params.id as string;

  const fetchOrganization = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.organizations.get(organizationId);
      setOrganization(response.data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch organization'));
      console.error('Failed to fetch organization:', err);
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    if (organizationId) {
      fetchOrganization();
    }
  }, [organizationId, fetchOrganization]);

  const getUserRole = () => {
    if (!organization || !user) return null;
    const member = organization.members?.find(m => m.user_id === user.id);
    return member?.role || null;
  };

  const canEdit = () => {
    const role = getUserRole();
    return role !== null && (role === 'owner' || role === 'admin');
  };

  const canDelete = () => {
    const role = getUserRole();
    return role !== null && role === 'owner';
  };

  const handleEdit = () => {
    if (!organization) return;
    setEditFormData({
      name: organization.name,
      description: organization.description || '',
    });
    editModal.openModal('edit');
  };

  const handleUpdate = async (data: EditOrganizationData) => {
    if (!organization) return;
    
    try {
      const response = await api.organizations.update(organizationId, data);
      setOrganization(response.data);
      toast({
        title: 'Organization updated',
        description: 'Your changes have been saved successfully.',
      });
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to update organization. Please try again.',
        variant: 'destructive',
      });
      throw err;
    }
  };

  const handleDelete = async () => {
    if (!organization) return;

    setConfirmModalData({
      title: 'Delete Organization',
      message: `Are you sure you want to delete "${organization.name}"? This will permanently delete all associated projects, data, and remove all members. This action cannot be undone.`,
      onConfirm: async () => {
      try {
        await api.organizations.delete(organizationId);
        toast({
          title: 'Organization deleted',
          description: 'The organization has been permanently deleted.',
        });
        router.push('/organizations');
      } catch (err) {
        toast({
          title: 'Error',
          description: 'Failed to delete organization. Please try again.',
          variant: 'destructive',
        });
      } finally {
        setConfirmModalOpen(false);
      }
    }});
    setConfirmModalOpen(true);
  };

  if (!organization) {
    return null;
  }

  const actions = [];
  if (canEdit()) {
    actions.push({
      label: 'Edit',
      icon: Edit,
      onClick: handleEdit,
    });
  }
  if (canDelete()) {
    actions.push({
      label: 'Delete',
      icon: Trash2,
      onClick: handleDelete,
      variant: 'destructive' as const,
    });
  }

  const tabs = [
    {
      id: 'overview',
      label: 'Overview',
      icon: Building2,
      content: (
        // CHANGE: Removed level="section" prop
        <ErrorBoundary>
          <LoadingBoundary>
            <OrganizationOverview organization={organization} />
          </LoadingBoundary>
        </ErrorBoundary>
      ),
    },
    {
      id: 'members',
      label: 'Members',
      icon: Users,
      badge: organization.members?.length || 0,
      content: (
        // CHANGE: Removed level="section" prop
        <ErrorBoundary>
          <LoadingBoundary>
            <OrganizationMembers 
              organizationId={organizationId}
              currentUserRole={getUserRole()}
              onUpdate={fetchOrganization}
            />
          </LoadingBoundary>
        </ErrorBoundary>
      ),
    },
    {
      id: 'invitations',
      label: 'Invitations',
      icon: Mail,
      content: (
        // CHANGE: Removed level="section" prop
        <ErrorBoundary>
          <LoadingBoundary>
            <OrganizationInvitations 
              organizationId={organizationId}
              currentUserRole={getUserRole()}
              onUpdate={fetchOrganization}
            />
          </LoadingBoundary>
        </ErrorBoundary>
      ),
      disabled: !canEdit(),
    },
    {
      id: 'audit-logs',
      label: 'Audit Logs',
      icon: Activity,
      content: (
        // CHANGE: Removed level="section" prop
        <ErrorBoundary>
          <LoadingBoundary>
            <OrganizationAuditLogs 
              organizationId={organizationId}
              currentUserRole={getUserRole()}
            />
          </LoadingBoundary>
        </ErrorBoundary>
      ),
      disabled: !canEdit(),
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings,
      content: (
        // CHANGE: Removed level="section" prop
        <ErrorBoundary>
          <LoadingBoundary>
            <OrganizationSettings 
              organization={organization}
              currentUserRole={getUserRole()}
              onUpdate={setOrganization}
            />
          </LoadingBoundary>
        </ErrorBoundary>
      ),
      disabled: !canEdit(),
    },
  ];

  return (
    <>
      <DetailLayout
        title={organization.name}
        subtitle={organization.description}
        status={
          organization.is_active 
            ? { label: 'Active', variant: 'default' }
            : { label: 'Inactive', variant: 'secondary' }
        }
        breadcrumbs={[
          { label: 'Organizations', href: '/organizations' },
          { label: organization.name },
        ]}
        actions={actions}
        tabs={tabs}
        loading={loading}
        error={error}
        onRetry={fetchOrganization}
        metadata={[
          {
            label: 'Created',
            value: organization.created_at 
              ? formatDistanceToNow(new Date(organization.created_at), { addSuffix: true })
              : 'Unknown',
            icon: Calendar,
          },
          {
            label: 'Your Role',
            value: getUserRole() || 'Member',
            icon: Shield,
          },
        ]}
      />

      <EntityModal
        {...editModal}
        onOpenChange={editModal.setOpen}
        entity="organization"
        title="Edit Organization"
        description="Update your organization's details."
        onSubmit={() => handleUpdate(editFormData)}
        submitLabel="Save Changes"
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-name">Organization Name</Label>
            <Input
              id="edit-name"
              value={editFormData.name}
              onChange={(e) => setEditFormData(prev => ({ 
                ...prev, 
                name: e.target.value 
              }))}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-description">Description</Label>
            <Textarea
              id="edit-description"
              rows={4}
              value={editFormData.description}
              onChange={(e) => setEditFormData(prev => ({ 
                ...prev, 
                description: e.target.value 
              }))}
            />
          </div>
        </div>
      </EntityModal>

      {confirmModalData && (
        <ConfirmActionModal
          open={confirmModalOpen}
          onOpenChange={setConfirmModalOpen}
          title={confirmModalData.title}
          message={confirmModalData.message}
          onConfirm={confirmModalData.onConfirm}
          type="danger"
          confirmLabel="Delete Organization"
        />
      )}
    </>
  );
}