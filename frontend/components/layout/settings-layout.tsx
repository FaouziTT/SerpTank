'use client';

import React, { ReactNode, useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Card } from '@/components/ui/card';
import { ChevronRight, Loader2 } from 'lucide-react';

export interface SettingsSection {
  id: string;
  label: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  content: ReactNode;
  badge?: string | number;
  disabled?: boolean;
}

export interface SettingsLayoutProps {
  title?: string;
  subtitle?: string;
  sections: SettingsSection[];
  defaultSection?: string;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  className?: string;
  sidebarClassName?: string;
  contentClassName?: string;
  showMobileNav?: boolean;
}

export function SettingsLayout({
  title = 'Settings',
  subtitle,
  sections,
  defaultSection,
  loading = false,
  error = null,
  onRetry,
  className,
  sidebarClassName,
  contentClassName,
  showMobileNav = true,
}: SettingsLayoutProps) {
  const [activeSection, setActiveSection] = useState(
    defaultSection || sections[0]?.id || ''
  );
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const currentSection = sections.find(s => s.id === activeSection);

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
        <p className="text-muted-foreground">Error loading settings</p>
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
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        {subtitle && (
          <p className="text-muted-foreground">{subtitle}</p>
        )}
      </div>

      {/* Mobile Section Selector */}
      {showMobileNav && (
        <div className="lg:hidden">
          <Button
            variant="outline"
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            className="w-full justify-between"
          >
            <span className="flex items-center space-x-2">
              {currentSection?.icon && (
                <currentSection.icon className="h-4 w-4" />
              )}
              <span>{currentSection?.label}</span>
            </span>
            <ChevronRight
              className={cn(
                'h-4 w-4 transition-transform',
                mobileNavOpen && 'rotate-90'
              )}
            />
          </Button>
          
          {mobileNavOpen && (
            <Card className="mt-2 p-2">
              <nav className="space-y-1">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => {
                      setActiveSection(section.id);
                      setMobileNavOpen(false);
                    }}
                    disabled={section.disabled}
                    className={cn(
                      'w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors',
                      activeSection === section.id
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted',
                      section.disabled && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    <span className="flex items-center space-x-3">
                      {section.icon && (
                        <section.icon className="h-4 w-4 flex-shrink-0" />
                      )}
                      <span className="text-left">
                        <div className="font-medium">{section.label}</div>
                        {section.description && (
                          <div className={cn(
                            'text-xs mt-0.5',
                            activeSection === section.id
                              ? 'text-primary-foreground/70'
                              : 'text-muted-foreground'
                          )}>
                            {section.description}
                          </div>
                        )}
                      </span>
                    </span>
                    {section.badge !== undefined && (
                      <span className={cn(
                        'ml-2 px-2 py-0.5 text-xs rounded-full',
                        activeSection === section.id
                          ? 'bg-primary-foreground/20 text-primary-foreground'
                          : 'bg-muted-foreground/20 text-muted-foreground'
                      )}>
                        {section.badge}
                      </span>
                    )}
                  </button>
                ))}
              </nav>
            </Card>
          )}
        </div>
      )}

      {/* Desktop Layout */}
      <div className="flex gap-6">
        {/* Sidebar */}
        <aside
          className={cn(
            'hidden lg:block w-64 flex-shrink-0',
            sidebarClassName
          )}
        >
          <nav className="sticky top-6 space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                disabled={section.disabled}
                className={cn(
                  'w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors',
                  activeSection === section.id
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted',
                  section.disabled && 'opacity-50 cursor-not-allowed'
                )}
              >
                <span className="flex items-center space-x-3">
                  {section.icon && (
                    <section.icon className="h-4 w-4 flex-shrink-0" />
                  )}
                  <span className="text-left">
                    <div className="font-medium">{section.label}</div>
                    {section.description && (
                      <div className={cn(
                        'text-xs mt-0.5',
                        activeSection === section.id
                          ? 'text-primary-foreground/70'
                          : 'text-muted-foreground'
                      )}>
                        {section.description}
                      </div>
                    )}
                  </span>
                </span>
                {section.badge !== undefined && (
                  <span className={cn(
                    'ml-2 px-2 py-0.5 text-xs rounded-full',
                    activeSection === section.id
                      ? 'bg-primary-foreground/20 text-primary-foreground'
                      : 'bg-muted-foreground/20 text-muted-foreground'
                  )}>
                    {section.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </aside>

        {/* Content */}
        <div className={cn('flex-1 min-w-0', contentClassName)}>
          {currentSection ? (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-semibold tracking-tight">
                  {currentSection.label}
                </h2>
                {currentSection.description && (
                  <p className="text-muted-foreground mt-1">
                    {currentSection.description}
                  </p>
                )}
              </div>
              <Separator />
              <div className="py-2">
                {currentSection.content}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              Select a section to view settings
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper component for settings form sections
export interface SettingsFormSectionProps {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

export function SettingsFormSection({
  title,
  description,
  children,
  className,
}: SettingsFormSectionProps) {
  return (
    <Card className={cn('p-6', className)}>
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-medium">{title}</h3>
          {description && (
            <p className="text-sm text-muted-foreground mt-1">
              {description}
            </p>
          )}
        </div>
        <Separator />
        <div className="space-y-4">
          {children}
        </div>
      </div>
    </Card>
  );
}