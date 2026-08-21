interface InfoGridItem {
  label: string;
  value: React.ReactNode;
  colSpan?: 1 | 2;
  mono?: boolean;
}

interface InfoGridProps {
  items: InfoGridItem[];
  columns?: 2 | 3;
  className?: string;
}

/**
 * InfoGrid — displays key-value pairs in a consistent grid layout.
 * Replaces the repeated "rounded-lg border p-3 bg-muted/5" pattern
 * used in device overview, hardware, OS, and other detail tabs.
 */
export function InfoGrid({ items, columns = 2, className = "" }: InfoGridProps) {
  const gridCols = columns === 3 ? "grid-cols-3" : "grid-cols-2";

  return (
    <div className={`grid ${gridCols} gap-4 ${className}`}>
      {items.map((item, i) => (
        <div
          key={i}
          className={`rounded-lg border border-border p-3 bg-muted/5 ${
            item.colSpan === 2 ? "col-span-2" : ""
          }`}
        >
          <span className="text-[10px] font-bold text-muted-foreground uppercase">
            {item.label}
          </span>
          <p
            className={`text-sm font-semibold mt-1 ${
              item.mono ? "font-mono text-xs" : ""
            }`}
          >
            {item.value ?? "—"}
          </p>
        </div>
      ))}
    </div>
  );
}
