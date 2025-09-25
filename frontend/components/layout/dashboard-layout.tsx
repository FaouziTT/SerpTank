'use client';

import { ReactNode } from 'react';
import { UnifiedSidebar } from './unified-sidebar';
import { ErrorBoundary } from '@/components/error-boundary';
import { WebSocketIntegration } from '@/components/websocket-integration';
import { LiveActivityFeed } from '@/components/live-activity-feed';
import { SEOOrb } from '@/components/ui/seo-orb';
import { motion, useScroll, useTransform } from 'framer-motion';

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { scrollY } = useScroll();

  // Parallax transforms for background elements
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  return (
    <>
      <WebSocketIntegration />
      <LiveActivityFeed />
      {/* Enhanced floating 3D orb */}
      <motion.div
        className="fixed right-[-200px] top-1/4 w-[600px] h-[600px] lg:w-[800px] lg:h-[800px] pointer-events-none z-[5]"
        style={{ y: heroY, scale: orbScale }}
      >
        <SEOOrb className="scale-100 opacity-50" />
      </motion.div>

      {/* Unified Dashboard Layout with Single Sidebar */}
      <div className="flex h-screen bg-background relative overflow-hidden">
        {/* Enhanced shell background with unified gradient system */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.012] via-accent/[0.012] to-background pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-t from-primary/[0.008] via-transparent to-accent/[0.008] pointer-events-none" />

        {/* Unified Sidebar with all functionality */}
        <div className="relative z-10">
          <ErrorBoundary>
            <UnifiedSidebar />
          </ErrorBoundary>
        </div>

        {/* Main content area - full height without header */}
        <div className="flex flex-1 flex-col relative z-10">
          {/* Content area takes full height */}
          <main className="flex-1 overflow-y-auto p-6 bg-background/50 backdrop-blur-[2px]">
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </main>
        </div>

        {/* Enhanced shell frame with subtle depth system */}
        <div className="absolute inset-0 pointer-events-none z-20">
          {/* Top edge highlight with brand integration */}
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
          {/* Left edge highlight */}
          <div className="absolute top-0 left-0 bottom-0 w-px bg-gradient-to-b from-transparent via-border/30 to-transparent" />
          {/* Right edge highlight */}
          <div className="absolute top-0 right-0 bottom-0 w-px bg-gradient-to-b from-transparent via-border/30 to-transparent" />
          {/* Bottom edge highlight with brand integration */}
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent" />
          {/* Corner accents for depth */}
          <div className="absolute top-0 left-0 w-2 h-2 bg-gradient-to-br from-primary/20 to-transparent rounded-br-lg" />
          <div className="absolute top-0 right-0 w-2 h-2 bg-gradient-to-bl from-accent/20 to-transparent rounded-bl-lg" />
          <div className="absolute bottom-0 left-0 w-2 h-2 bg-gradient-to-tr from-primary/20 to-transparent rounded-tr-lg" />
          <div className="absolute bottom-0 right-0 w-2 h-2 bg-gradient-to-tl from-accent/20 to-transparent rounded-tl-lg" />
        </div>
      </div>
    </>
  );
}