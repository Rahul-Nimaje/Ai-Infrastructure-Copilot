export interface ProgressBarProps {
  /** 0-100, clamped */
  value: number;
  label?: string;
  sublabel?: string;
  size?: "sm" | "md";
  variant?: "default" | "success" | "warning" | "destructive";
  showPercentLabel?: boolean;
  /** Pulsing fill for a known-in-progress-but-no-percentage-yet state (e.g. socket connecting) */
  indeterminate?: boolean;
  className?: string;
}

const VARIANT_CLASSES: Record<NonNullable<ProgressBarProps["variant"]>, string> = {
  default: "bg-primary",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  destructive: "bg-destructive",
};

function autoVariant(value: number): NonNullable<ProgressBarProps["variant"]> {
  if (value > 90) return "destructive";
  if (value > 70) return "warning";
  return "default";
}

/**
 * Shared progress bar — replaces the hand-rolled divs previously duplicated
 * for disk/memory usage; also used for live scan progress.
 */
export function ProgressBar({
  value,
  label,
  sublabel,
  size = "md",
  variant,
  showPercentLabel = true,
  indeterminate = false,
  className = "",
}: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, value));
  const barHeight = size === "sm" ? "h-1.5" : "h-2.5";
  const resolvedVariant = variant ?? autoVariant(pct);

  return (
    <div className={`space-y-1 ${className}`}>
      {(label || (showPercentLabel && !indeterminate)) && (
        <div className="flex items-center justify-between text-xs">
          {label && <span className="font-semibold text-foreground">{label}</span>}
          {showPercentLabel && !indeterminate && (
            <span className="font-mono text-muted-foreground">{Math.round(pct)}%</span>
          )}
        </div>
      )}
      <div className={`w-full bg-muted rounded-full overflow-hidden ${barHeight}`}>
        <div
          className={`${barHeight} rounded-full transition-all ${VARIANT_CLASSES[resolvedVariant]} ${
            indeterminate ? "w-1/3 animate-pulse" : ""
          }`}
          style={indeterminate ? undefined : { width: `${pct}%` }}
        />
      </div>
      {sublabel && <p className="text-[10px] text-muted-foreground">{sublabel}</p>}
    </div>
  );
}
