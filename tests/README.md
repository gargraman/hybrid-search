# Hybrid Search Test Suite

Comprehensive test suite for the hybrid-search project covering all major components:
- Database operations (PostgreSQL)
- Search functionality (Whoosh + Qdrant + PostgreSQL)
- API endpoints (FastAPI)
- Agent system (Multi-agent orchestration)
- Configuration management

## Test Structure

```
tests/
├── __init__.py           # Test package initialization
├── conftest.py           # Shared fixtures and pytest configuration
├── test_database.py      # Database operations tests
├── test_search.py        # Search functionality tests
├── test_api.py           # API endpoint tests
├── test_agents.py        # Agent system tests
├── test_config.py        # Configuration tests
└── README.md            # This file
```

## Test Categories

### Unit Tests (Mocked)
Fast tests that don't require external services. These use mocks and can run in any environment.

```bash
pytest -m unit
```

### Integration Tests (Real Services)
Tests that require running services:
- Qdrant vector database
- PostgreSQL database
- Whoosh index

```bash
pytest -m integration
```

### By Service
Tests can also be run by specific service requirements:

```bash
pytest -m whoosh      # Tests requiring Whoosh index
pytest -m qdrant      # Tests requiring Qdrant
pytest -m postgres    # Tests requiring PostgreSQL
```

## Test Coverage

### 1. Lexical Search Tests (Whoosh)

**Unit Tests:**
- `test_keyword_search_returns_empty_when_index_missing` - Graceful degradation
- `test_keyword_search_result_structure` - Result format validation
- `test_keyword_search_respects_top_k` - Limit parameter handling

**Integration Tests:**
- `test_keyword_search_with_temp_index` - Real Whoosh index
- `test_keyword_search_filters_by_cuisine` - Cuisine filtering

### 2. Semantic Search Tests (Qdrant + PostgreSQL)

**Unit Tests:**
- `test_semantic_search_returns_empty_on_error` - Error handling
- `test_semantic_search_result_structure` - Result format validation
- `test_semantic_search_enriches_text_field` - Text field enrichment

**Integration Tests:**
- `test_semantic_search_with_real_services` - Full stack semantic search

### 3. Hybrid Search Tests (Combined)

**Unit Tests:**
- `test_hybrid_search_combines_results` - Result merging
- `test_hybrid_search_filters_by_price` - Price filtering
- `test_hybrid_search_filters_by_dietary` - Dietary filtering
- `test_hybrid_search_filters_by_location` - Location filtering
- `test_hybrid_search_combines_all_filters` - Multi-filter support
- `test_hybrid_search_respects_top_k` - Result limiting

**Integration Tests:**
- `test_hybrid_search_with_all_services` - Full stack hybrid search

### 4. Helper Function Tests

- `test_filter_results_by_price` - Price filter logic
- `test_filter_results_by_dietary` - Dietary filter logic
- `test_filter_results_by_location` - Location filter logic
- `test_normalize_scores_*` - Score normalization
- `test_merge_results_*` - Result merging and deduplication

### 5. Performance Tests

- `test_hybrid_search_large_result_set` - Scalability with large datasets

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Enhanced mocking
- `pytest-timeout` - Test timeout handling

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Only unit tests (fast, no services required)
pytest -m unit

# Only integration tests (requires services)
pytest -m integration

# Tests requiring Whoosh
pytest -m whoosh

# Tests requiring Qdrant and PostgreSQL
pytest -m "qdrant and postgres"

# Exclude slow tests
pytest -m "not slow"
```

### Run Specific Test File

```bash
pytest tests/test_search.py
```

### Run Specific Test Class or Function

```bash
# Run specific class
pytest tests/test_search.py::TestKeywordSearchWhooshUnit

# Run specific test
pytest tests/test_search.py::TestKeywordSearchWhooshUnit::test_keyword_search_result_structure

# Run tests matching pattern
pytest -k "keyword_search"
pytest -k "filter"
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

### Run with Verbose Output

```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run with Debug Output

```bash
pytest -s  # Show print statements
pytest --log-cli-level=DEBUG  # Show debug logs
```

## Service Setup for Integration Tests

### Start Required Services

```bash
# Start Qdrant and PostgreSQL via Docker
docker-compose up -d

# Verify services are running
docker-compose ps

# Check Qdrant health
curl http://localhost:6333/health

# Check PostgreSQL connection
psql postgresql://user:password@localhost:5432/restaurantdb -c "SELECT 1;"
```

### Generate Test Data

```bash
# Generate seed data
python scripts/generate_seed_data.py

