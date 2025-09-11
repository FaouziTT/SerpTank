"use client";

import { useState, useEffect, useCallback, Suspense } from "react"; // <-- CHANGE: Imported useCallback
import { useRouter, useSearchParams } from "next/navigation";
import { Plus, FolderOpen, MoreVertical, Users, Globe, Calendar, Loader2, Sparkles } from "lucide-react";
import { motion, useScroll, useTransform } from 'framer-motion';
import { SEOOrb } from '@/components/ui/seo-orb';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api-client";
import { Project } from "@/types/api";
import { useAuth } from "@/lib/auth-context";
import { useProject } from "@/lib/project-context";
import { useToast } from "@/components/ui/use-toast";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { ListLayout } from "@/components/layout/list-layout";
import { EntityModal } from "@/components/ui/entity-modal";
import { ConfirmActionModal } from "@/components/ui/confirm-action-modal";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ProjectAnalysisLoading } from "@/components/ui/project-analysis-loading";

function ProjectsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { currentOrganization: organization } = useProject();
  const { toast } = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string[]>>({});
  const [sortBy, setSortBy] = useState("created_at");
  
  // Modal states
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Analysis loading state
  const [showAnalysisLoading, setShowAnalysisLoading] = useState(false);
  const [newProjectData, setNewProjectData] = useState<{
    id: number;
    name: string;
    url: string;
  } | null>(null);
  
  // Form states
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    url: "",
  });

  // Parallax and scroll effects
  const { scrollY } = useScroll();
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  // Check for action query parameter
  useEffect(() => {
    const action = searchParams.get('action');
    if (action === 'create') {
      setCreateModalOpen(true);
      // Remove the query parameter to clean up the URL
      router.replace('/projects');
    }
  }, [searchParams, router]);

  // <-- CHANGE: Wrapped in useCallback
  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.projects.list(organization?.id);
      setProjects(response.data.items || response.data);
    } catch (error) {
      console.error("Failed to fetch projects:", error);
      toast({
        title: "Error",
        description: "Failed to load projects. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [organization?.id, toast]);

  useEffect(() => {
    if (organization) {
      fetchProjects();
    } else {
      setLoading(false);
    }
  }, [organization, fetchProjects]); // <-- CHANGE: Added fetchProjects to dependency array

  const handleCreateProject = async () => {
    // Validate required fields
    if (!formData.name?.trim()) {
      toast({
        title: "Validation Error",
        description: "Project name is required.",
        variant: "destructive",
      });
      return;
    }
    
    if (!formData.url?.trim()) {
      toast({
        title: "Validation Error",
        description: "Website URL is required.",
        variant: "destructive",
      });
      return;
    }
    
    // Basic URL validation
    try {
      new URL(formData.url);
    } catch {
      toast({
        title: "Validation Error",
        description: "Please enter a valid URL (e.g., https://example.com)",
        variant: "destructive",
      });
      return;
    }
    
    try {
      setSubmitting(true);
      if (!organization?.id) {
        toast({
          title: "Error",
          description: "Please select an organization first.",
          variant: "destructive",
        });
        return;
      }
      
      const response = await api.projects.create({
        name: formData.name.trim(),
        organization_id: organization.id,
        description: formData.description?.trim() || undefined,
        url: formData.url.trim(),
        run_initial_crawl: true, // Start crawling the website immediately
        run_initial_core_web_vitals: true, // Run Core Web Vitals analysis
      });
      // Refresh the projects list to get the latest data
      await fetchProjects();
      setCreateModalOpen(false);
      setFormData({ name: "", description: "", url: "" });
      
      // Show analysis loading screen
      setNewProjectData({
        id: response.data.id,
        name: formData.name,
        url: formData.url
      });
      setShowAnalysisLoading(true);
      
      // Optional: Show a brief success toast
      toast({
        title: "Project created successfully!",
        description: "Starting website analysis...",
      });
    } catch (error: any) {
      console.error("Failed to create project:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Failed to create project. Please try again.";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditProject = async () => {
    if (!selectedProject) return;
    
    try {
      setSubmitting(true);
      const response = await api.projects.update(selectedProject.id, formData);
      setProjects(projects.map((p: Project) => p.id === selectedProject.id ? response.data : p));
      setEditModalOpen(false);
      toast({
        title: "Success",
        description: "Project updated successfully.",
      });
    } catch (error) {
      console.error("Failed to update project:", error);
      toast({
        title: "Error",
        description: "Failed to update project. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!selectedProject) return;
    
    try {
      setSubmitting(true);
      await api.projects.delete(selectedProject.id);
      setProjects(projects.filter((p: Project) => p.id !== selectedProject.id));
      setDeleteModalOpen(false);
      toast({
        title: "Success",
        description: "Project deleted successfully.",
      });
    } catch (error) {
      console.error("Failed to delete project:", error);
      toast({
        title: "Error",
        description: "Failed to delete project. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const filteredProjects = projects.filter((project: Project) => {
    // Search filter
    if (searchTerm && !project.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !project.description?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    
    // Status filter
    if (selectedFilters.status?.length > 0) {
      const status = project.is_active ? "active" : "inactive";
      if (!selectedFilters.status.includes(status)) {
        return false;
      }
    }
    
    return true;
  });

  // Sort projects
  const sortedProjects = [...filteredProjects].sort((a: Project, b: Project) => {
    switch (sortBy) {
      case "name":
        return a.name.localeCompare(b.name);
      case "created_at":
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      case "sites":
        return (b.sites_count || 0) - (a.sites_count || 0);
      default:
        return 0;
    }
  });

  const getStatusBadge = (project: Project) => {
    if (project.is_active) {
      return <Badge variant="default">Active</Badge>;
    }
    return <Badge variant="secondary">Inactive</Badge>;
  };

  if (!organization) {
    return (
      <DashboardLayout>
        <div className="container mx-auto p-6">
          <Card>
            <CardContent className="text-center py-8">
              <h3 className="text-lg font-semibold mb-2">No Organization Selected</h3>
              <p className="text-muted-foreground mb-4">
                Please select an organization to manage projects
              </p>
              <Button onClick={() => router.push("/organizations")}>
                Go to Organizations
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
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
                  Project Management
                </Badge>
              </motion.div>
              
              <motion.h1 
                className="text-5xl sm:text-6xl font-bold tracking-tighter mb-4 leading-[0.9]"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <span className="block">SEO</span>
                <span className="block text-gradient-electric">Projects</span>
              </motion.h1>
              
              <motion.p 
                className="text-lg sm:text-xl text-muted-foreground leading-relaxed max-w-2xl"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3 }}
              >
                Organize and manage your SEO projects with comprehensive analytics and insights
              </motion.p>
            </div>
          </motion.div>

          <ListLayout
        title="Projects"
        searchPlaceholder="Search projects by name or description..."
        onSearch={setSearchTerm}
        filters={[
          {
            id: "status",
            label: "Status",
            type: "multiselect",
            options: [
              { id: "active", label: "Active", value: "active" },
              { id: "inactive", label: "Inactive", value: "inactive" },
            ],
          },
        ]}
        selectedFilters={selectedFilters}
        onFilterChange={(filterId, value) => {
          setSelectedFilters(prev => ({
            ...prev,
            [filterId]: Array.isArray(value) ? value : [value]
          }));
        }}
        sortOptions={[
          { id: "created_at", label: "Date Created", value: "created_at" },
          { id: "name", label: "Name", value: "name" },
          { id: "sites", label: "Sites Count", value: "sites" },
        ]}
        selectedSort={sortBy}
        onSortChange={setSortBy}
        actions={[
          {
            label: "New Project",
            onClick: () => {
              setFormData({ name: "", description: "", url: "" });
              setCreateModalOpen(true);
            },
            icon: Plus,
          },
        ]}
        emptyState={{
          icon: FolderOpen,
          title: "No projects found",
          message: searchTerm
            ? "No projects match your search criteria"
            : "Create your first project to organize your sites",
          action: !searchTerm ? {
            label: "Create Your First Project",
            onClick: () => {
              setFormData({ name: "", description: "", url: "" });
              setCreateModalOpen(true);
            },
          } : undefined,
        }}
      >
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-6 bg-muted rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-muted rounded w-1/2"></div>
                </CardHeader>
                <CardContent>
                  <div className="h-4 bg-muted rounded w-full mb-2"></div>
                  <div className="h-4 bg-muted rounded w-2/3"></div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {sortedProjects.map((project) => (
              <Card
                key={project.id}
                className="hover:shadow-lg transition-shadow cursor-pointer relative"
                onClick={() => router.push(`/projects/${project.id}`)}
              >
                <div className="absolute top-4 right-4" onClick={(e) => e.stopPropagation()}>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Actions</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => router.push(`/projects/${project.id}`)}>
                        View Details
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => {
                        setSelectedProject(project);
                        setFormData({
                          name: project.name,
                          description: project.description || "",
                          url: project.url || "",
                        });
                        setEditModalOpen(true);
                      }}>
                        Edit Project
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => router.push(`/projects/${project.id}?tab=settings`)}>
                        Project Settings
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem 
                        className="text-destructive"
                        onClick={() => {
                          setSelectedProject(project);
                          setDeleteModalOpen(true);
                        }}
                      >
                        Delete Project
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <CardHeader>
                  <div className="flex items-start justify-between pr-8">
                    <div className="flex-1">
                      <CardTitle className="flex items-center gap-2">
                        <FolderOpen className="h-5 w-5" />
                        {project.name}
                      </CardTitle>
                      {project.description && (
                        <CardDescription className="mt-1 line-clamp-2">
                          {project.description}
                        </CardDescription>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Status</span>
                      {getStatusBadge(project)}
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">{project.sites_count || 0}</p>
                          <p className="text-xs text-muted-foreground">Sites</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">{project.team_members_count || 0}</p>
                          <p className="text-xs text-muted-foreground">Members</p>
                        </div>
                      </div>
                    </div>

                    <div className="pt-2 border-t">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        Created {new Date(project.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          )}
          </ListLayout>
        </div>
      </DashboardLayout>

      {/* Create Project Modal */}
      <EntityModal
        entity="project"
        action="create"
        open={createModalOpen}
        onOpenChange={(open) => {
          setCreateModalOpen(open);
          if (!open) {
            // Reset form when closing
            setFormData({ name: "", description: "", url: "" });
          }
        }}
        title="Create New Project"
        description="Projects help you organize your sites and collaborate with your team."
        onSubmit={handleCreateProject}
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="name">Project Name</Label>
            <Input
              id="name"
              placeholder="My SEO Project"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="url">Website URL</Label>
            <Input
              id="url"
              type="url"
              placeholder="https://example.com"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              required
              pattern="https?://.*"
              title="Please enter a valid URL starting with http:// or https://"
            />
          </div>
          <div>
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea
              id="description"
              placeholder="Brief description of the project..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>
        </div>
      </EntityModal>

      {/* Edit Project Modal */}
      <EntityModal
        entity="project"
        action="edit"
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        title="Edit Project"
        description="Update project information."
        onSubmit={handleEditProject}
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="edit-name">Project Name</Label>
            <Input
              id="edit-name"
              placeholder="My SEO Project"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="edit-description">Description</Label>
            <Textarea
              id="edit-description"
              placeholder="Brief description of the project..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>
        </div>
      </EntityModal>

      {/* Delete Confirmation Modal */}
      <ConfirmActionModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        onConfirm={handleDeleteProject}
        type="danger"
        title="Delete Project"
        message={`Are you sure you want to delete ${selectedProject?.name}? This action cannot be undone and will remove all project data, sites, team members, and configurations.`}
        confirmLabel="Delete Project"
        loading={submitting}
      />
      
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
              title: "Analysis Complete!",
              description: "Your project is ready. You can now view detailed insights.",
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

export default function ProjectsPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin" /></div>}>
      <ProjectsPageContent />
    </Suspense>
  );
}