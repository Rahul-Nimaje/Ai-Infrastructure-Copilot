---
name: senior-qa-engineer
description: >-
  Use this skill when designing testing strategies, writing unit tests (Jest/Vitest/pytest), component tests, end-to-end (E2E) automation (Playwright/Cypress), performance & load testing (k6), and evaluating system reliability.
---

# Senior QA Engineer Skill

This skill defines the quality assurance standards, test automation patterns, regression strategies, and verification workflows for the AI Infrastructure Copilot codebase.

## 1. Automated Testing Strategy & Pyramid

- **Unit Testing (Jest / Vitest / pytest)**:
  - Unit test utility functions, state transformations, business logic modules, and API route helpers.
  - Maintain high test coverage on core algorithms (e.g., token parsing, text chunking, payload validation).
  - Mock external network calls and database dependencies deterministically.
- **Integration & API Testing**:
  - Write API automation tests verifying request/response schemas, status codes, error models, and database side effects.
  - Test authentication workflows, RBAC enforcement, and invalid payload rejections.
- **End-to-End (E2E) Automation (Playwright / Cypress)**:
  - Automate critical user journeys (e.g., user login, uploading knowledge base documents, triggering AI chat queries, verifying citations).
  - Use resilient locator strategies: prefer data attributes (`data-testid`), role selectors, or aria labels over brittle CSS paths.

## 2. AI & Performance Testing

- **RAG & LLM Evaluation Framework**:
  - Test AI output consistency against benchmark evaluation datasets.
  - Validate citation link accuracy, source document matching, and fallback handling when vector retrieval yields low confidence scores.
- **Performance & Load Testing (k6 / Locust)**:
  - Simulate concurrent streaming chat requests, file uploads, and background worker queue saturation.
  - Track response latency percentiles (p90, p95, p99), throughput (RPS), and server resource consumption under load.

## 3. Test Maintenance & CI Integration

- **Flaky Test Prevention**:
  - Avoid fixed sleep/wait calls (`time.sleep` or `waitForTimeout`); use event-driven dynamic assertions (`waitForSelector`, `waitForResponse`).
  - Isolate test environments with fresh seed data or clean database transactions for every test suite execution.
- **CI Test Execution**:
  - Run fast unit tests on pre-commit hooks / PR checks.
  - Run full E2E and integration suites prior to production merge or deployment release tags.

## 4. Testing & Verification Runbook

1. **Debugging E2E Test Failures**:
   - Run Playwright in UI or debug mode: `npx playwright test --debug`.
   - Inspect captured test traces, screenshots, and console logs artifacts.
2. **Executing Local Test Suite**:
   - Web application tests: `npm run test` or `npm run test:e2e`.
   - Python AI Orchestrator tests: `pytest apps/ai-orchestrator/tests/ -v`.
