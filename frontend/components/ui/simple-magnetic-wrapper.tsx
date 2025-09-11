'use client';

import React, { useRef, useState, useEffect, Children, cloneElement } from 'react';

interface SimpleMagneticWrapperProps {
  children: React.ReactElement;
  magneticStrength?: number;
  horizontalStrength?: number;
  verticalStrength?: number;
  className?: string;
}

export function SimpleMagneticWrapper({ 
  children, 
  magneticStrength = 0.3,
  horizontalStrength,
  verticalStrength,
  className = ''
}: SimpleMagneticWrapperProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!wrapperRef.current) return;

    const rect = wrapperRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Use custom strengths if provided, otherwise use general magneticStrength
    const xStrength = horizontalStrength !== undefined ? horizontalStrength : magneticStrength;
    const yStrength = verticalStrength !== undefined ? verticalStrength : magneticStrength;
    
    // Restrict horizontal movement more than vertical
    const distanceX = (e.clientX - centerX) * xStrength * 0.5; // 50% of vertical movement
    const distanceY = (e.clientY - centerY) * yStrength;

    setTransform({ x: distanceX, y: distanceY });
  };

  const handleMouseLeave = () => {
    setTransform({ x: 0, y: 0 });
    setIsHovered(false);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  return (
    <div
      ref={wrapperRef}
      className={`inline-block ${className}`}
      style={{
        transform: `translate(${transform.x}px, ${transform.y}px)`,
        transition: isHovered 
          ? 'transform 0.1s ease-out' 
          : 'transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onMouseEnter={handleMouseEnter}
    >
      {children}
    </div>
  );
}