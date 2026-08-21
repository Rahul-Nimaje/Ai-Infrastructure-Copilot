// ─── Pagination ───────────────────────────────────────────────
export const DEFAULT_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 15;
export const PAGE_SIZE_OPTIONS = [5, 10, 15, 20, 50] as const;

// ─── Date / Time ──────────────────────────────────────────────
export const DATE_FORMAT = "MMM dd, yyyy";
export const DATETIME_FORMAT = "MMM dd, yyyy HH:mm";
export const TIME_FORMAT = "HH:mm:ss";

// ─── File Uploads ─────────────────────────────────────────────
export const MAX_CSV_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
export const ACCEPTED_CSV_TYPES = [".csv"] as const;

// ─── Polling ──────────────────────────────────────────────────
export const DEVICE_POLL_INTERVAL_MS = 5_000;
export const SCAN_POLL_INTERVAL_MS = 3_000;

// ─── Sort ─────────────────────────────────────────────────────
export type SortOrder = "asc" | "desc";
