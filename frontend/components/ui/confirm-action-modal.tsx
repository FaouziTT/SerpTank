'use client';

import React from 'react';
import { AlertTriangle, Info, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

export type ConfirmationType = 'danger' | 'warning' | 'info' | 'success';

export interface ConfirmActionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void | Promise<void>;
  onCancel?: () => void;
  title: string;
  message: string;
  type?: ConfirmationType;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
}

const TYPE_CONFIG: Record<ConfirmationType, {
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  confirmVariant: 'default' | 'destructive';
}> = {
  danger: {
    icon: AlertTriangle,
    iconColor: 'text-destructive',
    confirmVariant: 'destructive',
  },
  warning: {
    icon: AlertCircle,
    iconColor: 'text-yellow-600',
    confirmVariant: 'default',
  },
  info: {
    icon: Info,
    iconColor: 'text-blue-600',
    confirmVariant: 'default',
  },
  success: {
    icon: CheckCircle,
    iconColor: 'text-green-600',
    confirmVariant: 'default',
  },
};

export function ConfirmActionModal({
  open,
  onOpenChange,
  onConfirm,
  onCancel,
  title,
  message,
  type = 'warning',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  loading = false,
}: ConfirmActionModalProps) {
  const config = TYPE_CONFIG[type];
  const Icon = config.icon;

  const handleConfirm = async () => {
    await onConfirm();
    onOpenChange(false);
  };

  const handleCancel = () => {
    onCancel?.();
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-start space-x-3">
            <Icon className={cn('h-5 w-5 mt-0.5', config.iconColor)} />
            <div className="flex-1">
              <AlertDialogTitle>{title}</AlertDialogTitle>
              <AlertDialogDescription className="mt-2">
                {message}
              </AlertDialogDescription>
            </div>
          </div>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel} disabled={loading}>
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={loading}
            className={cn(
              config.confirmVariant === 'destructive' &&
                'bg-destructive text-destructive-foreground hover:bg-destructive/90'
            )}
          >
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// Helper hook for managing confirm action modal
export function useConfirmAction() {
  const [open, setOpen] = React.useState(false);
  const [config, setConfig] = React.useState<Omit<ConfirmActionModalProps, 'open' | 'onOpenChange'>>({
    title: '',
    message: '',
    onConfirm: () => {},
  });

  const confirm = (options: Omit<ConfirmActionModalProps, 'open' | 'onOpenChange'>) => {
    return new Promise<boolean>((resolve) => {
      setConfig({
        ...options,
        onConfirm: async () => {
          await options.onConfirm();
          resolve(true);
        },
        onCancel: () => {
          options.onCancel?.();
          resolve(false);
        },
      });
      setOpen(true);
    });
  };

  return {
    open,
    setOpen,
    confirm,
    modalProps: {
      ...config,
      open,
      onOpenChange: setOpen,
    },
  };
}