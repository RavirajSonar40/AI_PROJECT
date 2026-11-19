# Hosted deployment

This repository is prepared for the following split deployment:

- **Supabase**: PostgreSQL with the `vector` extension enabled.
- **Railway**: Redis service.
- **Render**: FastAPI backend from `Dockerfile`, with `/health/ready` as its health check and a ten-minute cron health check.
- **Vercel**: Angular frontend from the `frontend` directory.

## 1. Supabase

Create a project, enable the `vector` extension in Database → Extensions, and copy the connection string. Render should receive it as `DATABASE_URL`. Use the SQLAlchemy form expected by this app:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres
```

If Supabase provides a pooled URL, keep the `postgresql` host/port/user/password values but use the `postgresql+psycopg` scheme.

## 2. Railway Redis

Create a Redis service and copy its private connection URL into Render as `REDIS_URL`.

## 3. Render backend

Create a Blueprint from this repository. `render.yaml` creates the API and the health-check cron. Set these secret values in Render:

- `DATABASE_URL`: Supabase connection string
- `REDIS_URL`: Railway Redis URL
- `GROQ_API_KEY`: provider key used by the production LLM configuration
- `FRONTEND_ORIGIN`: the Vercel production URL; comma-separate additional preview origins if needed

The container runs `alembic upgrade head` before Uvicorn, so the Supabase schema is migrated on first deploy. Render supplies `PORT`; the container uses it automatically.

The web service is configured as Render `starter` so it remains continuously available. The cron is an additional requested liveness check, not a replacement for an always-on plan.

## 4. Vercel frontend

Import the repository into Vercel and set the project root to `frontend`. Set the build command to `npm run build` and the output directory to `dist/frontend/browser`.

Add a Vercel environment variable:

```text
API_URL=https://YOUR-RENDER-SERVICE.onrender.com
```

The build writes this value into `config.js`. For local Docker, the default remains `/api`, which is proxied by Nginx to the backend container.

## Health endpoints

- `GET /health/live`: process liveness, used by the cron
- `GET /health/ready`: database and Redis readiness, used by Render
