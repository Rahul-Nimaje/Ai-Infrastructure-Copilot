import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  className?: string;
  children?: React.ReactNode;
}

export function EmptyState({ icon: Icon, title, description, className = "", children }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2 p-16 text-center ${className}`}>
      {Icon && <Icon className="h-8 w-8 text-muted-foreground opacity-40" />}
      <span className="text-sm font-semibold">{title}</span>
      {description && (
        <span className="text-xs text-muted-foreground">{description}</span>
      )}
      {children}
    </div>
  );
}
