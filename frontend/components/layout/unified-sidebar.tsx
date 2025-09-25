'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { routeGroups } from '@/lib/routes';
import * as Icons from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { useProject } from '@/lib/project-context';
import { useWebSocketSync } from '@/lib/websocket-sync';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import {
  Building2,
  ChevronDown,
  Check,
  ChevronsUpDown,
  Plus,
  LogOut,
  Power,
  RefreshCw,
  Clock,
  PanelLeftClose,
  PanelLeftOpen
} from 'lucide-react';
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
import { Separator } from '@/components/ui/separator';
import { EntityModal } from '@/components/ui/entity-modal';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import { api } from '@/lib/api-client';
import { ThemeToggle } from '@/components/theme-toggle';
import { SearchBar } from '@/components/search-bar';
import { ProjectSelector } from '@/components/project-selector';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Bell, User, Settings, FolderOpen, Globe, Users, CreditCard, Shield, Sparkles } from 'lucide-react';

export function UnifiedSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const { isConnected } = useWebSocketSync();
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

  // Responsive collapse state (matching original sidebar)
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Accordion state for navigation sections
  const [openSections, setOpenSections] = useState<string[]>([]);

  // Modal states for organization creation
  const [orgModalOpen, setOrgModalOpen] = useState(false);
  const [orgPopoverOpen, setOrgPopoverOpen] = useState(false);
  const [projectPopoverOpen, setProjectPopoverOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [orgFormData, setOrgFormData] = useState({ name: '', description: '' });

  // Session timer state
  const [sessionTime, setSessionTime] = useState('9 min 5s');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Auto-collapse on mobile (matching original sidebar functionality)
  useEffect(() => {
    const handleResize = () => {
      setIsCollapsed(window.innerWidth < 1024);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Update session timer (mock implementation)
  useEffect(() => {
    const interval = setInterval(() => {
      // This would typically come from your auth context or session management
      const now = new Date();
      const minutes = now.getMinutes() % 10;
      const seconds = now.getSeconds();
      setSessionTime(`${minutes} min ${seconds}s`);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Function to check if user has access to a route
  const hasAccess = (item: any) => {
    if (!user) return false;

    // If no roles specified, allow all authenticated users
    if (!item.roles || item.roles.length === 0) return true;

    // Check if user is admin for admin-only routes
    if (item.adminOnly && !user.is_superuser) return false;

    // Check role-based access
    const userRole = user.is_superuser ? 'admin' : 'user';
    return item.roles.includes(userRole);
  };

  // Filter navigation items based on user access
  const getFilteredItems = (items: readonly any[]) => {
    return items
      .map((item: any) => ({
        ...item,
        icon: Icons[item.icon as keyof typeof Icons] as any,
      }))
      .filter(hasAccess);
  };

  // Navigation sections matching original sidebar structure
  const navigationSections = [
    {
      title: 'MAIN MENU',
      items: getFilteredItems(routeGroups.overview),
      isCollapsible: false, // Always show main menu
    },
    {
      title: 'CORE PILLARS',
      items: getFilteredItems(routeGroups.corePillars),
      isCollapsible: true,
    },
    {
      title: 'INTEGRATIONS',
      items: getFilteredItems(routeGroups.integrations),
      isCollapsible: true,
    },
  ];

  // Add admin section only if user is superuser
  if (user?.is_superuser && routeGroups.admin) {
    navigationSections.push({
      title: 'ADMINISTRATION',
      items: getFilteredItems(routeGroups.admin),
      isCollapsible: true,
    });
  }

  // Filter out empty sections
  const filteredNavigationSections = navigationSections.filter(section => section.items.length > 0);

  // Determine which section should be open by default based on current path
  const getDefaultOpenSections = () => {
    const defaultSections: string[] = [];
    filteredNavigationSections.forEach(section => {
      if (section.isCollapsible && section.items.some(item => pathname === item.href)) {
        defaultSections.push(section.title);
      }
    });
    return defaultSections;
  };

  // Initialize accordion state with the section containing the active page
  useEffect(() => {
    if (openSections.length === 0) {
      setOpenSections(getDefaultOpenSections());
    }
  }, [pathname]);

  // Toggle accordion section
  const toggleSection = (sectionTitle: string) => {
    setOpenSections(prev =>
      prev.includes(sectionTitle)
        ? prev.filter(title => title !== sectionTitle)
        : [...prev, sectionTitle]
    );
  };

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

  const handleRefreshSession = async () => {
    setIsRefreshing(true);
    // Simulate session refresh
    setTimeout(() => {
      setIsRefreshing(false);
      toast({
        title: 'Session refreshed',
        description: 'Your session has been extended.',
      });
    }, 1000);
  };

  if (isLoading) {
    return (
      <div className="w-80 h-screen bg-card/90 backdrop-blur-xl border-r border-border/40 animate-pulse">
        <div className="p-6">
          <div className="h-12 bg-muted rounded-lg mb-6" />
          <div className="space-y-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-10 bg-muted rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className={cn(
        "flex flex-col bg-card rounded-xl shadow-xl relative transition-all duration-300 m-4 overflow-hidden",
        "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.1),0_4px_6px_-1px_rgba(0,0,0,0.1),0_2px_4px_-1px_rgba(0,0,0,0.06)]",
        "dark:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05),0_8px_25px_-5px_rgba(0,0,0,0.3),0_4px_6px_-2px_rgba(0,0,0,0.05)]",
        isCollapsed ? "w-20" : "w-80"
      )}
      style={{ height: "calc(100vh - 32px)" }}
      animate={{ width: isCollapsed ? 80 : 320 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
    >

      {/* Header Section (Top) */}
      <div className={cn(
        "shrink-0 relative after:absolute after:bottom-0 after:left-0 after:right-0 after:h-px after:bg-gradient-to-r after:from-transparent after:via-border/60 after:to-transparent after:shadow-sm",
        isCollapsed ? "p-4" : "p-8"
      )}>
        {/* Enhanced Logo Section with Collapse Support */}
        <div className="flex items-center justify-between w-full relative">
          <motion.div
            className="flex items-center space-x-4 group"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Logo */}
            <div className="flex items-center space-x-1">
              <Image
                src="/serptank-orb-logo.svg"
                alt="SerpTank"
                width={55}
                height={55}
                className="w-[55px] h-[55px] object-contain transition-all duration-300 group-hover:scale-110"
              />
              {!isCollapsed && (
                <h1 className="text-xl font-bold tracking-tight text-foreground">SerpTank</h1>
              )}
            </div>
          </motion.div>

          <div className="flex items-center space-x-2">
            {user?.is_superuser && !isCollapsed && (
              <Badge variant="secondary" className="text-xs neon-glow-green">
                <Icons.Shield className="mr-1 h-3 w-3" />
                Admin
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="h-8 w-8 p-0 hover:bg-accent/40 transition-colors duration-200"
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? (
                <PanelLeftOpen className="h-4 w-4" />
              ) : (
                <PanelLeftClose className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

      </div>


      {/* Navigation Menu */}
      <nav className={cn(
        "flex-1 overflow-y-auto py-6 relative bg-gradient-to-b from-background/30 to-background/10 backdrop-blur-sm",
        isCollapsed ? "px-2" : "px-8"
      )}>
        {/* Hierarchical Project Selector Pill */}
        {!isCollapsed && (
          <div className="bg-muted rounded-lg mb-6">
            <ProjectSelector />
          </div>
        )}

        <div className="space-y-4">
          {filteredNavigationSections.map((section, sectionIndex) => (
            <motion.div
              key={section.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: sectionIndex * 0.1 }}
            >
              {!isCollapsed && (
                <div>
                  {/* Section Header */}
                  {section.isCollapsible ? (
                    <button
                      onClick={() => toggleSection(section.title)}
                      className="flex items-center justify-between w-full mb-3 px-3 text-[12px] font-bold uppercase tracking-wide text-muted-foreground/70 hover:text-muted-foreground transition-colors duration-200 font-montserrat"
                    >
                      <span>{section.title}</span>
                      <Icons.ChevronDown
                        className={cn(
                          "h-3 w-3 transition-transform duration-300 ease-in-out",
                          openSections.includes(section.title) ? "rotate-90" : ""
                        )}
                      />
                    </button>
                  ) : (
                    <h3 className="mb-3 px-3 text-[12px] font-bold uppercase tracking-wide text-muted-foreground/70 font-montserrat">
                      {section.title}
                    </h3>
                  )}

                  {/* Section Content */}
                  <div className={cn(
                    "transition-all duration-300 ease-in-out",
                    !section.isCollapsible || openSections.includes(section.title)
                      ? "max-h-[1000px] opacity-100"
                      : "max-h-0 opacity-0 overflow-hidden"
                  )}>
                    <div className="space-y-1 pb-2">
                      {section.items.map((item, itemIndex) => {
                        const isActive = pathname === item.href;
                        return (
                          <motion.div
                            key={item.name}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.3, delay: (sectionIndex * 0.1) + (itemIndex * 0.05) }}
                            whileHover={{ x: 4 }}
                          >
                            <Link
                              href={item.href}
                              className={cn(
                                'flex items-center rounded-xl transition-all duration-200 group focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-offset-2 focus:ring-offset-background',
                                'px-3 py-2.5 text-sm font-medium mx-2 my-0.5 font-inter',
                                isActive
                                  ? 'bg-gradient-to-r from-green-500/25 via-green-400/20 to-green-500/15 text-green-700 dark:text-green-300 shadow-md border border-green-500/40 shadow-green-500/10'
                                  : 'text-muted-foreground hover:bg-gradient-to-r hover:from-blue-500/15 hover:via-blue-400/10 hover:to-blue-500/8 hover:text-foreground hover:shadow-md hover:border hover:border-blue-500/20 hover:shadow-blue-500/5'
                              )}
                            >
                              <div className={cn(
                                "h-5 w-5 mr-3 transition-all duration-300 group-hover:-translate-y-0.5",
                                isActive
                                  ? "text-green-600 dark:text-green-400 drop-shadow-sm"
                                  : "text-muted-foreground group-hover:text-foreground"
                              )}>
                                <item.icon className="h-full w-full" />
                              </div>
                              <span className="flex-1 transition-all duration-300 group-hover:text-foreground group-hover:brightness-110">{item.name}</span>
                              {item.adminOnly && (
                                <Badge variant="outline" className="ml-auto text-xs">
                                  Admin
                                </Badge>
                              )}
                            </Link>
                          </motion.div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Collapsed state - show all items as icons */}
              {isCollapsed && (
                <div className="space-y-1">
                  {section.items.map((item, itemIndex) => {
                    const isActive = pathname === item.href;
                    return (
                      <motion.div
                        key={item.name}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: (sectionIndex * 0.1) + (itemIndex * 0.05) }}
                        whileHover={{ x: 4 }}
                      >
                        <Link
                          href={item.href}
                          className={cn(
                            'flex items-center rounded-xl transition-all duration-200 group focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-offset-2 focus:ring-offset-background',
                            'p-2.5 justify-center mx-2 my-0.5',
                            isActive
                              ? 'bg-gradient-to-r from-green-500/25 via-green-400/20 to-green-500/15 text-green-700 dark:text-green-300 shadow-md border border-green-500/40 shadow-green-500/10'
                              : 'text-muted-foreground hover:bg-gradient-to-r hover:from-blue-500/15 hover:via-blue-400/10 hover:to-blue-500/8 hover:text-foreground hover:shadow-md hover:border hover:border-blue-500/20 hover:shadow-blue-500/5'
                          )}
                          title={item.name}
                        >
                          <div className={cn(
                            "h-5 w-5 transition-all duration-300 group-hover:-translate-y-0.5",
                            isActive
                              ? "text-green-600 dark:text-green-400 drop-shadow-sm"
                              : "text-muted-foreground group-hover:text-foreground"
                          )}>
                            <item.icon className="h-full w-full" />
                          </div>
                        </Link>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </nav>

      {/* User Section (Bottom) */}
      <div className={cn(
        "shrink-0 relative before:absolute before:top-0 before:left-0 before:right-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-border/40 before:to-transparent before:shadow-sm",
        isCollapsed ? "p-4" : "p-8"
      )}>
        {!isCollapsed ? (
          <div className="flex items-center justify-between">
            {/* User Info */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex items-center space-x-3 p-0 h-auto w-auto bg-transparent hover:bg-transparent border-0"
                >
                  <div className="h-10 w-10 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-semibold text-sm">
                    {user?.username?.[0]?.toUpperCase() || 'U'}
                  </div>
                  <div className="flex-1 min-w-0 text-left">
                    <div className="font-medium text-sm text-foreground">
                      {user?.username || 'User'}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Session ends in {sessionTime}
                    </div>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-64">
                <DropdownMenuLabel className="font-semibold">My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="font-semibold text-muted-foreground">Management</DropdownMenuLabel>

                <DropdownMenuItem asChild>
                  <Link href="/organizations" className="flex items-center py-2 px-3">
                    <Building2 className="mr-2 h-4 w-4" />
                    <span>Organizations</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/projects" className="flex items-center py-2 px-3">
                    <FolderOpen className="mr-2 h-4 w-4" />
                    <span>Projects</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/sites" className="flex items-center py-2 px-3">
                    <Globe className="mr-2 h-4 w-4" />
                    <span>Sites</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/team" className="flex items-center py-2 px-3">
                    <Users className="mr-2 h-4 w-4" />
                    <span>Team</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/billing" className="flex items-center py-2 px-3">
                    <CreditCard className="mr-2 h-4 w-4" />
                    <span>Billing</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuSeparator />

                <DropdownMenuItem asChild>
                  <Link href="/settings" className="flex items-center py-2 px-3">
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Settings</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="flex items-center text-destructive py-2 px-3">
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Green Power Button */}
            <Button
              size="sm"
              onClick={logout}
              className="h-10 w-10 p-0 bg-green-600 hover:bg-green-700 text-white rounded-lg shadow-sm"
              title="Logout"
            >
              <Power className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div className="flex justify-center">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="p-3 h-auto w-auto bg-muted/30 hover:bg-muted/50 rounded-lg"
                >
                  <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-semibold text-sm">
                    {user?.username?.[0]?.toUpperCase() || 'U'}
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="center" className="w-64">
                <DropdownMenuLabel className="font-semibold">My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="font-semibold text-muted-foreground">Management</DropdownMenuLabel>

                <DropdownMenuItem asChild>
                  <Link href="/organizations" className="flex items-center py-2 px-3">
                    <Building2 className="mr-2 h-4 w-4" />
                    <span>Organizations</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/projects" className="flex items-center py-2 px-3">
                    <FolderOpen className="mr-2 h-4 w-4" />
                    <span>Projects</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/sites" className="flex items-center py-2 px-3">
                    <Globe className="mr-2 h-4 w-4" />
                    <span>Sites</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/team" className="flex items-center py-2 px-3">
                    <Users className="mr-2 h-4 w-4" />
                    <span>Team</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link href="/billing" className="flex items-center py-2 px-3">
                    <CreditCard className="mr-2 h-4 w-4" />
                    <span>Billing</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuSeparator />

                <DropdownMenuItem asChild>
                  <Link href="/settings" className="flex items-center py-2 px-3">
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Settings</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="flex items-center text-destructive py-2 px-3">
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}

        {/* Real-time Connected Status */}
        <div className="flex justify-center mt-3">
          {!isCollapsed ? (
            <Badge
              variant={isConnected ? "default" : "secondary"}
              className={cn(
                "text-xs px-3 py-1 rounded-full",
                isConnected
                  ? "bg-blue-500/20 text-blue-700 dark:text-blue-300 border border-blue-500/30"
                  : "bg-gray-500/20 text-gray-700 dark:text-gray-300 border border-gray-500/30"
              )}
            >
              <div className={cn(
                "w-2 h-2 rounded-full mr-2",
                isConnected ? "bg-blue-500 animate-pulse" : "bg-gray-500"
              )} />
              {isConnected ? "Real-time Connected" : "Real-time Disconnected"}
            </Badge>
          ) : (
            <div
              className={cn(
                "w-3 h-3 rounded-full",
                isConnected ? "bg-blue-500 animate-pulse" : "bg-gray-500"
              )}
              title={isConnected ? "Real-time Connected" : "Real-time Disconnected"}
            />
          )}
        </div>

      </div>

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
    </motion.div>
  );
}