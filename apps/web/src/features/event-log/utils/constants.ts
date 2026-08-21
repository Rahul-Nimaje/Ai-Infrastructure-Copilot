export const LOG_LEVELS = {
  ERROR: "error",
  CRITICAL: "critical",
  WARNING: "warning",
  INFORMATION: "information",
} as const;

export const LOG_LEVEL_VARIANTS = {
  [LOG_LEVELS.ERROR]: "destructive",
  [LOG_LEVELS.CRITICAL]: "destructive",
  [LOG_LEVELS.WARNING]: "warning",
  [LOG_LEVELS.INFORMATION]: "success",
} as const;
