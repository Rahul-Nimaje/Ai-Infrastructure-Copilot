---
name: senior-infrastructure-engineer
description: >-
  Use this skill when designing, provisioning, managing, or troubleshooting infrastructure, process orchestration (PM2/Docker/K8s), containerization, CI/CD pipelines, database persistence, and system monitoring.
---

# Senior Infrastructure Engineer Skill

This skill provides operational patterns, deployment strategies, and runbooks for managing infrastructure, processes, and service reliability across the AI Infrastructure Copilot environment.

## 1. Process Management & Application Runtime

- **PM2 Orchestration**:
  - Maintain process declarations in `ecosystem.config.js` with structured application entries (`web`, `ai-orchestrator`, `celery-worker`).
  - Configure log file paths (`out_file`, `error_file`, `combine_logs`), log rotation, and environment variable isolation (`production`, `development`).
  - Set cluster/fork modes, restart backoff delays, and auto-restart resource thresholds (e.g., max memory restart limit).
- **Containerization & Docker**:
  - Maintain multi-stage Dockerfiles optimizing image layer caching and minimal production runtime footprints (e.g., Alpine or Distroless base images).
  - Ensure non-root container users for production security.
  - Utilize docker-compose for local environment replication (PostgreSQL, Redis, Vector DB, worker nodes).

## 2. Database & State Management

- **PostgreSQL & Migration Management**:
  - Enforce schema management via Prisma ORM / Alembic migrations.
  - Execute schema synchronization carefully to prevent database drift or locks on large tables.
  - Configure connection pooling (e.g., PgBouncer, Prisma connection pools) to handle high concurrent connection limits.
- **Caching & Message Broker (Redis)**:
  - Configure Redis memory evictions strategies (e.g., `volatile-lru`) and persistence policies (AOF/RDB).
  - Separate volatile cache key spaces from persistent background task queues (Celery/BullMQ).

## 3. CI/CD & Observability

- **CI/CD Pipelines**:
  - Build automated workflows for linting, type-checking, automated testing, and security scanning on pull requests.
  - Enforce atomic deployment steps with automatic rollback capability on health check failures.
- **Monitoring & Log Aggregation**:
  - Instrument metrics collection for CPU, memory, event loop lag, HTTP status rates, and worker queue depths.
  - Centralize structured JSON logging across all services.

## 4. Operational Runbooks

1. **Investigating PM2 Service Failures**:
   - Run `pm2 status` and `pm2 logs <app-name> --lines 100` to inspect uncaught exceptions.
   - Check system memory (`free -h`) and disk usage (`df -h`).
   - Reload process without downtime: `pm2 reload ecosystem.config.js --env production`.
2. **Handling Celery / Worker Queue Backlog**:
   - Check worker process availability: `celery -A app.celery_app inspect active`.
   - Monitor Redis queue length and scale consumer concurrency if worker nodes are bottlenecked.
