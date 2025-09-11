'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Search, 
  Home, 
  Building2, 
  Globe, 
  FolderOpen, 
  BarChart3, 
  Settings, 
  FileText,
  Monitor,
  Plus,
  ArrowRight,
  Clock,
  Star,
  Command as CommandIcon,
  User,
  Shield,
  Key,
  Bell,
  CreditCard,
  Link,
  Users,
  TrendingUp,
  FileSearch,
  Youtube,
  Share2,
  AlertCircle,
  Activity,
  Package,
  HelpCircle
} from 'lucide-react';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '@/components/ui/command';
import { useModals } from '@/lib/modal-context';
import { api } from '@/lib/api-client';
import { useDebounce } from '@/lib/hooks/use-debounce';
import { cn } from '@/lib/utils';

interface CommandOption {
  id: string;
  label: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  shortcut?: string;
  action: () => void;
  keywords?: string[];
  category: 'navigation' | 'action' | 'search' | 'recent' | 'help';
}

interface SearchResult {
  id: string;
  title: string;
  subtitle?: string;
  type: 'organization' | 'site' | 'project' | 'user' | 'report' | 'keyword' | 'page';
  url?: string;
  icon?: React.ComponentType<{ className?: string }>;
}

// Icon mapping for different entity types
const ENTITY_ICONS = {
  organization: Building2,
  site: Globe,
  project: FolderOpen,
  user: User,
  report: FileText,
  keyword: TrendingUp,
  page: FileSearch,
};

// Navigation options
const NAVIGATION_OPTIONS: CommandOption[] = [
  {
    id: 'nav-dashboard',
    label: 'Dashboard',
    description: 'Go to dashboard',
    icon: Home,
    shortcut: '⌘D',
    action: () => window.location.href = '/dashboard',
    keywords: ['home', 'overview'],
    category: 'navigation',
  },
  {
    id: 'nav-organizations',
    label: 'Organizations',
    description: 'View all organizations',
    icon: Building2,
    shortcut: '⌘O',
    action: () => window.location.href = '/organizations',
    keywords: ['orgs', 'companies'],
    category: 'navigation',
  },
  {
    id: 'nav-sites',
    label: 'Sites',
    description: 'Manage your sites',
    icon: Globe,
    shortcut: '⌘S',
    action: () => window.location.href = '/sites',
    keywords: ['websites', 'domains'],
    category: 'navigation',
  },
  {
    id: 'nav-projects',
    label: 'Projects',
    description: 'View all projects',
    icon: FolderOpen,
    shortcut: '⌘P',
    action: () => window.location.href = '/projects',
    keywords: ['workspaces'],
    category: 'navigation',
  },
  {
    id: 'nav-analytics-seo',
    label: 'SEO Analytics',
    description: 'SEO performance overview',
    icon: BarChart3,
    action: () => window.location.href = '/analytics/seo',
    keywords: ['seo', 'search', 'performance'],
    category: 'navigation',
  },
  {
    id: 'nav-analytics-search-console',
    label: 'Search Console',
    description: 'Google Search Console data',
    icon: Search,
    action: () => window.location.href = '/analytics/search-console',
    keywords: ['gsc', 'google'],
    category: 'navigation',
  },
  {
    id: 'nav-analytics-competitors',
    label: 'Competitor Analysis',
    description: 'Analyze your competition',
    icon: TrendingUp,
    action: () => window.location.href = '/analytics/competitors',
    keywords: ['serp', 'competition'],
    category: 'navigation',
  },
  {
    id: 'nav-analytics-content',
    label: 'Content Analysis',
    description: 'Content optimization insights',
    icon: FileText,
    action: () => window.location.href = '/analytics/content',
    keywords: ['content', 'optimization'],
    category: 'navigation',
  },
  {
    id: 'nav-analytics-trends',
    label: 'Trends & Social',
    description: 'Google Trends, YouTube, Social Media',
    icon: Share2,
    action: () => window.location.href = '/analytics/trends',
    keywords: ['trends', 'youtube', 'social'],
    category: 'navigation',
  },
  {
    id: 'nav-reports',
    label: 'Reports',
    description: 'View and manage reports',
    icon: FileText,
    action: () => window.location.href = '/reports',
    keywords: ['documents', 'exports'],
    category: 'navigation',
  },
  {
    id: 'nav-monitoring',
    label: 'Monitoring',
    description: 'System health and performance',
    icon: Monitor,
    action: () => window.location.href = '/monitoring',
    keywords: ['health', 'performance', 'tasks'],
    category: 'navigation',
  },
  {
    id: 'nav-settings',
    label: 'Settings',
    description: 'Application settings',
    icon: Settings,
    shortcut: '⌘,',
    action: () => window.location.href = '/settings',
    keywords: ['preferences', 'configuration'],
    category: 'navigation',
  },
];

