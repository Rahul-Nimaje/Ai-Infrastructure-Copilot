import { z } from "zod";

export const designationSchema = z.object({
  department_id: z.string().min(1, "Department is required"),
  name: z.string().min(1, "Designation name is required"),
  description: z.string().optional().nullable().or(z.literal("")),
  status: z.enum(["active", "inactive"]),
});

export type DesignationFormValues = z.infer<typeof designationSchema>;
