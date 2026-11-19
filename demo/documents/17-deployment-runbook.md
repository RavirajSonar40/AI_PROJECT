# Deployment and Operations Runbook

## Requirements
- Docker Desktop with at least 8 GB of RAM allocated.
- Node.js 20 and npm for the frontend.
- Environment variables configured in the .env file.

## Starting the environment
1. Start the infrastructure: docker compose up -d db redis.
2. Apply migrations: docker compose run --rm api alembic upgrade head.
3. Start the API: docker compose up -d api.
4. Start the frontend: npm start inside the frontend directory.

## Health checks
- GET /health returns the API's general status.
- GET /health/ready confirms connectivity to PostgreSQL and Redis.
- GET /health/live shows the process is alive.

If /health/ready fails, check the database credentials first
and then connectivity to Redis.

## Default ports
- 8000: FastAPI backend.
- 4200: Angular frontend.
- 5434: PostgreSQL on the host, mapped to 5432 in the container.
- 5433: test database.
- 6379: Redis.

## Common problems
### The API will not start
Check the logs with docker compose logs api.
Connection errors usually mean the database is not ready yet.

### Embedding generation fails
The first use downloads the model from Hugging Face.
If the cache directory is not writable, the process fails with permission denied.
Fix: point HOME and HF_HOME to a writable directory.

### Migration fails on the vector extension
The pgvector extension must exist before creating VECTOR columns.
Run CREATE EXTENSION IF NOT EXISTS vector in the database.

### 429 Too Many Requests
The per-minute request limit has been exceeded.
Wait until the value in the Retry-After header.

## Backups
PostgreSQL is dumped daily at 03:00 and kept for 30 days.
Uploaded files are backed up weekly.

## Updating dependencies
Update one dependency at a time, run the test suite
and check quality metrics before deploying.

## Rollback
Keep the previous image tagged. If a deployment fails,
redeploy the previous tag and restore the last dump if a destructive migration ran.
