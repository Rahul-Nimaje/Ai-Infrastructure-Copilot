import { Card, CardContent } from "@/components/ui/card";
import type { StatCard } from "@/features/dashboard/types";

export function StatCards({ cards }: { cards: StatCard[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className="p-4">
            <div className="text-xs font-semibold text-muted-foreground">{card.label}</div>
            <div className="mt-2 text-2xl font-extrabold tracking-tight">{card.value}</div>
            <div className="mt-1 text-[11px] text-muted-foreground">{card.delta}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
