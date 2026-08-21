import { z } from "zod";

// CIDR only (e.g. 10.20.4.0/24) — matches the backend's expected target_range shape.
const CIDR_PATTERN = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;

export const SCAN_MODES = ["quick", "standard", "full"] as const;

export const startScanSchema = z.object({
  target_range: z
    .string()
    .min(1, "Target CIDR range is required")
    .regex(CIDR_PATTERN, "Enter a valid CIDR range, e.g. 10.20.4.0/24"),
  scan_mode: z.enum(SCAN_MODES, { message: "Select a scan mode" }),
});

export type StartScanFormValues = z.infer<typeof startScanSchema>;
