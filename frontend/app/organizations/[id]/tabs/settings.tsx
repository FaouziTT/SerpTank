'use client';

import { useState } from 'react';
import { Settings, Shield, Bell, Link2, Trash2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { SettingsFormSection } from '@/components/layout/settings-layout';
import { api } from '@/lib/api-client';
import { Organization } from '@/types/api';
import { useToast } from '@/components/ui/use-toast';
import { ConfirmActionModal } from '@/components/ui/confirm-action-modal';
import { useRouter } from 'next/navigation';

interface OrganizationSettingsProps {
  organization: Organization;
  currentUserRole: string | null;
  onUpdate: (org: Organization) => void;
}

export function OrganizationSettings({ organization, currentUserRole, onUpdate }: OrganizationSettingsProps) {
  const { toast } = useToast();
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const router = useRouter();
  
  const [settings, setSettings] = useState({
    allowMemberInvites: false,
    requireApproval: true,
    notifyOnNewMember: true,
    notifyOnProjectCreation: true,
  });

  const canManageSettings = currentUserRole === 'owner';

  const handleSaveSettings = async () => {
    try {
      // In a real implementation, this would save to the backend
      toast({
        title: 'Settings saved',
        description: 'Organization settings have been updated successfully.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save settings. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteOrganization = () => {
    setConfirmModalOpen(true);
  };

  const confirmDeleteOrganization = async () => {
    try {
      await api.organizations.delete(organization.id);
      toast({
        title: 'Organization deleted',
        description: 'The organization has been permanently deleted.',
      });
      router.push('/organizations');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete organization. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setConfirmModalOpen(false);
    }
  };

  return (
    <div className="space-y-6">
      <SettingsFormSection
        title="General Settings"
        description="Configure general organization preferences"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="member-invites">Allow Member Invites</Label>
              <p className="text-sm text-muted-foreground">
                Allow organization members to invite new members
              </p>
            </div>
            <Switch
              id="member-invites"
              checked={settings.allowMemberInvites}
              onCheckedChange={(checked) => 
                setSettings(prev => ({ ...prev, allowMemberInvites: checked }))
              }
              disabled={!canManageSettings}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="require-approval">Require Approval</Label>
              <p className="text-sm text-muted-foreground">
                New members must be approved by an admin
              </p>
            </div>
            <Switch
              id="require-approval"
              checked={settings.requireApproval}
              onCheckedChange={(checked) => 
                setSettings(prev => ({ ...prev, requireApproval: checked }))
              }
              disabled={!canManageSettings}
            />
          </div>
        </div>
      </SettingsFormSection>

      <SettingsFormSection
        title="Notifications"
        description="Configure notification preferences for the organization"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="notify-member">New Member Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Notify admins when new members join
              </p>
            </div>
            <Switch
              id="notify-member"
              checked={settings.notifyOnNewMember}
              onCheckedChange={(checked) => 
                setSettings(prev => ({ ...prev, notifyOnNewMember: checked }))
              }
              disabled={!canManageSettings}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="notify-project">Project Creation Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Notify admins when new projects are created
              </p>
            </div>
            <Switch
              id="notify-project"
              checked={settings.notifyOnProjectCreation}
              onCheckedChange={(checked) => 
                setSettings(prev => ({ ...prev, notifyOnProjectCreation: checked }))
              }
              disabled={!canManageSettings}
            />
          </div>
        </div>
      </SettingsFormSection>

      {canManageSettings && (
        <>
          <div className="flex justify-end">
            <Button onClick={handleSaveSettings}>
              Save Settings
            </Button>
          </div>

          <Separator />

          <SettingsFormSection
            title="Danger Zone"
            description="Irreversible and destructive actions"
          >
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-destructive">Delete Organization</CardTitle>
                <CardDescription>
                  Permanently delete this organization and all associated data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="destructive"
                  onClick={handleDeleteOrganization}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Organization
                </Button>
              </CardContent>
            </Card>
          </SettingsFormSection>
        </>
      )}
      <ConfirmActionModal
        open={confirmModalOpen}
        onOpenChange={setConfirmModalOpen}
        title="Delete Organization"
        message={`Are you sure you want to permanently delete "${organization.name}"? This will delete all projects, sites, and data associated with this organization. This action cannot be undone.`}
        onConfirm={confirmDeleteOrganization}
        type="danger"
        confirmLabel="Delete Organization"
      />
    </div>
  );
}