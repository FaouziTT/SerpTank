'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Search, 
  Filter, 
  Calendar, 
  Tag, 
  User, 
  Building2, 
  FolderOpen, 
  Globe, 
  FileText,
  Clock,
  X,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { useSearch, SearchResult, SearchFilter, highlightSearchResult } from '@/lib/search-context';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

const ENTITY_TYPES = [
  { id: 'organization', label: 'Organizations', icon: Building2 },
  { id: 'project', label: 'Projects', icon: FolderOpen },
  { id: 'site', label: 'Sites', icon: Globe },
  { id: 'report', label: 'Reports', icon: FileText },
  { id: 'user', label: 'Users', icon: User },
] as const;

const STATUS_OPTIONS = [
  { id: 'active', label: 'Active', color: 'bg-green-500' },
  { id: 'inactive', label: 'Inactive', color: 'bg-gray-500' },
  { id: 'pending', label: 'Pending', color: 'bg-yellow-500' },
  { id: 'archived', label: 'Archived', color: 'bg-red-500' },
];

export function AdvancedSearch() {
  const router = useRouter();
  const {
    query,
    setQuery,
    filters,
    setFilters,
    results,
    isSearching,
    error,
    search,
    clearSearch,
    searchHistory,
    clearHistory,
    suggestions,
    isAdvancedSearchOpen,
    setIsAdvancedSearchOpen,
  } = useSearch();

  const [localQuery, setLocalQuery] = useState(query);
  const [activeTab, setActiveTab] = useState<'all' | 'filters' | 'history'>('all');

  // Sync local query with global query
  useEffect(() => {
    setLocalQuery(query);
  }, [query]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(localQuery);
    search(localQuery, filters);
  };

  const handleTypeToggle = (type: string) => {
    const currentTypes = filters.type || [];
    const newTypes = currentTypes.includes(type as any)
      ? currentTypes.filter(t => t !== type)
      : [...currentTypes, type as any];
    
    setFilters({ ...filters, type: newTypes.length ? newTypes : undefined });
  };

  const handleStatusToggle = (status: string) => {
    const currentStatuses = filters.status || [];
    const newStatuses = currentStatuses.includes(status)
      ? currentStatuses.filter(s => s !== status)
      : [...currentStatuses, status];
    
    setFilters({ ...filters, status: newStatuses.length ? newStatuses : undefined });
  };

  const handleResultClick = (result: SearchResult) => {
    if (result.url) {
      router.push(result.url);
      setIsAdvancedSearchOpen(false);
    }
  };

  const getResultIcon = (type: string) => {
    const entityType = ENTITY_TYPES.find(t => t.id === type);
    return entityType?.icon || FileText;
  };

  return (
    <Dialog open={isAdvancedSearchOpen} onOpenChange={setIsAdvancedSearchOpen}>
      <DialogContent className="max-w-4xl max-h-[80vh] p-0">
        <div className="flex h-full">
          {/* Search Header */}
          <div className="flex-1 flex flex-col">
            <div className="p-6 pb-0">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Advanced Search
                </DialogTitle>
                <DialogDescription>
                  Search across all your organizations, projects, sites, and reports
                </DialogDescription>
              </DialogHeader>

              {/* Search Input */}
              <form onSubmit={handleSearch} className="mt-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <Input
                    type="search"
                    placeholder="Search everything..."
                    value={localQuery}
                    onChange={(e) => setLocalQuery(e.target.value)}
                    className="pl-10 pr-4 h-12 text-lg"
                    autoFocus
                  />
                  {localQuery && (
                    <button
                      type="button"
                      onClick={() => {
                        setLocalQuery('');
                        clearSearch();
                      }}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2"
                    >
                      <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                    </button>
                  )}
                </div>
              </form>

              {/* Suggestions */}
              {suggestions.length > 0 && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Try:</span>
                  {suggestions.map((suggestion, index) => (
                    <Badge
                      key={index}
                      variant="secondary"
                      className="cursor-pointer"
                      onClick={() => {
                        setLocalQuery(suggestion);
                        search(suggestion, filters);
                      }}
                    >
                      {suggestion}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="flex-1 flex flex-col">
              <TabsList className="mx-6 mt-4">
                <TabsTrigger value="all" className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  All Results
                  {results.length > 0 && (
                    <Badge variant="secondary" className="ml-1">
                      {results.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="filters" className="flex items-center gap-2">
                  <Filter className="h-4 w-4" />
                  Filters
                  {Object.keys(filters).length > 0 && (
                    <Badge variant="secondary" className="ml-1">
                      {Object.keys(filters).length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="history" className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  History
                  {searchHistory.length > 0 && (
                    <Badge variant="secondary" className="ml-1">
                      {searchHistory.length}
                    </Badge>
                  )}
                </TabsTrigger>
              </TabsList>

              {/* Results */}
              <TabsContent value="all" className="flex-1 mx-6 mb-6 mt-4">
                <ScrollArea className="h-[400px]">
                  {isSearching ? (
                    <div className="space-y-3">
                      {[...Array(5)].map((_, i) => (
                        <Card key={i}>
                          <CardContent className="p-4">
                            <Skeleton className="h-5 w-3/4 mb-2" />
                            <Skeleton className="h-4 w-full" />
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : results.length > 0 ? (
                    <div className="space-y-3">
                      {results.map((result) => {
                        const Icon = getResultIcon(result.type);
                        return (
                          <Card
                            key={result.id}
                            className="cursor-pointer hover:shadow-md transition-shadow"
                            onClick={() => handleResultClick(result)}
                          >
                            <CardContent className="p-4">
                              <div className="flex items-start gap-3">
                                <div className={cn(
                                  'p-2 rounded-lg',
                                  result.type === 'organization' && 'bg-blue-100 dark:bg-blue-900',
                                  result.type === 'project' && 'bg-green-100 dark:bg-green-900',
                                  result.type === 'site' && 'bg-purple-100 dark:bg-purple-900',
                                  result.type === 'report' && 'bg-orange-100 dark:bg-orange-900',
                                  result.type === 'user' && 'bg-pink-100 dark:bg-pink-900',
                                )}>
                                  <Icon className="h-4 w-4" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h4 className="font-medium text-sm">
                                    {highlightSearchResult(result.title, query)}
                                  </h4>
                                  {result.description && (
                                    <p className="text-sm text-muted-foreground mt-1">
                                      {highlightSearchResult(result.description, query)}
                                    </p>
                                  )}
                                  <div className="flex items-center gap-2 mt-2">
                                    <Badge variant="outline" className="text-xs">
                                      {result.type}
                                    </Badge>
                                    {result.metadata?.url && (
                                      <span className="text-xs text-muted-foreground">
                                        {result.metadata.url}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  ) : localQuery ? (
                    <div className="text-center py-12">
                      <p className="text-muted-foreground">No results found for &quot;{localQuery}&quot;</p>
                      <p className="text-sm text-muted-foreground mt-2">
                        Try adjusting your search or filters
                      </p>
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <p className="text-muted-foreground">Enter a search query to get started</p>
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              {/* Filters */}
              <TabsContent value="filters" className="flex-1 mx-6 mb-6 mt-4">
                <div className="space-y-6">
                  {/* Entity Type Filter */}
                  <div>
                    <Label className="text-sm font-medium mb-3 block">Entity Type</Label>
                    <div className="space-y-2">
                      {ENTITY_TYPES.map((type) => {
                        const Icon = type.icon;
                        return (
                          <div key={type.id} className="flex items-center space-x-2">
                            <Checkbox
                              id={type.id}
                              checked={filters.type?.includes(type.id as any) || false}
                              onCheckedChange={() => handleTypeToggle(type.id)}
                            />
                            <Label
                              htmlFor={type.id}
                              className="flex items-center gap-2 cursor-pointer"
                            >
                              <Icon className="h-4 w-4" />
                              {type.label}
                            </Label>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <Separator />

                  {/* Status Filter */}
                  <div>
                    <Label className="text-sm font-medium mb-3 block">Status</Label>
                    <div className="space-y-2">
                      {STATUS_OPTIONS.map((status) => (
                        <div key={status.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={status.id}
                            checked={filters.status?.includes(status.id) || false}
                            onCheckedChange={() => handleStatusToggle(status.id)}
                          />
                          <Label
                            htmlFor={status.id}
                            className="flex items-center gap-2 cursor-pointer"
                          >
                            <span className={cn('w-2 h-2 rounded-full', status.color)} />
                            {status.label}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>

                  <Separator />

                  {/* Date Range Filter */}
                  <div>
                    <Label className="text-sm font-medium mb-3 block">Date Range</Label>
                    <DateRangePicker
                      value={filters.dateRange || { start: new Date(), end: new Date() }}
                      onChange={(range) => setFilters({ ...filters, dateRange: range })}
                    />
                  </div>

                  {/* Clear Filters */}
                  {Object.keys(filters).length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setFilters({})}
                      className="w-full"
                    >
                      Clear All Filters
                    </Button>
                  )}
                </div>
              </TabsContent>

              {/* History */}
              <TabsContent value="history" className="flex-1 mx-6 mb-6 mt-4">
                <ScrollArea className="h-[400px]">
                  {searchHistory.length > 0 ? (
                    <div className="space-y-2">
                      {searchHistory.map((item, index) => (
                        <Card
                          key={index}
                          className="cursor-pointer hover:shadow-md transition-shadow"
                          onClick={() => {
                            setLocalQuery(item.query);
                            setFilters(item.filters || {});
                            search(item.query, item.filters);
                            setActiveTab('all');
                          }}
                        >
                          <CardContent className="p-3">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium text-sm">{item.query}</p>
                                <div className="flex items-center gap-2 mt-1">
                                  <span className="text-xs text-muted-foreground">
                                    {new Date(item.timestamp).toLocaleDateString()}
                                  </span>
                                  {item.resultCount !== undefined && (
                                    <Badge variant="secondary" className="text-xs">
                                      {item.resultCount} results
                                    </Badge>
                                  )}
                                </div>
                              </div>
                              <Clock className="h-4 w-4 text-muted-foreground" />
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={clearHistory}
                        className="w-full mt-2"
                      >
                        Clear History
                      </Button>
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <p className="text-muted-foreground">No search history yet</p>
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}