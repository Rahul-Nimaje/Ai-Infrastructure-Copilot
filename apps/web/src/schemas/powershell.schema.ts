import { z } from "zod";

export const powerShellSchema = z.object({
  description: z.string().min(5, "Description must be at least 5 characters long").trim(),
});

export type PowerShellFormValues = z.infer<typeof powerShellSchema>;
