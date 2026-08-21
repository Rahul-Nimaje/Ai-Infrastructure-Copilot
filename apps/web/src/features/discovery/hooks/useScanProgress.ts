import { useCallback, useState } from "react";
import type { ScanProgressEvent, ScanCompletedEvent, DeviceProgressEvent } from "@ai-infra-copilot/shared-types";
import { useSocketContext } from "@/providers/socket-provider";
import { useSocketEvent } from "@/hooks/useSocketEvent";
import { useAppDispatch } from "@/hooks/store-hooks";
import { apiSlice } from "@/store/api-slice";

const TERMINAL_STATUSES = new Set(["completed", "partial", "failed", "credentials_required", "cancelled"]);

/**
 * Live scan/device progress, driven by the discovery.scan.progress /
 * discovery.device.progress socket events. The existing RTK Query polling
 * (5s devices / 3s scans) keeps running underneath as a safety net — this
 * hook only drives the live progress bar/phase text and triggers an early
 * cache refresh on terminal events so the UI doesn't wait for the next poll.
 */
export function useScanProgress() {
  const { connected } = useSocketContext();
  const dispatch = useAppDispatch();
  const [scanProgress, setScanProgress] = useState<ScanProgressEvent | null>(null);
  const [lastDeviceEvent, setLastDeviceEvent] = useState<DeviceProgressEvent | null>(null);

  const onScanProgress = useCallback(
    (evt: ScanProgressEvent) => {
      setScanProgress(evt);
    },
    []
  );

  const onScanCompleted = useCallback(
    (evt: ScanCompletedEvent) => {
      setScanProgress(null);
      dispatch(apiSlice.util.invalidateTags(["Devices", "Scans"]));
    },
    [dispatch]
  );

  const onDeviceProgress = useCallback(
    (evt: DeviceProgressEvent) => {
      setLastDeviceEvent(evt);
      if (TERMINAL_STATUSES.has(evt.status)) {
        dispatch(apiSlice.util.invalidateTags(["Devices"]));
      }
    },
    [dispatch]
  );

  useSocketEvent("discovery.scan.progress", onScanProgress);
  useSocketEvent("discovery.scan.completed", onScanCompleted);
  useSocketEvent("discovery.device.progress", onDeviceProgress);

  const progressPct =
    scanProgress && scanProgress.devices_total > 0
      ? Math.round((scanProgress.devices_processed / scanProgress.devices_total) * 100)
      : null;

  return { scanProgress, lastDeviceEvent, progressPct, isLive: connected };
}