// Action options
const ACTION_OPTIONS: CommandOption[] = [
  {
    id: 'action-create-organization',
    label: 'Create Organization',
    description: 'Create a new organization',
    icon: Plus,
    action: () => {}, // Will be set dynamically
    keywords: ['new', 'add', 'organization'],
    category: 'action',
  },
  {
    id: 'action-create-site',
    label: 'Add Site',
    description: 'Add a new site to monitor',
    icon: Plus,
    action: () => {}, // Will be set dynamically
    keywords: ['new', 'add', 'site', 'website'],
    category: 'action',
  },
  {
    id: 'action-create-project',
    label: 'Create Project',
    description: 'Start a new project',
    icon: Plus,
    action: () => {}, // Will be set dynamically
    keywords: ['new', 'add', 'project'],
    category: 'action',
  },
  {
    id: 'action-invite-user',
    label: 'Invite Team Member',
    description: 'Invite someone to your team',
    icon: Users,
    action: () => {}, // Will be set dynamically
    keywords: ['invite', 'add', 'user', 'team'],
    category: 'action',
  },
  {
    id: 'action-generate-report',
    label: 'Generate Report',
    description: 'Create a new report',
    icon: FileText,
    action: () => {}, // Will be set dynamically
    keywords: ['create', 'export', 'report'],
    category: 'action',
  },
];

