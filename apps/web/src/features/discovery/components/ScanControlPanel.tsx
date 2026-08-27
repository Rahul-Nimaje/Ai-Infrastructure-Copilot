"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Play, Square, Wifi } from "lucide-react";
import type { DeviceScan } from "@ai-infra-copilot/shared-types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { ProgressBar } from "@/components/common";
import { TextField, FormField } from "@/components/common/FormField";
import { startScanSchema, type StartScanFormValues } from "@/schemas/discovery-scan.schema";
import { SCAN_MODE_OPTIONS, DEFAULT_TARGET_RANGE, DEFAULT_SCAN_MODE } from "@/utils/constants";
import { useScanProgress } from "@/features/discovery/hooks/useScanProgress";
import { useGetLocalSubnetQuery } from "@/features/discovery/services/discovery-api";

interface ScanControlPanelProps {
  activeScan: DeviceScan | undefined;
  onStartScan: (values: StartScanFormValues) => Promise<void>;
  onStopScan: () => Promise<void>;
  isStartLoading: boolean;
  isStopLoading: boolean;
}

export function ScanControlPanel({
  activeScan,
  onStartScan,
  onStopScan,
  isStartLoading,
  isStopLoading,
}: ScanControlPanelProps) {
  const [confirmStopOpen, setConfirmStopOpen] = useState(false);
  const { scanProgress, progressPct, isLive } = useScanProgress();
  const { data: localSubnetData } = useGetLocalSubnetQuery();

  const { control, handleSubmit, watch, setValue } = useForm<StartScanFormValues>({
    resolver: zodResolver(startScanSchema),
    defaultValues: { target_range: DEFAULT_TARGET_RANGE, scan_mode: DEFAULT_SCAN_MODE },
  });
  const selectedMode = watch("scan_mode");
  const currentTarget = watch("target_range");

  // Auto-set target range from auto-detected network subnet when loaded
  useEffect(() => {
    if (localSubnetData?.suggested_target || localSubnetData?.cidr_range) {
      const autoTarget = localSubnetData.suggested_target || localSubnetData.cidr_range;
      if (!currentTarget || currentTarget === DEFAULT_TARGET_RANGE) {
        setValue("target_range", autoTarget);
      }
    }
  }, [localSubnetData, currentTarget, setValue]);

  const handleAutoDetect = () => {
    if (localSubnetData?.suggested_target || localSubnetData?.cidr_range) {
      setValue("target_range", localSubnetData.suggested_target || localSubnetData.cidr_range);
    }
  };

  const handleConfirmStop = async () => {
    await onStopScan();
  };

  return (
    <Card className="border-border/60 shadow-md">
      <CardHeader>
        <CardTitle>Discovery Control Center</CardTitle>
        <CardDescription>Initiate a new subnet sweep to populate inventory.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onStartScan)} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-foreground">Subnet Target (CIDR range) *</label>
              {localSubnetData?.local_ip && (
                <button
                  type="button"
                  onClick={handleAutoDetect}
                  className="flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline"
                  title={`Detected server IP: ${localSubnetData.local_ip}`}
                >
                  <Wifi className="h-3 w-3 text-emerald-500" />
                  Auto-detect IP ({localSubnetData.cidr_range})
                </button>
              )}
            </div>
            <TextField
              name="target_range"
              control={control}
              required
              placeholder="192.168.0.0/24"
              disabled={!!activeScan}
            />
          </div>

          <FormField label="Scan Mode" required>
            <div className="grid grid-cols-1 gap-2">
              {SCAN_MODE_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const isActive = selectedMode === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    disabled={!!activeScan}
                    onClick={() => setValue("scan_mode", opt.value)}
                    className={`flex items-start gap-2.5 rounded-lg border p-2.5 text-left transition-colors ${
                      isActive
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-muted/20"
                    } ${activeScan ? "opacity-60 cursor-not-allowed" : ""}`}
                  >
                    <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                    <div>
                      <div className="text-xs font-bold">{opt.label}</div>
                      <div className="text-[10px] text-muted-foreground">{opt.description}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </FormField>

          {activeScan ? (
            <>
              {scanProgress && (
                <ProgressBar
                  value={progressPct ?? 0}
                  indeterminate={progressPct === null}
                  label={`Phase: ${scanProgress.phase}`}
                  sublabel={`${scanProgress.devices_processed}/${scanProgress.devices_total} devices processed${!isLive ? " (live updates unavailable, refreshing periodically)" : ""}`}
                />
              )}
              <Button
                type="button"
                variant="destructive"
                onClick={() => setConfirmStopOpen(true)}
                disabled={isStopLoading}
                className="w-full gap-2 font-bold shadow"
              >
                <Square className="h-4 w-4 fill-white" />
                Terminate Current Scan
              </Button>
            </>
          ) : (
            <Button
              type="submit"
              disabled={isStartLoading}
              className="w-full gap-2 font-bold bg-gradient-to-r from-primary to-indigo-600 shadow-md text-white"
            >
              <Play className="h-4 w-4 fill-white" />
              Launch Scan Sweep
            </Button>
          )}
        </form>
      </CardContent>

      <ConfirmationDialog
        isOpen={confirmStopOpen}
        onClose={() => setConfirmStopOpen(false)}
        onConfirm={handleConfirmStop}
        title="Stop Network Scan"
        description={`This will immediately terminate the in-progress scan of ${activeScan?.target_range ?? "the target range"}. Devices not yet processed will not be inventoried in this sweep. This action cannot be undone.`}
        confirmText="Stop Scan"
        variant="destructive"
        isLoading={isStopLoading}
      />
    </Card>
  );
}
