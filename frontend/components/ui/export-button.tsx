import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useExport, ExportOptions, formatDataForExport } from '@/lib/hooks/use-export';
import { Download, FileText, Database, Table } from 'lucide-react';
import { notifications } from '@/lib/notification-service';

interface ExportButtonProps {
  data: any[];
  filename: string;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'default' | 'lg';
  className?: string;
  children?: React.ReactNode;
  // Advanced options
  columns?: string[];
  flattenNested?: boolean;
  showAdvancedOptions?: boolean;
}

export function ExportButton({ 
  data, 
  filename, 
  variant = 'outline',
  size = 'sm',
  className,
  children,
  columns,
  flattenNested = false,
  showAdvancedOptions = true
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [format, setFormat] = useState<'csv' | 'excel' | 'json'>('csv');
  const { exportData, isExporting } = useExport();

  const handleQuickExport = async (exportFormat: 'csv' | 'excel' | 'json') => {
    try {
      const formattedData = formatDataForExport(data, { flattenNested });
      
      await exportData(formattedData, filename, {
        format: exportFormat,
        columns,
        includeHeaders: true
      });

      notifications.success(
        'Export Complete',
        `Data exported as ${exportFormat.toUpperCase()}`
      );
    } catch (error) {
      notifications.error(
        'Export Failed',
        error instanceof Error ? error.message : 'Failed to export data'
      );
    }
  };

  const handleAdvancedExport = async () => {
    try {
      const formattedData = formatDataForExport(data, { flattenNested });
      
      await exportData(formattedData, filename, {
        format,
        columns,
        includeHeaders: true
      });

      notifications.success(
        'Export Complete',
        `Data exported as ${format.toUpperCase()}`
      );
      
      setIsOpen(false);
    } catch (error) {
      notifications.error(
        'Export Failed',
        error instanceof Error ? error.message : 'Failed to export data'
      );
    }
  };

  if (!data || data.length === 0) {
    return (
      <Button
        variant={variant}
        size={size}
        className={className}
        disabled
      >
        <Download className="w-4 h-4 mr-2" />
        {children || 'Export'}
      </Button>
    );
  }

  if (!showAdvancedOptions) {
    return (
      <Button
        variant={variant}
        size={size}
        className={className}
        onClick={() => handleQuickExport('csv')}
        disabled={isExporting}
      >
        <Download className="w-4 h-4 mr-2" />
        {children || 'Export CSV'}
      </Button>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          variant={variant}
          size={size}
          className={className}
          disabled={isExporting}
        >
          <Download className="w-4 h-4 mr-2" />
          {children || 'Export'}
        </Button>
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Export Data</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">Export Format</label>
            <Select value={format} onValueChange={(value: 'csv' | 'excel' | 'json') => setFormat(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    CSV (Comma Separated)
                  </div>
                </SelectItem>
                <SelectItem value="excel">
                  <div className="flex items-center gap-2">
                    <Table className="w-4 h-4" />
                    Excel (.xlsx)
                  </div>
                </SelectItem>
                <SelectItem value="json">
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4" />
                    JSON
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="text-sm text-muted-foreground">
            <p>Records to export: <span className="font-medium">{data.length}</span></p>
            {columns && (
              <p>Columns: <span className="font-medium">{columns.length}</span></p>
            )}
          </div>

          {/* Quick export buttons */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Quick Export:</p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickExport('csv')}
                disabled={isExporting}
                className="flex-1"
              >
                <FileText className="w-4 h-4 mr-1" />
                CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickExport('excel')}
                disabled={isExporting}
                className="flex-1"
              >
                <Table className="w-4 h-4 mr-1" />
                Excel
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickExport('json')}
                disabled={isExporting}
                className="flex-1"
              >
                <Database className="w-4 h-4 mr-1" />
                JSON
              </Button>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setIsOpen(false)}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleAdvancedExport}
              disabled={isExporting}
              className="flex-1"
            >
              {isExporting ? 'Exporting...' : 'Export'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Simple export button for quick CSV export
export function QuickExportButton({ 
  data, 
  filename, 
  variant = 'outline',
  size = 'sm',
  className 
}: Pick<ExportButtonProps, 'data' | 'filename' | 'variant' | 'size' | 'className'>) {
  return (
    <ExportButton
      data={data}
      filename={filename}
      variant={variant}
      size={size}
      className={className}
      showAdvancedOptions={false}
    />
  );
}