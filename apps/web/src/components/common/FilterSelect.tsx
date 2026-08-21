import { Label } from "@/components/ui/label";

export interface SelectOption {
  value: string;
  label: string;
}

interface FilterSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: readonly SelectOption[] | SelectOption[];
  disabled?: boolean;
  className?: string;
  size?: "sm" | "md";
}

export function FilterSelect({
  label,
  value,
  onChange,
  options,
  disabled = false,
  className = "",
  size = "sm",
}: FilterSelectProps) {
  const heightClass = size === "sm" ? "h-8" : "h-10";

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <Label className="text-[10px] font-bold text-muted-foreground uppercase">
        {label}
      </Label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`${heightClass} rounded border border-border bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50`}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
