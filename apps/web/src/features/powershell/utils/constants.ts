export const RISK_LEVELS = {
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
} as const;

export const RISK_BADGE_VARIANTS = {
  [RISK_LEVELS.LOW]: "success",
  [RISK_LEVELS.MEDIUM]: "warning",
  [RISK_LEVELS.HIGH]: "destructive",
} as const;
