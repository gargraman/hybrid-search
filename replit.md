# AI-Powered Hybrid Culinary Search Engine - Replit Setup

## Overview
This is an AI-powered hybrid search engine for restaurant menus that combines semantic (vector-based) and keyword search. It was successfully imported from GitHub and adapted for the Replit environment.

## Current State
- **Status**: Running successfully on Replit
- **Port**: 5000 (web interface)
- **API Framework**: FastAPI
- **Search Mode**: Simple hybrid search (agent-based orchestration disabled due to framework incompatibility)

## Recent Changes (Nov 30, 2025)
1. Installed Python 3.11 and all dependencies (excluding macOS-specific packages)
2. Created PostgreSQL database using Replit's built-in database
3. Configured environment variables for database and service connections
4. Updated main.py to run on port 5000 for Replit's web preview
5. Modified main.py to gracefully fall back to simple hybrid search when agent orchestration is unavailable
6. Created workflow to run the FastAPI application
7. Updated .gitignore for Python project conventions

## Project Architecture

### Backend Components
- **FastAPI**: RESTful API server running on port 5000
- **Search Engine**: Hybrid search combining:
  - Semantic search via ChromaDB (vector database)
  - Keyword search via Whoosh (local search index)
  - Optional Elasticsearch support (not configured)
- **Database**: PostgreSQL for metadata storage
- **Monitoring**: Prometheus metrics on port 8001

### Search Functionality
The application supports two modes:
1. **Agent-based (currently disabled)**: Multi-agent orchestration using BeeAI framework with LLM-powered query parsing, validation, and ranking
2. **Simple hybrid search (active)**: Direct combination of semantic and keyword search results

### Key Files
- `src/main.py`: FastAPI application entry point
- `src/search/hybrid_search.py`: Core search functionality
- `config/settings.py`: Configuration settings
- `config/db_config.py`: Database configuration

## Environment Variables

### Configured (Shared Environment)
- `POSTGRES_DSN`: PostgreSQL connection string (uses DATABASE_URL)
- `QDRANT_HOST`: localhost (vector database, not active)
- `QDRANT_PORT`: 6333
- `ES_HOST`: localhost (Elasticsearch, not active)
- `ES_PORT`: 9200
- `ES_SCHEME`: http

### Required for Full Functionality (Not Set)
- `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`: For LLM-powered agent orchestration
- `QDRANT_API_KEY`: For Qdrant cloud (optional)

## API Endpoints

### Available Endpoints
- `POST /search`: Search for menu items
  - Request: `{"query": "vegan tacos", "top_k": 10}`
  - Returns: List of search results with scores and metadata
- `GET /health`: Health check endpoint
- `GET /metrics`: Prometheus metrics
- `GET /docs`: Interactive API documentation (Swagger UI)

## Known Limitations

1. **Agent Orchestration Disabled**: The BeeAI framework version has compatibility issues, so advanced LLM-powered features are currently disabled
2. **External Services Not Running**: Qdrant and Elasticsearch are configured but not running (using ChromaDB and Whoosh instead)
3. **No Data Ingested**: The search indices need to be populated with restaurant data
4. **macOS Packages Removed**: pyobjc packages removed for Linux compatibility

## Next Steps for Development

### Immediate Tasks
1. Run data ingestion to populate search indices
2. Test search functionality with sample queries
3. Configure deployment for production

### Future Enhancements
1. Fix BeeAI framework compatibility or migrate to compatible version
2. Set up Qdrant cloud service for vector search
3. Add LLM API keys for advanced query parsing and ranking
4. Implement data ingestion workflow
5. Add authentication and authorization
6. Enhance monitoring and logging

## User Preferences
- None documented yet

## Development Notes
- The application is designed to work gracefully even when external services (Qdrant, Elasticsearch, LLM APIs) are unavailable
- All search fallbacks to local ChromaDB and Whoosh indices
- The codebase supports easy extension with new search backends and data sources