# Ingest into Whoosh
python src/ingest.py

# Ingest into Qdrant + PostgreSQL
python src/ingest_qdrant_postgres.py
```

### Verify Test Data

```bash
# Check Whoosh index
ls -la ./whoosh_index/

# Check Qdrant collections
curl http://localhost:6333/collections

# Check PostgreSQL data
psql postgresql://user:password@localhost:5432/restaurantdb -c "SELECT COUNT(*) FROM restaurants;"
```

## Additional Test Modules

### Database Operations Tests (`test_database.py`)

Tests for PostgreSQL database operations with connection pool management:
- Table creation with pool
- Restaurant insertion with proper ID handling
- Menu item insertion with ON CONFLICT handling
- Connection pool lifecycle management
- Async context manager usage

Run: `pytest tests/test_database.py -v`

### API Endpoint Tests (`test_api.py`)

Tests for FastAPI endpoints:
- `/search` endpoint validation and filtering
- Health check endpoints (`/health`, `/health/live`, `/health/ready`)
- Request validation and error handling
- Metrics endpoint availability
- Performance characteristics

Run: `pytest tests/test_api.py -v`

### Agent Tests (`test_agents.py`)

Tests for multi-agent orchestration system:
- Orchestrator initialization with pool/client
- SearchAgent filtering logic
- API key handling and fallback
- Edge cases (missing keys, no results)

Run: `pytest tests/test_agents.py -v`

### Configuration Tests (`test_config.py`)

Tests for configuration management:
- Settings loading from environment variables
- Pydantic validation (DSN format, port ranges)
- SecretStr usage for API keys
- Default values and edge cases

Run: `pytest tests/test_config.py -v`

## Test Markers Reference

| Marker | Description |
|--------|-------------|
| `unit` | Fast tests with mocked dependencies |
| `integration` | Tests requiring real services |
| `whoosh` | Tests requiring Whoosh index |
| `qdrant` | Tests requiring Qdrant vector database |
| `postgres` | Tests requiring PostgreSQL database |
| `slow` | Tests that take significant time to run |
| `api` | Tests for API endpoints |
| `database` | Tests for database operations |
| `search` | Tests for search functionality |
| `agents` | Tests for agent functionality |
| `config` | Tests for configuration |

## Continuous Integration

For CI/CD pipelines, run unit tests by default:

```bash
# Fast CI run (unit tests only)
pytest -m unit --tb=short

# Full CI run (requires services)
pytest --tb=short --maxfail=5
```

## Troubleshooting

### Tests Skip with "Service not available"

Integration tests automatically skip when required services aren't running. To run these tests:

1. Ensure Docker services are running: `docker-compose up -d`
2. Verify data is ingested (see "Generate Test Data" section)
3. Run integration tests: `pytest -m integration`

### Import Errors

Ensure project root is in Python path:

```bash
export PYTHONPATH=/Users/dhungarg/projects/github/hybrid-search:$PYTHONPATH
pytest
```

Or run tests from project root:

```bash
cd /Users/dhungarg/projects/github/hybrid-search
pytest
```

### Whoosh Index Not Found

Create the Whoosh index:

```bash
python src/ingest.py
```

### Async Test Warnings

If you see warnings about asyncio, ensure `pytest-asyncio` is installed:

```bash
pip install pytest-asyncio==0.24.0
```

## Contributing

When adding new tests:

1. Add appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
2. Use descriptive docstrings explaining what the test validates
3. Follow TDD principles - write failing tests first
4. Use fixtures from `conftest.py` for common setup
5. Mock external dependencies for unit tests
6. Add integration tests for end-to-end validation

## Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use descriptive names: `test_hybrid_search_filters_by_price_and_location`

## Example Test Run Output

```bash
$ pytest -v

tests/test_search.py::TestKeywordSearchWhooshUnit::test_keyword_search_returns_empty_when_index_missing PASSED
tests/test_search.py::TestKeywordSearchWhooshUnit::test_keyword_search_result_structure PASSED
tests/test_search.py::TestSemanticSearchUnit::test_semantic_search_returns_empty_on_error PASSED
tests/test_search.py::TestHybridSearchUnit::test_hybrid_search_combines_results PASSED
tests/test_search.py::TestHybridSearchUnit::test_hybrid_search_filters_by_price PASSED
tests/test_search.py::TestHelperFunctions::test_normalize_scores_multiple_results PASSED

==================== 25 passed, 3 skipped in 2.45s ====================
```

## License

Same as parent project.
