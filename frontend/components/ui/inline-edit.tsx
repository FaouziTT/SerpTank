'use client';

import { useState, useRef, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Check, X, Edit2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InlineEditProps {
  value: string;
  onSave: (value: string) => void | Promise<void>;
  className?: string;
  inputClassName?: string;
  multiline?: boolean;
  placeholder?: string;
  disabled?: boolean;
  showEditButton?: boolean;
  validation?: (value: string) => boolean | string;
}

export function InlineEdit({
  value,
  onSave,
  className,
  inputClassName,
  multiline = false,
  placeholder = 'Click to edit',
  disabled = false,
  showEditButton = true,
  validation,
}: InlineEditProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  useEffect(() => {
    setEditValue(value);
  }, [value]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSave = async () => {
    // Validate if function provided
    if (validation) {
      const result = validation(editValue);
      if (typeof result === 'string') {
        setError(result);
        return;
      } else if (!result) {
        setError('Invalid value');
        return;
      }
    }

    setError(null);
    setIsSaving(true);

    try {
      await onSave(editValue);
      setIsEditing(false);
    } catch (error) {
      setError('Failed to save');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditValue(value);
    setError(null);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !multiline) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  if (disabled && !isEditing) {
    return <span className={className}>{value || placeholder}</span>;
  }

  if (isEditing) {
    const InputComponent = multiline ? Textarea : Input;
    
    return (
      <div className={cn('flex items-start gap-2', className)}>
        <div className="flex-1 space-y-1">
          <InputComponent
            ref={inputRef as any}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => {
              // Don't cancel on blur if we're clicking a button
              if (!document.activeElement?.closest('.inline-edit-actions')) {
                setTimeout(handleCancel, 200);
              }
            }}
            className={cn(
              'h-auto min-h-0 py-1',
              error && 'border-destructive',
              inputClassName
            )}
            disabled={isSaving}
          />
          {error && (
            <p className="text-xs text-destructive">{error}</p>
          )}
        </div>
        <div className="inline-edit-actions flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0"
            onClick={handleSave}
            disabled={isSaving}
          >
            <Check className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0"
            onClick={handleCancel}
            disabled={isSaving}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'group flex items-center gap-2 cursor-pointer rounded px-2 py-1 -mx-2 -my-1 hover:bg-muted transition-colors',
        className
      )}
      onClick={() => !disabled && setIsEditing(true)}
    >
      <span className={cn(!value && 'text-muted-foreground')}>
        {value || placeholder}
      </span>
      {showEditButton && (
        <Edit2 className="h-3 w-3 opacity-0 group-hover:opacity-50 transition-opacity" />
      )}
    </div>
  );
}

// Table cell variant for inline editing
export function InlineEditCell({
  value,
  onSave,
  ...props
}: InlineEditProps) {
  return (
    <InlineEdit
      value={value}
      onSave={onSave}
      showEditButton={false}
      className="px-0 py-0 -mx-0 -my-0"
      inputClassName="h-full"
      {...props}
    />
  );
}