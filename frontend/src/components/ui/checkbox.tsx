"use client";

import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  onCheckedChange?: (checked: boolean) => void;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, onCheckedChange, ...props }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      props.onChange?.(e);
      onCheckedChange?.(e.target.checked);
    };

    return (
      <div className="relative">
        <input
          type="checkbox"
          className={cn(
            "peer border-primary focus-visible:ring-ring h-4 w-4 shrink-0 rounded-sm border shadow focus-visible:ring-1 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
            "cursor-pointer appearance-none",
            "checked:bg-primary checked:border-primary",
            className,
          )}
          ref={ref}
          onChange={handleChange}
          {...props}
        />
        <Check className="text-primary-foreground pointer-events-none absolute top-0.5 left-0.5 h-3 w-3 opacity-0 peer-checked:opacity-100" />
      </div>
    );
  },
);
Checkbox.displayName = "Checkbox";

export { Checkbox };
