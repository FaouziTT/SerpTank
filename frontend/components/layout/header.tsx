'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Bell, ChevronDown, LogOut, Settings, User, Sparkles, Building2, FolderOpen, Globe, Users, CreditCard } from 'lucide-react';
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import Link from 'next/link';
import { ThemeToggle } from '@/components/theme-toggle';
import { ProjectSelector } from '@/components/project-selector';
import { SearchBar } from '@/components/search-bar';
import { motion } from 'framer-motion';

export function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-50 flex h-20 items-center justify-between border-b border-border/40 bg-background/90 backdrop-blur-xl px-6 relative shadow-sm shadow-border/20" style={{ gridTemplateColumns: '256px 1fr' }}>
      {/* Enhanced shell background gradient */}
      <div className="absolute inset-0 bg-gradient-to-r from-primary/[0.015] via-accent/[0.015] to-primary/[0.008] pointer-events-none" />
      {/* Subtle depth enhancement */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

      <motion.div
        className="flex items-center space-x-6 flex-1 relative z-10"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        style={{ marginLeft: '24px' }} // Align with sidebar content padding (px-6 = 24px)
      >
        {/* Clean project selection with consistent spacing */}
        <div className="flex items-center">
          <ProjectSelector />
        </div>

        {/* Enhanced search with reduced prominence to not compete with logo */}
        <SearchBar
          className="max-w-sm bg-card/70 backdrop-blur-sm border-border/40 shadow-sm hover:border-primary/20 transition-all duration-300 text-sm"
          placeholder="Search projects, insights..."
        />
      </motion.div>
      
      <motion.div
        className="flex items-center space-x-4 relative z-10"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Secondary actions with refined hierarchy */}
        <div className="flex items-center space-x-3">
          <ThemeToggle />

          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="bg-card/60 backdrop-blur-sm border border-border/50 hover:bg-primary/10 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/20 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-background"
              >
                <Bell className="h-5 w-5" />
              </Button>
            </PopoverTrigger>
          <PopoverContent align="end" className="w-80 bg-card/80 backdrop-blur-xl border-border/50">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Notifications</h3>
                <span className="text-sm text-muted-foreground">No new notifications</span>
              </div>
              <div className="text-center py-8 text-muted-foreground">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">You're all caught up!</p>
              </div>
            </div>
          </PopoverContent>
        </Popover>
        
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="flex items-center space-x-3 bg-card/60 backdrop-blur-sm border border-border/50 hover:bg-primary/10 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/20 transition-all duration-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-background"
              >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent text-primary-foreground font-bold neon-glow-blue">
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="hidden md:inline-block font-medium">{user?.username}</span>
              <ChevronDown className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64 bg-card/80 backdrop-blur-xl border-border/50">
            <DropdownMenuLabel className="font-semibold text-gradient">My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings/profile" className="flex items-center py-3 px-4 rounded-lg hover:bg-primary/10 transition-colors">
                <div className="mr-3 h-5 w-5 p-0.5 rounded-lg bg-primary/10">
                  <User className="h-full w-full text-primary" />
                </div>
                <span className="font-medium">Profile</span>
              </Link>
            </DropdownMenuItem>
            
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="font-semibold text-muted-foreground">Management</DropdownMenuLabel>
            
            <DropdownMenuItem asChild>
              <Link href="/organizations" className="flex items-center py-2 px-4 rounded-lg hover:bg-blue-500/10 transition-colors">
                <div className="mr-3 h-5 w-5 p-0.5 rounded-lg bg-blue-500/10">
                  <Building2 className="h-full w-full text-blue-500" />
                </div>
                <span className="font-medium">Organizations</span>
              </Link>
            </DropdownMenuItem>
            
            <DropdownMenuItem asChild>
              <Link href="/projects" className="flex items-center py-2 px-4 rounded-lg hover:bg-green-500/10 transition-colors">
                <div className="mr-3 h-5 w-5 p-0.5 rounded-lg bg-green-500/10">
                  <FolderOpen className="h-full w-full text-green-500" />
                </div>
                <span className="font-medium">Projects</span>
              </Link>
            </DropdownMenuItem>
            
            <DropdownMenuItem asChild>
              <Link href="/sites" className="flex items-center py-2 px-4 rounded-lg hover:bg-purple-500/10 transition-colors">
                <div className="mr-3 h-5 w-5 p-0.5 rounded-lg bg-purple-500/10">
                  <Globe className="h-full w-full text-purple-500" />
                </div>
                <span className="font-medium">Sites</span>
              </Link>
            </DropdownMenuItem>
            
            <DropdownMenuItem asChild>
              <Link href="/team" className="flex items-center py-2 px-4 rounded-lg hover:bg-orange-500/10 transition-colors">
                <div className="mr-3 h-5 w-5 p-0.5 rounded-lg bg-orange-500/10">
                  <Users className="h-full w-full text-orange-500" />
                </div>
                <span className="font-medium">Team</span>
              </Link>
            </DropdownMenuItem>
            
            <DropdownMenuItem asChild>
              <Link href="/billing" className="flex items-center py-2 px-4 rounded-lg hover:bg-yellow-500/10 transition-colors">
                <div className="mr-3 h-5 w-5 p-0.5 rounded-lg bg-yellow-500/10">
                  <CreditCard className="h-full w-full text-yellow-500" />
                </div>
                <span className="font-medium">Billing</span>
              </Link>
            </DropdownMenuItem>
            
            <DropdownMenuSeparator />
            
            <DropdownMenuItem asChild>
              <Link href="/settings" className="flex items-center py-3 px-4 rounded-lg hover:bg-accent/10 transition-colors">
                <div className="mr-3 h-5 w-5 p-0.5 rounded-lg bg-accent/10">
                  <Settings className="h-full w-full text-accent" />
                </div>
                <span className="font-medium">Settings</span>
              </Link>
            </DropdownMenuItem>
            
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="flex items-center text-destructive py-3 px-4 rounded-lg hover:bg-destructive/10 transition-colors">
              <div className="mr-3 h-5 w-5 p-0.5 rounded-lg bg-destructive/10">
                <LogOut className="h-full w-full text-destructive" />
              </div>
              <span className="font-medium">Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </motion.div>
    </header>
  );
}