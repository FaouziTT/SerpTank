'use client';

import { useState, useEffect, useCallback } from 'react'; // <-- CHANGE: Imported useCallback
import { Mail, Clock, Copy, Trash2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api-client';
import { OrganizationInvitation } from '@/types/api';
import { useToast } from '@/components/ui/use-toast';
import { formatDistanceToNow } from 'date-fns';

interface OrganizationInvitationsProps {
  organizationId: string;
  currentUserRole: string | null;
  onUpdate: () => void;
}

export function OrganizationInvitations({ organizationId, currentUserRole, onUpdate }: OrganizationInvitationsProps) {
  const { toast } = useToast();
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const [loading, setLoading] = useState(true);

  // <-- CHANGE: Wrapped in useCallback
  const fetchInvitations = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.organizations.getInvitations(organizationId);
      setInvitations(response.data || []);
    } catch (error) {
      console.error('Failed to fetch invitations:', error);
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    fetchInvitations();
  }, [fetchInvitations]); // <-- CHANGE: Updated dependency array

  const handleCopyLink = (invitation: OrganizationInvitation) => {
    // In a real implementation, construct the invitation link
    const inviteLink = `${window.location.origin}/invitations/${invitation.id}/accept`;
    navigator.clipboard.writeText(inviteLink);
    toast({
      title: 'Link copied',
      description: 'Invitation link copied to clipboard',
    });
  };

  const handleDelete = async (invitationId: string) => {
    try {
      await api.organizations.deleteInvitation(invitationId);
      toast({
        title: 'Invitation deleted',
        description: 'The invitation has been removed',
      });
      fetchInvitations();
      onUpdate();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete invitation',
        variant: 'destructive',
      });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pending Invitations</CardTitle>
        <CardDescription>
          Manage pending invitations to join the organization
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-muted animate-pulse rounded" />
            ))}
          </div>
        ) : invitations.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground">
            No pending invitations
          </div>
        ) : (
          <div className="space-y-3">
            {invitations.map(invitation => (
              <div key={invitation.id} className="flex items-center justify-between p-3 rounded-lg border">
                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <div className="font-medium">{invitation.email}</div>
                    <div className="text-sm text-muted-foreground">
                      Invited {formatDistanceToNow(new Date(invitation.created_at), { addSuffix: true })}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{invitation.role}</Badge>
                  <Badge variant={invitation.status === 'pending' ? 'outline' : 'default'}>
                    <Clock className="h-3 w-3 mr-1" />
                    {invitation.status}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleCopyLink(invitation)}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(invitation.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}