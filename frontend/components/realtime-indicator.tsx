'use client';

import { useRealtime } from '@/lib/realtime-context';
import { Badge } from '@/components/ui/badge';
import { Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';

export function RealtimeIndicator({ className }: { className?: string }) {
  const { isConnected, lastUpdate } = useRealtime();

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Badge
        variant={isConnected ? 'secondary' : 'outline'}
        className={cn(
          'flex items-center gap-1.5 transition-colors',
          isConnected
            ? 'bg-green-500/10 text-green-600 border-green-500/20'
            : 'bg-red-500/10 text-red-600 border-red-500/20'
        )}
      >
        {isConnected ? (
          <>
            <Wifi className="h-3 w-3" />
            <span className="text-xs">Live</span>
          </>
        ) : (
          <>
            <WifiOff className="h-3 w-3" />
            <span className="text-xs">Offline</span>
          </>
        )}
      </Badge>
      
      {isConnected && lastUpdate && (
        <span className="text-xs text-muted-foreground">
          Last update: {new Date(lastUpdate.timestamp).toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}