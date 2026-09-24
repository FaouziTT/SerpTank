import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}

/** Honest empty state: explains why there is no data and what to do next. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
        {Icon ? (
          <div className="bg-muted mb-4 rounded-full p-4">
            <Icon className="text-muted-foreground h-8 w-8" aria-hidden />
          </div>
        ) : null}
        <h3 className="mb-2 text-lg font-semibold">{title}</h3>
        <p className="text-muted-foreground mb-4 max-w-md text-sm">{description}</p>
        {action}
      </CardContent>
    </Card>
  );
}
