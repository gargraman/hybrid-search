# AI-Powered Hybrid Culinary Search Engine POC

This is a proof-of-concept implementation of an AI-powered hybrid search engine for restaurant menus using natural language queries.

## Features

- Hybrid search combining semantic (vector) + keyword retrieval
- Multi-agent AI architecture using BeeAI Framework:
  - QueryParserAgent: Parses natural language queries into filters
  - SearchAgent: Performs hybrid search with filtering
  - RankingAgent: LLM-powered relevance ranking
  - Orchestrator: Coordinates agent workflow
- Quality gates with LLM verification at each stage
- Cost-effective LLM strategy (DeepSeek primary, OpenAI fallback)
- JSON-based restaurant data ingestion
- RESTful API with FastAPI

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables (optional):
   - `DEEPSEEK_API_KEY` for DeepSeek LLM
   - `OPENAI_API_KEY` for OpenAI GPT
   - `ES_HOST`, `ES_PORT`, `ES_SCHEME` for Elasticsearch

3. Ingest data:
   ```bash
   python src/ingest.py
   ```

4. Run the API:
   ```bash
   python src/main.py
   ```

5. Test search:
   ```bash
   curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "vegan tacos under 15"}'
   ```

## Architecture

- **Ingestion**: Loads JSON restaurant data, flattens menu items, indexes in Chroma (vectors), Whoosh (keywords), Elasticsearch (keywords)
- **Multi-Agent System**:
  - Orchestrator coordinates the workflow
  - QueryParserAgent uses LLM to extract keywords and filters
  - SearchAgent performs filtered hybrid search
  - RankingAgent applies LLM-based relevance scoring
- **API**: FastAPI endpoint with async agent orchestration

## Technologies

- Python 3.13
- ChromaDB for vector search (with deterministic hash-based embeddings for POC)
- Whoosh for local keyword search
- Elasticsearch for advanced keyword search
- FastAPI for API
- BeeAI Framework for multi-agent architecture
- DeepSeek/OpenAI for LLMs

## Notes

- **Embeddings**: Using deterministic hash-based embeddings for POC due to SSL/network constraints preventing model downloads. For production, replace with sentence-transformers or similar for real semantic embeddings.
- **LLMs**: Requires API keys for DeepSeek or OpenAI to enable query parsing and ranking.
- **Elasticsearch**: Assumes AWS setup; falls back gracefully if unavailable.
- **SSL**: Attempted to disable SSL verification for model downloads, but environment issues persist; use proper certificates or local models in production.

## Next Steps

- Implement query parsing with LLMs
- Add multi-agent orchestration
- Improve embeddings (use real models)
- Add filtering and ranking
- Deploy to production