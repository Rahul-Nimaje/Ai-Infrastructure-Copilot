import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { InfrastructureCategory } from "@/features/infrastructure/types";

function barColor(pct: number): string {
  if (pct >= 85) return "bg-red-500";
  if (pct >= 65) return "bg-amber-500";
  return "bg-emerald-500";
}

function Metric({ label, pct }: { label: string; pct: number }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="text-[10.5px] font-bold uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className={`h-full rounded-full ${barColor(pct)}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs font-bold">{pct}%</div>
    </div>
  );
}

export function CategoryCard({ category }: { category: InfrastructureCategory }) {
  if (category.kind === "placeholder") {
    return (
      <Card>
        <CardContent className="flex h-full flex-col items-center justify-center gap-1 p-4 text-center text-muted-foreground">
          <div className="text-sm font-semibold text-foreground">{category.name}</div>
          <div className="text-xs">Not connected yet</div>
        </CardContent>
      </Card>
    );
  }

  const overall =
    category.critical > 0
      ? { label: "Critical", variant: "destructive" as const }
      : category.warning > 0
        ? { label: "Warning", variant: "warning" as const }
        : { label: "Healthy", variant: "success" as const };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-4 flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold">{category.name}</div>
            <div className="text-[11.5px] text-muted-foreground">{category.count} nodes</div>
          </div>
          <Badge variant={overall.variant}>{overall.label}</Badge>
        </div>

        <div className="mb-3.5 grid grid-cols-3 gap-3">
          <Metric label="CPU" pct={category.cpu} />
          <Metric label="Memory" pct={category.mem} />
          <Metric label="Disk" pct={category.disk} />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2.5 border-t border-border pt-3">
          <div className="flex flex-wrap items-center gap-1.5 text-[11.5px] text-muted-foreground">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="mr-1.5">{category.healthy} healthy</span>
            {category.warning > 0 && (
              <>
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
                <span className="mr-1.5">{category.warning} warning</span>
              </>
            )}
            {category.critical > 0 && (
              <>
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-red-500" />
                <span>{category.critical} critical</span>
              </>
            )}
          </div>
          <Link
            href={category.href}
            className="rounded-md bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:opacity-90"
          >
            Open
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
