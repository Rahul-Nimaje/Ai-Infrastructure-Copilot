import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PageHeaderAction {
  label: string;
  icon?: LucideIcon;
  onClick: () => void;
  disabled?: boolean;
  variant?: "default" | "outline" | "ghost" | "destructive";
  className?: string;
}

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: PageHeaderAction[];
  children?: React.ReactNode;
}

export function PageHeader({ title, description, actions, children }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {(actions || children) && (
        <div className="flex flex-wrap items-center gap-3 self-start md:self-center">
          {actions?.map((action) => {
            const Icon = action.icon;
            return (
              <Button
                key={action.label}
                variant={action.variant ?? "default"}
                onClick={action.onClick}
                disabled={action.disabled}
                className={`gap-2 ${action.className ?? ""}`}
              >
                {Icon && <Icon className="h-4 w-4" />}
                {action.label}
              </Button>
            );
          })}
          {children}
        </div>
      )}
    </div>
  );
}
