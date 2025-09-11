"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { 
  ArrowLeft, Activity, Filter, Calendar, User as UserIcon, 
  Clock, FileText, Download, Search, ChevronDown,
  Shield, UserPlus, UserMinus, Settings, FolderOpen,
  Edit, Trash2, Mail, Building
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api-client";
import { Organization, AuditLog, OrganizationMember, User } from "@/types/api";
import { useAuth } from "@/lib/auth-context";

type ActionType = "all" | "organization" | "member" | "project" | "invitation" | "settings";
type DateRange = "all" | "today" | "week" | "month" | "custom";

export default function OrganizationAuditLogsPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [actionType, setActionType] = useState<ActionType>("all");
  const [dateRange, setDateRange] = useState<DateRange>("all");
  const [selectedUser, setSelectedUser] = useState<string>("all");
  
  const organizationId = params.id as string;

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [orgResponse, logsResponse] = await Promise.all([
        api.organizations.get(organizationId),
        api.organizations.getAuditLogs(organizationId),
      ]);
      
      // Check permissions
      const org = orgResponse.data;
      const member = org.members?.find((m: OrganizationMember) => m.user_id === user?.id);
      const role = member?.role;
      
      if (role !== "owner" && role !== "admin") {
        router.push(`/organizations/${organizationId}`);
        return;
      }
      
      setOrganization(org);
      setAuditLogs(logsResponse.data);
    } catch (error) {
      console.error("Failed to fetch data:", error);
      router.push("/organizations");
    } finally {
      setLoading(false);
    }
  }, [organizationId, user?.id, router]);

  useEffect(() => {
    if (organizationId) {
      fetchData();
    }
  }, [organizationId, fetchData]);

  const getActionIcon = (action: string) => {
    if (action.includes("organization")) return <Building className="h-4 w-4" />;
    if (action.includes("member") || action.includes("user")) return <UserIcon className="h-4 w-4" />;
    if (action.includes("project")) return <FolderOpen className="h-4 w-4" />;
    if (action.includes("invitation")) return <Mail className="h-4 w-4" />;
    if (action.includes("settings")) return <Settings className="h-4 w-4" />;
    if (action.includes("role")) return <Shield className="h-4 w-4" />;
    if (action.includes("delete") || action.includes("remove")) return <Trash2 className="h-4 w-4" />;
    if (action.includes("edit") || action.includes("update")) return <Edit className="h-4 w-4" />;
    if (action.includes("create") || action.includes("add")) return <UserPlus className="h-4 w-4" />;
    return <Activity className="h-4 w-4" />;
  };

  const getActionColor = (action: string) => {
    if (action.includes("delete") || action.includes("remove")) return "text-destructive";
    if (action.includes("create") || action.includes("add")) return "text-green-600";
    if (action.includes("update") || action.includes("edit")) return "text-blue-600";
    return "text-muted-foreground";
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getRelativeTime = (date: string) => {
    const now = new Date();
    const then = new Date(date);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays < 7) return `${diffDays} days ago`;
    return formatDate(date);
  };

  const handleExportLogs = async () => {
    try {
      setDownloading(true);
      // In a real app, this would download a CSV or JSON file
      const data = JSON.stringify(filteredLogs, null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${organizationId}-${new Date().toISOString()}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Failed to export logs:", error);
    } finally {
      setDownloading(false);
    }
  };

  // Get unique users for filter
  const uniqueUsers = Array.from(new Set(auditLogs.map((log) => log.user?.id)))
    .map((userId) => auditLogs.find((log) => log.user?.id === userId)?.user)
    .filter((user): user is User => Boolean(user));

  // Filter logs
  const filteredLogs = auditLogs.filter((log) => {
    // Search filter
    if (searchTerm && !log.action.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !log.details?.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !log.user?.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !log.user?.email?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }

    // Action type filter
    if (actionType !== "all") {
      if (actionType === "organization" && !log.action.includes("organization")) return false;
      if (actionType === "member" && !log.action.includes("member") && !log.action.includes("user")) return false;
      if (actionType === "project" && !log.action.includes("project")) return false;
      if (actionType === "invitation" && !log.action.includes("invitation")) return false;
      if (actionType === "settings" && !log.action.includes("settings")) return false;
    }

    // User filter
    if (selectedUser !== "all" && log.user?.id !== selectedUser) {
      return false;
    }

    // Date filter
    if (dateRange !== "all") {
      const logDate = new Date(log.created_at);
      const now = new Date();
      
      if (dateRange === "today") {
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        if (logDate < today) return false;
      } else if (dateRange === "week") {
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        if (logDate < weekAgo) return false;
      } else if (dateRange === "month") {
        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        if (logDate < monthAgo) return false;
      }
    }

    return true;
  });

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-muted rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-20 bg-muted rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!organization) {
    return null;
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/organizations/${organizationId}`)}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <Separator orientation="vertical" className="h-6" />
          <div>
            <h1 className="text-2xl font-bold">Audit Logs</h1>
            <p className="text-muted-foreground">{organization.name}</p>
          </div>
        </div>
        
        <Button
          variant="outline"
          onClick={handleExportLogs}
          disabled={downloading || filteredLogs.length === 0}
        >
          <Download className="h-4 w-4 mr-2" />
          Export Logs
        </Button>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Filter audit logs by action type, user, or date range
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search logs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Action Type</Label>
              <Select value={actionType} onValueChange={(value) => setActionType(value as ActionType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  <SelectItem value="organization">Organization</SelectItem>
                  <SelectItem value="member">Members</SelectItem>
                  <SelectItem value="project">Projects</SelectItem>
                  <SelectItem value="invitation">Invitations</SelectItem>
                  <SelectItem value="settings">Settings</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>User</Label>
              <Select value={selectedUser} onValueChange={setSelectedUser}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Users</SelectItem>
                  {uniqueUsers.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.full_name || user.email}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Date Range</Label>
              <Select value={dateRange} onValueChange={(value) => setDateRange(value as DateRange)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Time</SelectItem>
                  <SelectItem value="today">Today</SelectItem>
                  <SelectItem value="week">Last 7 Days</SelectItem>
                  <SelectItem value="month">Last 30 Days</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Activity Log ({filteredLogs.length})</CardTitle>
          <CardDescription>
            All actions performed in this organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredLogs.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No audit logs found matching your filters</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredLogs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-start gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className={`mt-1 ${getActionColor(log.action)}`}>
                    {getActionIcon(log.action)}
                  </div>
                  
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">
                        {log.user?.full_name || log.user?.email || "System"}
                      </p>
                      <span className="text-muted-foreground">•</span>
                      <span className="text-sm text-muted-foreground">
                        {getRelativeTime(log.created_at)}
                      </span>
                    </div>
                    
                    <p className="text-sm">
                      {log.action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </p>
                    
                    {log.details && (
                      <p className="text-sm text-muted-foreground">
                        {typeof log.details === 'string' ? log.details : JSON.stringify(log.details)}
                      </p>
                    )}
                    
                    {log.metadata && (
                      <div className="flex gap-2 mt-2">
                        {Object.entries(log.metadata).map(([key, value]) => (
                          <Badge key={key} variant="outline" className="text-xs">
                            {key}: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <div className="text-xs text-muted-foreground">
                    <p>{formatDate(log.created_at)}</p>
                    {log.ip_address && (
                      <p className="mt-1">IP: {log.ip_address}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}