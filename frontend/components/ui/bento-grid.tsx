'use client';

import React from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface BentoGridProps {
  children: React.ReactNode;
  className?: string;
}

export function BentoGrid({ children, className }: BentoGridProps) {
  return (
    <div className={cn(
      "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6",
      "auto-rows-[20rem]",
      className
    )}>
      {children}
    </div>
  );
}

interface BentoGridItemProps {
  children: React.ReactNode;
  className?: string;
  colSpan?: 1 | 2 | 3 | 4;
  rowSpan?: 1 | 2 | 3;
  delay?: number;
  gradient?: boolean;
  interactive?: boolean;
}

export function BentoGridItem({
  children,
  className,
  colSpan = 1,
  rowSpan = 1,
  delay = 0,
  gradient = false,
  interactive = true,
}: BentoGridItemProps) {
  const [mousePosition, setMousePosition] = React.useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = React.useState(false);
  const itemRef = React.useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!itemRef.current || !interactive) return;

    const rect = itemRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    setMousePosition({ x, y });
  };

  const spanClasses = {
    col: {
      1: 'col-span-1',
      2: 'col-span-1 md:col-span-2',
      3: 'col-span-1 md:col-span-2 lg:col-span-3',
      4: 'col-span-1 md:col-span-2 lg:col-span-4',
    },
    row: {
      1: 'row-span-1',
      2: 'row-span-1 md:row-span-2',
      3: 'row-span-1 md:row-span-2 lg:row-span-3',
    },
  };

  return (
    <motion.div
      ref={itemRef}
      className={cn(
        "relative group overflow-hidden rounded-2xl",
        "bg-card/50 backdrop-blur-sm",
        "border border-border/50",
        "transition-all duration-300",
        interactive && "hover:border-border hover:shadow-lg hover:shadow-primary/5",
        spanClasses.col[colSpan],
        spanClasses.row[rowSpan],
        className
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false);
        setMousePosition({ x: 0.5, y: 0.5 });
      }}
      whileHover={interactive ? { y: -4 } : {}}
    >
      {/* Gradient background */}
      {gradient && (
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-accent/5 to-transparent opacity-50" />
      )}

      {/* Interactive light effect */}
      {interactive && (
        <motion.div
          className="absolute inset-0 opacity-0 transition-opacity duration-300"
          style={{
            background: `radial-gradient(circle at ${mousePosition.x * 100}% ${mousePosition.y * 100}%, rgba(var(--primary), 0.1) 0%, transparent 50%)`,
          }}
          animate={{ opacity: isHovered ? 1 : 0 }}
        />
      )}

      {/* Content */}
      <div className="relative z-10 h-full">
        {children}
      </div>
    </motion.div>
  );
}

// Preset Bento Grid Items

export function BentoHero({
  title,
  description,
  children,
  className,
  ...props
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
} & BentoGridItemProps) {
  return (
    <BentoGridItem 
      colSpan={2} 
      rowSpan={2} 
      gradient 
      className={cn("p-8 md:p-12", className)} 
      {...props}
    >
      <div className="flex flex-col h-full">
        <div className="flex-1">
          <motion.h2 
            className="text-4xl md:text-5xl font-bold mb-4 leading-tight"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            {title}
          </motion.h2>
          {description && (
            <motion.p 
              className="text-lg text-muted-foreground mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {description}
            </motion.p>
          )}
        </div>
        {children}
      </div>
    </BentoGridItem>
  );
}

export function BentoMetric({
  value,
  label,
  icon: Icon,
  trend,
  className,
  ...props
}: {
  value: string | number;
  label: string;
  icon?: React.ElementType;
  trend?: { value: string; positive: boolean };
} & Omit<BentoGridItemProps, 'children'>) {
  return (
    <BentoGridItem className={cn("p-6", className)} {...props}>
      <div className="flex flex-col h-full">
        {Icon && (
          <div className="w-12 h-12 rounded-xl bg-muted/20 flex items-center justify-center mb-4">
            <Icon className="h-6 w-6 text-primary" />
          </div>
        )}
        <div className="flex-1">
          <div className="text-3xl md:text-4xl font-bold mb-2">{value}</div>
          <div className="text-sm text-muted-foreground">{label}</div>
        </div>
        {trend && (
          <div className={cn(
            "text-sm font-medium mt-4",
            trend.positive ? "text-green-500" : "text-red-500"
          )}>
            {trend.value}
          </div>
        )}
      </div>
    </BentoGridItem>
  );
}

export function BentoFeature({
  title,
  description,
  icon: Icon,
  children,
  className,
  ...props
}: {
  title: string;
  description: string;
  icon?: React.ElementType;
  children?: React.ReactNode;
} & Omit<BentoGridItemProps, 'children'>) {
  return (
    <BentoGridItem className={cn("p-6", className)} {...props}>
      <div className="flex flex-col h-full">
        {Icon && (
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mb-4">
            <Icon className="h-7 w-7 text-primary" />
          </div>
        )}
        <h3 className="text-xl font-semibold mb-2">{title}</h3>
        <p className="text-muted-foreground text-sm mb-4 flex-1">{description}</p>
        {children}
      </div>
    </BentoGridItem>
  );
}

export function BentoChart({
  title,
  children,
  className,
  ...props
}: {
  title?: string;
  children: React.ReactNode;
} & BentoGridItemProps) {
  return (
    <BentoGridItem 
      colSpan={2} 
      className={cn("p-6", className)} 
      {...props}
    >
      {title && (
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
      )}
      <div className="h-full">{children}</div>
    </BentoGridItem>
  );
}

export function BentoImage({
  src,
  alt,
  title,
  description,
  className,
  ...props
}: {
  src: string;
  alt: string;
  title?: string;
  description?: string;
} & BentoGridItemProps) {
  return (
    <BentoGridItem className={cn("p-0 overflow-hidden", className)} {...props}>
      <div className="relative h-full">
        <Image 
          src={src} 
          alt={alt} 
          fill
          className="object-cover"
        />
        {(title || description) && (
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent p-6 flex flex-col justify-end">
            {title && <h3 className="text-xl font-semibold text-white mb-1">{title}</h3>}
            {description && <p className="text-sm text-white/80">{description}</p>}
          </div>
        )}
      </div>
    </BentoGridItem>
  );
}