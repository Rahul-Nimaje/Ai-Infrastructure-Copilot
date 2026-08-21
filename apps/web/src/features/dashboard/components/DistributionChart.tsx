import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DistributionRow } from "@/features/dashboard/types";

export function DistributionChart({
  title,
  rows,
  barColor,
}: {
  title: string;
  rows: DistributionRow[];
  barColor: (label: string) => string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center gap-2.5">
            <span className="w-20 flex-shrink-0 text-xs text-muted-foreground">{row.label}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
              <div className={`h-full rounded-full ${barColor(row.label)}`} style={{ width: `${row.pct}%` }} />
            </div>
            <span className="w-6 flex-shrink-0 text-right text-xs font-bold">{row.count}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
