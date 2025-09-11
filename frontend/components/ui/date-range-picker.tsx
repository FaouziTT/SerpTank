'use client';

import * as React from 'react';
import { CalendarIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface DateRange {
  start: Date;
  end: Date;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
}

export function DateRangePicker({
  value,
  onChange,
  className,
}: DateRangePickerProps) {
  const presets = [
    {
      label: 'Last 7 days',
      getValue: () => ({
        start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
        end: new Date(),
      }),
    },
    {
      label: 'Last 30 days',
      getValue: () => ({
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        end: new Date(),
      }),
    },
    {
      label: 'Last 90 days',
      getValue: () => ({
        start: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
        end: new Date(),
      }),
    },
    {
      label: 'Last 12 months',
      getValue: () => ({
        start: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000),
        end: new Date(),
      }),
    },
  ];

  const getCurrentPreset = () => {
    const daysDiff = Math.floor((value.end.getTime() - value.start.getTime()) / (1000 * 60 * 60 * 24));
    
    if (daysDiff <= 7) return 'Last 7 days';
    if (daysDiff <= 30) return 'Last 30 days';
    if (daysDiff <= 90) return 'Last 90 days';
    if (daysDiff <= 365) return 'Last 12 months';
    return 'Custom range';
  };

  return (
    <Select
      value={getCurrentPreset()}
      onValueChange={(preset) => {
        const selected = presets.find((p) => p.label === preset);
        if (selected) {
          onChange(selected.getValue());
        }
      }}
    >
      <SelectTrigger className={cn('w-[160px]', className)}>
        <CalendarIcon className="mr-2 h-4 w-4" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {presets.map((preset) => (
          <SelectItem key={preset.label} value={preset.label}>
            {preset.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}