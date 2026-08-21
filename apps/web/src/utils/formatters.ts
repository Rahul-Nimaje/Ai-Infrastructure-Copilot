/**
 * Format a date/datetime value for display.
 */
export function formatDate(
  value: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!value) return "—";
  const date = typeof value === "string" ? new Date(value) : value;
  if (isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, options);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = typeof value === "string" ? new Date(value) : value;
  if (isNaN(date.getTime())) return "—";
  return date.toLocaleString();
}

/**
 * Format byte values into human-readable sizes.
 */
export function formatBytes(bytes: number | null | undefined, decimals = 1): string {
  if (bytes == null || bytes === 0) return "—";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

/**
 * Format bytes to GB specifically (common in hardware specs).
 */
export function bytesToGB(bytes: number | null | undefined, decimals = 0): string {
  if (bytes == null || bytes === 0) return "—";
  return `${(bytes / Math.pow(1024, 3)).toFixed(decimals)} GB`;
}

/**
 * Format MHz to GHz.
 */
export function mhzToGhz(mhz: number | null | undefined, decimals = 1): string {
  if (mhz == null || mhz === 0) return "—";
  return `${(mhz / 1000).toFixed(decimals)} GHz`;
}

/**
 * Format a duration string or display a fallback.
 */
export function formatDuration(value: string | null | undefined): string {
  return value || "—";
}

/**
 * Format a currency value.
 */
export function formatCurrency(value: number, currency = "USD", locale = "en-US"): string {
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(value);
}

/**
 * Safe string display — returns "—" for null/undefined/empty.
 */
export function displayValue(value: string | number | null | undefined, fallback = "—"): string {
  if (value == null || value === "") return fallback;
  return String(value);
}
