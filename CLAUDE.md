# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Powered Hybrid Culinary Search Engine POC - A proof-of-concept implementation of an AI-powered hybrid search engine for restaurant menus using natural language queries.

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Database Setup (Docker)
```bash
# Start Qdrant and PostgreSQL
docker-compose up -d
```

### Data Generation & Ingestion
```bash
# Generate seed data (200 restaurants with geo metadata)
python scripts/generate_seed_data.py

# Whoosh (lexical ingestion)
python src/ingest.py

# Qdrant + PostgreSQL (semantic ingestion - recommended)
python src/ingest_qdrant_postgres.py
```

### Run API Server
```bash
python src/main.py
```

### Test Search
```bash
# Basic search
curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "vegan tacos under 15"}'

# Location-aware search
curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "pizza in San Francisco under 20"}'
```

### Monitoring & Health Checks
```bash
# Health check
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8001/metrics
curl http://localhost:8000/metrics

# API documentation
open http://localhost:8000/docs
```

## Architecture

### Multi-Agent System (BeeAI Framework)
- **Orchestrator** (`src/agents/orchestrator.py`): Coordinates the entire search workflow
- **QueryParserAgent** (`src/agents/query_parser.py`): Parses natural language queries into structured filters (keywords, price, dietary requirements, location)
- **SearchAgent** (`src/agents/search_agent.py`): Performs filtered hybrid search combining semantic and keyword retrieval
- **RankingAgent** (`src/agents/ranking_agent.py`): Applies LLM-based relevance scoring to results
- **QualityAgent** (`src/agents/quality_agent.py`): Validates and filters search results for relevance, completeness, and safety
- **VerificationAgent** (`src/agents/verification_agent.py`): Checks search results for factual accuracy and compliance with business rules

	- **Hybrid Search** (`src/search/hybrid_search.py`): Combines semantic (Qdrant) and keyword (Whoosh) search with filtering capabilities
	- **Qdrant + PostgreSQL Search** (`src/search/qdrant_postgres_search.py`): Alternative search implementation using Qdrant for vectors and PostgreSQL for metadata
	- **Semantic Search**: Qdrant with sentence-transformer embeddings persisted via PostgreSQL/Qdrant ingestion
- **Keyword Search**: Whoosh (local) and Elasticsearch (optional) with graceful fallbacks

### Data Flow
1. Seed data generation → JSON restaurant data with deterministic geo metadata (city, state, lat/long)
2. JSON restaurant data ingestion → flattened menu items with full metadata
3. Indexing in multiple backends (Qdrant for vectors, Whoosh/PostgreSQL for lexical + metadata)
4. Query parsing with LLMs → structured filters (keywords, price, dietary, location)
5. Hybrid search with filtering → combined results from semantic + keyword search
6. Quality validation and verification checks → filtered results
7. LLM-based relevance ranking → final scored results

## Technology Stack

- **Python 3.13** with FastAPI for REST API
- **Vector Database**: Qdrant for semantic search (vector embeddings)
- **Metadata Store**: PostgreSQL for restaurant/menu metadata, geo data, and relational queries
- **Keyword Search**: Whoosh (local) / Elasticsearch (optional)
- **Embeddings**: Deterministic hash-based (POC) or sentence-transformers (production-ready)
- **BeeAI Framework** for multi-agent architecture
- **LLMs**: DeepSeek (primary) / OpenAI (fallback) for query parsing and ranking
- **Monitoring**: Prometheus metrics, Loguru logging, health checks
- **Data Generation**: `scripts/generate_seed_data.py` for creating test data with geo metadata

## Configuration

Environment variables in `config/settings.py`:
- `DEEPSEEK_API_KEY`: DeepSeek API key for LLM operations
- `OPENAI_API_KEY`: OpenAI API key (fallback LLM)
- `ES_HOST`, `ES_PORT`, `ES_SCHEME`: Elasticsearch configuration (optional)

Database configuration in `config/db_config.py`:
- `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`: Qdrant vector database configuration
- `POSTGRES_DSN`: PostgreSQL database connection string

## Monitoring & Observability

- **Prometheus Metrics**: Search request counts and latency histograms exposed on port 8001
- **Structured Logging**: Loguru-based logging with search query details and performance metrics
- **Health Endpoint**: `/health` for service status monitoring
- **Graceful Fallback**: Automatic fallback to basic hybrid search when agents fail
- **Error Tracking**: Comprehensive error logging with request context

## Key Features & Production Notes

- **Geo Metadata Integration**: All restaurants include city, state, latitude, longitude for location-based filtering and future geocoding integration (see `docs/geo_metadata.md`)
- **Seed Data Generation**: Deterministic test data with 200 restaurants across 20 US cities using `scripts/generate_seed_data.py`
- **Embeddings**: Currently using deterministic hash-based embeddings due to SSL/network constraints. Modern sentence-transformers are now available in requirements.txt for production use
- **LLMs**: Requires API keys for DeepSeek or OpenAI to enable query parsing and ranking
- **Database Stack**: Qdrant + PostgreSQL + Whoosh for hybrid search at scale (ChromaDB removed in recent commits)
- **Location-aware Search**: Filter by city/state in natural language queries (e.g., "pizza in San Francisco")
- **No Test Suite**: Tests directory exists but is empty
- **Monitoring**: Basic Prometheus metrics implemented; consider adding agent-level metrics for production

## Project Structure

```
src/
├── agents/          # Multi-agent system (orchestrator, query_parser, search_agent, ranking_agent, quality_agent, verification_agent)
├── models/          # Data models (restaurant.py with geo fields)
├── search/          # Core search (hybrid_search.py with location filtering, qdrant_postgres_search.py)
├── db/              # Database integrations (qdrant.py, postgres.py with geo schema)
├── utils/           # Utilities (chunking.py, docling_input.py)
├── ingest.py        # Whoosh ingestion script (lexical)
├── ingest_qdrant_postgres.py # Qdrant + PostgreSQL ingestion script
└── main.py          # FastAPI application entry point

config/
├── settings.py      # Environment configuration
└── db_config.py     # Database connection configuration

scripts/
└── generate_seed_data.py # Generates 200 test restaurants with geo metadata

input/
├── seed/            # Generated seed data (200 restaurants)
└── restaurant*.json # Sample input files

docs/
└── geo_metadata.md  # Geo metadata integration and geocoding strategy
```

## Important Implementation Details

### Geo Metadata Architecture
- All restaurants include `city`, `state`, `latitude`, `longitude` fields
- Seed data uses deterministic coordinates for 20 major US cities
- PostgreSQL schema includes geo columns with proper indexing
- Qdrant payloads include geo metadata for semantic search results
- Whoosh documents include city/state for keyword filtering
- Location filtering works across all search backends (see `src/search/hybrid_search.py:filter_results`)
- Ready for future geocoding integration without schema changes (see `docs/geo_metadata.md`)

### Database Schema
- **restaurants** table: Includes geo fields (city, state, latitude, longitude, cuisine) with unique index on (name, address)
- **menu_items** table: References restaurants with external_id for Qdrant join queries
- PostgreSQL joins enriched with Qdrant vector search results for complete metadata retrieval

### Hybrid Search Strategy
- Semantic search via Qdrant (vector embeddings) → `src/search/qdrant_postgres_search.py`
- Keyword search via Whoosh → `src/search/hybrid_search.py:keyword_search_whoosh`
- Results merged with score normalization and filtering
- Filters applied post-merge: price_max, dietary restrictions, location matching
- Graceful fallback to basic search when advanced features unavailable