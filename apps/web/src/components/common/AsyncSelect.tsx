"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, X, Loader2, Search, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

export interface AsyncSelectOption {
  value: string;
  label: string;
}

export interface AsyncSelectFetchParams {
  search: string;
  page: number;
}

export interface AsyncSelectFetchResult {
  items: AsyncSelectOption[];
  total: number;
}

interface BaseProps {
  fetchOptions: (params: AsyncSelectFetchParams) => Promise<AsyncSelectFetchResult>;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  pageSize?: number;
  className?: string;
}

interface SingleProps extends BaseProps {
  multiple?: false;
  value: string | null;
  onChange: (value: string | null) => void;
}

interface MultiProps extends BaseProps {
  multiple: true;
  value: string[];
  onChange: (value: string[]) => void;
}

type AsyncSelectProps = SingleProps | MultiProps;

export function AsyncSelect(props: AsyncSelectProps) {
  const {
    fetchOptions,
    placeholder = "Select...",
    disabled = false,
    error,
    pageSize = 20,
    className = "",
  } = props;

  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  const [options, setOptions] = useState<AsyncSelectOption[]>([]);
  const [labelMap, setLabelMap] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const requestIdRef = useRef(0);
  const [panelRect, setPanelRect] = useState<{ top: number; left: number; width: number } | null>(null);

  const hasMore = options.length < total;

  const runFetch = useCallback(
    async (nextPage: number, searchTerm: string, append: boolean) => {
      const requestId = ++requestIdRef.current;
      setLoading(true);
      try {
        const result = await fetchOptions({ search: searchTerm, page: nextPage });
        if (requestIdRef.current !== requestId) return;
        setTotal(result.total);
        setOptions((prev) => (append ? [...prev, ...result.items] : result.items));
        setLabelMap((prev) => {
          const next = { ...prev };
          result.items.forEach((opt) => {
            next[opt.value] = opt.label;
          });
          return next;
        });
      } finally {
        if (requestIdRef.current === requestId) setLoading(false);
      }
    },
    [fetchOptions]
  );

  // Warm the label map on mount so a pre-selected value can render its label immediately.
  useEffect(() => {
    runFetch(1, "", false);
    setPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reset + refetch when the (debounced) search term changes while open.
  useEffect(() => {
    if (!open) return;
    setPage(1);
    runFetch(1, debouncedSearch, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, open]);

  const loadMore = useCallback(() => {
    if (loading || !hasMore) return;
    const nextPage = page + 1;
    setPage(nextPage);
    runFetch(nextPage, debouncedSearch, true);
  }, [loading, hasMore, page, debouncedSearch, runFetch]);

  // Infinite scroll: observe the sentinel at the bottom of the option list.
  useEffect(() => {
    if (!open || !sentinelRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore();
      },
      { root: panelRef.current }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [open, loadMore]);

  const positionPanel = useCallback(() => {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setPanelRect({ top: rect.bottom + 4, left: rect.left, width: rect.width });
  }, []);

  const handleOpen = () => {
    if (disabled) return;
    positionPanel();
    setOpen(true);
    setSearch("");
    setTimeout(() => searchInputRef.current?.focus(), 0);
  };

  useEffect(() => {
    if (!open) return;
    const handleReposition = () => positionPanel();
    const handleOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (panelRef.current?.contains(target) || triggerRef.current?.contains(target)) return;
      setOpen(false);
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("resize", handleReposition);
    window.addEventListener("scroll", handleReposition, true);
    document.addEventListener("mousedown", handleOutside);
    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("resize", handleReposition);
      window.removeEventListener("scroll", handleReposition, true);
      document.removeEventListener("mousedown", handleOutside);
      window.removeEventListener("keydown", handleKey);
    };
  }, [open, positionPanel]);

  const isSelected = (optionValue: string) =>
    props.multiple ? props.value.includes(optionValue) : props.value === optionValue;

  const handleSelect = (optionValue: string) => {
    if (props.multiple) {
      const current = props.value;
      const next = current.includes(optionValue)
        ? current.filter((v) => v !== optionValue)
        : [...current, optionValue];
      props.onChange(next);
    } else {
      props.onChange(optionValue);
      setOpen(false);
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (props.multiple) props.onChange([]);
    else props.onChange(null);
  };

  const displayLabel = props.multiple
    ? props.value.length === 0
      ? placeholder
      : props.value.map((v) => labelMap[v] ?? v).join(", ")
    : props.value
    ? labelMap[props.value] ?? props.value
    : placeholder;

  const hasValue = props.multiple ? props.value.length > 0 : !!props.value;

  return (
    <div className={cn("relative w-full", className)}>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : handleOpen())}
        className={cn(
          "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed",
          error && "border-destructive focus:ring-destructive"
        )}
      >
        <span className={cn("truncate text-left", !hasValue && "text-muted-foreground")}>{displayLabel}</span>
        <span className="flex items-center gap-1 shrink-0">
          {hasValue && !disabled && (
            <X className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" onClick={handleClear} />
          )}
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </span>
      </button>
      {error && <p className="mt-1 text-xs font-medium text-destructive">{error}</p>}

      {open &&
        panelRect &&
        createPortal(
          <div
            ref={panelRef}
            style={{
              position: "fixed",
              top: panelRect.top,
              left: panelRect.left,
              width: panelRect.width,
              pointerEvents: "auto",
            }}
            className="z-[60] rounded-md border border-border bg-card text-card-foreground shadow-lg"
          >
            <div className="flex items-center gap-2 border-b border-border p-2">
              <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <input
                ref={searchInputRef}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search..."
                className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
            </div>
            <div className="max-h-[240px] overflow-y-auto p-1">
              {options.length === 0 && !loading && (
                <div className="p-3 text-center text-xs text-muted-foreground">No results found</div>
              )}
              {options.map((opt) => {
                const selected = isSelected(opt.value);
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleSelect(opt.value)}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 rounded-sm px-2.5 py-2 text-left text-sm hover:bg-muted",
                      selected && "bg-primary/5 font-medium text-primary"
                    )}
                  >
                    <span className="truncate">{opt.label}</span>
                    {selected && <Check className="h-3.5 w-3.5 shrink-0" />}
                  </button>
                );
              })}
              <div ref={sentinelRef} />
              {loading && (
                <div className="flex items-center justify-center gap-1.5 p-3 text-xs text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Loading...
                </div>
              )}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
