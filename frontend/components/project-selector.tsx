'use client';

import { useState, useRef, useEffect } from 'react';
import { Check, ChevronsUpDown, Plus, Building2, ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '@/components/ui/command';
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useProject } from '@/lib/project-context';
import { Organization } from '@/types/api';
import { Separator } from '@/components/ui/separator';
import { EntityModal } from '@/components/ui/entity-modal';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import { api } from '@/lib/api-client';
import { useRouter } from 'next/navigation';
import { ProjectAnalysisLoading } from '@/components/ui/project-analysis-loading';

export function ProjectSelector() {
  const router = useRouter();
  const { toast } = useToast();
  const { 
    organizations, 
    projects, 
    currentOrganization, 
    currentProject,
    setCurrentOrganization,
    setCurrentProject,
    isLoading,
    refetch
  } = useProject();

  // Modal states
  const [orgModalOpen, setOrgModalOpen] = useState(false);
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Hierarchical popover states
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [popoverView, setPopoverView] = useState<'organizations' | 'projects'>('organizations');
  const [viewingOrg, setViewingOrg] = useState<Organization | null>(null);

  // Legacy popover states (keeping for compatibility)
  const [orgPopoverOpen, setOrgPopoverOpen] = useState(false);
  const [projectPopoverOpen, setProjectPopoverOpen] = useState(false);

  // Form states
  const [orgFormData, setOrgFormData] = useState({ name: '', description: '' });
  const [projectFormData, setProjectFormData] = useState({ name: '', description: '', url: '' });

  // Refs for width measurement
  const orgTriggerRef = useRef<HTMLButtonElement>(null);
  const projectTriggerRef = useRef<HTMLButtonElement>(null);

  // State for measured widths
  const [orgTriggerWidth, setOrgTriggerWidth] = useState<number | null>(null);
  const [projectTriggerWidth, setProjectTriggerWidth] = useState<number | null>(null);
  
  // Analysis loading state
  const [showAnalysisLoading, setShowAnalysisLoading] = useState(false);
  const [newProjectData, setNewProjectData] = useState<{
    id: number;
    name: string;
    url: string;
  } | null>(null);

  // Effect to measure button widths
  useEffect(() => {
    const measureWidths = () => {
      if (orgTriggerRef.current) {
        setOrgTriggerWidth(orgTriggerRef.current.offsetWidth);
      }
      if (projectTriggerRef.current) {
        setProjectTriggerWidth(projectTriggerRef.current.offsetWidth);
      }
    };

    // Measure on mount and when dependencies change
    measureWidths();

    // Add resize listener for responsive updates
    const handleResize = () => measureWidths();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, [currentOrganization, currentProject, organizations, projects]);

  // Handler functions
  const handleCreateOrganization = async () => {
    if (!orgFormData.name?.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Organization name is required.',
        variant: 'destructive',
      });
      return;
    }

    try {
      setSubmitting(true);
      const response = await api.organizations.create({
        name: orgFormData.name.trim(),
        description: orgFormData.description?.trim() || undefined,
      });
      
      toast({
        title: 'Organization created',
        description: `${orgFormData.name} has been created successfully.`,
      });
      
      // Refresh data and select the new organization
      refetch();
      setCurrentOrganization(response.data);
      setOrgModalOpen(false);
      setOrgFormData({ name: '', description: '' });
    } catch (error: any) {
      console.error('Failed to create organization:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create organization. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateProject = async () => {
    if (!projectFormData.name?.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Project name is required.',
        variant: 'destructive',
      });
      return;
    }

    if (!projectFormData.url?.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Website URL is required.',
        variant: 'destructive',
      });
      return;
    }

    try {
      new URL(projectFormData.url);
    } catch {
      toast({
        title: 'Validation Error',
        description: 'Please enter a valid URL (e.g., https://example.com)',
        variant: 'destructive',
      });
      return;
    }

    if (!currentOrganization?.id) {
      toast({
        title: 'Error',
        description: 'Please select an organization first.',
        variant: 'destructive',
      });
      return;
    }

    try {
      setSubmitting(true);
      const response = await api.projects.create({
        name: projectFormData.name.trim(),
        organization_id: currentOrganization.id,
        description: projectFormData.description?.trim() || undefined,
        url: projectFormData.url.trim(),
        run_initial_crawl: true,
        run_initial_core_web_vitals: true,
      });
      
      // Show analysis loading screen
      setNewProjectData({
        id: response.data.id,
        name: projectFormData.name,
        url: projectFormData.url
      });
      setShowAnalysisLoading(true);
      
      // Refresh data and select the new project
      refetch();
      setCurrentProject(response.data);
      setProjectModalOpen(false);
      setProjectFormData({ name: '', description: '', url: '' });
      
      // Optional: Show a brief success toast
      toast({
        title: 'Project created successfully!',
        description: 'Starting website analysis...',
      });
    } catch (error: any) {
      console.error('Failed to create project:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create project. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="h-8 w-48 bg-muted animate-pulse rounded-md" />
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2">
      {/* Hierarchical Context Switcher */}
      <Popover
        open={popoverOpen}
        onOpenChange={(open) => {
          if (!open) {
            // Reset the view when the popover closes
            setPopoverView('organizations');
            setViewingOrg(null);
          }
          setPopoverOpen(open);
        }}
      >
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            role="combobox"
            className="w-full justify-between text-left px-3 py-4"
          >
            <div className="flex items-center truncate">
              <Building2 className="mr-2 h-4 w-4 shrink-0" />
              <span className="font-semibold truncate">
                {currentOrganization?.name || 'Select Organization'}
              </span>
              <span className="mx-2 text-muted-foreground">/</span>
              <span className="truncate text-muted-foreground">
                {currentProject?.name || 'Select Project'}
              </span>
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80 p-0" side="bottom" align="start">
          <Command>
            {popoverView === 'organizations' ? (
              // Organization List View
              <>
                <CommandInput placeholder="Search organizations..." />
                <CommandEmpty>No organization found.</CommandEmpty>
                <CommandGroup>
                  {organizations.map((org) => (
                    <CommandItem
                      key={org.id}
                      value={org.id.toString()}
                      onSelect={() => {
                        setViewingOrg(org);
                        setPopoverView('projects');
                      }}
                    >
                      <Check
                        className={cn(
                          'mr-2 h-4 w-4',
                          currentOrganization?.id === org.id ? 'opacity-100' : 'opacity-0'
                        )}
                      />
                      {org.name}
                    </CommandItem>
                  ))}
                </CommandGroup>
                <Separator />
                <CommandGroup>
                  <CommandItem
                    value="create-org"
                    className="cursor-pointer hover:bg-accent"
                    onSelect={() => {
                      setOrgFormData({ name: '', description: '' });
                      setOrgModalOpen(true);
                      setPopoverOpen(false);
                    }}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Create Organization
                  </CommandItem>
                </CommandGroup>
              </>
            ) : (
              // Project List View
              <>
                <CommandGroup>
                  <CommandItem onSelect={() => setPopoverView('organizations')}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Organizations
                  </CommandItem>
                </CommandGroup>
                <Separator />
                <CommandGroup heading={viewingOrg?.name}>
                  <CommandInput placeholder="Search projects..." />
                  <CommandEmpty>No project found.</CommandEmpty>
                  {projects
                    .filter(p => p.organization_id === viewingOrg?.id)
                    .map((project) => (
                      <CommandItem
                        key={project.id}
                        value={project.id.toString()}
                        onSelect={() => {
                          setCurrentOrganization(viewingOrg);
                          setCurrentProject(project);
                          setPopoverOpen(false);
                        }}
                      >
                        <Check
                          className={cn(
                            'mr-2 h-4 w-4',
                            currentProject?.id === project.id ? 'opacity-100' : 'opacity-0'
                          )}
                        />
                        {project.name}
                      </CommandItem>
                    ))}
                </CommandGroup>
                <Separator />
                <CommandGroup>
                  <CommandItem
                    value="create-project"
                    className="cursor-pointer hover:bg-accent"
                    onSelect={() => {
                      // Ensure we have the viewing org context for project creation
                      if (viewingOrg && !currentOrganization) {
                        setCurrentOrganization(viewingOrg);
                      }
                      setProjectFormData({ name: '', description: '', url: '' });
                      setProjectModalOpen(true);
                      setPopoverOpen(false);
                    }}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Create Project
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </Command>
        </PopoverContent>
      </Popover>

      {/* Organization Creation Modal */}
      <EntityModal
        entity="organization"
        action="create"
        open={orgModalOpen}
        onOpenChange={(open) => {
          setOrgModalOpen(open);
          if (!open) {
            setOrgFormData({ name: '', description: '' });
          }
        }}
        title="Create New Organization"
        description="Organizations help you collaborate with your team on multiple projects."
        onSubmit={handleCreateOrganization}
        submitLabel="Create Organization"
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="org-name">Organization Name</Label>
            <Input
              id="org-name"
              placeholder="Acme Corporation"
              value={orgFormData.name}
              onChange={(e) => setOrgFormData(prev => ({ 
                ...prev, 
                name: e.target.value 
              }))}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="org-description">Description</Label>
            <Textarea
              id="org-description"
              placeholder="Describe your organization's purpose..."
              rows={4}
              value={orgFormData.description}
              onChange={(e) => setOrgFormData(prev => ({ 
                ...prev, 
                description: e.target.value 
              }))}
            />
          </div>
        </div>
      </EntityModal>

      {/* Project Creation Modal */}
      <EntityModal
        entity="project"
        action="create"
        open={projectModalOpen}
        onOpenChange={(open) => {
          setProjectModalOpen(open);
          if (!open) {
            setProjectFormData({ name: '', description: '', url: '' });
          }
        }}
        title="Create New Project"
        description="Projects help you organize your sites and collaborate with your team."
        onSubmit={handleCreateProject}
        submitLabel="Create Project"
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="project-name">Project Name</Label>
            <Input
              id="project-name"
              placeholder="My SEO Project"
              value={projectFormData.name}
              onChange={(e) => setProjectFormData(prev => ({ 
                ...prev, 
                name: e.target.value 
              }))}
              required
            />
          </div>
          <div>
            <Label htmlFor="project-url">Website URL</Label>
            <Input
              id="project-url"
              type="url"
              placeholder="https://example.com"
              value={projectFormData.url}
              onChange={(e) => setProjectFormData(prev => ({ 
                ...prev, 
                url: e.target.value 
              }))}
              required
              pattern="https?://.*"
              title="Please enter a valid URL starting with http:// or https://"
            />
          </div>
          <div>
            <Label htmlFor="project-description">Description (optional)</Label>
            <Textarea
              id="project-description"
              placeholder="Brief description of the project..."
              value={projectFormData.description}
              onChange={(e) => setProjectFormData(prev => ({ 
                ...prev, 
                description: e.target.value 
              }))}
              rows={3}
            />
          </div>
        </div>
      </EntityModal>
      
      {/* Analysis Loading Screen */}
      {showAnalysisLoading && newProjectData && (
        <ProjectAnalysisLoading
          projectId={newProjectData.id}
          projectName={newProjectData.name}
          projectUrl={newProjectData.url}
          onClose={() => {
            setShowAnalysisLoading(false);
            setNewProjectData(null);
          }}
          showCloseButton={true}
          redirectOnComplete={false}
          onComplete={() => {
            // Close the loading screen and show success message
            setShowAnalysisLoading(false);
            setNewProjectData(null);
            toast({
              title: 'Analysis Complete!',
              description: 'Your project is ready. You can now view detailed insights.',
              action: (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => router.push(`/projects/${newProjectData.id}`)}
                >
                  View Project
                </Button>
              ),
            });
          }}
        />
      )}
    </div>
  );
}