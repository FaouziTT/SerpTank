'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { routes, routeGroups } from '@/lib/routes';
import * as Icons from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { Badge } from '@/components/ui/badge';
import { motion } from 'framer-motion';

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Auto-collapse on mobile
  useEffect(() => {
    const handleResize = () => {
      setIsCollapsed(window.innerWidth < 1024);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Function to check if user has access to a route
  const hasAccess = (item: any) => {
    if (!user) return false;
    
    // If no roles specified, allow all authenticated users
    if (!item.roles || item.roles.length === 0) return true;
    
    // Check if user is admin for admin-only routes
    if (item.adminOnly && !user.is_superuser) return false;
    
    // Check role-based access
    const userRole = user.is_superuser ? 'admin' : 'user';
    return item.roles.includes(userRole);
  };

  // Filter navigation items based on user access
  const getFilteredItems = (items: readonly any[]) => {
    return items
      .map((item: any) => ({
        ...item,
        icon: Icons[item.icon as keyof typeof Icons] as any,
      }))
      .filter(hasAccess);
  };

  const navigation = [
    {
      title: 'Overview',
      items: getFilteredItems(routeGroups.overview),
    },
    {
      title: 'Core Pillars',
      items: getFilteredItems(routeGroups.corePillars),
    },
    {
      title: 'Integrations',
      items: getFilteredItems(routeGroups.integrations),
    },
  ];

  // Add admin section only if user is superuser
  if (user?.is_superuser && routeGroups.admin) {
    navigation.push({
      title: 'Administration',
      items: getFilteredItems(routeGroups.admin),
    });
  }

  // Filter out empty sections
  const filteredNavigation = navigation.filter(section => section.items.length > 0);

  return (
    <motion.div
      className={cn(
        "flex h-screen flex-col bg-card/90 backdrop-blur-xl border-r border-border/40 relative shadow-xl shadow-border/20 transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}
      animate={{ width: isCollapsed ? 64 : 256 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
    >
      {/* Enhanced unified background gradient with depth */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/[0.015] via-accent/[0.015] to-primary/[0.008] pointer-events-none" />
      {/* Subtle inner shadow for depth */}
      <div className="absolute inset-0 shadow-inner shadow-primary/5 pointer-events-none rounded-r-lg" />

      {/* Brand anchor section with enhanced prominence */}
      <div className="flex h-20 items-center px-6 border-b border-border/40 relative bg-background/20 backdrop-blur-sm shrink-0">
        <div className="flex items-center justify-between w-full">
          <motion.div
            className="flex items-center space-x-4 group"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Enhanced logo with optimal sizing and presence */}
            <div className="relative group">
              <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center neon-glow-blue shadow-xl transition-all duration-300 group-hover:shadow-2xl group-hover:scale-105">
                <Image
                  src="/serptank-orb-enhanced.svg"
                  alt="SerpTank"
                  width={28}
                  height={28}
                  className="w-7 h-7 object-contain transition-all duration-300 group-hover:scale-110"
                />
              </div>
              {/* Enhanced brand echo with interaction */}
              <div className="absolute -inset-1.5 bg-gradient-to-br from-primary/25 to-accent/25 rounded-3xl blur-md -z-10 transition-all duration-300 group-hover:from-primary/35 group-hover:to-accent/35" />
              {/* Breathing brand pulse */}
              <div className="absolute -inset-2 bg-gradient-to-br from-primary/10 to-accent/10 rounded-3xl blur-lg -z-20 animate-pulse" />
            </div>

            {/* Enhanced typography hierarchy with optimal sizing */}
            {!isCollapsed && (
              <div className="flex-1 ml-1">
                <h1 className="text-2xl font-bold tracking-tight text-gradient-electric leading-tight transition-all duration-300 group-hover:text-gradient-electric-bright">SerpTank</h1>
                <p className="text-xs text-muted-foreground font-medium tracking-wide opacity-80 transition-all duration-300 group-hover:opacity-100">AI-Powered Platform</p>
              </div>
            )}
          </motion.div>
          {user?.is_superuser && !isCollapsed && (
            <Badge variant="secondary" className="text-xs neon-glow-green">
              <Icons.Shield className="mr-1 h-3 w-3" />
              Admin
            </Badge>
          )}
        </div>
      </div>
      <nav className="flex-1 overflow-hidden px-5 py-3 relative">
        <div className="flex flex-col h-full justify-start space-y-3">
          {filteredNavigation.map((section: any, sectionIndex: number) => (
            <motion.div
              key={section.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: sectionIndex * 0.1 }}
              className="flex-shrink-0"
            >
              {!isCollapsed && (
                <h3 className="mb-1.5 px-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  {section.title}
                </h3>
              )}
              <div className="space-y-0.5">
              {section.items.map((item: any, itemIndex: number) => {
                const isActive = pathname === item.href;
                return (
                  <motion.div
                    key={item.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: (sectionIndex * 0.1) + (itemIndex * 0.05) }}
                    whileHover={{ x: 4 }}
                    className="group"
                  >
                    <Link
                      href={item.href}
                      className={cn(
                        'flex items-center rounded-2xl transition-all duration-300 card-float group focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-background',
                        isCollapsed ? 'px-2 py-2 justify-center' : 'px-4 py-2 text-sm font-medium',
                        isActive
                          ? 'bg-primary/15 text-primary border border-primary/30 shadow-lg shadow-primary/20 neon-glow-blue backdrop-blur-sm'
                          : 'text-muted-foreground hover:bg-primary/8 hover:text-foreground hover:backdrop-blur-sm hover:border-primary/20 hover:border hover:shadow-md hover:shadow-primary/10'
                      )}
                      title={isCollapsed ? item.name : undefined}
                    >
                      <div className={cn(
                        "h-5 w-5 p-0.5 rounded-lg transition-all duration-300",
                        isCollapsed ? "mr-0" : "mr-3",
                        isActive
                          ? "bg-primary/25 text-primary shadow-sm shadow-primary/20"
                          : "group-hover:bg-primary/15 group-hover:text-primary group-hover:shadow-sm group-hover:shadow-primary/10"
                      )}>
                        <item.icon className="h-full w-full" />
                      </div>
                      {!isCollapsed && (
                        <>
                          <span className="flex-1">{item.name}</span>
                          {item.adminOnly && (
                            <Badge variant="outline" className="ml-auto text-xs">
                              Admin
                            </Badge>
                          )}
                        </>
                      )}
                    </Link>
                  </motion.div>
                );
              })}
              </div>
            </motion.div>
          ))}
        </div>
      </nav>
      
      {/* Enhanced bottom section with brand continuity */}
      <div className="h-12 border-t border-border/40 bg-gradient-to-t from-primary/[0.025] via-accent/[0.015] to-transparent relative shrink-0">
        {/* Subtle brand echo at bottom */}
        <div className="absolute top-0 left-6 right-6 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
      </div>
    </motion.div>

  );
}