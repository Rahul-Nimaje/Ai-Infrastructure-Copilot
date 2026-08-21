/**
 * Debounce a function — delays invocation until after `delay` ms of inactivity.
 */
export function debounce<T extends (...args: any[]) => void>(fn: T, delay: number): T {
  let timer: ReturnType<typeof setTimeout>;
  return ((...args: any[]) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  }) as unknown as T;
}

/**
 * Throttle a function — limits invocation to at most once per `limit` ms.
 */
export function throttle<T extends (...args: any[]) => void>(fn: T, limit: number): T {
  let inThrottle = false;
  return ((...args: any[]) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  }) as unknown as T;
}

/**
 * Trigger a file download from a URL.
 */
export function downloadFile(url: string, filename?: string): void {
  const a = document.createElement("a");
  a.href = url;
  if (filename) a.download = filename;
  a.target = "_blank";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/**
 * Copy text to the clipboard.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/**
 * Remove null / undefined / empty-string fields from an object.
 */
export function removeEmptyFields<T extends Record<string, unknown>>(obj: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(obj).filter(([, v]) => v != null && v !== "")
  ) as Partial<T>;
}

/**
 * Convert an object to URL query params string.
 */
export function objectToQueryParams(obj: Record<string, string | number | boolean | undefined | null>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(obj)) {
    if (value != null && value !== "") {
      params.set(key, String(value));
    }
  }
  return params.toString();
}

/**
 * Generate select options from a string array.
 */
export function generateOptions(values: string[], allLabel = "All"): { value: string; label: string }[] {
  return [{ value: "", label: allLabel }, ...values.map((v) => ({ value: v, label: v }))];
}

/**
 * Get user initials from full name.
 */
export function getInitials(fullName: string | null | undefined, maxChars = 2): string {
  if (!fullName) return "?";
  return fullName
    .split(" ")
    .map((part) => part[0])
    .slice(0, maxChars)
    .join("")
    .toUpperCase();
}
