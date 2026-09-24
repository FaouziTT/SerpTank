import { Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface LoadingStateProps {
  message?: string;
  size?: "sm" | "md" | "lg";
  fullHeight?: boolean;
}

export function LoadingState({
  message = "Loading...",
  size = "md",
  fullHeight = false,
}: LoadingStateProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
  };

  const containerClass = fullHeight ? "h-[60vh]" : "py-8";

  return (
    <Card className="border-muted/50">
      <CardContent className={`flex flex-col items-center justify-center ${containerClass}`}>
        <Loader2 className={`${sizeClasses[size]} text-primary mb-4 animate-spin`} />
        <p className="text-muted-foreground text-sm">{message}</p>
      </CardContent>
    </Card>
  );
}
