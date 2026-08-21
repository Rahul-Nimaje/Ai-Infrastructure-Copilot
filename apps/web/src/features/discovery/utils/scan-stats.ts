import type { Device } from "@ai-infra-copilot/shared-types";

export interface DeviceStats {
  total: number;
  online: number;
  offline: number;
  scanning: number;
  completed: number;
  failed: number;
  credentialsRequired: number;
}

const SCANNING_STATUSES = new Set(["discovered", "identifying", "scanning"]);

/** Pure aggregation over the current page of devices — mirrors the pattern
 * used by features/infrastructure/utils/infrastructure.utils.ts. Note this
 * only reflects the *current page*, not the full org-wide device set (the
 * device list endpoint doesn't return org-wide aggregates) — acceptable for
 * an at-a-glance dashboard row, not meant to be a precise report. */
export function computeDeviceStats(devices: Device[], total: number): DeviceStats {
  return devices.reduce<DeviceStats>(
    (acc, d) => {
      if (d.status?.toLowerCase() === "online") acc.online += 1;
      if (d.status?.toLowerCase() === "offline") acc.offline += 1;
      if (d.scan_status && SCANNING_STATUSES.has(d.scan_status)) acc.scanning += 1;
      if (d.scan_status === "completed") acc.completed += 1;
      if (d.scan_status === "failed") acc.failed += 1;
      if (d.scan_status === "credentials_required") acc.credentialsRequired += 1;
      return acc;
    },
    { total, online: 0, offline: 0, scanning: 0, completed: 0, failed: 0, credentialsRequired: 0 }
  );
}
