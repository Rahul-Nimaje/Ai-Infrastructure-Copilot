// Request/response envelope shapes per docs/05-api-design.md Section 1.
import type { User } from "../entities";

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id: string;
  };
}

export interface ApiSuccess<T> {
  data: T;
}

export interface ApiListSuccess<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number;
  mfa_required?: boolean;
  mfa_challenge_id?: string;
  user?: User;
}

export interface MfaVerifyRequest {
  mfa_challenge_id: string;
  code: string;
}

export interface GenerateScriptRequest {
  description: string;
  target_server_id?: string;
  language: "powershell" | "bash";
}

export interface ExecuteScriptRequest {
  target_server_id: string;
  parameters?: Record<string, unknown>;
}

export interface ApproveTaskRequest {
  comment?: string;
}

export interface RejectTaskRequest {
  reason: string;
}

export interface SendMessageRequest {
  content: string;
}
