'use client';

import React, { ReactNode, useState } from 'react';
import { Search, Filter, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  BulkActionsProvider, 
  BulkActionsToolbar, 
  BulkSelectAllCheckbox 
} from '@/components/ui/bulk-actions';

export interface ActionItem {
  label: string;
  onClick: () => void;
  icon?: React.ComponentType<{ className?: string }>;
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'ghost' | 'link';
  disabled?: boolean;
  loading?: boolean;
}

export interface FilterOption {
  id: string;
  label: string;
  value: string;
}

export interface FilterConfig {
  id: string;
  label: string;
  type: 'select' | 'multiselect' | 'search';
  options?: FilterOption[];
  placeholder?: string;
}

export interface SortOption {
  id: string;
  label: string;
  value: string;
}

export interface EmptyStateConfig {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  message: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface ListLayoutProps<T = any> {
  title: string;
  subtitle?: string;
  searchPlaceholder?: string;
  filters?: FilterConfig[];
  sortOptions?: SortOption[];
  actions?: ActionItem[];
  emptyState?: EmptyStateConfig;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  onSearch?: (query: string) => void;
  onFilterChange?: (filterId: string, value: string | string[]) => void;
  onSortChange?: (sortValue: string) => void;
  selectedFilters?: Record<string, string | string[]>;
  selectedSort?: string;
  totalCount?: number;
  children: ReactNode;
  className?: string;
  bulkActions?: {
    enabled: boolean;
    items?: T[];
    getItemId?: (item: T) => string;
    actions?: ActionItem[];
  };
}

export function ListLayout<T = any>({
  title,
  subtitle,
  searchPlaceholder = 'Search...',
  filters = [],
  sortOptions = [],
  actions = [],
  emptyState,
  loading = false,
  error = null,
  onRetry,
  onSearch,
  onFilterChange,
  onSortChange,
  selectedFilters = {},
  selectedSort,
  totalCount,
  children,
  className,
  bulkActions,
}: ListLayoutProps<T>) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState<Record<string, string | string[]>>(selectedFilters);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch?.(searchQuery);
  };

  const handleFilterChange = (filterId: string, value: string | string[]) => {
    setActiveFilters(prev => ({ ...prev, [filterId]: value }));
    onFilterChange?.(filterId, value);
  };

  const clearFilter = (filterId: string) => {
    const newFilters = { ...activeFilters };
    delete newFilters[filterId];
    setActiveFilters(newFilters);
    onFilterChange?.(filterId, '');
  };

  const activeFilterCount = Object.keys(activeFilters).filter(
    key => activeFilters[key] && (Array.isArray(activeFilters[key]) ? activeFilters[key].length > 0 : true)
  ).length;

  const isEmpty = React.Children.count(children) === 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <p className="text-muted-foreground">Error loading data</p>
        <p className="text-sm text-muted-foreground">{error.message}</p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline">
            Retry
          </Button>
        )}
      </div>
    );
  }

  const content = (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex flex-col space-y-4 sm:space-y-0 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          {subtitle && (
            <p className="text-muted-foreground">{subtitle}</p>
          )}
          {totalCount !== undefined && (
            <p className="text-sm text-muted-foreground">
              {totalCount} {totalCount === 1 ? 'item' : 'items'}
            </p>
          )}
        </div>
        
        {/* Actions */}
        {actions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {actions.map((action, index) => (
              <Button
                key={index}
                variant={action.variant || 'default'}
                onClick={action.onClick}
                disabled={action.disabled || action.loading}
              >
                {action.loading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : action.icon ? (
                  <action.icon className="h-4 w-4 mr-2" />
                ) : null}
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>

      {/* Bulk Actions Toolbar */}
      {bulkActions?.enabled && (
        <BulkActionsToolbar 
          actions={bulkActions.actions?.map(action => ({
            ...action,
            onClick: async (selectedItems) => {
              action.onClick();
            }
          }))}
        />
      )}

      {/* Search and Filters */}
      {(onSearch || filters.length > 0 || sortOptions.length > 0) && (
        <div className="flex flex-col space-y-4 sm:space-y-0 sm:flex-row sm:items-center sm:space-x-4">
          {/* Search */}
          {onSearch && (
            <form onSubmit={handleSearch} className="flex-1 max-w-sm">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder={searchPlaceholder}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </form>
          )}

          {/* Filters */}
          {filters.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <Filter className="h-4 w-4 mr-2" />
                  Filters
                  {activeFilterCount > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {activeFilterCount}
                    </Badge>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>Filter by</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {filters.map((filter) => {
                  if (filter.type === 'multiselect' && filter.options) {
                    return (
                      <div key={filter.id} className="px-2 py-1.5">
                        <p className="text-sm font-medium mb-1">{filter.label}</p>
                        {filter.options.map((option) => (
                          <DropdownMenuCheckboxItem
                            key={option.id}
                            checked={
                              Array.isArray(activeFilters[filter.id])
                                ? activeFilters[filter.id].includes(option.value)
                                : false
                            }
                            onCheckedChange={(checked) => {
                              const current = Array.isArray(activeFilters[filter.id])
                                ? activeFilters[filter.id] as string[]
                                : [];
                              const newValue = checked
                                ? [...current, option.value]
                                : current.filter((v) => v !== option.value);
                              handleFilterChange(filter.id, newValue);
                            }}
                          >
                            {option.label}
                          </DropdownMenuCheckboxItem>
                        ))}
                      </div>
                    );
                  }
                  return null;
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {/* Sort */}
          {sortOptions.length > 0 && (
            <Select value={selectedSort} onValueChange={onSortChange}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Sort by..." />
              </SelectTrigger>
              <SelectContent>
                {sortOptions.map((option) => (
                  <SelectItem key={option.id} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      )}

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(activeFilters).map(([filterId, value]) => {
            if (!value || (Array.isArray(value) && value.length === 0)) return null;
            const filter = filters.find(f => f.id === filterId);
            if (!filter) return null;

            if (Array.isArray(value)) {
              return value.map((v) => {
                const option = filter.options?.find(o => o.value === v);
                return (
                  <Badge key={`${filterId}-${v}`} variant="secondary">
                    {filter.label}: {option?.label || v}
                    <button
                      onClick={() => {
                        const newValue = value.filter(item => item !== v);
                        handleFilterChange(filterId, newValue);
                      }}
                      className="ml-1.5 hover:text-foreground"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                );
              });
            }

            return (
              <Badge key={filterId} variant="secondary">
                {filter.label}: {value}
                <button
                  onClick={() => clearFilter(filterId)}
                  className="ml-1.5 hover:text-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            );
          })}
        </div>
      )}

      {/* Content */}
      {isEmpty && emptyState ? (
        <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
          {emptyState.icon && (
            <emptyState.icon className="h-12 w-12 text-muted-foreground" />
          )}
          <div className="text-center space-y-2">
            <h3 className="text-lg font-medium">{emptyState.title}</h3>
            <p className="text-muted-foreground max-w-sm">{emptyState.message}</p>
          </div>
          {emptyState.action && (
            <Button onClick={emptyState.action.onClick}>
              {emptyState.action.label}
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {children}
        </div>
      )}
    </div>
  );

  // Wrap with BulkActionsProvider if bulk actions are enabled
  if (bulkActions?.enabled && bulkActions.items && bulkActions.getItemId) {
    return (
      <BulkActionsProvider
        items={bulkActions.items}
        getItemId={bulkActions.getItemId}
      >
        {content}
      </BulkActionsProvider>
    );
  }

  return content;
}