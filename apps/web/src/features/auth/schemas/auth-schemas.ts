import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email({ message: "Invalid email address" }),
  password: z.string().min(1, { message: "Password is required" }),
});

export const mfaSchema = z.object({
  mfaCode: z.string().length(6, { message: "MFA code must be exactly 6 digits" }).regex(/^\d+$/, { message: "MFA code must contain only digits" }),
});

export type LoginInput = z.infer<typeof loginSchema>;
export type MfaInput = z.infer<typeof mfaSchema>;
