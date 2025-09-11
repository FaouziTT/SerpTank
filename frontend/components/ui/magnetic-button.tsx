'use client';

import React, { forwardRef, useRef, useState, useImperativeHandle } from 'react';
import { cn } from '@/lib/utils';

interface MagneticButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'neon' | 'glow' | 'gradient' | 'premium' | 'glass';
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'icon';
  magneticStrength?: number;
  onPositionChange?: (x: number, y: number) => void;
  siblingPositions?: Array<{ x: number; y: number; width: number; height: number }>;
}

export const MagneticButton = forwardRef<HTMLButtonElement, MagneticButtonProps>((
  {
    children,
    className,
    variant = 'primary',
    size = 'md',
    magneticStrength = 0.3,
    onPositionChange,
    siblingPositions = [],
    ...props
  },
  ref
) => {
  const internalRef = useRef<HTMLButtonElement>(null);
  const buttonRef = internalRef;
  const [transform, setTransform] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);
  
  useImperativeHandle(ref, () => internalRef.current!);

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!buttonRef.current) return;

    const rect = buttonRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    let distanceX = (e.clientX - centerX) * magneticStrength;
    let distanceY = (e.clientY - centerY) * magneticStrength;

    // Check for collisions with sibling buttons
    siblingPositions.forEach((sibling) => {
      const dx = centerX + distanceX - sibling.x;
      const dy = centerY + distanceY - sibling.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const minDistance = (rect.width + sibling.width) / 2 + 15; // 15px buffer

      if (distance < minDistance && distance > 0) {
        // Push away from sibling
        const pushX = (dx / distance) * (minDistance - distance);
        const pushY = (dy / distance) * (minDistance - distance);
        distanceX += pushX * 0.5;
        distanceY += pushY * 0.5;
      }
    });

    setTransform({ x: distanceX, y: distanceY });
    
    // Notify parent of position change
    if (onPositionChange) {
      onPositionChange(centerX + distanceX, centerY + distanceY);
    }
  };

  const handleMouseLeave = () => {
    setTransform({ x: 0, y: 0 });
    setIsHovered(false);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
    xl: 'px-10 py-5 text-xl',
    icon: 'h-10 w-10 p-2'
  };

  const variantClasses = {
    primary: cn(
      'bg-primary text-primary-foreground',
      'hover:shadow-[0_0_20px_rgba(59,130,246,0.3)]',
      'border-2 border-transparent hover:border-primary/50'
    ),
    secondary: cn(
      'bg-secondary text-secondary-foreground',
      'hover:shadow-[0_0_15px_rgba(0,0,0,0.1)]',
      'border border-border hover:border-primary/30'
    ),
    ghost: cn(
      'bg-transparent',
      'hover:bg-primary/10',
      'border border-border hover:border-primary'
    ),
    neon: cn(
      'bg-gradient-to-r from-primary via-primary to-accent',
      'text-white font-semibold',
      'hover:shadow-[0_0_25px_rgba(59,130,246,0.3)]',
      'border border-transparent',
      'relative overflow-hidden',
      'before:absolute before:inset-0',
      'before:bg-gradient-to-r before:from-accent before:to-primary',
      'before:opacity-0 hover:before:opacity-100',
      'before:transition-opacity before:duration-300'
    ),
    glow: cn(
      'bg-primary text-white font-semibold',
      'shadow-[0_0_20px_rgba(59,130,246,0.15)]',
      'hover:shadow-[0_0_30px_rgba(59,130,246,0.3)]',
      'border border-primary/20',
      'hover:bg-primary/90',
      'relative overflow-hidden'
    ),
    gradient: cn(
      'bg-gradient-to-r from-primary to-primary/80',
      'text-white font-semibold',
      'hover:from-primary/90 hover:to-primary/70',
      'shadow-lg hover:shadow-xl',
      'border border-white/10',
      'relative overflow-hidden'
    ),
    premium: cn(
      'btn-premium',
      'text-white font-semibold',
      'border-0'
    ),
    glass: cn(
      'bg-black/20 backdrop-blur-md',
      'text-white font-semibold',
      'ring-1 ring-white/30', // Changed from border to ring to not affect height
      'shadow-[0_8px_32px_0_rgba(0,0,0,0.3)]',
      'hover:bg-black/30',
      'hover:ring-white/40',
      'hover:shadow-[0_8px_40px_0_rgba(0,0,0,0.4)]',
      'relative overflow-hidden',
      'before:absolute before:inset-0',
      'before:bg-gradient-to-b before:from-white/10 before:to-transparent',
      'before:opacity-50'
    )
  };

  return (
    <button
      ref={internalRef}
      className={cn(
        // Base styles
        'relative inline-flex items-center justify-center',
        'font-semibold rounded-xl',
        'transition-all duration-300 ease-out',
        'transform-gpu',
        'btn-magnetic',
        'isolate', // Creates stacking context to contain blur
        
        // Size
        sizeClasses[size],
        
        // Variant
        variantClasses[variant],
        
        // Hover scale
        'hover:scale-105',
        
        // Focus styles
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        
        className
      )}
      style={{
        transform: `translate(${transform.x}px, ${transform.y}px)`,
        transition: isHovered 
          ? 'transform 0.1s ease-out' 
          : 'transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onMouseEnter={handleMouseEnter}
      {...props}
    >
      {/* Glow effects based on variant */}
      {variant === 'neon' && (
        <>
          <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-primary to-accent opacity-20 blur-lg -z-10" />
          <span className="absolute inset-[-2px] rounded-xl bg-gradient-to-r from-primary via-accent to-primary opacity-75 -z-20 animate-pulse" />
        </>
      )}
      {variant === 'glow' && (
        <span className="absolute inset-0 rounded-xl bg-primary opacity-20 blur-xl -z-10 group-hover:opacity-30 transition-opacity" />
      )}
      {variant === 'gradient' && (
        <span className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
      )}
      {variant === 'premium' && (
        <span className="absolute inset-0 rounded-xl" />
      )}
      {variant === 'glass' && (
        <>
          <span className="absolute inset-0 bg-gradient-to-r from-primary/20 via-accent/20 to-primary/20 opacity-50 blur-xl -z-10 group-hover:opacity-70 transition-opacity" />
          <span className="absolute inset-[-1px] rounded-xl bg-gradient-to-r from-white/0 via-white/20 to-white/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        </>
      )}
      
      {/* Button content */}
      <span className="relative z-10 flex items-center gap-2">{children}</span>
      
      {/* Shimmer effect on hover */}
      <span className="absolute inset-0 rounded-xl overflow-hidden">
        <span className={cn(
          "absolute inset-0 -translate-x-full",
          "bg-gradient-to-r from-transparent via-white/20 to-transparent",
          "transition-transform duration-700",
          isHovered && "translate-x-full"
        )} />
      </span>
    </button>
  );
});

MagneticButton.displayName = 'MagneticButton';