import { z } from "zod";

export const roleSchema = z.object({
  name: z.string().min(2, "Role name must be at least 2 characters long").trim(),
  description: z.string().optional(),
});

export type RoleFormValues = z.infer<typeof roleSchema>;
