---
name: senior-ai-engineer
description: >-
  Use this skill when designing, building, optimizing, or debugging AI/ML features, RAG (Retrieval-Augmented Generation) pipelines, LLM orchestrations, prompt templates, vector databases, model integrations, and evaluation frameworks.
---

# Senior AI Engineer Skill

This skill provides comprehensive patterns, architectural guidelines, and runbooks for AI Engineering, LLM orchestration, and RAG systems within the AI Infrastructure Copilot codebase.

## 1. RAG & Retrieval Architecture

- **Document Ingestion & Chunking**:
  - Implement semantic chunking or dynamic sliding window chunking tailored to document types (e.g., code, markdown, PDF documentation, log files).
  - Include rich metadata (source, section, line numbers, document title, timestamps, access level) in chunks to enable hybrid filtering.
- **Embedding & Vector Search**:
  - Use high-performance embedding models with appropriate dimensional vectors.
  - Implement vector store indexing strategies (e.g., HNSW with cosine or dot product similarity).
  - Use hybrid retrieval combining BM25 keyword search with dense vector embeddings to maximize precision and recall.
- **Reranking & Context Compression**:
  - Apply cross-encoder reranking models (e.g., Cohere Rerank, BGE Reranker) to rank top candidate chunks.
  - Compress context windows by eliminating duplicate information and irrelevant content before passing to LLMs.

## 2. LLM Orchestration & Agentic Workflows

- **Agent Patterns**:
  - Use structured, single-responsibility agents (e.g., Planner, Retriever, Execution, Evaluator).
  - Enforce explicit state transitions and schema validation using Pydantic or TypeScript Zod.
- **Prompt Engineering & Tool Use**:
  - Maintain system prompts in dedicated template modules; avoid inline hardcoded prompt strings.
  - Enforce strict JSON output parsing or Function Calling / Structured Outputs schemas.
  - Include explicit fallback mechanisms (e.g., retry logic with backoff, schema repair prompts).
- **Latency & Streaming**:
  - Implement Server-Sent Events (SSE) or WebSockets for real-time streaming of response tokens and tool invocation steps.
  - Implement caching (Redis / Semantic Cache) for frequent embeddings and common queries.

## 3. Quality, Safety & Evaluation

- **Hallucination & Citation Verification**:
  - Ground all generated answers strictly in retrieved contexts with inline source citations.
  - Implement verification passes to audit generated outputs against source document snippets.
- **Guardrails & Security**:
  - Sanitize user inputs against prompt injection and jailbreak attempts.
  - Filter output for sensitive information (PII, credentials, internal infrastructure tokens).
- **Evaluation Benchmarks**:
  - Track RAG performance metrics: Context Precision, Context Recall, Faithfulness, Answer Relevance.

## 4. Troubleshooting & Debugging Runbook

1. **Low Retrieval Precision**:
   - Inspect chunk sizes and overlap parameters.
   - Verify metadata pre-filtering logic in vector store queries.
   - Adjust hybrid search weights (dense vs sparse weighting).
2. **High Latency / Time-To-First-Token**:
   - Profile embedding generation vs LLM generation latency.
   - Ensure streaming output is enabled end-to-end.
   - Verify connection pooling to vector databases and Redis caches.