// Help options
const HELP_OPTIONS: CommandOption[] = [
  {
    id: 'help-docs',
    label: 'Documentation',
    description: 'View documentation',
    icon: HelpCircle,
    action: () => window.location.href = '/help/docs',
    keywords: ['help', 'docs', 'guide'],
    category: 'help',
  },
  {
    id: 'help-support',
    label: 'Contact Support',
    description: 'Get help from our team',
    icon: AlertCircle,
    action: () => window.location.href = '/help/support',
    keywords: ['help', 'contact', 'support'],
    category: 'help',
  },
  {
    id: 'help-shortcuts',
    label: 'Keyboard Shortcuts',
    description: 'View all keyboard shortcuts',
    icon: CommandIcon,
    shortcut: '?',
    action: () => {}, // Will show shortcuts modal
    keywords: ['shortcuts', 'keys', 'hotkeys'],
    category: 'help',
  },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [recentItems, setRecentItems] = useState<SearchResult[]>([]);
  
  const router = useRouter();
  const { openEntityModal, openConfirmModal } = useModals();
  const debouncedSearch = useDebounce(search, 300);

  // Load recent items from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('command-palette-recent');
    if (stored) {
      try {
        setRecentItems(JSON.parse(stored));
      } catch (e) {
        console.error('Failed to parse recent items', e);
      }
    }
  }, []);

  // Save to recent items
  const addToRecent = useCallback((item: SearchResult) => {
    const newRecent = [item, ...recentItems.filter(i => i.id !== item.id)].slice(0, 5);
    setRecentItems(newRecent);
    localStorage.setItem('command-palette-recent', JSON.stringify(newRecent));
  }, [recentItems]);

  // Set up action handlers with modal system
  const actionOptions = useMemo(() => {
    return ACTION_OPTIONS.map(option => {
      switch (option.id) {
        case 'action-create-organization':
          return {
            ...option,
            action: () => {
              setOpen(false);
              openEntityModal({
                entity: 'organization',
                action: 'create',
                title: 'Create New Organization',
                onSuccess: () => router.push('/organizations'),
              });
            },
          };
        case 'action-create-site':
          return {
            ...option,
            action: () => {
              setOpen(false);
              openEntityModal({
                entity: 'site',
                action: 'create',
                title: 'Add New Site',
                onSuccess: () => router.push('/sites'),
              });
            },
          };
        case 'action-create-project':
          return {
            ...option,
            action: () => {
              setOpen(false);
              openEntityModal({
                entity: 'project',
                action: 'create',
                title: 'Create New Project',
                onSuccess: () => router.push('/projects'),
              });
            },
          };
        default:
          return option;
      }
    });
  }, [openEntityModal, router]);

  // Search across all entities
  useEffect(() => {
    if (!debouncedSearch || debouncedSearch.length < 2) {
      setSearchResults([]);
      return;
    }

    const performSearch = async () => {
      setLoading(true);
      try {
        // Search multiple endpoints in parallel
        const [orgs, sites, projects, keywords] = await Promise.all([
          api.organizations.list().catch(() => ({ data: [] })),
          api.sites.list().catch(() => ({ data: [] })),
          api.projects.list().catch(() => ({ data: [] })),
          api.serpAnalysis.search({ query: debouncedSearch }).catch(() => ({ data: { results: [] } })),
        ]);

        const results: SearchResult[] = [
          ...(orgs.data || []).filter((org: any) => 
            org.name?.toLowerCase().includes(debouncedSearch.toLowerCase())
          ).slice(0, 5).map((org: any) => ({
            id: `org-${org.id}`,
            title: org.name,
            subtitle: `${org.members_count || 0} members`,
            type: 'organization' as const,
            url: `/organizations/${org.id}`,
            icon: Building2,
          })),
          ...(sites.data || []).filter((site: any) => 
            site.name?.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
            site.url?.toLowerCase().includes(debouncedSearch.toLowerCase())
          ).slice(0, 5).map((site: any) => ({
            id: `site-${site.id}`,
            title: site.name || site.url,
            subtitle: site.url,
            type: 'site' as const,
            url: `/sites/${site.id}`,
            icon: Globe,
          })),
          ...(projects.data || []).filter((project: any) => 
            project.name?.toLowerCase().includes(debouncedSearch.toLowerCase())
          ).slice(0, 5).map((project: any) => ({
            id: `project-${project.id}`,
            title: project.name,
            subtitle: project.description,
            type: 'project' as const,
            url: `/projects/${project.id}`,
            icon: FolderOpen,
          })),
          ...((keywords as any).results || (keywords.data as any)?.results || []).map((keyword: any) => ({
            id: `keyword-${keyword.id}`,
            title: keyword.keyword,
            subtitle: `Position: ${keyword.position}`,
            type: 'keyword' as const,
            url: `/analytics/seo?keyword=${encodeURIComponent(keyword.keyword)}`,
            icon: TrendingUp,
          })),
        ];

        setSearchResults(results);
      } catch (error) {
        console.error('Search error:', error);
        setSearchResults([]);
      } finally {
        setLoading(false);
      }
    };

    performSearch();
  }, [debouncedSearch]);

  // Keyboard shortcut handler
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const handleSelect = (result: SearchResult) => {
    addToRecent(result);
    setOpen(false);
    if (result.url) {
      router.push(result.url);
    }
  };

  const filteredNavOptions = NAVIGATION_OPTIONS.filter(option =>
    !search || 
    option.label.toLowerCase().includes(search.toLowerCase()) ||
    option.description?.toLowerCase().includes(search.toLowerCase()) ||
    option.keywords?.some(k => k.toLowerCase().includes(search.toLowerCase()))
  );

  const filteredActionOptions = actionOptions.filter(option =>
    !search || 
    option.label.toLowerCase().includes(search.toLowerCase()) ||
    option.description?.toLowerCase().includes(search.toLowerCase()) ||
    option.keywords?.some(k => k.toLowerCase().includes(search.toLowerCase()))
  );

  const filteredHelpOptions = HELP_OPTIONS.filter(option =>
    !search || 
    option.label.toLowerCase().includes(search.toLowerCase()) ||
    option.description?.toLowerCase().includes(search.toLowerCase()) ||
    option.keywords?.some(k => k.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <CommandIcon className="h-4 w-4" />
        <span className="hidden sm:inline">Command Palette</span>
        <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput
          placeholder="Search or type a command..."
          value={search}
          onValueChange={setSearch}
        />
        <CommandList>
          {loading && (
            <CommandEmpty>Searching...</CommandEmpty>
          )}

          {!loading && !search && recentItems.length > 0 && (
            <>
              <CommandGroup heading="Recent">
                {recentItems.map((item) => {
                  const Icon = item.icon || ENTITY_ICONS[item.type];
                  return (
                    <CommandItem
                      key={item.id}
                      onSelect={() => handleSelect(item)}
                      className="flex items-center gap-2"
                    >
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <div className="font-medium">{item.title}</div>
                        {item.subtitle && (
                          <div className="text-xs text-muted-foreground">{item.subtitle}</div>
                        )}
                      </div>
                      <Clock className="h-3 w-3 text-muted-foreground" />
                    </CommandItem>
                  );
                })}
              </CommandGroup>
              <CommandSeparator />
            </>
          )}

          {searchResults.length > 0 && (
            <>
              <CommandGroup heading="Search Results">
                {searchResults.map((result) => {
                  const Icon = result.icon || ENTITY_ICONS[result.type];
                  return (
                    <CommandItem
                      key={result.id}
                      onSelect={() => handleSelect(result)}
                      className="flex items-center gap-2"
                    >
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <div className="font-medium">{result.title}</div>
                        {result.subtitle && (
                          <div className="text-xs text-muted-foreground">{result.subtitle}</div>
                        )}
                      </div>
                      <ArrowRight className="h-3 w-3 text-muted-foreground" />
                    </CommandItem>
                  );
                })}
              </CommandGroup>
              <CommandSeparator />
            </>
          )}

          {filteredNavOptions.length > 0 && (
            <CommandGroup heading="Navigation">
              {filteredNavOptions.map((option) => (
                <CommandItem
                  key={option.id}
                  onSelect={() => {
                    setOpen(false);
                    option.action();
                  }}
                  className="flex items-center gap-2"
                >
                  {option.icon && <option.icon className="h-4 w-4 text-muted-foreground" />}
                  <div className="flex-1">
                    <div className="font-medium">{option.label}</div>
                    {option.description && (
                      <div className="text-xs text-muted-foreground">{option.description}</div>
                    )}
                  </div>
                  {option.shortcut && <CommandShortcut>{option.shortcut}</CommandShortcut>}
                </CommandItem>
              ))}
            </CommandGroup>
          )}

          {filteredActionOptions.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Actions">
                {filteredActionOptions.map((option) => (
                  <CommandItem
                    key={option.id}
                    onSelect={() => {
                      option.action();
                    }}
                    className="flex items-center gap-2"
                  >
                    {option.icon && <option.icon className="h-4 w-4 text-muted-foreground" />}
                    <div className="flex-1">
                      <div className="font-medium">{option.label}</div>
                      {option.description && (
                        <div className="text-xs text-muted-foreground">{option.description}</div>
                      )}
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}

          {filteredHelpOptions.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Help">
                {filteredHelpOptions.map((option) => (
                  <CommandItem
                    key={option.id}
                    onSelect={() => {
                      setOpen(false);
                      option.action();
                    }}
                    className="flex items-center gap-2"
                  >
                    {option.icon && <option.icon className="h-4 w-4 text-muted-foreground" />}
                    <div className="flex-1">
                      <div className="font-medium">{option.label}</div>
                      {option.description && (
                        <div className="text-xs text-muted-foreground">{option.description}</div>
                      )}
                    </div>
                    {option.shortcut && <CommandShortcut>{option.shortcut}</CommandShortcut>}
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}

          {!loading && search && searchResults.length === 0 && 
           filteredNavOptions.length === 0 && 
           filteredActionOptions.length === 0 && 
           filteredHelpOptions.length === 0 && (
            <CommandEmpty>No results found for &quot;{search}&quot;</CommandEmpty>
          )}
        </CommandList>
      </CommandDialog>
    </>
  );
}