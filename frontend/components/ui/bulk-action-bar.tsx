import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  Trash2, 
  Download, 
  Archive, 
  Tag, 
  Copy, 
  Move, 
  MoreHorizontal,
  X,
  Check
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export interface BulkAction {
  id: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary';
  dangerous?: boolean;
  confirmation?: {
    title: string;
    description: string;
  };
}

interface BulkActionBarProps {
  selectedCount: number;
  onAction: (actionId: string) => void | Promise<void>;
  onClear: () => void;
  actions?: BulkAction[];
  isPerformingAction?: boolean;
  lastAction?: string | null;
  className?: string;
  position?: 'fixed' | 'sticky' | 'static';
}

const defaultActions: BulkAction[] = [
  {
    id: 'export',
    label: 'Export',
    icon: Download,
    variant: 'outline',
  },
  {
    id: 'archive',
    label: 'Archive',
    icon: Archive,
    variant: 'outline',
  },
  {
    id: 'delete',
    label: 'Delete',
    icon: Trash2,
    variant: 'destructive',
    dangerous: true,
    confirmation: {
      title: 'Delete selected items',
      description: 'This action cannot be undone. Are you sure you want to delete the selected items?'
    }
  },
];

export function BulkActionBar({
  selectedCount,
  onAction,
  onClear,
  actions = defaultActions,
  isPerformingAction = false,
  lastAction = null,
  className = '',
  position = 'fixed'
}: BulkActionBarProps) {
  if (selectedCount === 0) {
    return null;
  }

  const positionClasses = {
    fixed: 'fixed bottom-4 left-1/2 transform -translate-x-1/2 z-50',
    sticky: 'sticky bottom-4 z-50',
    static: 'relative z-10'
  };

  const primaryActions = actions.slice(0, 3);
  const secondaryActions = actions.slice(3);

  return (
    <div className={`${positionClasses[position]} ${className}`}>
      <div className="bg-card border rounded-lg shadow-lg p-4 min-w-[400px] max-w-2xl">
        <div className="flex items-center justify-between gap-4">
          {/* Selection info */}
          <div className="flex items-center gap-3">
            <Badge variant="secondary" className="flex items-center gap-1">
              <Check className="w-3 h-3" />
              {selectedCount} selected
            </Badge>
            <Separator orientation="vertical" className="h-4" />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-1 justify-center">
            {primaryActions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant || 'default'}
                size="sm"
                onClick={() => onAction(action.id)}
                disabled={isPerformingAction}
                className="gap-2"
              >
                {action.icon && (
                  <action.icon className={`w-4 h-4 ${
                    isPerformingAction && lastAction === action.id ? 'animate-spin' : ''
                  }`} />
                )}
                {isPerformingAction && lastAction === action.id ? 'Processing...' : action.label}
              </Button>
            ))}

            {/* More actions dropdown */}
            {secondaryActions.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <MoreHorizontal className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="center">
                  {secondaryActions.map((action, index) => (
                    <React.Fragment key={action.id}>
                      {index > 0 && action.dangerous && <DropdownMenuSeparator />}
                      <DropdownMenuItem
                        onClick={() => onAction(action.id)}
                        disabled={isPerformingAction}
                        className={action.dangerous ? 'text-destructive focus:text-destructive' : ''}
                      >
                        {action.icon && <action.icon className="w-4 h-4 mr-2" />}
                        {action.label}
                      </DropdownMenuItem>
                    </React.Fragment>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {/* Clear selection */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            disabled={isPerformingAction}
            className="gap-2"
          >
            <X className="w-4 h-4" />
            Clear
          </Button>
        </div>
      </div>
    </div>
  );
}

// Simple bulk action bar for specific use cases
export function SimpleBulkActionBar({
  selectedCount,
  onDelete,
  onExport,
  onClear,
  isPerformingAction = false,
  className = ''
}: {
  selectedCount: number;
  onDelete?: () => void;
  onExport?: () => void;
  onClear: () => void;
  isPerformingAction?: boolean;
  className?: string;
}) {
  const actions: BulkAction[] = [];
  
  if (onExport) {
    actions.push({
      id: 'export',
      label: 'Export',
      icon: Download,
      variant: 'outline',
    });
  }
  
  if (onDelete) {
    actions.push({
      id: 'delete',
      label: 'Delete',
      icon: Trash2,
      variant: 'destructive',
      dangerous: true,
    });
  }

  const handleAction = (actionId: string) => {
    switch (actionId) {
      case 'export':
        onExport?.();
        break;
      case 'delete':
        onDelete?.();
        break;
    }
  };

  return (
    <BulkActionBar
      selectedCount={selectedCount}
      onAction={handleAction}
      onClear={onClear}
      actions={actions}
      isPerformingAction={isPerformingAction}
      className={className}
    />
  );
}

// Bulk checkbox component for table headers
export function BulkCheckbox({
  checked,
  indeterminate,
  onChange,
  disabled = false,
  'aria-label': ariaLabel = 'Select all items'
}: {
  checked: boolean;
  indeterminate?: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  'aria-label'?: string;
}) {
  return (
    <div className="flex items-center">
      <input
        type="checkbox"
        checked={checked}
        ref={(el) => {
          if (el) el.indeterminate = indeterminate || false;
        }}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        aria-label={ariaLabel}
        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary focus:ring-offset-0"
      />
    </div>
  );
}