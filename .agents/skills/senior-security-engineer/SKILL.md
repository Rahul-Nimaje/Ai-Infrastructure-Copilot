---
name: senior-security-engineer
description: >-
  Use this skill when auditing, implementing, or hardening application security, secret management, OWASP top 10 defenses, prompt injection defenses, encryption, compliance, vulnerability scans, and access control models (RBAC/ABAC).
---

# Senior Security Engineer Skill

This skill provides guidelines, security controls, threat mitigation techniques, and compliance checks for securing the AI Infrastructure Copilot codebase, data, and operations.

## 1. Application & API Security

- **OWASP Top 10 Safeguards**:
  - Enforce strict input validation and output encoding to eliminate SQL injection, command injection, and Cross-Site Scripting (XSS).
  - Use parameterized queries exclusively; forbid raw string concatenation in database calls.
  - Implement CSRF protection for cookie-authenticated sessions and enforce strict `SameSite` flags.
- **Authentication & Authorization**:
  - Hash passwords using bcrypt, Argon2, or PBKDF2 with high cost factors.
  - Require MFA capability for administrative roles.
  - Enforce principle of least privilege in RBAC permissions across all API endpoints.

## 2. AI & LLM Specific Security

- **Prompt Injection Defense**:
  - Delimit user inputs clearly within LLM prompts (e.g., system vs user boundaries).
  - Use secondary validation agents or safety classifiers to inspect inputs/outputs for malicious prompt overrides or jailbreaks.
- **Data Leakage & Privacy**:
  - Redact PII (Personally Identifiable Information), API keys, passwords, and private credentials prior to sending prompts to external LLM provider APIs.
  - Ensure multi-tenant vector store collections enforce tenant isolation at query time.

## 3. Secrets & Data Protection

- **Secret Management**:
  - Never commit credentials, private keys, or API tokens into version control (`.env` files must be in `.gitignore`).
  - Access runtime secrets via environment variables or secret managers (e.g., HashiCorp Vault, AWS Secrets Manager).
- **Data Encryption**:
  - Enforce TLS 1.3/1.2 for all data in transit.
  - Encrypt sensitive database columns (e.g., third-party access tokens, connection strings) at rest using AES-256-GCM.

## 4. Audit & Incident Response Runbook

1. **Security Vulnerability Scanning**:
   - Run dependency vulnerability checks: `npm audit` / `pip-audit`.
   - Scan container images for vulnerabilities: `trivy image <image_name>`.
2. **Investigating Compromised Tokens / Credentials**:
   - Immediately revoke active JWT refresh tokens in Redis / Database.
   - Rotate affected credentials/API keys in secret manager and restart services.
   - Inspect security audit logs for unauthorized access patterns.
