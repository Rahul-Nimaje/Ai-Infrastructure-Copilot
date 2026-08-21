import type { BadgeProps } from "@/components/ui/badge";

// ─── Generic status → badge variant mapping ───────────────────
export const STATUS_BADGE_VARIANT: Record<string, BadgeProps["variant"]> = {
  online: "success",
  active: "success",
  running: "success",
  up: "success",
  completed: "success",

  offline: "destructive",
  disabled: "destructive",
  failed: "destructive",
  down: "destructive",
  critical: "destructive",

  warning: "warning",
  pending: "warning",
  invited: "warning",
  idle: "warning",

  unknown: "muted",
  stopped: "muted",
};

// ─── Status display labels (title-cased) ──────────────────────
export const STATUS_LABELS: Record<string, string> = {
  online: "Online",
  offline: "Offline",
  active: "Active",
  disabled: "Disabled",
  invited: "Invited",
  running: "Running",
  pending: "Pending",
  completed: "Completed",
  failed: "Failed",
  idle: "Idle",
  up: "Up",
  down: "Down",
  stopped: "Stopped",
  unknown: "Unknown",
};

// ─── User status filter options ───────────────────────────────
export const USER_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "invited", label: "Invited" },
  { value: "disabled", label: "Disabled" },
] as const;

// ─── Scan status filter options ───────────────────────────────
export const SCAN_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
] as const;

// ─── Common active/inactive status options ───────────────────
export const COMMON_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
] as const;

