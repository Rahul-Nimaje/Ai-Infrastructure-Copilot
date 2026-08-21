export const CHAT_ROLES = {
  USER: "user",
  ASSISTANT: "assistant",
  AGENT_STEP: "agent_step",
} as const;

export const PROPOSALS_RISK_VARIANTS = {
  high: "destructive",
  low: "success",
  medium: "warning",
} as const;
