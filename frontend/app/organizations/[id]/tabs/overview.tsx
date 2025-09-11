'use client';

import { useState, useEffect, useCallback } from 'react'; // <-- CHANGE: Imported useCallback
import { Building2, FolderOpen, Users, Calendar, Activity, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { api } from '@/lib/api-client';
import { Organization, Project, Site, OrganizationMember } from '@/types/api';
import { formatDistanceToNow } from 'date-fns';
import { useRouter } from 'next/navigation';

interface OrganizationOverviewProps {
  organization: Organization;
}

export function OrganizationOverview({ organization }: OrganizationOverviewProps) {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalProjects: 0,
    activeProjects: 0,
    totalSites: 0,
    activeSites: 0,
  });

  // <-- CHANGE: Wrapped in useCallback
  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.projects.list(organization.id);
      const projectList = response.data || [];
      setProjects(projectList);
      
      // Calculate stats
      const activeProjects = projectList.filter((p: Project) => p.is_active).length;
      const totalSites = projectList.reduce((sum: number, p: Project) => sum + (p.sites?.length || 0), 0);
      const activeSites = projectList.reduce((sum: number, p: Project) => 
        sum + (p.sites?.filter((s: Site) => s.is_active).length || 0), 0
      );
      
      setStats({
        totalProjects: projectList.length,
        activeProjects,
        totalSites,
        activeSites,
      });
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
    }
  }, [organization.id]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]); // <-- CHANGE: Updated dependency array

  const getRecentActivity = () => {
    const activities = [];
    
    // Add organization creation
    if (organization.created_at) {
      activities.push({
        type: 'created',
        message: 'Organization created',
        timestamp: organization.created_at,
        icon: Building2,
      });
    }
    
    // Add project activities
    projects.forEach((project: Project) => {
      if (project.created_at) {
        activities.push({
          type: 'project_created',
          message: `Project "${project.name}" created`,
          timestamp: project.created_at,
          icon: FolderOpen,
        });
      }
    });
    
    // Sort by timestamp descending
    return activities
      .sort((a: { timestamp: string }, b: { timestamp: string }) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 5);
  };

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Members</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{organization.members?.length || 0}</div>
            <p className="text-xs text-muted-foreground">
              Active members in organization
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Projects</CardTitle>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalProjects}</div>
            <p className="text-xs text-muted-foreground">
              {stats.activeProjects} active projects
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sites</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalSites}</div>
            <p className="text-xs text-muted-foreground">
              {stats.activeSites} active sites
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Organization Age</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {organization.created_at 
                ? formatDistanceToNow(new Date(organization.created_at), { addSuffix: false })
                : 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground">
              Since creation
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Projects List */}
        <Card>
          <CardHeader>
            <CardTitle>Projects</CardTitle>
            <CardDescription>
              All projects in this organization
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i: number) => (
                  <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                ))}
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground">
                No projects yet. Create your first project to get started.
              </div>
            ) : (
              <div className="space-y-3">
                {projects.map((project: Project) => (
                  <div
                    key={project.id}
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => router.push(`/projects/${project.id}`)}
                  >
                    <div className="flex items-center gap-3">
                      <FolderOpen className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <div className="font-medium">{project.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {project.sites?.length || 0} sites
                        </div>
                      </div>
                    </div>
                    <Badge variant={project.is_active ? 'default' : 'secondary'}>
                      {project.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest actions in this organization
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {getRecentActivity().length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  No recent activity
                </div>
              ) : (
                getRecentActivity().map((activity: {
                  type: string;
                  message: string;
                  timestamp: string;
                  icon: any;
                }, index: number) => {
                  const Icon = activity.icon;
                  return (
                    <div key={index} className="flex items-start gap-3">
                      <div className="p-2 bg-muted rounded-full">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">{activity.message}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Member Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Member Distribution</CardTitle>
          <CardDescription>
            Breakdown of member roles in the organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {['owner', 'admin', 'member'].map((role: string) => {
              const count = organization.members?.filter((m: OrganizationMember) => m.role === role).length || 0;
              const percentage = organization.members?.length 
                ? (count / organization.members.length) * 100 
                : 0;
              
              return (
                <div key={role} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="capitalize">{role}s</span>
                    <span className="text-muted-foreground">{count}</span>
                  </div>
                  <Progress value={percentage} className="h-2" />
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}