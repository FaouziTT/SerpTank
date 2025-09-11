'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Building2, Users, FolderOpen, Calendar, Sparkles } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { ListLayout } from '@/components/layout/list-layout';
import { EntityModal, useEntityModal } from '@/components/ui/entity-modal';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { InlineEdit } from '@/components/ui/inline-edit';
import { api } from '@/lib/api-client';
import { Organization } from '@/types/api';
import { useAuth } from '@/lib/auth-context';
import { useToast } from '@/components/ui/use-toast';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { motion, useScroll, useTransform } from 'framer-motion';
import { SEOOrb } from '@/components/ui/seo-orb';

interface CreateOrganizationData {
  name: string;
  description: string;
}

export default function OrganizationsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { toast } = useToast();
  const createModal = useEntityModal<CreateOrganizationData>();
  
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState({
    search: '',
    role: '',
  });
  const [formData, setFormData] = useState<CreateOrganizationData>({
    name: '',
    description: '',
  });

  // Parallax and scroll effects
  const { scrollY } = useScroll();
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    fetchOrganizations();
  }, []);

  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.organizations.list();
      setOrganizations(response.data || []);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch organizations'));
      console.error('Failed to fetch organizations:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrganization = async (data: CreateOrganizationData) => {
    try {
      const response = await api.organizations.create(data);
      toast({
        title: 'Organization created',
        description: `${data.name} has been created successfully.`,
      });
      await fetchOrganizations();
      router.push(`/organizations/${response.data.id}`);
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to create organization. Please try again.',
        variant: 'destructive',
      });
      throw err;
    }
  };

  const getMemberRole = (org: Organization) => {
    const member = org.members?.find((m: any) => m.user_id === user?.id);
    return member?.role || 'member';
  };

  const getMemberCount = (org: Organization) => {
    return org.members_count || org.members?.length || 0;
  };

  const getProjectCount = (org: Organization) => {
    return org.projects_count || 0;
  };

  const filteredOrganizations = organizations.filter((org: Organization) => {
    const matchesSearch = !filters.search || 
      org.name.toLowerCase().includes(filters.search.toLowerCase()) ||
      org.description?.toLowerCase().includes(filters.search.toLowerCase());
    
    const matchesRole = !filters.role || getMemberRole(org) === filters.role;
    
    return matchesSearch && matchesRole;
  });

  const roleOptions = [
    { id: 'all', label: 'All Roles', value: '' },
    { id: 'owner', label: 'Owner', value: 'owner' },
    { id: 'admin', label: 'Admin', value: 'admin' },
    { id: 'member', label: 'Member', value: 'member' },
  ];

  const sortOptions = [
    { id: 'name', label: 'Name (A-Z)', value: 'name-asc' },
    { id: 'name-desc', label: 'Name (Z-A)', value: 'name-desc' },
    { id: 'recent', label: 'Recently Updated', value: 'updated-desc' },
    { id: 'members', label: 'Most Members', value: 'members-desc' },
  ];


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
                  Organization Management
                </Badge>
              </motion.div>
              
              <motion.h1 
                className="text-5xl sm:text-6xl font-bold tracking-tighter mb-4 leading-[0.9]"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <span className="block">Team</span>
                <span className="block text-gradient-electric">Organizations</span>
              </motion.h1>
              
              <motion.p 
                className="text-lg sm:text-xl text-muted-foreground leading-relaxed max-w-2xl"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3 }}
              >
                Manage your organizations and team collaborations with advanced tools
              </motion.p>
            </div>
          </motion.div>

          <ListLayout
        title="Organizations"
        searchPlaceholder="Search organizations..."
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
        actions={[
          {
            label: 'New Organization',
            icon: Plus,
            onClick: () => {
              setFormData({ name: '', description: '' });
              createModal.openModal('create');
            },
            'data-action': 'new-organization',
          } as any,
        ]}
        loading={loading}
        error={error}
        onRetry={fetchOrganizations}
        totalCount={filteredOrganizations.length}
        emptyState={{
          icon: Building2,
          title: 'No organizations found',
          message: filters.search
            ? 'No organizations match your search criteria'
            : 'Create your first organization to get started',
          action: !filters.search ? {
            label: 'Create Organization',
            onClick: () => {
              setFormData({ name: '', description: '' });
              createModal.openModal('create');
            },
          } : undefined,
        }}
      >
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredOrganizations.map((org: Organization, index: number) => (
            <Card
              key={org.id}
              className="hover:shadow-lg transition-all cursor-pointer group"
              onClick={() => {
                router.push(`/organizations/${org.id}`);
              }}
            >
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <Building2 className="h-5 w-5 text-muted-foreground" />
                      <div 
                        onClick={(e) => e.stopPropagation()}
                        className="flex-1"
                      >
                        <InlineEdit
                          value={org.name}
                          onSave={async (newName) => {
                            try {
                              await api.organizations.update(org.id, { name: newName });
                              setOrganizations((orgs: Organization[]) => 
                                orgs.map((o: Organization) => o.id === org.id ? { ...o, name: newName } : o)
                              );
                              toast({
                                title: 'Organization updated',
                                description: 'Organization name has been updated successfully.',
                              });
                            } catch (error) {
                              toast({
                                title: 'Update failed',
                                description: 'Failed to update organization name.',
                                variant: 'destructive',
                              });
                              throw error;
                            }
                          }}
                          validation={(value) => {
                            if (!value.trim()) return 'Name is required';
                            if (value.length > 100) return 'Name is too long';
                            return true;
                          }}
                          disabled={getMemberRole(org) !== 'owner'}
                        />
                      </div>
                    </CardTitle>
                    <CardDescription className="mt-1 line-clamp-2">
                      {org.description || 'No description provided'}
                    </CardDescription>
                  </div>
                  <Badge 
                    variant={getMemberRole(org) === 'owner' ? 'default' : 'secondary'}
                    className="ml-2"
                  >
                    {getMemberRole(org)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4 text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Users className="h-4 w-4" />
                        <span>{getMemberCount(org)} members</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <FolderOpen className="h-4 w-4" />
                        <span>{getProjectCount(org)} projects</span>
                      </div>
                    </div>
                  </div>
                  {org.updated_at && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      <span>Updated {formatDistanceToNow(new Date(org.updated_at), { addSuffix: true })}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
          </div>
          </ListLayout>
        </div>
      </DashboardLayout>

      <EntityModal
        {...createModal}
        onOpenChange={createModal.setOpen}
        entity="organization"
        title="Create New Organization"
        description="Organizations help you collaborate with your team on multiple projects."
        onSubmit={() => handleCreateOrganization(formData)}
        submitLabel="Create Organization"
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Organization Name</Label>
            <Input
              id="name"
              placeholder="Acme Corporation"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ 
                ...prev, 
                name: e.target.value 
              }))}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Describe your organization's purpose..."
              rows={4}
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ 
                ...prev, 
                description: e.target.value 
              }))}
            />
          </div>
        </div>
      </EntityModal>
    </div>
  );
}