'use client';

import React, { ReactNode } from 'react';
import { ChevronRight, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import Link from 'next/link';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface ActionItem {
  label: string;
  onClick: () => void;
  icon?: React.ComponentType<{ className?: string }>;
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'ghost' | 'link';
  disabled?: boolean;
  loading?: boolean;
}

export interface TabItem {
  id: string;
  label: string;
  content: ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  badge?: string | number;
  disabled?: boolean;
}

export interface DetailLayoutProps {
  title: string;
  subtitle?: string;
  status?: {
    label: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline';
  };
  breadcrumbs: BreadcrumbItem[];
  actions?: ActionItem[];
  tabs: TabItem[];
  defaultTab?: string;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  metadata?: Array<{
    label: string;
    value: ReactNode;
    icon?: React.ComponentType<{ className?: string }>;
  }>;
  className?: string;
}

export function DetailLayout({
  title,
  subtitle,
  status,
  breadcrumbs,
  actions = [],
  tabs,
  defaultTab,
  loading = false,
  error = null,
  onRetry,
  metadata = [],
  className,
}: DetailLayoutProps) {
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

  return (
    <div className={cn('space-y-6', className)}>
      {/* Breadcrumbs */}
      <nav className="flex items-center space-x-2 text-sm text-muted-foreground">
        {breadcrumbs.map((crumb, index) => (
          <React.Fragment key={index}>
            {index > 0 && <ChevronRight className="h-4 w-4" />}
            {crumb.href ? (
              <Link href={crumb.href} className="hover:text-foreground transition-colors">
                {crumb.label}
              </Link>
            ) : (
              <span className="text-foreground font-medium">{crumb.label}</span>
            )}
          </React.Fragment>
        ))}
      </nav>

      {/* Header */}
      <div className="flex flex-col space-y-4 sm:space-y-0 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
            {status && (
              <Badge variant={status.variant} className="ml-2">
                {status.label}
              </Badge>
            )}
          </div>
          {subtitle && (
            <p className="text-muted-foreground">{subtitle}</p>
          )}
          {metadata.length > 0 && (
            <div className="flex flex-wrap gap-4 mt-3">
              {metadata.map((item, index) => (
                <div key={index} className="flex items-center space-x-1.5 text-sm">
                  {item.icon && <item.icon className="h-4 w-4 text-muted-foreground" />}
                  <span className="text-muted-foreground">{item.label}:</span>
                  <span className="font-medium">{item.value}</span>
                </div>
              ))}
            </div>
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
                size="sm"
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

      {/* Tabs */}
      <Tabs defaultValue={defaultTab || tabs[0]?.id} className="space-y-4">
        <div className="border-b">
          <TabsList className="h-auto p-0 bg-transparent">
            {tabs.map((tab) => (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                disabled={tab.disabled}
                className="relative rounded-none border-b-2 border-transparent data-[state=active]:border-primary px-4 pb-3 pt-2 font-medium text-muted-foreground transition-all data-[state=active]:text-foreground"
              >
                <div className="flex items-center space-x-2">
                  {tab.icon && <tab.icon className="h-4 w-4" />}
                  <span>{tab.label}</span>
                  {tab.badge !== undefined && (
                    <Badge variant="secondary" className="ml-1.5 h-5 px-1.5">
                      {tab.badge}
                    </Badge>
                  )}
                </div>
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        
        {tabs.map((tab) => (
          <TabsContent key={tab.id} value={tab.id} className="space-y-4">
            {tab.content}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}