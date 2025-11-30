# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Powered Hybrid Culinary Search Engine POC - A proof-of-concept implementation of an AI-powered hybrid search engine for restaurant menus using natural language queries.

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Data Ingestion
```bash
python src/ingest.py
```

### Run API Server
```bash
python src/main.py
```

### Test Search
```bash
curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "vegan tacos under 15"}'
```

## Architecture

### Multi-Agent System (BeeAI Framework)
- **Orchestrator** (`src/agents/orchestrator.py`): Coordinates the entire search workflow
- **QueryParserAgent** (`src/agents/query_parser.py`): Parses natural language queries into structured filters (keywords, price, dietary requirements, location)
- **SearchAgent** (`src/agents/search_agent.py`): Performs filtered hybrid search combining semantic and keyword retrieval
- **RankingAgent** (`src/agents/ranking_agent.py`): Applies LLM-based relevance scoring to results

### Search Implementation
- **Hybrid Search** (`src/search/hybrid_search.py`): Combines semantic (ChromaDB) and keyword (Whoosh/Elasticsearch) search with filtering capabilities
- **Semantic Search**: ChromaDB with deterministic hash-based embeddings (POC limitation)
- **Keyword Search**: Whoosh (local) and Elasticsearch (optional) with graceful fallbacks

### Data Flow
1. JSON restaurant data ingestion → flattened menu items
2. Indexing in multiple backends (Chroma for vectors, Whoosh for keywords)
3. Query parsing with LLMs → structured filters
4. Hybrid search with filtering → combined results
5. LLM-based relevance ranking → final scored results

## Technology Stack

- **Python 3.13** with FastAPI for REST API
- **ChromaDB** for vector search (using deterministic hash-based embeddings for POC)
- **Whoosh** for local keyword search
- **Elasticsearch** for advanced keyword search (optional, graceful fallback)
- **BeeAI Framework** for multi-agent architecture
- **LLMs**: DeepSeek (primary) / OpenAI (fallback) for query parsing and ranking

## Configuration

Environment variables in `config/settings.py`:
- `DEEPSEEK_API_KEY`: DeepSeek API key for LLM operations
- `OPENAI_API_KEY`: OpenAI API key (fallback LLM)
- `ES_HOST`, `ES_PORT`, `ES_SCHEME`: Elasticsearch configuration (optional)

## Key Limitations & Production Notes

- **Embeddings**: Currently using deterministic hash-based embeddings due to SSL/network constraints. Replace with sentence-transformers or similar for production
- **LLMs**: Requires API keys for DeepSeek or OpenAI to enable query parsing and ranking
- **SSL Issues**: Environment has SSL verification issues preventing model downloads
- **No Test Suite**: Tests directory exists but is empty

## Project Structure

```
src/
├── agents/          # Multi-agent system components
├── models/          # Data models (restaurant.py)
├── search/          # Core search functionality
├── ingest.py        # Data ingestion script
└── main.py          # FastAPI application entry point

config/
└── settings.py      # Environment configuration

input/               # Sample data files
docs/                # Project documentation
```