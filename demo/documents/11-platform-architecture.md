# Platform Architecture — AI Knowledge & Action Platform

## Overview
The platform is a knowledge and action system built in three layers:
an Angular frontend, a FastAPI backend and an agent engine based on LangGraph.

The goal is to answer questions using your own documents, execute tools
and require human approval before sensitive actions.

## Components
- Angular 20 frontend served on port 4200. It calls the API on port 8000.
- FastAPI backend with automatic OpenAPI documentation at /docs.
- PostgreSQL 17 with the pgvector extension for semantic search.
- Redis 7 as the query embedding cache and rate-limit counter.
- LangGraph 1.x to orchestrate the agent graph and persistent memory.

## Ingestion flow
1. The user uploads a PDF, TXT or MD file of up to 10 MB.
2. The parser extracts clean text.
3. The chunker splits the text into fragments of 1000 characters with 200 overlap.
4. Each fragment becomes a 384-dimension vector using
   sentence-transformers paraphrase-multilingual-MiniLM-L12-v2.
5. Vectors are stored in the embedding column of type VECTOR(384) in pgvector.

## Query flow
The question is embedded and compared with the stored fragments using
cosine distance. The most similar fragments are sent to the language model
as context so it can generate an answer with citations.

## Conversation persistence
LangGraph uses AsyncPostgresSaver as its checkpointer, so every conversation thread
(thread_id) keeps its state and can be resumed.

## Observability
The API exposes /health, /health/ready and /health/live, plus Prometheus metrics
at /metrics. Logs are structured JSON with a request_id per request.

## Security
CORS restricted to the frontend origin, per-client rate limiting
and strict validation of file size and type on upload.

## Deployment
The development environment runs with Docker Compose: db, redis, api and the Angular dev server.
In production, a managed database should be separated from the application plane.
