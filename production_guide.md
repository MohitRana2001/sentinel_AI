# Sentinel AI Production Guide

This checklist summarises the steps required to run Sentinel AI in a production (or air-gapped) environment. Use it alongside `using_gemma.md` and `using_alloy_db.md` for component-specific instructions.

## 1. Core Services

| Service | Notes |
|---------|-------|
| **FastAPI backend** | Run with `uvicorn main:app --host 0.0.0.0 --port 8000`. Configure via environment variables; no hot reload in production. |
| **Redis** | Required for Pub/Sub between the upload API and the processors. Use a dedicated Redis instance or enable persistence (`appendonly yes`) for crash recovery. |
| **Document Processor** | Long-running worker (`python processors/document_processor_service.py`). Needs Tesseract, PyMuPDF, dl_translate models, and access to the embedding LLM. |
| **Graph Processor** | Worker (`python processors/graph_processor_service.py`). Requires Neo4j (optional but recommended) and the graph LLM. |
| **Audio/Video Processor** | Optional worker for multimodal transcription. Requires GPU-accessible Gemma3:12b. |
| **Neo4j** | Stores knowledge graphs. Run as a managed cluster or single instance depending on scale. |
| **AlloyDB / PostgreSQL** | Primary application database with pgvector. |
| **Ollama (Gemma models)** | Hosts the summarisation, graph, chat, and embedding models. Ensure each model is pulled and warmed up. |

## 2. Environment Configuration

1. Copy `.env.example` to `.env` and `.env.local`.
2. Set `USE_SQLITE_FOR_DEV=false` for production and point to AlloyDB (see `using_alloy_db.md`).
3. Disable Gemini (`USE_GEMINI_FOR_DEV=false`) and configure the Ollama hosts (see `using_gemma.md`).
4. Provide secure secrets:
   - `SECRET_KEY` for JWT.
   - `ALLOYDB_PASSWORD`, `REDIS_PASSWORD`, `NEO4J_PASSWORD`.
   - Any GCS credentials if cloud storage is needed; otherwise configure the local storage root for the air-gapped path.
5. Reduce logging verbosity by setting `DEBUG=false`.

## 3. Build & Deployment

- **Containerisation**: The repo includes a `Dockerfile` and `docker-compose.yml`. For production use build-time multi-stage images and run each service as its own container (backend, processors, Redis, Neo4j, Ollama).
- **Process supervision**: If running bare metal, use systemd or supervisord to keep the workers alive.
- **Static assets**: Build the Next.js frontend (`npm run build && npm run start`) behind a reverse proxy.
- **TLS/Ingress**: Terminate TLS at the proxy (Nginx/Envoy/Traefik). Proxy `/api` to FastAPI and the rest to the Next.js app.

## 4. Data & Storage

- **Object storage**: For disconnected deployments, point `LOCAL_GCS_STORAGE_PATH` to a large, backed-up volume so uploaded files persist.
- **Database migrations**: Initialise Alembic and version-control DDL changes.
- **Backups**: Schedule regular AlloyDB and Neo4j backups. If using filesystem-based storage, snapshot it on the same cadence.
- **Retention policy**: Decide how long to keep raw uploads vs. derived text. Add cron jobs to archive or purge.

## 5. Security & RBAC

- Integrate the login flow with your identity provider (replace the dummy auth context). Ensure password hashing and MFA as required.
- Harden Redis (bind to localhost or restrict via firewall, enforce `requirepass`).
- Rotate API keys and secrets regularly. Avoid committing them to the repo.
- Enable HTTPS, enforce strong TLS ciphers, and add WAF rules if exposed to the internet.
- Review the RBAC fields on `processing_jobs`, `documents`, `activity_logs` to verify they align with station/district/state separation requirements.

## 6. Monitoring & Observability

- Enable FastAPI access logging and collect metrics (Prometheus or Stackdriver).
- Monitor Redis queue depth to detect stuck processors.
- Collect Ollama request timing for LLM health.
- Use structured logging in processors to capture errors (consider `structlog` or `loguru`).
- Set up alerting for:
  - Job failures (`processing_jobs.status = 'failed'`).
  - Worker crashes.
  - Low disk space on storage volumes.

## 7. Validation Checklist

Before declaring production readiness:

- [ ] Upload a multi-file job (document + audio) and verify each processor completes.
- [ ] Confirm document summaries, translations, graph entities, and chat responses are stored in AlloyDB.
- [ ] Validate Neo4j contains the generated nodes/relationships (or confirm fallback logic if Neo4j is optional).
- [ ] Run `POST /api/v1/chat` from the API docs and check the chat tab displays the same response.
- [ ] Simulate worker restart (kill process) and ensure redispatched jobs continue processing.
- [ ] Test backup restore: snapshot AlloyDB, restore to a staging instance, and run the API against it.

## 8. API Documentation

FastAPI automatically serves Swagger UI at:

```
http://<backend-host>:8000/api/v1/docs
```

Use this endpoint to explore and debug the services (upload, status, graph, chat, etc.).

---

With these steps in place you will have a reproducible, monitored deployment that aligns with the original solution architecture: distributed processors, CPU-only Gemma models, and a PGVector-backed retrieval layer suitable for police station deployments.
