'use client';

import { useState, useMemo } from 'react';
import { VirtualList } from './virtual-list';
import { cn } from '@/lib/utils';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

export interface ColumnDef<T> {
  id: string;
  header: string | React.ReactNode;
  accessorKey?: keyof T;
  accessorFn?: (row: T) => any;
  cell?: (props: { row: T; value: any }) => React.ReactNode;
  sortable?: boolean;
  width?: number | string;
  className?: string;
}

interface VirtualTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  rowHeight?: number;
  containerHeight?: number | string;
  onRowClick?: (row: T) => void;
  getRowId?: (row: T) => string;
  className?: string;
  containerClassName?: string;
  stickyHeader?: boolean;
}

export function VirtualTable<T>({
  data,
  columns,
  rowHeight = 52,
  containerHeight = 600,
  onRowClick,
  getRowId,
  className,
  containerClassName,
  stickyHeader = true,
}: VirtualTableProps<T>) {
  const [sortConfig, setSortConfig] = useState<{
    column: string;
    direction: 'asc' | 'desc';
  } | null>(null);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortConfig) return data;

    const column = columns.find(col => col.id === sortConfig.column);
    if (!column) return data;

    return [...data].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      if (column.accessorFn) {
        aValue = column.accessorFn(a);
        bValue = column.accessorFn(b);
      } else if (column.accessorKey) {
        aValue = a[column.accessorKey];
        bValue = b[column.accessorKey];
      } else {
        return 0;
      }

      if (aValue === bValue) return 0;
      
      const result = aValue < bValue ? -1 : 1;
      return sortConfig.direction === 'asc' ? result : -result;
    });
  }, [data, columns, sortConfig]);

  const handleSort = (columnId: string) => {
    setSortConfig(current => {
      if (!current || current.column !== columnId) {
        return { column: columnId, direction: 'asc' };
      }
      if (current.direction === 'asc') {
        return { column: columnId, direction: 'desc' };
      }
      return null;
    });
  };

  const renderRow = (row: T, index: number) => {
    const rowId = getRowId ? getRowId(row) : index.toString();

    return (
      <TableRow
        key={rowId}
        className={cn(
          'hover:bg-muted/50 transition-colors',
          onRowClick && 'cursor-pointer'
        )}
        onClick={() => onRowClick?.(row)}
      >
        {columns.map(column => {
          let value: any;
          if (column.accessorFn) {
            value = column.accessorFn(row);
          } else if (column.accessorKey) {
            value = row[column.accessorKey];
          }

          return (
            <TableCell
              key={column.id}
              className={cn('py-3', column.className)}
              style={{ width: column.width }}
            >
              {column.cell ? column.cell({ row, value }) : value}
            </TableCell>
          );
        })}
      </TableRow>
    );
  };

  return (
    <div className={cn('relative', containerClassName)}>
      {/* Sticky header */}
      {stickyHeader && (
        <div className="sticky top-0 z-10 bg-background border-b">
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map(column => (
                  <TableHead
                    key={column.id}
                    className={cn(
                      column.sortable && 'cursor-pointer select-none',
                      column.className
                    )}
                    style={{ width: column.width }}
                    onClick={() => column.sortable && handleSort(column.id)}
                  >
                    <div className="flex items-center gap-2">
                      {typeof column.header === 'string' ? (
                        <span>{column.header}</span>
                      ) : (
                        column.header
                      )}
                      {column.sortable && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-4 w-4 p-0"
                        >
                          {sortConfig?.column === column.id ? (
                            sortConfig.direction === 'asc' ? (
                              <ArrowUp className="h-4 w-4" />
                            ) : (
                              <ArrowDown className="h-4 w-4" />
                            )
                          ) : (
                            <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
                          )}
                        </Button>
                      )}
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
          </Table>
        </div>
      )}

      {/* Virtual list body */}
      <VirtualList
        items={sortedData}
        itemHeight={rowHeight}
        renderItem={renderRow}
        containerClassName={cn(
          'overflow-auto',
          typeof containerHeight === 'number' && `h-[${containerHeight}px]`
        )}
        className={className}
        overscan={5}
      />
    </div>
  );
}

// Hook for table state management
export function useTableState<T>() {
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (rowId: string) => {
    setSelectedRows(prev => {
      const next = new Set(prev);
      if (next.has(rowId)) {
        next.delete(rowId);
      } else {
        next.add(rowId);
      }
      return next;
    });
  };

  const toggleAllRows = (rowIds: string[]) => {
    setSelectedRows(prev => {
      if (prev.size === rowIds.length) {
        return new Set();
      }
      return new Set(rowIds);
    });
  };

  const toggleExpanded = (rowId: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(rowId)) {
        next.delete(rowId);
      } else {
        next.add(rowId);
      }
      return next;
    });
  };

  return {
    selectedRows,
    expandedRows,
    toggleRow,
    toggleAllRows,
    toggleExpanded,
    clearSelection: () => setSelectedRows(new Set()),
  };
}