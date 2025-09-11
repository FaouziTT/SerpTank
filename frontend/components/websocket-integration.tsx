'use client';

import { useEffect } from 'react';
import { useWebSocketSync } from '@/lib/websocket-sync';
import { useAuth } from '@/lib/auth-context';
import { Badge } from '@/components/ui/badge';
import { Wifi, WifiOff } from 'lucide-react';

/**
 * Component that integrates WebSocket real-time updates with the app
 * Should be included at the root level of authenticated pages
 */
export function WebSocketIntegration() {
  const { isConnected } = useWebSocketSync();
  const { user } = useAuth();

  // Don't render anything if user is not authenticated
  if (!user) {
    return null;
  }

  return (
    <>
      {/* Connection status indicator (only in development) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 left-4 z-50">
          <Badge 
            variant={isConnected ? 'default' : 'secondary'}
            className="flex items-center gap-2"
          >
            {isConnected ? (
              <>
                <Wifi className="h-3 w-3" />
                Real-time Connected
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3" />
                Real-time Disconnected
              </>
            )}
          </Badge>
        </div>
      )}
    </>
  );
}