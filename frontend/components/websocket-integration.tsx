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
      {/* Connection status now handled by the sidebar */}
    </>
  );
}