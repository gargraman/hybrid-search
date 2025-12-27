# AI-Powered Hybrid Culinary Search Engine POC

This repository is a developer-focused proof-of-concept for an AI-powered hybrid search engine for restaurant menus, supporting natural language queries and scalable, production-ready architecture.

## Features

- True hybrid search: semantic (vector, Qdrant) + keyword (Whoosh, Elasticsearch)
- Multi-agent orchestration (BeeAI):
  - QueryParserAgent: LLM-powered query parsing
  - SearchAgent: Hybrid search with context assembled from structured JSON summaries
  - QualityAgent: LLM-based result validation
  - VerificationAgent: LLM-based business rule compliance
  - RankingAgent: LLM-powered relevance scoring
  - Orchestrator: Full agent workflow coordination
- Quality gates at every stage
- Monitoring: Prometheus metrics, health endpoints, structured logging
- Scalable DB architecture: Qdrant for vectors, PostgreSQL for metadata
- RESTful API (FastAPI) with OpenAPI docs
- Secure, configurable, and ready for production deployment

## Developer Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   - `DEEPSEEK_API_KEY` or `OPENAI_API_KEY` for LLMs
   - `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY` for Qdrant
   - `POSTGRES_DSN` for PostgreSQL
   - `ES_HOST`, `ES_PORT`, `ES_SCHEME` for Elasticsearch

3. **Start Qdrant and PostgreSQL:**
   - Qdrant: [Docker quickstart](https://qdrant.tech/documentation/quick-start/)
   - PostgreSQL: Use Docker or local install

4. **Ingest data:**
   ```bash
   python src/ingest_qdrant_postgres.py
   ```

5. **Run the API:**
   ```bash
   python src/main.py
   ```

6. **Monitor health and metrics:**
   - Health: [GET] `/health`
   - Metrics: [GET] `/metrics` (Prometheus scrape)
   - API docs: [GET] `/docs`

7. **Test search:**
   ```bash
   curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "vegan tacos under 15"}'
   ```

## Architecture Overview

- **Ingestion:**
  - Parses and chunks JSON input using native schema-aware logic
  - Stores vectors in Qdrant, metadata in PostgreSQL
- **Multi-Agent System:**
  - Orchestrator coordinates QueryParser, Search, Quality, Verification, and Ranking agents
  - Each agent uses LLMs for its specialized task
- **Search:**
  - Semantic search via Qdrant (sentence-transformers embeddings)
  - Keyword search via Whoosh/Elasticsearch
  - Results merged and filtered by agents
- **API:**
  - FastAPI async endpoints, OpenAPI docs, health/metrics
- **Monitoring:**
  - Prometheus metrics, Loguru logging
- **Security:**
  - Input validation, ready for OAuth2/JWT integration

## Technologies

- Python 3.13
- Qdrant (vector DB)
- PostgreSQL (metadata)
- Whoosh, Elasticsearch (keyword search)
- FastAPI (API)
- BeeAI Framework (multi-agent)
- DeepSeek/OpenAI (LLMs)
- Prometheus, Loguru (monitoring/logging)

## Developer Notes

- **Embeddings:** Uses sentence-transformers for real semantic search. For local/offline, fallback to deterministic vectors.
- **LLMs:** All agents use LLMs for parsing, validation, ranking, and verification. Set API keys in your environment.
- **Config:** All DB and service credentials are environment-driven for security and portability.
- **Extensibility:** Add new agents, business rules, or data sources easily.
- **Testing:** Validate chunking, agent outputs, and DB integration with provided utilities.
- **Production:** Ready for containerization, scaling, and cloud deployment.

## Next Steps for Developers

- Extend agent logic for domain-specific rules
- Integrate advanced security (OAuth2/JWT)
- Add more API endpoints and documentation
- Automate deployment (Docker, CI/CD)
- Expand monitoring and alerting

---

**For questions, improvements, or contributions, see the code comments and agent modules. This repo is designed for rapid prototyping and production-grade extension.**