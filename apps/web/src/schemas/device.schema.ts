import { z } from "zod";

export const registerServerSchema = z.object({
  hostname: z.string().min(1, "Hostname is required"),
  ipAddress: z.string().optional().or(z.literal("")),
  osVersion: z.string().optional().or(z.literal("")),
  username: z.string().min(1, "WinRM username is required"),
  secret: z.string().min(1, "WinRM password is required"),
  winrmUseSsl: z.boolean(),
  winrmPort: z.string().min(1, "WinRM port is required"),
});

export type RegisterServerFormValues = z.infer<typeof registerServerSchema>;
