"use client";

import { ArrowUpDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "./EmptyState";
import { LoadingState } from "./LoadingState";
import { Pagination } from "./Pagination";
import type { LucideIcon } from "lucide-react";

// ─── Column Definition ────────────────────────────────────────
export interface DataTableColumn<T> {
  key: string;
  header: string;
  sortable?: boolean;
  className?: string;
  headerClassName?: string;
  render: (row: T) => React.ReactNode;
}

// ─── Props ────────────────────────────────────────────────────
interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  data: T[];
  loading?: boolean;
  loadingMessage?: string;

  // Empty state
  emptyIcon?: LucideIcon;
  emptyTitle?: string;
  emptyDescription?: string;

  // Row
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  isRowActive?: (row: T) => boolean;

  // Selection
  selectable?: boolean;
  selectedIds?: string[];
  onSelectAll?: () => void;
  onSelectRow?: (id: string) => void;

  // Sorting
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  onSort?: (field: string) => void;

  // Pagination
  page?: number;
  pageSize?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  paginationLabel?: string;

  // Styling
  className?: string;
  minWidth?: string;
}

export function DataTable<T>({
  columns,
  data,
  loading = false,
  loadingMessage = "Loading...",
  emptyIcon,
  emptyTitle = "No data found",
  emptyDescription,
  rowKey,
  onRowClick,
  isRowActive,
  selectable = false,
  selectedIds = [],
  onSelectAll,
  onSelectRow,
  sortBy,
  sortOrder,
  onSort,
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  paginationLabel = "items",
  className = "",
  minWidth = "700px",
}: DataTableProps<T>) {
  return (
    <Card className={`border-border/60 shadow-md ${className}`}>
      <CardContent className="p-0 overflow-x-auto">
        {loading ? (
          <LoadingState message={loadingMessage} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={emptyIcon}
            title={emptyTitle}
            description={emptyDescription}
          />
        ) : (
          <table className={`w-full border-collapse text-left text-xs`} style={{ minWidth }}>
            <thead>
              <tr className="border-b border-border bg-muted/20 text-muted-foreground font-bold uppercase tracking-wider">
                {selectable && (
                  <th className="p-3 w-[40px]">
                    <input
                      type="checkbox"
                      checked={selectedIds.length === data.length && data.length > 0}
                      onChange={onSelectAll}
                      className="rounded border-border"
                    />
                  </th>
                )}
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`p-3 ${col.sortable ? "cursor-pointer hover:text-foreground" : ""} ${col.headerClassName ?? ""}`}
                    onClick={col.sortable && onSort ? () => onSort(col.key) : undefined}
                  >
                    <div className="flex items-center gap-1">
                      {col.header}
                      {col.sortable && (
                        <ArrowUpDown
                          className={`h-3 w-3 ${sortBy === col.key ? "text-foreground" : "text-muted-foreground/50"}`}
                        />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {data.map((row) => {
                const id = rowKey(row);
                const isSelected = selectedIds.includes(id);
                const isActive = isRowActive?.(row) ?? false;

                return (
                  <tr
                    key={id}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={`hover:bg-muted/30 transition-colors ${
                      onRowClick ? "cursor-pointer" : ""
                    } ${isActive || isSelected ? "bg-primary/5 hover:bg-primary/5" : ""}`}
                  >
                    {selectable && (
                      <td className="p-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            e.stopPropagation();
                            onSelectRow?.(id);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="rounded border-border"
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td key={col.key} className={`p-3 ${col.className ?? ""}`}>
                        {col.render(row)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </CardContent>

      {page != null && pageSize != null && total != null && onPageChange && (
        <Pagination
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
          summaryLabel={paginationLabel}
        />
      )}
    </Card>
  );
}
