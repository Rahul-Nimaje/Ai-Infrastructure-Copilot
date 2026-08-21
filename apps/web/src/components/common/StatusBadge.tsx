import { Badge } from "@/components/ui/badge";
import { getStatusVariant, getStatusLabel } from "@/utils/mappers";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

/**
 * StatusBadge — renders a Badge with the correct variant based on an object map.
 * Eliminates all if/else status-to-variant logic from individual components.
 */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge variant={getStatusVariant(status)} className={className}>
      {getStatusLabel(status)}
    </Badge>
  );
}
