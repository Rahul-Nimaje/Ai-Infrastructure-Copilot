---
name: senior-backend-engineer
description: >-
  Use this skill when developing, refactoring, or optimizing backend services (Node.js/Express/FastAPI/Python), REST/GraphQL APIs, database queries, ORMs (Prisma/SQLAlchemy), authentication (JWT/OAuth), and background job processing.
---

# Senior Backend Engineer Skill

This skill outlines design principles, backend coding practices, schema design, and error handling strategies for services in the AI Infrastructure Copilot codebase.

## 1. REST & GraphQL API Design

- **API Standardization**:
  - Enforce clean, predictable URL hierarchies (e.g., `/api/v1/knowledge-base/documents`).
  - Use standard HTTP status codes (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`, `500 Internal Error`).
  - Standardize error response payloads: `{ "error": { "code": "INVALID_INPUT", "message": "...", "details": [...] } }`.
- **Validation & Serialization**:
  - Use Zod (TypeScript) or Pydantic (Python) for strict runtime payload validation.
  - Never allow raw user input directly into database queries or system shell executions.

## 2. Database Architecture & Data Access

- **ORM & SQL Best Practices**:
  - Write efficient Prisma or SQLAlchemy queries; prevent N+1 query problems using explicit relation includes (`include`, `joinedload`).
  - Index frequently queried columns, foreign keys, and filtering flags.
  - Implement transactions for multi-step mutations to guarantee consistency.
- **Database Migrations**:
  - Keep migration files idempotent and backward-compatible.
  - Never run destructive migrations (drop column/table) without prior multi-step field deprecation.

## 3. Asynchronous Tasks & Microservices

- **Queue Management (Celery / BullMQ)**:
  - Design idempotent tasks that can be safely retried upon network/database transient failures.
  - Set explicit task timeouts, retry limits, and dead-letter queues (DLQ) for unrecoverable errors.
  - Offload heavy operations (e.g., document parsing, embedding generation, PDF rendering) to background workers.
- **Authentication & RBAC**:
  - Enforce JWT authentication with short-lived access tokens and secure refresh token rotation.
  - Implement Role-Based Access Control (RBAC) middleware verifying permissions on every protected endpoint.

## 4. Maintenance & Debugging Runbook

1. **Performance Bottleneck Analysis**:
   - Enable query logging to identify slow SQL queries.
   - Profile event loop lag (Node.js) or GIL blockings (Python).
   - Use Redis caching for expensive recalculations or read-heavy endpoints.
2. **Handling Uncaught Exceptions**:
   - Maintain centralized exception handling middleware.
   - Ensure database transactions roll back automatically on unhandled exceptions.
