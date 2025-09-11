'use client';

import Link from 'next/link';
import Image from 'next/image'; // <-- CHANGE: Imported Image component
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { routes, routeGroups } from '@/lib/routes';
import * as Icons from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { Badge } from '@/components/ui/badge';
import { motion } from 'framer-motion';

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

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
    <div className="flex h-screen w-64 flex-col bg-card/80 backdrop-blur-xl border-r border-border/50 relative">
      {/* Subtle background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/[0.01] via-accent/[0.01] to-transparent pointer-events-none" />
      
      <div className="flex h-20 items-center px-6 border-b border-border/50 relative">
        <div className="flex items-center justify-between w-full">
          <motion.div 
            className="flex items-center space-x-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="relative">
              <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center neon-glow-blue">
                {/* CHANGE: Replaced <img> with <Image> */}
                <Image src="/serptank-orb-enhanced.svg" alt="SerpTank" width={24} height={24} className="w-6 h-6 object-contain" />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-gradient-electric">SerpTank</h1>
              <p className="text-xs text-muted-foreground">AI-Powered Platform</p>
            </div>
          </motion.div>
          {user?.is_superuser && (
            <Badge variant="secondary" className="text-xs neon-glow-green">
              <Icons.Shield className="mr-1 h-3 w-3" />
              Admin
            </Badge>
          )}
        </div>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-4 py-6 relative">
        {filteredNavigation.map((section: any, sectionIndex: number) => (
          <motion.div
            key={section.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: sectionIndex * 0.1 }}
            className="mb-6"
          >
            <h3 className="mb-3 px-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {section.title}
            </h3>
            <div className="space-y-1">
              {section.items.map((item: any, itemIndex: number) => {
                const isActive = pathname === item.href;
                return (
                  <motion.div
                    key={item.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: (sectionIndex * 0.1) + (itemIndex * 0.05) }}
                    whileHover={{ x: 5 }}
                    className="group"
                  >
                    <Link
                      href={item.href}
                      className={cn(
                        'flex items-center rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-300 card-float',
                        isActive
                          ? 'bg-primary/10 text-primary border border-primary/20 shadow-sm neon-glow-blue'
                          : 'text-muted-foreground hover:bg-card/50 hover:text-foreground hover:backdrop-blur-sm hover:border-border/50 hover:border'
                      )}
                    >
                      <div className={cn(
                        "mr-3 h-5 w-5 p-0.5 rounded-lg transition-all duration-300",
                        isActive 
                          ? "bg-primary/20 text-primary" 
                          : "group-hover:bg-primary/10 group-hover:text-primary"
                      )}>
                        <item.icon className="h-full w-full" />
                      </div>
                      <span className="flex-1">{item.name}</span>
                      {item.adminOnly && (
                        <Badge variant="outline" className="ml-auto text-xs">
                          Admin
                        </Badge>
                      )}
                    </Link>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        ))}
      </nav>
      
      {/* Subtle gradient at bottom */}
      <div className="h-16 border-t border-border/50 bg-gradient-to-t from-primary/[0.02] to-transparent" />
    </div>
  );
}