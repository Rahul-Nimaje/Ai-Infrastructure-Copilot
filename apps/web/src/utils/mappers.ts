import type { BadgeProps } from "@/components/ui/badge";
import { STATUS_BADGE_VARIANT, STATUS_LABELS } from "@/utils/constants/status.constants";
import { DEVICE_ICON_COLOR } from "@/utils/constants/device.constants";

/**
 * Map a status string to a Badge variant using the centralized object map.
 * Falls back to "muted" for unknown statuses.
 */
export function getStatusVariant(status: string | null | undefined): BadgeProps["variant"] {
  if (!status) return "muted";
  return STATUS_BADGE_VARIANT[status.toLowerCase()] ?? "muted";
}

/**
 * Map a status string to a display label.
 */
export function getStatusLabel(status: string | null | undefined): string {
  if (!status) return "Unknown";
  return STATUS_LABELS[status.toLowerCase()] ?? status;
}

/**
 * Map a device type string to a Tailwind color class for its icon.
 */
export function getDeviceIconColor(deviceType: string | null | undefined): string {
  if (!deviceType) return "text-blue-500";
  const t = deviceType.toLowerCase();
  for (const [key, color] of Object.entries(DEVICE_ICON_COLOR)) {
    if (t.includes(key)) return color;
  }
  return "text-blue-500";
}
