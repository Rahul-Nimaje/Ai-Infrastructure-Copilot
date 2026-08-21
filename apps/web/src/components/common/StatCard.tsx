import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  label: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  iconColor?: string;
  iconBgColor?: string;
  gradient?: string;
  pulse?: boolean;
  className?: string;
}

export function StatCard({
  label,
  value,
  description,
  icon: Icon,
  iconColor = "text-indigo-600",
  iconBgColor = "bg-indigo-500/10",
  gradient = "from-card to-indigo-500/5",
  pulse = false,
  className = "",
}: StatCardProps) {
  return (
    <Card className={`bg-gradient-to-br ${gradient} border-border/60 ${className}`}>
      <CardContent className="p-6 flex items-center justify-between">
        <div className="space-y-1">
          <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
            {label}
          </span>
          <div className="text-3xl font-extrabold">{value}</div>
          {description && (
            <p className="text-[10px] text-muted-foreground">{description}</p>
          )}
        </div>
        <div className={`rounded-xl ${iconBgColor} p-3 ${iconColor}`}>
          <Icon className={`h-6 w-6 ${pulse ? "animate-pulse" : ""}`} />
        </div>
      </CardContent>
    </Card>
  );
}
