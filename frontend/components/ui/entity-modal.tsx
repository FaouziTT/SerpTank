'use client';

import React, { ReactNode, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

export type EntityType = 'organization' | 'site' | 'project' | 'user' | 'team-member' | 'api-key' | 'webhook' | string;
export type ActionType = 'create' | 'edit' | 'delete' | 'view';

export interface EntityModalProps {
  entity: EntityType;
  action: ActionType;
  data?: any;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit?: (data?: any) => Promise<void> | void;
  onSuccess?: (data?: any) => void;
  onError?: (error: Error) => void;
  title?: string;
  description?: string;
  children?: ReactNode;
  submitLabel?: string;
  cancelLabel?: string;
  submitVariant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  showFooter?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  className?: string;
}

const DEFAULT_TITLES: Record<ActionType, string> = {
  create: 'Create New',
  edit: 'Edit',
  delete: 'Delete',
  view: 'View Details',
};

const DEFAULT_SUBMIT_LABELS: Record<ActionType, string> = {
  create: 'Create',
  edit: 'Save Changes',
  delete: 'Delete',
  view: 'Close',
};

const DEFAULT_SUBMIT_VARIANTS: Record<ActionType, EntityModalProps['submitVariant']> = {
  create: 'default',
  edit: 'default',
  delete: 'destructive',
  view: 'secondary',
};

const ENTITY_LABELS: Record<string, string> = {
  organization: 'Organization',
  site: 'Site',
  project: 'Project',
  user: 'User',
  'team-member': 'Team Member',
  'api-key': 'API Key',
  webhook: 'Webhook',
};

const SIZE_CLASSES = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-[90vw]',
};

export function EntityModal({
  entity,
  action,
  data,
  open,
  onOpenChange,
  onSubmit,
  onSuccess,
  onError,
  title,
  description,
  children,
  submitLabel,
  cancelLabel = 'Cancel',
  submitVariant,
  showFooter = true,
  size = 'md',
  className,
}: EntityModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Generate default title if not provided
  const defaultTitle = `${DEFAULT_TITLES[action]} ${ENTITY_LABELS[entity] || entity}`;
  const modalTitle = title || defaultTitle;

  // Generate default description for delete action
  const defaultDeleteDescription = action === 'delete' 
    ? `Are you sure you want to delete this ${ENTITY_LABELS[entity]?.toLowerCase() || entity}? This action cannot be undone.`
    : undefined;
  const modalDescription = description || defaultDeleteDescription;

  // Determine submit button properties
  const submitButtonLabel = submitLabel || DEFAULT_SUBMIT_LABELS[action];
  const submitButtonVariant = submitVariant || DEFAULT_SUBMIT_VARIANTS[action];

  // Reset error when modal opens/closes
  useEffect(() => {
    if (!open) {
      setError(null);
      setLoading(false);
    }
  }, [open]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (!onSubmit || action === 'view') {
      onOpenChange(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await onSubmit();
      onSuccess?.(result);
      onOpenChange(false);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('An error occurred');
      setError(error);
      onError?.(error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (!loading) {
      onOpenChange(false);
    }
  };

  // Special handling for delete modals - simpler layout
  if (action === 'delete' && !children) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className={cn(SIZE_CLASSES[size], className)}>
          <DialogHeader>
            <DialogTitle>{modalTitle}</DialogTitle>
            {modalDescription && (
              <DialogDescription>{modalDescription}</DialogDescription>
            )}
          </DialogHeader>
          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              {error.message}
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleCancel}
              disabled={loading}
            >
              {cancelLabel}
            </Button>
            <Button
              variant={submitButtonVariant}
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {submitButtonLabel}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(SIZE_CLASSES[size], 'flex flex-col max-h-[90vh]', className)}>
        <DialogHeader>
          <DialogTitle>{modalTitle}</DialogTitle>
          {modalDescription && (
            <DialogDescription>{modalDescription}</DialogDescription>
          )}
        </DialogHeader>
        
        <ScrollArea className="flex-1 -mx-6 px-6">
          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive mb-4">
              {error.message}
            </div>
          )}
          
          {children ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              {children}
            </form>
          ) : (
            <div className="py-8 text-center text-muted-foreground">
              No content provided
            </div>
          )}
        </ScrollArea>

        {showFooter && (
          <DialogFooter className="mt-6">
            {action !== 'view' && (
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                disabled={loading}
              >
                {cancelLabel}
              </Button>
            )}
            <Button
              type={children ? 'submit' : 'button'}
              variant={submitButtonVariant}
              onClick={children ? undefined : handleSubmit}
              disabled={loading}
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {submitButtonLabel}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Helper hook for managing entity modal state
export function useEntityModal<T = any>() {
  const [open, setOpen] = useState(false);
  const [action, setAction] = useState<ActionType>('view');
  const [data, setData] = useState<T | undefined>();

  const openModal = (actionType: ActionType, entityData?: T) => {
    setAction(actionType);
    setData(entityData);
    setOpen(true);
  };

  const closeModal = () => {
    setOpen(false);
    // Clear data after animation completes
    setTimeout(() => {
      setData(undefined);
    }, 200);
  };

  return {
    open,
    action,
    data,
    openModal,
    closeModal,
    setOpen,
  };
}