'use client';

import React, { forwardRef, useRef, useState, useImperativeHandle } from 'react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

interface CTAButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onDrag' | 'onDragStart' | 'onDragEnd' | 'onAnimationStart' | 'onAnimationEnd'> {
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'primary' | 'secondary';
  magneticStrength?: number;
  onPositionChange?: (x: number, y: number) => void;
  siblingPositions?: Array<{ x: number; y: number; width: number; height: number }>;
}

export const CTAButton = forwardRef<HTMLButtonElement, CTAButtonProps>((
  {
    children,
    className,
    size = 'lg',
    variant = 'primary',
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
  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
    xl: 'px-10 py-5 text-xl'
  };

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
      const minDistance = (rect.width + sibling.width) / 2 + 20; // 20px buffer

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

  return (
    <motion.button
      ref={internalRef}
      className={cn(
        // Base styles
        'relative inline-flex items-center justify-center',
        'font-semibold rounded-xl',
        'text-white',
        'transition-all duration-300',
        'group',
        'transform-gpu',
        
        // Size
        sizeClasses[size],
        
        // Custom styling
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
      whileHover={{ scale: isHovered ? 1.05 : 1 }}
      whileTap={{ scale: 0.95 }}
      {...props}
    >
      {/* Background layers based on variant */}
      {variant === 'primary' ? (
        <>
          <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 shadow-lg" />
          <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300 shadow-xl" />
          <span className="absolute inset-0 rounded-xl bg-blue-500/20 blur-xl group-hover:bg-blue-400/30 transition-all duration-300" />
          <span className="absolute inset-[-2px] rounded-xl bg-gradient-to-r from-blue-400 via-purple-500 to-blue-400 opacity-0 group-hover:opacity-75 blur-sm transition-opacity duration-300" />
          <span className="absolute inset-[1px] rounded-[11px] bg-gradient-to-b from-white/20 to-transparent opacity-50" />
        </>
      ) : (
        <>
          <span className="absolute inset-0 rounded-xl bg-black/20 backdrop-blur-md shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] border border-white/30" />
          <span className="absolute inset-0 rounded-xl bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          <span className="absolute inset-[1px] rounded-[11px] bg-gradient-to-b from-white/10 to-transparent opacity-50" />
        </>
      )}
      {/* Shine effect */}
      <motion.span
        className="absolute inset-0 rounded-xl overflow-hidden"
        style={{
          background: 'linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.3) 50%, transparent 60%)',
          transform: 'translateX(-100%)'
        }}
        animate={{
          transform: ['translateX(-100%)', 'translateX(100%)']
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          repeatDelay: 3,
          ease: 'easeInOut'
        }}
      />
      
      {/* Content */}
      <span className="relative z-10 flex items-center gap-2">
        {children}
      </span>
      
    </motion.button>
  );
});

CTAButton.displayName = 'CTAButton';