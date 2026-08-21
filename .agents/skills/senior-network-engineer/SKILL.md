---
name: senior-network-engineer
description: >-
  Use this skill when configuring, optimizing, or troubleshooting networking, API proxies, reverse proxies (Nginx/Traefik), ingress controllers, DNS, load balancing, WebSocket/gRPC streaming connections, and TLS/SSL configurations.
---

# Senior Network Engineer Skill

This skill provides architectural guidance, configuration standards, and diagnostic procedures for networking, routing, reverse proxying, and communications protocols in the AI Infrastructure Copilot system.

## 1. Gateway & Reverse Proxy Architecture

- **Nginx / Traefik Configuration**:
  - Maintain clean upstream definitions with keep-alive connections to microservices (Frontend Web, AI Orchestrator, Auth Service).
  - Configure request routing, path rewrites, headers forwarding (`X-Forwarded-For`, `X-Forwarded-Proto`, `Host`, `X-Request-ID`).
  - Set request size limits appropriate for document uploads (e.g., `client_max_body_size 50M`).
- **Load Balancing & Failover**:
  - Configure round-robin or least-connections load balancing across horizontal service instances.
  - Implement health checks and passive backend passive failure detection (`max_fails`, `fail_timeout`).

## 2. Real-Time Protocols & Streaming

- **WebSocket & Server-Sent Events (SSE)**:
  - Enable HTTP/1.1 upgrade headers (`Upgrade $http_upgrade`, `Connection "upgrade"`) for WebSocket endpoints.
  - Set appropriate proxy read timeouts (`proxy_read_timeout 3600s`) for persistent SSE connections and long-running AI generation responses.
  - Disable proxy buffering (`proxy_buffering off`) for real-time token streaming routes.
- **gRPC & HTTP/2**:
  - Configure HTTP/2 end-to-end routing for high-throughput internal microservice communications.

## 3. Network Security & Performance

- **TLS/SSL Hardening**:
  - Enforce modern TLS protocols (TLS 1.2, TLS 1.3) and strong cipher suites.
  - Automate SSL certificate renewal via Let's Encrypt / Certbot or ACME controllers.
  - Implement HSTS (HTTP Strict Transport Security) headers.
- **Rate Limiting & Protection**:
  - Implement rate limiting per IP or authenticated user to prevent API abuse (`limit_req_zone`).
  - Protect internal admin routes and database endpoints from public ingress exposure.

## 4. Diagnostics & Troubleshooting Runbook

1. **Debugging SSE / Streaming Timeouts (504 Gateway Timeout)**:
   - Check proxy timeout settings: `proxy_read_timeout`, `proxy_send_timeout`.
   - Verify `proxy_buffering off` is set for streaming endpoints (`/api/v1/chat/stream`).
2. **Diagnosing CORS & Header Issues**:
   - Check preflight `OPTIONS` request responses and allowed origins/methods/headers.
   - Ensure reverse proxy does not duplicate `Access-Control-Allow-Origin` headers injected by application services.
3. **Connectivity Testing**:
   - Test socket connection: `curl -ivN -H "Accept: text/event-stream" http://localhost:8000/health`.
   - Trace packet routing: `traceroute` or `mtr` for network latency bottlenecks.
