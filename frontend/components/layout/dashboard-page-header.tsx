'use client';

import { ReactNode } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

interface DashboardPageHeaderProps {
  title: string;
  description?: string;
  badge?: {
    icon?: ReactNode;
    text: string;
    variant?: 'default' | 'secondary' | 'destructive' | 'outline';
  };
  actions?: ReactNode;
  className?: string;
}

export function DashboardPageHeader({
  title,
  description,
  badge,
  actions,
  className
}: DashboardPageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={cn(
        // Optimized height: 80px total (vs previous ~250px) - slightly taller for better aesthetics
        "flex items-center justify-between min-h-[80px] mb-6",
        "border-b border-border/50 pb-4",
        className
      )}
    >
      <div className="min-w-0 flex-1">
        {/* Badge with icon */}
        {badge && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Badge
              variant={badge.variant || "secondary"}
              className="mb-3 animate-slide-up-fade"
            >
              {badge.icon && <span className="mr-1 h-3 w-3">{badge.icon}</span>}
              {badge.text}
            </Badge>
          </motion.div>
        )}

        {/* Enhanced title with gradient styling */}
        <motion.h1
          className="text-3xl font-bold tracking-tighter mb-2 leading-tight text-gradient-electric"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {title}
        </motion.h1>

        {/* Enhanced description with better styling */}
        {description && (
          <motion.p
            className="text-base text-muted-foreground leading-relaxed max-w-3xl"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            {description}
          </motion.p>
        )}
      </div>

      {/* Action buttons aligned right */}
      {actions && (
        <div className="flex items-center gap-2 shrink-0 ml-4">
          {actions}
        </div>
      )}
    </motion.div>
  );
}

// Convenience variants for common page types
export function DashboardPageHeaderWithSearch({
  title,
  description,
  badge,
  onSearch,
  searchPlaceholder = "Search...",
  actions,
  className
}: DashboardPageHeaderProps & {
  onSearch?: (query: string) => void;
  searchPlaceholder?: string;
}) {
  return (
    <DashboardPageHeader
      title={title}
      description={description}
      badge={badge}
      className={className}
      actions={
        <div className="flex items-center gap-2">
          {onSearch && (
            <div className="relative">
              <input
                type="text"
                placeholder={searchPlaceholder}
                onChange={(e) => onSearch(e.target.value)}
                className="w-64 px-3 py-1.5 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          )}
          {actions}
        </div>
      }
    />
  );
}

// Analytics-focused variant
export function AnalyticsPageHeader({
  title,
  description,
  badge,
  dateRange,
  onDateRangeChange,
  actions,
  className
}: DashboardPageHeaderProps & {
  dateRange?: string;
  onDateRangeChange?: (range: string) => void;
}) {
  return (
    <DashboardPageHeader
      title={title}
      description={description}
      badge={badge}
      className={className}
      actions={
        <div className="flex items-center gap-2">
          {dateRange && onDateRangeChange && (
            <select
              value={dateRange}
              onChange={(e) => onDateRangeChange(e.target.value)}
              className="px-3 py-1.5 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="7days">Last 7 Days</option>
              <option value="28days">Last 28 Days</option>
              <option value="3months">Last 3 Months</option>
              <option value="6months">Last 6 Months</option>
            </select>
          )}
          {actions}
        </div>
      }
    />
  );
}