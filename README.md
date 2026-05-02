# PDF RAG API

FastAPI service where users upload PDFs, wait for background indexing, then ask grounded questions over the uploaded document.

## Stack

- FastAPI with async endpoints and `BackgroundTasks`
- PostgreSQL with `pgvector` for vector storage and similarity search
- Redis for cached answers to repeated questions
- NVIDIA NIM hosted inference for embeddings and `openai/gpt-oss-120b` answer generation
- OpenAI-compatible Python client for calling NVIDIA's API protocol
- `pypdf` for PDF text extraction

## Run

```bash
cp .env.example .env
docker compose up --build
```

Set `NVIDIA_API_KEY` in `.env` before uploading or asking questions.

API docs:

```text
http://localhost:8000/docs
```

## Endpoints

```text
POST   /documents/upload
GET    /documents/{document_id}/status
POST   /documents/{document_id}/ask
DELETE /documents/{document_id}
```

## Retrieval Notes

PDF text is split into token-aware chunks with overlap. The overlap helps preserve context that crosses page or paragraph boundaries. At query time, the API embeds the question, retrieves top matching chunks filtered by `document_id`, drops weak matches, and sends the best chunks to the generation model with page metadata for citations.

The default embedding model is `nvidia/nv-embedqa-e5-v5`, which uses 1024-dimensional vectors. Document chunks are embedded with `input_type=passage`; user questions are embedded with `input_type=query`. The default chunk size is 320 tokens with 50 tokens of overlap so chunks stay under NVIDIA's 512-token embedding limit even when tokenizer counts differ. If you change `EMBEDDING_MODEL` or `EMBEDDING_DIMENSIONS`, use a fresh database volume or add a migration because the `pgvector` column dimension is part of the table schema.
