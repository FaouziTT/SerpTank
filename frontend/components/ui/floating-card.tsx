'use client';

import React, { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface FloatingCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onDrag' | 'onDragStart' | 'onDragEnd' | 'onAnimationStart' | 'onAnimationEnd'> {
  children: React.ReactNode;
  depth?: 'shallow' | 'medium' | 'deep';
  glowColor?: 'primary' | 'accent' | 'destructive' | 'none';
  floatAnimation?: boolean;
  delay?: number;
}

export function FloatingCard({
  children,
  className,
  depth = 'medium',
  glowColor = 'primary',
  floatAnimation = true,
  delay = 0,
  ...props
}: FloatingCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;

    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    setMousePosition({ x, y });
  };

  const handleMouseEnter = () => setIsHovered(true);
  const handleMouseLeave = () => {
    setIsHovered(false);
    setMousePosition({ x: 0.5, y: 0.5 });
  };

  const depthStyles = {
    shallow: {
      transform: isHovered 
        ? `perspective(1000px) rotateX(${(mousePosition.y - 0.5) * -5}deg) rotateY(${(mousePosition.x - 0.5) * 5}deg) translateZ(10px)`
        : 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)',
      transition: 'transform 0.3s ease-out',
    },
    medium: {
      transform: isHovered 
        ? `perspective(1000px) rotateX(${(mousePosition.y - 0.5) * -10}deg) rotateY(${(mousePosition.x - 0.5) * 10}deg) translateZ(20px)`
        : 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)',
      transition: 'transform 0.3s ease-out',
    },
    deep: {
      transform: isHovered 
        ? `perspective(1000px) rotateX(${(mousePosition.y - 0.5) * -15}deg) rotateY(${(mousePosition.x - 0.5) * 15}deg) translateZ(30px)`
        : 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)',
      transition: 'transform 0.3s ease-out',
    },
  };

  const glowColors = {
    primary: 'from-primary/20 via-primary/10 to-transparent',
    accent: 'from-accent/20 via-accent/10 to-transparent',
    destructive: 'from-destructive/20 via-destructive/10 to-transparent',
    none: '',
  };

  return (
    <motion.div
      ref={cardRef}
      className={cn('relative group', className)}
      style={depthStyles[depth]}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        duration: 0.6, 
        delay: delay,
        ease: [0.23, 1, 0.32, 1]
      }}
      whileHover={{ y: floatAnimation ? -10 : 0 }}
      {...props}
    >
      {/* Glow effect background */}
      {glowColor !== 'none' && (
        <motion.div
          className={cn(
            'absolute -inset-1 rounded-2xl bg-gradient-to-r opacity-0 blur-xl transition-opacity duration-500',
            glowColors[glowColor]
          )}
          animate={{ opacity: isHovered ? 0.6 : 0 }}
        />
      )}

      {/* Card content with glass effect */}
      <div className={cn(
        'relative h-full rounded-2xl',
        'bg-card/80 backdrop-blur-xl',
        'border border-border/50',
        'overflow-hidden',
        'transform-gpu',
        isHovered && 'border-border'
      )}>
        {/* Shine effect on hover */}
        <motion.div
          className="absolute inset-0 opacity-0"
          style={{
            background: `radial-gradient(circle at ${mousePosition.x * 100}% ${mousePosition.y * 100}%, rgba(255,255,255,0.1) 0%, transparent 50%)`,
          }}
          animate={{ opacity: isHovered ? 1 : 0 }}
          transition={{ duration: 0.3 }}
        />

        {/* Content */}
        <div className="relative z-10">
          {children}
        </div>

        {/* Bottom gradient fade */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background/20 to-transparent pointer-events-none" />
      </div>
    </motion.div>
  );
}

// Preset card variants
export function FeatureFloatingCard({ 
  icon: Icon, 
  title, 
  description, 
  features = [], 
  index = 0,
  ...props 
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  features?: string[];
  index?: number;
} & Omit<FloatingCardProps, 'children'>) {
  return (
    <FloatingCard delay={index * 0.1} {...props}>
      <div className="p-8">
        {/* Icon with animated background */}
        <div className="relative mb-6">
          <motion.div
            className="absolute inset-0 bg-gradient-to-br from-primary/20 to-accent/20 rounded-2xl blur-lg"
            animate={{
              scale: [1, 1.1, 1],
              opacity: [0.5, 0.8, 0.5],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
          <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-accent/10 flex items-center justify-center">
            <Icon className="h-8 w-8 text-primary" />
          </div>
        </div>

        {/* Content */}
        <h3 className="text-2xl font-bold mb-3">{title}</h3>
        <p className="text-muted-foreground mb-6">{description}</p>

        {/* Features list */}
        {features.length > 0 && (
          <ul className="space-y-2">
            {features.map((feature, idx) => (
              <motion.li
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 + idx * 0.05 }}
                className="flex items-center text-sm"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-accent mr-2" />
                <span>{feature}</span>
              </motion.li>
            ))}
          </ul>
        )}
      </div>
    </FloatingCard>
  );
}

// Metric card variant
export function MetricFloatingCard({
  value,
  label,
  change,
  icon: Icon,
  index = 0,
  ...props
}: {
  value: string | number;
  label: string;
  change?: string;
  icon?: React.ElementType;
  index?: number;
} & Omit<FloatingCardProps, 'children'>) {
  return (
    <FloatingCard 
      depth="shallow" 
      delay={index * 0.05} 
      className="h-full" 
      {...props}
    >
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          {Icon && (
            <div className="w-10 h-10 rounded-lg bg-muted/20 flex items-center justify-center">
              <Icon className="h-5 w-5 text-muted-foreground" />
            </div>
          )}
          {change && (
            <span className={cn(
              "text-sm font-medium",
              change.startsWith('+') ? 'text-green-500' : 'text-red-500'
            )}>
              {change}
            </span>
          )}
        </div>
        <div className="text-3xl font-bold mb-1">{value}</div>
        <div className="text-sm text-muted-foreground">{label}</div>
      </div>
    </FloatingCard>
  );
}