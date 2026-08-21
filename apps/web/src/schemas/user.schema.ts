import { z } from "zod";

export const userSchema = z.object({
  fullName: z.string().min(1, "Full name is required"),
  username: z.string().min(1, "Username is required"),
  email: z.string().email("Invalid email address"),
  password: z.string().optional().or(z.literal("")),
  employeeId: z.string().optional(),
  departmentId: z.string().min(1, "Department is required"),
  designationId: z.string().min(1, "Designation is required"),
  phoneNumber: z.string().optional(),
  status: z.enum(["active", "invited", "disabled"]),
  roles: z.array(z.string()),
});

export type UserFormValues = z.infer<typeof userSchema>;
