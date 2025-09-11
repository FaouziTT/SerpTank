'use client';

import { useRef, useState, useEffect, useCallback, ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface VirtualListProps<T> {
  items: T[];
  itemHeight: number | ((index: number) => number);
  renderItem: (item: T, index: number) => ReactNode;
  className?: string;
  containerClassName?: string;
  overscan?: number;
  onScroll?: (scrollTop: number) => void;
  estimatedItemSize?: number;
}

export function VirtualList<T>({
  items,
  itemHeight,
  renderItem,
  className,
  containerClassName,
  overscan = 3,
  onScroll,
  estimatedItemSize = 50,
}: VirtualListProps<T>) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  // Calculate item heights and positions
  const getItemHeight = useCallback(
    (index: number) => {
      if (typeof itemHeight === 'function') {
        return itemHeight(index);
      }
      return itemHeight;
    },
    [itemHeight]
  );

  // Calculate total height
  const totalHeight = items.reduce((sum, _, index) => {
    return sum + getItemHeight(index);
  }, 0);

  // Calculate visible range
  const getVisibleRange = useCallback(() => {
    if (!containerHeight) return { start: 0, end: 0 };

    let accumulatedHeight = 0;
    let start = 0;
    let end = items.length - 1;

    // Find start index
    for (let i = 0; i < items.length; i++) {
      const height = getItemHeight(i);
      if (accumulatedHeight + height > scrollTop) {
        start = Math.max(0, i - overscan);
        break;
      }
      accumulatedHeight += height;
    }

    // Find end index
    accumulatedHeight = 0;
    for (let i = start; i < items.length; i++) {
      if (accumulatedHeight > scrollTop + containerHeight) {
        end = Math.min(items.length - 1, i + overscan);
        break;
      }
      accumulatedHeight += getItemHeight(i);
    }

    return { start, end };
  }, [items.length, containerHeight, scrollTop, overscan, getItemHeight]);

  const { start, end } = getVisibleRange();

  // Calculate offset for visible items
  const getItemOffset = useCallback(
    (index: number) => {
      let offset = 0;
      for (let i = 0; i < index; i++) {
        offset += getItemHeight(i);
      }
      return offset;
    },
    [getItemHeight]
  );

  // Handle scroll
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const scrollTop = e.currentTarget.scrollTop;
    setScrollTop(scrollTop);
    onScroll?.(scrollTop);
  }, [onScroll]);

  // Handle container resize
  useEffect(() => {
    const handleResize = () => {
      if (scrollRef.current) {
        setContainerHeight(scrollRef.current.clientHeight);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Render visible items
  const visibleItems = [];
  for (let i = start; i <= end; i++) {
    const item = items[i];
    if (!item) continue;

    const offset = getItemOffset(i);
    visibleItems.push(
      <div
        key={i}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          transform: `translateY(${offset}px)`,
        }}
      >
        {renderItem(item, i)}
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className={cn('relative overflow-auto', containerClassName)}
      onScroll={handleScroll}
    >
      <div
        className={cn('relative', className)}
        style={{ height: totalHeight }}
      >
        {visibleItems}
      </div>
    </div>
  );
}

// Hook for dynamic height virtual list
export function useVirtualList<T>({
  items,
  estimatedItemSize = 50,
  getItemHeight,
  overscan = 3,
}: {
  items: T[];
  estimatedItemSize?: number;
  getItemHeight?: (index: number) => number;
  overscan?: number;
}) {
  const [measurements, setMeasurements] = useState<Map<number, number>>(new Map());

  const measureItem = useCallback((index: number, height: number) => {
    setMeasurements(prev => {
      const next = new Map(prev);
      next.set(index, height);
      return next;
    });
  }, []);

  const getHeight = useCallback(
    (index: number) => {
      return measurements.get(index) || getItemHeight?.(index) || estimatedItemSize;
    },
    [measurements, getItemHeight, estimatedItemSize]
  );

  return {
    getHeight,
    measureItem,
  };
}