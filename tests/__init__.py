"""
Test package for hybrid-search project.

This package contains comprehensive test suites for:
- Lexical/Keyword Search (Whoosh)
- Semantic Search (Qdrant + PostgreSQL)
- Hybrid Search (Combined)

Test categories:
- Unit tests: Fast tests with mocked dependencies
- Integration tests: Tests requiring real services (Qdrant, PostgreSQL, Whoosh)
- Performance tests: Tests focused on scalability and performance

Run tests with:
    pytest                          # Run all tests
    pytest -m unit                  # Run only unit tests
    pytest -m integration           # Run only integration tests
    pytest tests/test_search.py     # Run specific test file
    pytest -k "keyword_search"      # Run tests matching pattern
    pytest --cov=src                # Run with coverage report
"""

__version__ = "0.1.0"
