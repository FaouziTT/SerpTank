'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  duration: number;
  delay: number;
}

// Deterministic pseudo-random number generator for consistent values
function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

interface SEOOrbProps {
  className?: string;
  colorTheme?: 'default' | 'blue' | 'purple' | 'green' | 'orange' | 'electric' | 'neon' | 'cyan';
}

export function SEOOrb({ className = '', colorTheme = 'default' }: SEOOrbProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Generate particles with deterministic values based on index
  const particles: Particle[] = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    x: seededRandom(i * 2) * 100 - 50,
    y: seededRandom(i * 3) * 100 - 50,
    size: seededRandom(i * 5) * 4 + 2,
    duration: seededRandom(i * 7) * 20 + 10,
    delay: seededRandom(i * 11) * 5,
  }));

  // Color themes for different pages
  const colorThemes = {
    default: {
      core: 'from-primary via-accent to-destructive',
      secondary: 'from-primary via-purple-600 to-accent',
      tertiary: 'from-destructive via-yellow-400 to-primary',
      particles: 'from-primary to-accent',
      rays: ['via-primary', 'via-accent', 'via-destructive']
    },
    blue: {
      core: 'from-blue-500 via-cyan-400 to-blue-600',
      secondary: 'from-blue-600 via-indigo-500 to-cyan-400',
      tertiary: 'from-cyan-400 via-sky-300 to-blue-500',
      particles: 'from-blue-500 to-cyan-400',
      rays: ['via-blue-500', 'via-cyan-400', 'via-indigo-500']
    },
    purple: {
      core: 'from-purple-500 via-pink-400 to-purple-600',
      secondary: 'from-purple-600 via-violet-500 to-pink-400',
      tertiary: 'from-pink-400 via-fuchsia-300 to-purple-500',
      particles: 'from-purple-500 to-pink-400',
      rays: ['via-purple-500', 'via-pink-400', 'via-violet-500']
    },
    green: {
      core: 'from-green-500 via-emerald-400 to-green-600',
      secondary: 'from-green-600 via-teal-500 to-emerald-400',
      tertiary: 'from-emerald-400 via-mint-300 to-green-500',
      particles: 'from-green-500 to-emerald-400',
      rays: ['via-green-500', 'via-emerald-400', 'via-teal-500']
    },
    orange: {
      core: 'from-orange-500 via-amber-400 to-orange-600',
      secondary: 'from-orange-600 via-yellow-500 to-amber-400',
      tertiary: 'from-amber-400 via-yellow-300 to-orange-500',
      particles: 'from-orange-500 to-amber-400',
      rays: ['via-orange-500', 'via-amber-400', 'via-yellow-500']
    },
    electric: {
      core: 'from-blue-600 via-purple-600 to-pink-600',
      secondary: 'from-blue-500 via-purple-500 to-pink-500',
      tertiary: 'from-cyan-400 via-blue-500 to-purple-600',
      particles: 'from-blue-500 to-purple-500',
      rays: ['via-blue-600', 'via-purple-600', 'via-pink-600']
    },
    neon: {
      core: 'from-green-400 via-yellow-400 to-pink-400',
      secondary: 'from-green-500 via-blue-500 to-purple-600',
      tertiary: 'from-cyan-300 via-green-400 to-yellow-400',
      particles: 'from-green-400 to-yellow-400',
      rays: ['via-green-400', 'via-yellow-400', 'via-pink-400']
    },
    cyan: {
      core: 'from-cyan-400 via-blue-500 to-teal-500',
      secondary: 'from-cyan-500 via-teal-400 to-blue-600',
      tertiary: 'from-teal-300 via-cyan-400 to-blue-400',
      particles: 'from-cyan-400 to-teal-400',
      rays: ['via-cyan-500', 'via-teal-400', 'via-blue-500']
    }
  };

  const theme = colorThemes[colorTheme];

  return (
    <div ref={containerRef} className={`relative w-full h-full ${className}`}>
      {/* Main orb with enhanced glow */}
      <motion.div
        className="absolute inset-0"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1.5, ease: "easeOut" }}
      >
        {/* Core orb */}
        <div className={`absolute inset-0 rounded-full bg-gradient-to-tr ${theme.core} opacity-100 blur-[80px] orb-glow`} />
        
        {/* Secondary layer */}
        <motion.div
          className={`absolute inset-4 rounded-full bg-gradient-to-br ${theme.secondary} opacity-80 blur-[60px]`}
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 180, 360],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        
        {/* Tertiary layer */}
        <motion.div
          className={`absolute inset-8 rounded-full bg-gradient-to-tl ${theme.tertiary} opacity-60 blur-[40px]`}
          animate={{
            scale: [1.2, 1, 1.2],
            rotate: [360, 180, 0],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        
        {/* Inner bright core */}
        <motion.div
          className="absolute inset-16 rounded-full bg-white opacity-20 blur-[20px]"
          animate={{
            scale: [1, 1.3, 1],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      </motion.div>
      
      {/* Particle system */}
      <div className="absolute inset-0 overflow-hidden">
        {particles.map((particle) => (
          <motion.div
            key={particle.id}
            className={`absolute w-1 h-1 rounded-full bg-gradient-to-r ${theme.particles}`}
            style={{
              left: '50%',
              top: '50%',
              width: `${particle.size}px`,
              height: `${particle.size}px`,
            }}
            animate={{
              x: [0, particle.x * 5],
              y: [0, particle.y * 5 - 100],
              opacity: [0, 1, 0],
              scale: [0, 1, 0],
            }}
            transition={{
              duration: particle.duration,
              delay: particle.delay,
              repeat: Infinity,
              ease: "easeOut"
            }}
          />
        ))}
      </div>
      
      {/* Light rays */}
      <div className="absolute inset-0">
        <motion.div
          className={`absolute left-1/2 top-1/2 w-[200%] h-[1px] bg-gradient-to-r from-transparent ${theme.rays[0]} to-transparent opacity-30`}
          style={{ transformOrigin: 'left center' }}
          animate={{
            rotate: [0, 360],
          }}
          transition={{
            duration: 30,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        <motion.div
          className={`absolute left-1/2 top-1/2 w-[200%] h-[1px] bg-gradient-to-r from-transparent ${theme.rays[1]} to-transparent opacity-30`}
          style={{ transformOrigin: 'left center' }}
          animate={{
            rotate: [45, 405],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        <motion.div
          className={`absolute left-1/2 top-1/2 w-[200%] h-[1px] bg-gradient-to-r from-transparent ${theme.rays[2]} to-transparent opacity-30`}
          style={{ transformOrigin: 'left center' }}
          animate={{
            rotate: [90, 450],
          }}
          transition={{
            duration: 35,
            repeat: Infinity,
            ease: "linear"
          }}
        />
      </div>
    </div>
  );
}