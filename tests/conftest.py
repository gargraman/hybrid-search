"""
Pytest configuration and shared fixtures for hybrid-search tests.

This module provides fixtures and test utilities that are shared across
the test suite, including service availability checks, mock data, and
test environment setup.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Service availability checks
def is_whoosh_available() -> bool:
    """Check if Whoosh index is available."""
    from config.settings import settings
    whoosh_path = Path(settings.whoosh_index_path)
    return whoosh_path.exists() and (whoosh_path / "_MAIN_1.toc").exists()


def is_qdrant_available() -> bool:
    """Check if Qdrant service is available."""
    try:
        from qdrant_client import QdrantClient
        from config.db_config import QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY

        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY)
        collections = client.get_collections()
        return True
    except Exception:
        return False


def is_postgres_available() -> bool:
    """Check if PostgreSQL service is available."""
    try:
        import asyncio
        import asyncpg
        from config.db_config import POSTGRES_DSN

        async def check():
            try:
                conn = await asyncpg.connect(POSTGRES_DSN)
                await conn.close()
                return True
            except Exception:
                return False

        return asyncio.run(check())
    except Exception:
        return False


# Pytest skip conditions
skip_if_no_whoosh = pytest.mark.skipif(
    not is_whoosh_available(),
    reason="Whoosh index not available"
)

skip_if_no_qdrant = pytest.mark.skipif(
    not is_qdrant_available(),
    reason="Qdrant service not available"
)

skip_if_no_postgres = pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL service not available"
)


# Mock data fixtures
@pytest.fixture
def mock_menu_item_metadata() -> Dict:
    """Provides mock metadata for a menu item."""
    return {
        "text": "Classic Margherita Pizza - Fresh mozzarella, tomato sauce, basil",
        "restaurant": "Mario's Italian Bistro",
        "restaurant_type": "Italian Restaurant",
        "address": "123 Main Street",
        "city": "San Francisco",
        "state": "CA",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "cuisine": "italian",
        "category": "Pizza",
        "price": 14.99,
        "rating": 4.5,
        "review_count": 250,
        "description": "Fresh mozzarella, tomato sauce, basil",
        "restaurant_description": "Traditional Italian cuisine",
        "restaurant_history": "Family-owned since 1985",
        "contact_phone": "415-555-0123",
        "contact_website": "www.marios-bistro.com",
        "rewards": "5% cashback"
    }


@pytest.fixture
def mock_search_result(mock_menu_item_metadata) -> Dict:
    """Provides a mock search result with metadata."""
    return {
        "id": "test-item-001",
        "score": 0.85,
        "metadata": mock_menu_item_metadata
    }


@pytest.fixture
def mock_multiple_search_results(mock_menu_item_metadata) -> List[Dict]:
    """Provides multiple mock search results."""
    results = []
    for i in range(5):
        metadata = mock_menu_item_metadata.copy()
        metadata["text"] = f"Menu Item {i+1} - {metadata['text']}"
        metadata["price"] = 10.0 + (i * 2.5)
        results.append({
            "id": f"test-item-{i+1:03d}",
            "score": 0.9 - (i * 0.1),
            "metadata": metadata
        })
    return results


@pytest.fixture
def mock_vegan_search_results() -> List[Dict]:
    """Provides mock search results for vegan items."""
    return [
        {
            "id": "vegan-001",
            "score": 0.92,
            "metadata": {
                "text": "Vegan Buddha Bowl - Quinoa, roasted vegetables, tahini",
                "restaurant": "Green Garden Cafe",
                "city": "San Francisco",
                "state": "CA",
                "price": 12.99,
                "description": "Vegan Buddha Bowl with fresh vegetables",
                "cuisine": "vegan",
                "category": "Bowls",
                "rating": 4.7,
                "review_count": 180
            }
        },
        {
            "id": "vegan-002",
            "score": 0.88,
            "metadata": {
                "text": "Vegan Tacos - Black beans, avocado, salsa",
                "restaurant": "Taco Heaven",
                "city": "Oakland",
                "state": "CA",
                "price": 9.99,
                "description": "Delicious vegan tacos",
                "cuisine": "mexican",
                "category": "Tacos",
                "rating": 4.5,
                "review_count": 95
            }
        }
    ]


@pytest.fixture
def mock_whoosh_index():
    """Provides a mock Whoosh index for testing."""
    mock_index = MagicMock()
    mock_searcher = MagicMock()
    mock_index.searcher.return_value.__enter__.return_value = mock_searcher
    mock_index.searcher.return_value.__exit__.return_value = None
    return mock_index


@pytest.fixture
def mock_qdrant_client():
    """Provides a mock Qdrant client for testing."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def mock_postgres_connection():
    """Provides a mock PostgreSQL connection for testing."""
    mock_conn = MagicMock()
    return mock_conn


# Environment setup fixtures
@pytest.fixture(autouse=True)
def reset_environment_vars():
    """Reset environment variables before each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_whoosh_index(tmp_path):
    """Creates a temporary Whoosh index for testing."""
    index_path = tmp_path / "test_whoosh_index"
    index_path.mkdir()

    from whoosh.fields import Schema, TEXT, ID, NUMERIC
    from whoosh.index import create_in

    schema = Schema(
        id=ID(stored=True),
        text=TEXT(stored=True),
        restaurant=TEXT(stored=True),
        cuisine=TEXT(stored=True),
        category=TEXT(stored=True),
        city=TEXT(stored=True),
        state=TEXT(stored=True),
        price=NUMERIC(stored=True, numtype=float),
        rating=NUMERIC(stored=True, numtype=float)
    )

    ix = create_in(str(index_path), schema)

    # Add some test documents
    writer = ix.writer()
    test_docs = [
        {
            "id": "test-1",
            "text": "Margherita Pizza with fresh mozzarella",
            "restaurant": "Mario's Bistro",
            "cuisine": "Italian",
            "category": "Pizza",
            "city": "San Francisco",
            "state": "CA",
            "price": 14.99,
            "rating": 4.5
        },
        {
            "id": "test-2",
            "text": "Vegan Tacos with black beans",
            "restaurant": "Taco Heaven",
            "cuisine": "Mexican",
            "category": "Tacos",
            "city": "Oakland",
            "state": "CA",
            "price": 9.99,
            "rating": 4.3
        },
        {
            "id": "test-3",
            "text": "Chicken Tikka Masala with basmati rice",
            "restaurant": "Spice Palace",
            "cuisine": "Indian",
            "category": "Entrees",
            "city": "Berkeley",
            "state": "CA",
            "price": 16.99,
            "rating": 4.7
        }
    ]

    for doc in test_docs:
        writer.add_document(**doc)
    writer.commit()

    yield str(index_path)


# Pytest hooks
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require external services"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that require external services"
    )
    config.addinivalue_line(
        "markers", "whoosh: Tests that require Whoosh index"
    )
    config.addinivalue_line(
        "markers", "qdrant: Tests that require Qdrant database"
    )
    config.addinivalue_line(
        "markers", "postgres: Tests that require PostgreSQL database"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Auto-mark based on test name patterns
        if "whoosh" in item.name.lower():
            item.add_marker(pytest.mark.whoosh)
        if "qdrant" in item.name.lower() or "semantic" in item.name.lower():
            item.add_marker(pytest.mark.qdrant)
        if "postgres" in item.name.lower():
            item.add_marker(pytest.mark.postgres)
