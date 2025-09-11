"use client";

import { useState, useEffect, useCallback, useMemo } from "react"; // <-- CHANGE: Imported useCallback and useMemo
import { useRouter } from "next/navigation";
import { AdminGuard } from "@/components/auth/admin-guard";
import { 
  FileText, Plus, Calendar, Download, Share2, Clock,
  BarChart3, TrendingUp, Users, Search, Filter,
  ChevronRight, Eye, Trash2, Copy, CheckCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/lib/auth-context";
import { useProject } from "@/lib/project-context";
import { useToast } from "@/components/ui/use-toast";
import { ListLayout } from "@/components/layout/list-layout";
import { EntityModal } from "@/components/ui/entity-modal";
import { ConfirmActionModal } from "@/components/ui/confirm-action-modal";
import { WizardModal } from "@/components/ui/wizard-modal";
import { api } from "@/lib/api-client";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Report {
  id: string;
  name: string;
  description?: string;
  type: "seo" | "performance" | "competitor" | "custom";
  status: "draft" | "published" | "scheduled";
  frequency?: "one-time" | "daily" | "weekly" | "monthly";
  created_at: string;
  updated_at: string;
  created_by: {
    id: string;
    name: string;
  };
  last_run?: string;
  next_run?: string;
  recipients?: string[];
}

export default function ReportsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { currentOrganization: organization, currentProject } = useProject();
  const { toast } = useToast();
  
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string[]>>({});
  const [sortBy, setSortBy] = useState("updated_at");
  
  // Modal states
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  // Removed currentStep state - WizardModal manages its own state
  
  // Form data for wizard
  const [reportConfig, setReportConfig] = useState({
    name: "",
    description: "",
    type: "seo",
    frequency: "one-time",
    metrics: [] as string[],
    filters: {} as Record<string, any>,
    recipients: [] as string[],
    schedule: {
      time: "09:00",
      dayOfWeek: 1,
      dayOfMonth: 1,
    }
  });

  // Mock data
  const mockReports: Report[] = useMemo(() => [
    {
      id: "1",
      name: "Weekly SEO Performance Report",
      description: "Comprehensive SEO metrics and rankings analysis",
      type: "seo",
      status: "published",
      frequency: "weekly",
      created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      created_by: { id: "1", name: "John Doe" },
      last_run: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      next_run: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(),
      recipients: ["team@example.com", "manager@example.com"]
    },
    {
      id: "2", 
      name: "Competitor Analysis Report",
      description: "Monthly competitor tracking and comparison",
      type: "competitor",
      status: "scheduled",
      frequency: "monthly",
      created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      created_by: { id: "2", name: "Jane Smith" },
      last_run: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      next_run: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
      recipients: ["leadership@example.com"]
    },
    {
      id: "3",
      name: "Q4 Performance Summary",
      description: "Quarterly performance metrics and insights",
      type: "performance",
      status: "draft",
      frequency: "one-time",
      created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      created_by: { id: "1", name: "John Doe" },
      recipients: []
    }
  ], []);

  // <-- CHANGE: Wrapped in useCallback
  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      
      // NOTE: Reports API endpoints are not yet implemented in the backend
      // When available, the implementation would be:
      /*
      const response = await api.reports.list({ 
        project_id: currentProject?.id,
        organization_id: organization?.id 
      });
      
      const reportsList = response.data.items || response.data;
      setReports(reportsList.map((report: any) => ({
        id: report.id,
        name: report.name,
        description: report.description,
        type: report.report_type || report.type,
        status: report.status,
        frequency: report.frequency,
        created_at: report.created_at,
        updated_at: report.updated_at,
        created_by: {
          id: report.created_by_id || report.user_id,
          name: report.created_by_name || report.user?.name || 'Unknown'
        },
        last_run: report.last_run_at,
        next_run: report.next_run_at,
        recipients: report.recipients || []
      })));
      */
      
      // Using mock data until backend is ready
      setTimeout(() => {
        setReports(mockReports);
        setLoading(false);
      }, 1000);
    } catch (error) {
      console.error("Failed to fetch reports:", error);
      toast({
        title: "Error",
        description: "Failed to load reports",
        variant: "destructive"
      });
      setLoading(false);
    }
  }, [toast, mockReports]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports, currentProject]); // <-- CHANGE: Updated dependency array

  const handleCreateReport = async () => {
    try {
      // NOTE: Reports API endpoints are not yet implemented in the backend
      // When available, the implementation would be:
      /*
      const response = await api.reports.create({
        ...reportConfig,
        project_id: currentProject?.id,
        organization_id: organization?.id
      });
      */
      
      // Mock implementation until backend is ready
      toast({
        title: "Report created",
        description: "Your report has been created successfully",
      });
      setCreateModalOpen(false);
      fetchReports();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create report",
        variant: "destructive"
      });
    }
  };

  const handleDeleteReport = async () => {
    if (!selectedReport) return;
    
    try {
      // NOTE: Reports API endpoints are not yet implemented in the backend
      // When available, the implementation would be:
      // await api.reports.delete(selectedReport.id);
      
      // Mock implementation until backend is ready
      toast({
        title: "Report deleted",
        description: "The report has been deleted successfully",
      });
      setDeleteModalOpen(false);
      setSelectedReport(null);
      fetchReports();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete report",
        variant: "destructive"
      });
    }
  };

  const handleShareReport = async (reportId: string) => {
    try {
      // Generate shareable link
      const link = `${window.location.origin}/reports/${reportId}`;
      await navigator.clipboard.writeText(link);
      toast({
        title: "Link copied",
        description: "Report link has been copied to clipboard",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to copy link",
        variant: "destructive"
      });
    }
  };

  const getReportTypeIcon = (type: string) => {
    switch (type) {
      case "seo":
        return <Search className="h-4 w-4" />;
      case "performance":
        return <TrendingUp className="h-4 w-4" />;
      case "competitor":
        return <Users className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "published":
        return <Badge variant="default">Published</Badge>;
      case "scheduled":
        return <Badge variant="secondary">Scheduled</Badge>;
      case "draft":
        return <Badge variant="outline">Draft</Badge>;
      default:
        return null;
    }
  };

  const getFrequencyBadge = (frequency?: string) => {
    if (!frequency) return null;
    return (
      <Badge variant="outline" className="ml-2">
        <Clock className="h-3 w-3 mr-1" />
        {frequency.charAt(0).toUpperCase() + frequency.slice(1)}
      </Badge>
    );
  };

  const filteredReports = reports.filter(report => {
    if (searchTerm && !report.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !report.description?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    
    if (selectedFilters.type?.length > 0 && !selectedFilters.type.includes(report.type)) {
      return false;
    }
    
    if (selectedFilters.status?.length > 0 && !selectedFilters.status.includes(report.status)) {
      return false;
    }
    
    return true;
  });

  const sortedReports = [...filteredReports].sort((a, b) => {
    switch (sortBy) {
      case "name":
        return a.name.localeCompare(b.name);
      case "created_at":
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      case "updated_at":
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      default:
        return 0;
    }
  });

  const wizardSteps = [
    {
      id: "details",
      title: "Report Details",
      content: (
        <div className="space-y-4">
          <div>
            <Label htmlFor="name">Report Name</Label>
            <Input
              id="name"
              value={reportConfig.name}
              onChange={(e) => setReportConfig({ ...reportConfig, name: e.target.value })}
              placeholder="Monthly SEO Report"
              required
            />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={reportConfig.description}
              onChange={(e) => setReportConfig({ ...reportConfig, description: e.target.value })}
              placeholder="Brief description of the report"
            />
          </div>
          <div>
            <Label htmlFor="type">Report Type</Label>
            <Select 
              value={reportConfig.type} 
              onValueChange={(value) => setReportConfig({ ...reportConfig, type: value })}
            >
              <SelectTrigger id="type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="seo">SEO Performance</SelectItem>
                <SelectItem value="performance">Site Performance</SelectItem>
                <SelectItem value="competitor">Competitor Analysis</SelectItem>
                <SelectItem value="custom">Custom Report</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      )
    },
    {
      id: "metrics",
      title: "Configure Metrics",
      content: (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Select the metrics and data points to include in your report
          </p>
          <div className="grid grid-cols-2 gap-4">
            {["Rankings", "Traffic", "Conversions", "Core Web Vitals", "Backlinks", "Keywords"].map(metric => (
              <label key={metric} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={reportConfig.metrics.includes(metric)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setReportConfig({ 
                        ...reportConfig, 
                        metrics: [...reportConfig.metrics, metric] 
                      });
                    } else {
                      setReportConfig({ 
                        ...reportConfig, 
                        metrics: reportConfig.metrics.filter(m => m !== metric) 
                      });
                    }
                  }}
                  className="rounded border-gray-300"
                />
                <span className="text-sm">{metric}</span>
              </label>
            ))}
          </div>
        </div>
      )
    },
    {
      id: "schedule",
      title: "Schedule & Recipients",
      content: (
        <div className="space-y-4">
          <div>
            <Label htmlFor="frequency">Frequency</Label>
            <Select 
              value={reportConfig.frequency} 
              onValueChange={(value) => setReportConfig({ ...reportConfig, frequency: value })}
            >
              <SelectTrigger id="frequency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="one-time">One-time</SelectItem>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {reportConfig.frequency !== "one-time" && (
            <div>
              <Label htmlFor="time">Delivery Time</Label>
              <Input
                id="time"
                type="time"
                value={reportConfig.schedule.time}
                onChange={(e) => setReportConfig({
                  ...reportConfig,
                  schedule: { ...reportConfig.schedule, time: e.target.value }
                })}
              />
            </div>
          )}
          <div>
            <Label htmlFor="recipients">Email Recipients</Label>
            <Input
              id="recipients"
              placeholder="email@example.com (comma separated)"
              value={reportConfig.recipients.join(", ")}
              onChange={(e) => setReportConfig({
                ...reportConfig,
                recipients: e.target.value.split(",").map(email => email.trim()).filter(Boolean)
              })}
            />
          </div>
        </div>
      )
    }
  ];

  return (
    <AdminGuard>
      <>
        <ListLayout
        title="Reports"
        searchPlaceholder="Search reports..."
        onSearch={setSearchTerm}
        filters={[
          {
            id: "type",
            label: "Type",
            type: "multiselect",
            options: [
              { id: "seo", label: "SEO Performance", value: "seo" },
              { id: "performance", label: "Site Performance", value: "performance" },
              { id: "competitor", label: "Competitor Analysis", value: "competitor" },
              { id: "custom", label: "Custom", value: "custom" },
            ],
          },
          {
            id: "status",
            label: "Status",
            type: "multiselect",
            options: [
              { id: "published", label: "Published", value: "published" },
              { id: "scheduled", label: "Scheduled", value: "scheduled" },
              { id: "draft", label: "Draft", value: "draft" },
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
          { id: "updated_at", label: "Last Updated", value: "updated_at" },
          { id: "created_at", label: "Date Created", value: "created_at" },
          { id: "name", label: "Name", value: "name" },
        ]}
        selectedSort={sortBy}
        onSortChange={setSortBy}
        actions={[
          {
            label: "Create Report",
            onClick: () => {
              setReportConfig({
                name: "",
                description: "",
                type: "seo",
                frequency: "one-time",
                metrics: [],
                filters: {},
                recipients: [],
                schedule: {
                  time: "09:00",
                  dayOfWeek: 1,
                  dayOfMonth: 1,
                }
              });
              setCreateModalOpen(true);
            },
            icon: Plus,
          },
        ]}
        emptyState={{
          icon: FileText,
          title: "No reports found",
          message: searchTerm
            ? "No reports match your search criteria"
            : "Create your first report to start tracking performance",
          action: !searchTerm ? {
            label: "Create Your First Report",
            onClick: () => setCreateModalOpen(true),
          } : undefined,
        }}
      >
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-5 bg-muted rounded w-3/4 mb-2"></div>
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
            {sortedReports.map((report) => (
              <Card
                key={report.id}
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/reports/${report.id}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="flex items-center gap-2 text-base">
                        {getReportTypeIcon(report.type)}
                        {report.name}
                      </CardTitle>
                      {report.description && (
                        <CardDescription className="mt-1 line-clamp-2">
                          {report.description}
                        </CardDescription>
                      )}
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="sm">
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/reports/${report.id}`);
                        }}>
                          <Eye className="h-4 w-4 mr-2" />
                          View Report
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => {
                          e.stopPropagation();
                          handleShareReport(report.id);
                        }}>
                          <Share2 className="h-4 w-4 mr-2" />
                          Share
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => {
                          e.stopPropagation();
                          // Download report
                        }}>
                          <Download className="h-4 w-4 mr-2" />
                          Download
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          className="text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedReport(report);
                            setDeleteModalOpen(true);
                          }}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      {getStatusBadge(report.status)}
                      {getFrequencyBadge(report.frequency)}
                    </div>
                    
                    <div className="text-sm text-muted-foreground space-y-1">
                      <div className="flex items-center gap-2">
                        <Users className="h-3 w-3" />
                        <span>Created by {report.created_by.name}</span>
                      </div>
                      {report.last_run && (
                        <div className="flex items-center gap-2">
                          <Clock className="h-3 w-3" />
                          <span>Last run: {new Date(report.last_run).toLocaleDateString()}</span>
                        </div>
                      )}
                      {report.recipients && report.recipients.length > 0 && (
                        <div className="flex items-center gap-2">
                          <Share2 className="h-3 w-3" />
                          <span>{report.recipients.length} recipients</span>
                        </div>
                      )}
                    </div>

                    {report.next_run && (
                      <div className="pt-2 border-t">
                        <p className="text-xs text-muted-foreground">
                          Next run: {new Date(report.next_run).toLocaleDateString()}
                        </p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </ListLayout>

      {/* Create Report Wizard */}
      <WizardModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        title="Create New Report"
        steps={wizardSteps}
        onComplete={handleCreateReport}
      />

      {/* Delete Confirmation Modal */}
      <ConfirmActionModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        onConfirm={handleDeleteReport}
        type="danger"
        title="Delete Report?"
        message={`Are you sure you want to delete ${selectedReport?.name}? This action cannot be undone.`}
        confirmLabel="Delete Report"
      />
      </>
    </AdminGuard>
  );
}