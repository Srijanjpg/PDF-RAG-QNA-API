# PDF RAG API

FastAPI service for uploading PDFs and asking grounded questions over their contents. The app extracts text in the background, splits it into token-aware chunks, stores embeddings in PostgreSQL with `pgvector`, and uses retrieval-augmented generation to answer questions with citations from the source document.

## What It Does

1. Upload a PDF.
2. Index it asynchronously.
3. Ask questions against the document.
4. Receive answers grounded in retrieved passages, with citations and cached responses for repeated queries.

## Key Features

- PDF upload with size validation and background processing
- Token-aware chunking with overlap to preserve context across page boundaries
- Vector search with PostgreSQL and `pgvector`
- Redis-backed answer caching
- Citation-rich responses that point back to the source chunks
- Docker-based local development setup

## Tech Stack

- FastAPI with async endpoints
- PostgreSQL + `pgvector` for similarity search
- Redis for caching
- NVIDIA NIM-compatible inference for embeddings and answer generation
- `pypdf` for PDF extraction
- `pydantic-settings` for configuration

## Getting Started

```bash
cp .env.example .env
docker compose up --build
```

Open the API docs at:

```text
http://localhost:8000/docs
```

Before uploading or asking questions, set either `NVIDIA_API_KEY` or `OPENAI_API_KEY` in `.env`.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/documents/upload` | Upload a PDF for background indexing |
| `GET` | `/documents/{document_id}/status` | Check indexing status and any error details |
| `POST` | `/documents/{document_id}/ask` | Ask a grounded question about the uploaded PDF |
| `DELETE` | `/documents/{document_id}` | Remove the document and its indexed chunks |

## Configuration

The main settings live in [app/config.py](app/config.py). Common values include:

| Setting | Default |
| --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://rag:rag@localhost:5432/rag` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `UPLOAD_DIR` | `uploads/` |
| `EMBEDDING_MODEL` | `nvidia/nv-embedqa-e5-v5` |
| `GENERATION_MODEL` | `openai/gpt-oss-120b` |
| `CHUNK_TOKENS` | `320` |
| `CHUNK_OVERLAP_TOKENS` | `50` |
| `RETRIEVAL_TOP_K` | `8` |
| `RETRIEVAL_MIN_SCORE` | `0.20` |

## How Retrieval Works

Uploaded PDFs are extracted into pages, chunked with overlap, and embedded as passages. When a question arrives, the service embeds the query, retrieves the most relevant chunks for that specific document, filters weak matches, and sends the strongest evidence to the generation model along with page metadata. If the same question is asked again, the cached response is returned when available.

The default embedding model uses 1024-dimensional vectors. If you change `EMBEDDING_MODEL` or `EMBEDDING_DIMENSIONS`, create a fresh database volume or add a migration so the `pgvector` column definition stays in sync.

## Project Structure

- [app/main.py](app/main.py) bootstraps the FastAPI app and static UI.
- [app/api.py](app/api.py) contains the document upload, status, ask, and delete routes.
- [app/tasks.py](app/tasks.py) handles PDF extraction, chunking, embedding, and persistence.
- [app/services/](app/services) contains the PDF, chunking, cache, and LLM helpers.

## License

No license has been specified yet.
