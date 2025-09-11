'use client';

import { ReactNode } from 'react';
import { Sidebar } from './sidebar';
import { Header } from './header';
import { ErrorBoundary } from '@/components/error-boundary';
import { WebSocketIntegration } from '@/components/websocket-integration';
import { LiveActivityFeed } from '@/components/live-activity-feed';

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <>
      <WebSocketIntegration />
      <LiveActivityFeed />
      <div className="flex h-screen bg-background">
        <ErrorBoundary>
          <Sidebar />
        </ErrorBoundary>
        <div className="flex flex-1 flex-col">
          <ErrorBoundary>
            <Header />
          </ErrorBoundary>
          <main className="flex-1 overflow-y-auto p-6">
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </main>
        </div>
      </div>
    </>
  );
}