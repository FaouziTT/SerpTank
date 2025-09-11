'use client';

import { useState, useCallback, createContext, useContext, ReactNode } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Check, X, Trash2, Archive, Tag, MoreHorizontal } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface BulkActionsContextType<T = any> {
  selectedItems: Set<string>;
  isAllSelected: boolean;
  isIndeterminate: boolean;
  toggleItem: (id: string) => void;
  toggleAll: () => void;
  clearSelection: () => void;
  getSelectedData: () => T[];
}

const BulkActionsContext = createContext<BulkActionsContextType | null>(null);

interface BulkActionsProviderProps<T> {
  children: ReactNode;
  items: T[];
  getItemId: (item: T) => string;
}

export function BulkActionsProvider<T>({ 
  children, 
  items, 
  getItemId 
}: BulkActionsProviderProps<T>) {
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

  const isAllSelected = items.length > 0 && selectedItems.size === items.length;
  const isIndeterminate = selectedItems.size > 0 && selectedItems.size < items.length;

  const toggleItem = useCallback((id: string) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  }, []);

  const toggleAll = useCallback(() => {
    if (isAllSelected) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(items.map(getItemId)));
    }
  }, [items, getItemId, isAllSelected]);

  const clearSelection = useCallback(() => {
    setSelectedItems(new Set());
  }, []);

  const getSelectedData = useCallback(() => {
    return items.filter(item => selectedItems.has(getItemId(item)));
  }, [items, selectedItems, getItemId]);

  const value: BulkActionsContextType<T> = {
    selectedItems,
    isAllSelected,
    isIndeterminate,
    toggleItem,
    toggleAll,
    clearSelection,
    getSelectedData,
  };

  return (
    <BulkActionsContext.Provider value={value}>
      {children}
    </BulkActionsContext.Provider>
  );
}

export function useBulkActions<T = any>() {
  const context = useContext(BulkActionsContext);
  if (!context) {
    throw new Error('useBulkActions must be used within BulkActionsProvider');
  }
  return context as BulkActionsContextType<T>;
}

// Checkbox for selecting all items
export function BulkSelectAllCheckbox({ className }: { className?: string }) {
  const { isAllSelected, isIndeterminate, toggleAll } = useBulkActions();

  return (
    <Checkbox
      checked={isAllSelected}
      onCheckedChange={toggleAll}
      className={className}
      aria-label="Select all"
      data-state={isIndeterminate ? 'indeterminate' : undefined}
    />
  );
}

// Checkbox for selecting individual items
export function BulkSelectItemCheckbox({ 
  itemId, 
  className 
}: { 
  itemId: string; 
  className?: string;
}) {
  const { selectedItems, toggleItem } = useBulkActions();

  return (
    <Checkbox
      checked={selectedItems.has(itemId)}
      onCheckedChange={() => toggleItem(itemId)}
      className={className}
      aria-label="Select item"
      onClick={(e) => e.stopPropagation()}
    />
  );
}

// Bulk actions toolbar
interface BulkActionsToolbarProps {
  actions?: Array<{
    label: string;
    icon?: React.ComponentType<{ className?: string }>;
    onClick: (selectedItems: any[]) => void | Promise<void>;
    variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
    requireConfirm?: boolean;
  }>;
  className?: string;
}

export function BulkActionsToolbar({ 
  actions = [], 
  className 
}: BulkActionsToolbarProps) {
  const { selectedItems, clearSelection, getSelectedData } = useBulkActions();
  const [isLoading, setIsLoading] = useState(false);

  if (selectedItems.size === 0) {
    return null;
  }

  const handleAction = async (action: typeof actions[0]) => {
    if (action.requireConfirm) {
      const confirmed = window.confirm(
        `Are you sure you want to ${action.label.toLowerCase()} ${selectedItems.size} items?`
      );
      if (!confirmed) return;
    }

    setIsLoading(true);
    try {
      await action.onClick(getSelectedData());
      clearSelection();
    } catch (error) {
      console.error('Bulk action failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Default actions if none provided
  const defaultActions = actions.length > 0 ? actions : [
    {
      label: 'Delete',
      icon: Trash2,
      onClick: async (items: any[]) => console.log('Delete items:', items),
      variant: 'destructive' as const,
      requireConfirm: true,
    },
    {
      label: 'Archive',
      icon: Archive,
      onClick: async (items: any[]) => console.log('Archive items:', items),
      variant: 'outline' as const,
    },
    {
      label: 'Tag',
      icon: Tag,
      onClick: async (items: any[]) => console.log('Tag items:', items),
      variant: 'outline' as const,
    },
  ];

  return (
    <div className={cn(
      'flex items-center gap-2 p-4 bg-muted/50 border rounded-lg animate-in slide-in-from-top-2',
      className
    )}>
      <span className="text-sm font-medium">
        {selectedItems.size} item{selectedItems.size > 1 ? 's' : ''} selected
      </span>
      
      <div className="flex items-center gap-2 ml-auto">
        {defaultActions.slice(0, 2).map((action, index) => {
          const Icon = action.icon;
          return (
            <Button
              key={index}
              size="sm"
              variant={action.variant}
              onClick={() => handleAction(action)}
              disabled={isLoading}
            >
              {Icon && <Icon className="h-4 w-4 mr-2" />}
              {action.label}
            </Button>
          );
        })}
        
        {defaultActions.length > 2 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="outline">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {defaultActions.slice(2).map((action, index) => {
                const Icon = action.icon;
                return (
                  <DropdownMenuItem
                    key={index}
                    onClick={() => handleAction(action)}
                  >
                    {Icon && <Icon className="h-4 w-4 mr-2" />}
                    {action.label}
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
        
        <Button
          size="sm"
          variant="ghost"
          onClick={clearSelection}
          disabled={isLoading}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// Helper component to wrap list items with bulk selection
interface BulkSelectableItemProps {
  itemId: string;
  children: ReactNode;
  className?: string;
}

export function BulkSelectableItem({ 
  itemId, 
  children, 
  className 
}: BulkSelectableItemProps) {
  const { selectedItems } = useBulkActions();
  const isSelected = selectedItems.has(itemId);

  return (
    <div className={cn(
      'relative',
      isSelected && 'ring-2 ring-primary ring-offset-2',
      className
    )}>
      <div className="absolute left-2 top-2 z-10">
        <BulkSelectItemCheckbox itemId={itemId} />
      </div>
      {children}
    </div>
  );
}