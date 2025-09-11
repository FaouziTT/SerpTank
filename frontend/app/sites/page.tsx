"use client";

import { useState, useEffect, useCallback } from "react"; // <-- CHANGE: Imported useCallback
import { useRouter } from "next/navigation";
import { Plus, Globe, ExternalLink, Activity, MoreVertical, CheckCircle, XCircle, Loader2, Trash2, Archive, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api-client";
import { Site, Project } from "@/types/api";
import { useAuth } from "@/lib/auth-context";
import { useProject } from "@/lib/project-context";
import { BulkSelectableItem } from "@/components/ui/bulk-actions";
import { useToast } from "@/components/ui/use-toast";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { ListLayout } from "@/components/layout/list-layout";
import { EntityModal } from "@/components/ui/entity-modal";
import { ConfirmActionModal } from "@/components/ui/confirm-action-modal";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from '@/lib/utils';
import { motion, useScroll, useTransform } from 'framer-motion';
import { SEOOrb } from '@/components/ui/seo-orb';

export default function SitesPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { currentProject } = useProject();
  const { toast } = useToast();
  const [sites, setSites] = useState<Site[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedSites, setSelectedSites] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string[]>>({});
  const [sortBy, setSortBy] = useState("created_at");
  
  // Modal states
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Form states
  const [formData, setFormData] = useState({
    url: "",
    name: "",
    description: "",
    project_id: "",
  });

  // Parallax and scroll effects
  const { scrollY } = useScroll();
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  // <-- CHANGE: Wrapped in useCallback
  const fetchSites = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.sites.list();
      // Ensure we always have an array, even if API returns unexpected data
      const sitesData = response?.data;
      if (Array.isArray(sitesData)) {
        setSites(sitesData);
      } else if (sitesData && typeof sitesData === 'object' && Array.isArray(sitesData.items)) {
        // Handle paginated response with items array
        setSites(sitesData.items);
      } else if (sitesData && typeof sitesData === 'object' && Array.isArray(sitesData.sites)) {
        // Handle case where data might be nested
        setSites(sitesData.sites);
      } else {
        console.warn('API returned non-array sites data:', sitesData);
        setSites([]);
      }
    } catch (error) {
      console.error("Failed to fetch sites:", error);
      setSites([]); // Ensure we set empty array on error
      toast({
        title: "Error",
        description: "Failed to load sites. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const fetchProjects = useCallback(async () => {
    try {
      const response = await api.projects.list();
      const projectsData = response?.data;
      if (Array.isArray(projectsData)) {
        setProjects(projectsData);
      } else if (projectsData && typeof projectsData === 'object' && Array.isArray(projectsData.items)) {
        // Handle paginated response
        setProjects(projectsData.items);
      } else {
        console.warn('API returned non-array projects data:', projectsData);
        setProjects([]);
      }
    } catch (error) {
      console.error("Failed to fetch projects:", error);
      setProjects([]);
    }
  }, []);

  useEffect(() => {
    fetchSites();
    fetchProjects();
  }, [fetchSites, fetchProjects]); // <-- CHANGE: Updated dependency array

  // Fetch health scores for all sites
  const [healthScores, setHealthScores] = useState<Record<string, number>>({});
  
  useEffect(() => {
    const fetchHealthScores = async () => {
      if (!Array.isArray(sites) || sites.length === 0) return;
      
      const scores: Record<string, number> = {};
      
      // Fetch health scores for each site
      await Promise.all(
        sites.map(async (site) => {
          try {
            const response = await api.diagnostic.getSiteHealth(site.id);
            const healthData = response.data;
            
            // Extract overall score from health data
            scores[site.id] = healthData.overall_score || 
                             healthData.health_score || 
                             healthData.score || 
                             0;
          } catch (error) {
            console.error(`Failed to fetch health score for site ${site.id}:`, error);
            // Set a default score on error
            scores[site.id] = 0;
          }
        })
      );
      
      setHealthScores(scores);
    };

    fetchHealthScores();
  }, [sites]);

  const handleCreateSite = async () => {
    try {
      setSubmitting(true);
      const response = await api.sites.create({
        ...formData,
        project_id: currentProject?.id || formData.project_id,
      });
      setSites([...sites, response.data]);
      setCreateModalOpen(false);
      setFormData({ url: "", name: "", description: "", project_id: "" });
      toast({
        title: "Success",
        description: "Site created successfully.",
      });
    } catch (error) {
      console.error("Failed to create site:", error);
      toast({
        title: "Error",
        description: "Failed to create site. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditSite = async () => {
    if (!selectedSite) return;
    
    try {
      setSubmitting(true);
      const response = await api.sites.update(selectedSite.id, formData);
      setSites(sites.map(s => s.id === selectedSite.id ? response.data : s));
      setEditModalOpen(false);
      toast({
        title: "Success",
        description: "Site updated successfully.",
      });
    } catch (error) {
      console.error("Failed to update site:", error);
      toast({
        title: "Error",
        description: "Failed to update site. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSite = async () => {
    if (!selectedSite) return;
    
    try {
      setSubmitting(true);
      await api.sites.delete(selectedSite.id);
      setSites(sites.filter(s => s.id !== selectedSite.id));
      setDeleteModalOpen(false);
      toast({
        title: "Success",
        description: "Site deleted successfully.",
      });
    } catch (error) {
      console.error("Failed to delete site:", error);
      toast({
        title: "Error",
        description: "Failed to delete site. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const filteredSites = Array.isArray(sites) ? sites.filter(site => {
    // Search filter
    if (searchTerm && !site.url.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !site.name?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    
    // Status filter
    if (selectedFilters.status?.length > 0) {
      const status = site.is_active ? "active" : "inactive";
      if (!selectedFilters.status.includes(status)) {
        return false;
      }
    }
    
    // Project filter
    if (selectedFilters.project?.length > 0 && site.project_id) {
      if (!selectedFilters.project.includes(site.project_id)) {
        return false;
      }
    }
    
    return true;
  }) : [];

  // Sort sites
  const sortedSites = [...filteredSites].sort((a, b) => {
    switch (sortBy) {
      case "name":
        return (a.name || a.url).localeCompare(b.name || b.url);
      case "created_at":
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      case "health":
        // Mock health score for now
        return 0;
      default:
        return 0;
    }
  });

  const getStatusBadge = (site: Site) => {
    if (site.is_active) {
      return <Badge variant="default"><CheckCircle className="h-3 w-3 mr-1" />Active</Badge>;
    }
    return <Badge variant="secondary"><XCircle className="h-3 w-3 mr-1" />Inactive</Badge>;
  };

  const getHealthScore = (site: Site) => {
    // Return cached health score or default
    return healthScores[site.id] || 0;
  };

  const getHealthColor = (score: number) => {
    if (score >= 90) return "text-green-600";
    if (score >= 70) return "text-yellow-600";
    return "text-red-600";
  };

  const handleBulkDelete = async () => {
    const selectedSitesList = Array.from(selectedSites);
    if (selectedSitesList.length === 0) return;
    
    const confirmed = window.confirm(
      `Are you sure you want to delete ${selectedSitesList.length} site(s)? This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    try {
      setSubmitting(true);
      await Promise.all(
        selectedSitesList.map(siteId => api.sites.delete(siteId))
      );
      setSites(sites.filter(s => !selectedSites.has(s.id)));
      setSelectedSites(new Set());
      toast({
        title: "Success",
        description: `${selectedSitesList.length} site(s) deleted successfully.`,
      });
    } catch (error) {
      console.error("Failed to delete sites:", error);
      toast({
        title: "Error",
        description: "Failed to delete some sites. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

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
                  Site Management
                </Badge>
              </motion.div>
              
              <motion.h1 
                className="text-5xl sm:text-6xl font-bold tracking-tighter mb-4 leading-[0.9]"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <span className="block">Website</span>
                <span className="block text-gradient-electric">Sites</span>
              </motion.h1>
              
              <motion.p 
                className="text-lg sm:text-xl text-muted-foreground leading-relaxed max-w-2xl"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3 }}
              >
                Monitor and manage your websites with comprehensive SEO analytics and performance tracking
              </motion.p>
            </div>
          </motion.div>

          <ListLayout
        title="Sites"
        searchPlaceholder="Search sites by name or URL..."
        onSearch={setSearchTerm}
        bulkActions={{
          enabled: true,
          items: sortedSites,
          getItemId: (site: Site) => site.id,
          actions: [
            {
              label: 'Delete',
              icon: Trash2,
              onClick: handleBulkDelete,
              variant: 'destructive' as const,
            },
            {
              label: 'Archive',
              icon: Archive,
              onClick: () => {
                toast({
                  title: "Coming Soon",
                  description: "Bulk archive feature will be available soon.",
                });
              },
            },
          ],
        }}
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
          {
            id: "project",
            label: "Project",
            type: "multiselect",
            options: projects.map(p => ({ id: p.id, label: p.name, value: p.id })),
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
          { id: "created_at", label: "Date Added", value: "created_at" },
          { id: "name", label: "Name", value: "name" },
          { id: "health", label: "Health Score", value: "health" },
        ]}
        selectedSort={sortBy}
        onSortChange={setSortBy}
        actions={[
          {
            label: "Add Site",
            onClick: () => {
              setFormData({ url: "", name: "", description: "", project_id: "" });
              setCreateModalOpen(true);
            },
            icon: Plus,
          },
        ]}
        emptyState={{
          icon: Globe,
          title: "No sites found",
          message: searchTerm
            ? "No sites match your search criteria"
            : "Add your first site to start monitoring",
          action: !searchTerm ? {
            label: "Add Your First Site",
            onClick: () => {
              setFormData({ url: "", name: "", description: "", project_id: "" });
              setCreateModalOpen(true);
            },
          } : undefined,
        }}
        loading={loading}
        totalCount={sortedSites.length}
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
            {sortedSites.map((site) => {
              const healthScore = getHealthScore(site);
              return (
                <BulkSelectableItem key={site.id} itemId={site.id}>
                  <Card
                    className="hover:shadow-lg transition-shadow cursor-pointer relative"
                    onClick={() => router.push(`/sites/${site.id}`)}
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
                        <DropdownMenuItem onClick={() => router.push(`/sites/${site.id}`)}>
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => {
                          setSelectedSite(site);
                          setFormData({
                            url: site.url,
                            name: site.name || "",
                            description: site.description || "",
                            project_id: site.project_id || "",
                          });
                          setEditModalOpen(true);
                        }}>
                          Edit Site
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => window.open(site.url, '_blank')}>
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Visit Site
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          className="text-destructive"
                          onClick={() => {
                            setSelectedSite(site);
                            setDeleteModalOpen(true);
                          }}
                        >
                          Delete Site
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  <CardHeader>
                    <div className="flex items-start justify-between pr-8">
                      <div className="flex-1">
                        <CardTitle className="flex items-center gap-2">
                          <Globe className="h-5 w-5" />
                          {site.name || new URL(site.url).hostname}
                        </CardTitle>
                        <CardDescription className="mt-1 break-all">
                          {site.url}
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Status</span>
                        {getStatusBadge(site)}
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Health Score</span>
                        <div className="flex items-center gap-2">
                          <Activity className={`h-4 w-4 ${getHealthColor(healthScore)}`} />
                          <span className={`font-medium ${getHealthColor(healthScore)}`}>
                            {healthScore}%
                          </span>
                        </div>
                      </div>

                      {site.project && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">Project</span>
                          <Badge variant="outline">{site.project.name}</Badge>
                        </div>
                      )}

                      <div className="pt-2 border-t">
                        <p className="text-xs text-muted-foreground">
                          Added {new Date(site.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </BulkSelectableItem>
              );
            })}
          </div>
          )}
          </ListLayout>
        </div>
      </DashboardLayout>

      {/* Create Site Modal */}
      <EntityModal
        entity="site"
        action="create"
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        title="Add New Site"
        description="Add a new website to monitor its SEO performance and health."
        onSubmit={handleCreateSite}
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="url">Website URL</Label>
            <Input
              id="url"
              type="url"
              placeholder="https://example.com"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="name">Site Name (optional)</Label>
            <Input
              id="name"
              placeholder="My Website"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea
              id="description"
              placeholder="Brief description of the site..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>
          <div>
            <Label htmlFor="project">Project (optional)</Label>
            <Select
              value={formData.project_id}
              onValueChange={(value) => setFormData({ ...formData, project_id: value })}
            >
              <SelectTrigger id="project">
                <SelectValue placeholder="Select a project" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </EntityModal>

      {/* Edit Site Modal */}
      <EntityModal
        entity="site"
        action="edit"
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        title="Edit Site"
        description="Update site information and settings."
        onSubmit={handleEditSite}
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="edit-url">Website URL</Label>
            <Input
              id="edit-url"
              type="url"
              placeholder="https://example.com"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="edit-name">Site Name</Label>
            <Input
              id="edit-name"
              placeholder="My Website"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="edit-description">Description</Label>
            <Textarea
              id="edit-description"
              placeholder="Brief description of the site..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>
          <div>
            <Label htmlFor="edit-project">Project</Label>
            <Select
              value={formData.project_id}
              onValueChange={(value) => setFormData({ ...formData, project_id: value })}
            >
              <SelectTrigger id="edit-project">
                <SelectValue placeholder="Select a project" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">No project</SelectItem>
                {projects.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </EntityModal>

      {/* Delete Confirmation Modal */}
      <ConfirmActionModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        onConfirm={handleDeleteSite}
        type="danger"
        title="Delete Site"
        message={`Are you sure you want to delete "${selectedSite?.name || selectedSite?.url}"? This action cannot be undone and will remove all associated data.`}
        confirmLabel="Delete Site"
        loading={submitting}
      />
    </div>
  );
}