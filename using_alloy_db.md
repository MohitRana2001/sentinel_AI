# Using AlloyDB in Production

Sentinel AI ships with SQLite enabled for local development, but the production design targets AlloyDB (PostgreSQL-compatible) with pgvector. This document explains the current schema, how to stand up AlloyDB, and how to connect the application.

## 1. Current Database Schema

The ORM models (see `backend/models.py`) map to the following tables:

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | RBAC-enabled user accounts | `email`, `hashed_password`, `rbac_level`, station/district/state identifiers, timestamps |
| `processing_jobs` | Upload jobs, one per user submission | `id` (UUID), `user_id`, `status`, `gcs_prefix`, `original_filenames`, `processed_files`, timestamps, `error_message` |
| `documents` | Individual processed files | `id`, `job_id`, RBAC fields, `original_filename`, `file_type`, artifact paths, cached `summary_text` |
| `document_chunks` | Text chunks used for retrieval | `id`, `document_id`, `chunk_index`, `chunk_text`, `embedding` (pgvector), JSON `metadata`, timestamps |
| `graph_entities` | Nodes extracted by the graph processor | `entity_id`, `entity_name`, `entity_type`, JSON `properties`, `document_id` |
| `graph_relationships` | Edges between entities | `source_entity_id`, `target_entity_id`, `relationship_type`, JSON `properties` |
| `activity_logs` | Audit trail | `user_id`, `activity_type`, JSON `details`, RBAC context, timestamp |

The chat feature reads from `document_chunks`, while the results/graph views join `documents`, `graph_entities`, and `graph_relationships`.

## 2. Provision AlloyDB

1. **Create an AlloyDB cluster** in your preferred region (e.g., `us-central1`). Use at least the standard primary instance size recommended for pgvector workloads (g2 or higher).
2. **Enable the `vector` extension** for the cluster. AlloyDB comes with pgvector pre-installed; you simply need to run `CREATE EXTENSION IF NOT EXISTS vector;` once per database.
3. **Create a database**:
   ```sql
   CREATE DATABASE sentinel_db;
   ```

4. Optionally create a dedicated user:
   ```sql
   CREATE USER sentinel_user WITH PASSWORD 'strong-password';
   GRANT ALL PRIVILEGES ON DATABASE sentinel_db TO sentinel_user;
   ```

## 3. Configure the Application

Update `.env` or deployment secrets with the AlloyDB connection details:

```env
USE_SQLITE_FOR_DEV=false
ALLOYDB_HOST=<primary-ip or proxy-host>
ALLOYDB_PORT=5432
ALLOYDB_USER=sentinel_user   # or postgres
ALLOYDB_PASSWORD=your-password
ALLOYDB_DATABASE=sentinel_db
```

When running on GKE or Compute Engine, route traffic through the AlloyDB Auth Proxy:

```bash
./cloud_sql_proxy \
  --port=5432 \
  --host=0.0.0.0 \
  --instance=PROJECT:REGION:CLUSTER=INSTANCE
```

## 4. Initialize the Schema

From the project root:

```bash
source backend/venv/bin/activate
PYTHONPATH=backend python - <<'PY'
from database import init_db
init_db()
PY
```

`init_db()` creates the tables and ensures the `vector` extension is loaded (the call is a no-op if it already exists).

## 5. Inspecting the Data

Use `psql` via the proxy or Cloud Shell:

```bash
psql "host=127.0.0.1 port=5432 dbname=sentinel_db user=sentinel_user password=your-password"
```

Helpful queries:

```sql
-- Jobs and their progress
SELECT id, status, processed_files, total_files, error_message
FROM processing_jobs
ORDER BY created_at DESC
LIMIT 10;

-- Documents and summaries
SELECT id, job_id, original_filename, summary_text
FROM documents
ORDER BY id DESC
LIMIT 10;

-- Preview chunks for RAG
SELECT document_id, chunk_index, left(chunk_text, 120) AS snippet
FROM document_chunks
ORDER BY created_at DESC
LIMIT 10;
```

To verify pgvector index usage:

```sql
SELECT * FROM pg_indexes WHERE tablename = 'document_chunks';
```

You should see `ix_document_chunks_embedding` using `ivfflat`.

## 6. Migration Tips

- The repository does not yet ship with Alembic migrations. For production, initialise Alembic so schema drift can be tracked:
  ```bash
  alembic init backend/migrations
  ```
- Consider creating read replicas for analytics. Pgvector similarity search benefits from additional memory; size accordingly.
- Enable automated backups and point-in-time recovery on the AlloyDB cluster to protect uploaded evidence.

Once AlloyDB is configured, the document processor and chat endpoints automatically switch from SQLite to PostgreSQL, preserving the exact same application behaviour with production-grade durability.
