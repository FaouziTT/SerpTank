"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "vertical" | "horizontal" | "both";
}

// Simple scroll area component as a placeholder until @radix-ui/react-scroll-area is installed
const ScrollArea = React.forwardRef<HTMLDivElement, ScrollAreaProps>(
  ({ className, children, orientation = "vertical", ...props }, ref) => {
    const scrollbarStyles = {
      vertical: "overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent",
      horizontal:
        "overflow-x-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent",
      both: "overflow-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent",
    };

    return (
      <div ref={ref} className={cn("relative", scrollbarStyles[orientation], className)} {...props}>
        {children}
      </div>
    );
  },
);

ScrollArea.displayName = "ScrollArea";

export { ScrollArea };
