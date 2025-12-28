"""
Comprehensive test suite for hybrid search functionality.

This module tests three main search types:
1. Lexical/Keyword Search (Whoosh)
2. Semantic Search (Qdrant + PostgreSQL)
3. Hybrid Search (Combined)

Tests are organized into unit tests (mocked) and integration tests (requiring services).
"""

import pytest
from typing import Dict, List
from unittest.mock import MagicMock, patch, AsyncMock

from src.search.hybrid_search import (
    keyword_search_whoosh,
    semantic_search,
    hybrid_search,
    filter_results,
    _merge_results
)


# ============================================================================
# UNIT TESTS - Lexical Search (Whoosh) - Mocked
# ============================================================================

class TestKeywordSearchWhooshUnit:
    """Unit tests for Whoosh keyword search with mocked dependencies."""

    @pytest.mark.unit
    def test_keyword_search_returns_empty_when_index_missing(self):
        """
        Test that keyword_search_whoosh returns empty list when index is unavailable.

        This ensures graceful degradation when Whoosh index doesn't exist.
        """
        with patch('src.search.hybrid_search.open_dir', side_effect=OSError("Index not found")):
            results = keyword_search_whoosh("pizza", top_k=10)
            assert results == []
            assert isinstance(results, list)

    @pytest.mark.unit
    def test_keyword_search_result_structure(self, mock_whoosh_index):
        """
        Test that keyword_search_whoosh returns correctly structured results.

        Validates:
        - Returns list of dictionaries
        - Each result has 'id', 'score', 'metadata' keys
        - Metadata contains expected fields
        """
        # Mock search hits
        mock_hit = MagicMock()
        mock_hit.get.side_effect = lambda key, default="": {
            "id": "test-001",
            "text": "Margherita Pizza with fresh mozzarella",
            "restaurant": "Mario's Bistro",
            "restaurant_type": "Italian Restaurant",
            "address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "cuisine": "Italian",
            "category": "Pizza",
            "price": 14.99,
            "rating": 4.5,
            "review_count": 120,
            "description": "Fresh mozzarella, tomato sauce, basil",
        }.get(key, default)
        mock_hit.score = 0.85

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [mock_hit]

        with patch('src.search.hybrid_search.open_dir') as mock_open_dir:
            mock_index = MagicMock()
            mock_index.searcher.return_value.__enter__.return_value = mock_searcher
            mock_index.searcher.return_value.__exit__.return_value = None
            mock_open_dir.return_value = mock_index

            results = keyword_search_whoosh("pizza", top_k=10)

            # Validate structure
            assert isinstance(results, list)
            assert len(results) == 1

            result = results[0]
            assert "id" in result
            assert "score" in result
            assert "metadata" in result

            # Validate score is float
            assert isinstance(result["score"], float)
            assert result["score"] == 0.85

            # Validate metadata structure
            metadata = result["metadata"]
            assert "text" in metadata
            assert "restaurant" in metadata
            assert "price" in metadata
            assert "city" in metadata
            assert "state" in metadata

    @pytest.mark.unit
    def test_keyword_search_respects_top_k(self, mock_whoosh_index):
        """
        Test that keyword_search_whoosh respects the top_k parameter.

        Ensures the limit parameter is passed correctly to Whoosh searcher.
        """
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        with patch('src.search.hybrid_search.open_dir') as mock_open_dir:
            mock_index = MagicMock()
            mock_index.searcher.return_value.__enter__.return_value = mock_searcher
            mock_index.searcher.return_value.__exit__.return_value = None
            mock_open_dir.return_value = mock_index

            keyword_search_whoosh("test query", top_k=5)

            # Verify search was called with correct limit
            call_args = mock_searcher.search.call_args
            assert call_args.kwargs.get('limit') == 5


# ============================================================================
# INTEGRATION TESTS - Lexical Search (Whoosh) - Real Index
# ============================================================================

class TestKeywordSearchWhooshIntegration:
    """Integration tests for Whoosh keyword search with real index."""

    @pytest.mark.integration
    @pytest.mark.whoosh
    def test_keyword_search_with_temp_index(self, temp_whoosh_index):
        """
        Test keyword_search_whoosh with a temporary real Whoosh index.

        This test uses a fixture that creates a real Whoosh index with test data.
        """
        with patch('config.settings.settings.whoosh_index_path', temp_whoosh_index):
            results = keyword_search_whoosh("pizza", top_k=10)

            assert isinstance(results, list)
            assert len(results) > 0

            # Validate result structure
            for result in results:
                assert "id" in result
                assert "score" in result
                assert "metadata" in result
                assert isinstance(result["score"], float)

                metadata = result["metadata"]
                assert "text" in metadata
                assert "restaurant" in metadata

    @pytest.mark.integration
    @pytest.mark.whoosh
    def test_keyword_search_filters_by_cuisine(self, temp_whoosh_index):
        """
        Test that keyword search can find items by cuisine type.
        """
        with patch('config.settings.settings.whoosh_index_path', temp_whoosh_index):
            results = keyword_search_whoosh("italian", top_k=10)

            assert len(results) > 0
            # At least one result should contain Italian cuisine
            italian_found = any("italian" in r["metadata"].get("cuisine", "").lower() for r in results)
            assert italian_found


# ============================================================================
# UNIT TESTS - Semantic Search (Qdrant + PostgreSQL) - Mocked
# ============================================================================

class TestSemanticSearchUnit:
    """Unit tests for semantic search with mocked dependencies."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_semantic_search_returns_empty_on_error(self):
        """
        Test that semantic_search returns empty list on errors.

        Ensures graceful degradation when Qdrant or PostgreSQL unavailable.
        """
        with patch('src.search.hybrid_search.get_embedding', side_effect=Exception("Connection error")):
            results = semantic_search("vegan pizza", top_k=10)
            assert results == []
            assert isinstance(results, list)

    @pytest.mark.unit
    def test_semantic_search_result_structure(self):
        """
        Test that semantic_search returns correctly structured results.

        Validates:
        - Returns list of dictionaries
        - Each result has 'id', 'score', 'metadata' keys
        - Score is float between 0-1
        - Metadata is enriched with 'text' field
        """
        mock_qdrant_results = [
            {
                "id": "semantic-001",
                "score": 0.92,
                "metadata": {
                    "name": "Vegan Buddha Bowl",
                    "description": "Quinoa with roasted vegetables",
                    "price": 12.99,
                    "restaurant": "Green Garden"
                }
            }
        ]

        async def mock_search_menu_items(query_vector, top_k):
            return mock_qdrant_results

        with patch('src.search.hybrid_search.get_embedding', return_value=[0.1] * 384):
            with patch('src.search.hybrid_search.search_menu_items', side_effect=mock_search_menu_items):
                results = semantic_search("healthy bowl", top_k=10)

                assert isinstance(results, list)
                assert len(results) == 1

                result = results[0]
                assert "id" in result
                assert "score" in result
                assert "metadata" in result

                # Validate score
                assert isinstance(result["score"], float)
                assert 0.0 <= result["score"] <= 1.0

                # Validate metadata has text field
                metadata = result["metadata"]
                assert "text" in metadata
                assert len(metadata["text"]) > 0

    @pytest.mark.unit
    def test_semantic_search_enriches_text_field(self):
        """
        Test that semantic_search enriches metadata with 'text' field.

        The text field should combine name and description if not present.
        """
        mock_qdrant_results = [
            {
                "id": "test-001",
                "score": 0.88,
                "metadata": {
                    "name": "Margherita Pizza",
                    "description": "Classic Italian pizza",
                    "price": 14.99
                }
            }
        ]

        async def mock_search_menu_items(query_vector, top_k):
            return mock_qdrant_results

        with patch('src.search.hybrid_search.get_embedding', return_value=[0.1] * 384):
            with patch('src.search.hybrid_search.search_menu_items', side_effect=mock_search_menu_items):
                results = semantic_search("pizza", top_k=10)

                metadata = results[0]["metadata"]
                assert "text" in metadata
                assert "Margherita Pizza" in metadata["text"]
                assert "Classic Italian pizza" in metadata["text"]


# ============================================================================
# INTEGRATION TESTS - Semantic Search (Qdrant + PostgreSQL) - Real Services
# ============================================================================

class TestSemanticSearchIntegration:
    """Integration tests for semantic search requiring real Qdrant and PostgreSQL."""

    @pytest.mark.integration
    @pytest.mark.qdrant
    @pytest.mark.postgres
    @pytest.mark.slow
    def test_semantic_search_with_real_services(self):
        """
        Test semantic_search with real Qdrant and PostgreSQL services.

        Note: This test requires running Qdrant and PostgreSQL services.
        It will be skipped if services are not available.
        """
        from tests.conftest import is_qdrant_available, is_postgres_available

        if not is_qdrant_available() or not is_postgres_available():
            pytest.skip("Qdrant or PostgreSQL service not available")

        results = semantic_search("Italian pasta dishes", top_k=5)

        # Should return results if data is indexed
        assert isinstance(results, list)

        if len(results) > 0:
            # Validate structure
            for result in results:
                assert "id" in result
                assert "score" in result
                assert "metadata" in result
                assert isinstance(result["score"], float)
                assert 0.0 <= result["score"] <= 1.0


# ============================================================================
# UNIT TESTS - Hybrid Search (Combined) - Mocked
# ============================================================================

class TestHybridSearchUnit:
    """Unit tests for hybrid search combining semantic and keyword search."""

    @pytest.mark.unit
    def test_hybrid_search_combines_results(self):
        """
        Test that hybrid_search combines semantic and keyword search results.

        Validates:
        - Calls both search methods
        - Merges results correctly
        - Returns sorted by score descending
        """
        mock_semantic = [
            {
                "id": "item-1",
                "score": 0.9,
                "metadata": {"text": "Vegan Pizza", "price": 12.99, "city": "SF"}
            }
        ]

        mock_lexical = [
            {
                "id": "item-2",
                "score": 0.8,
                "metadata": {"text": "Cheese Pizza", "price": 14.99, "city": "SF"}
            }
        ]

        with patch('src.search.hybrid_search.semantic_search', return_value=mock_semantic):
            with patch('src.search.hybrid_search.keyword_search_whoosh', return_value=mock_lexical):
                results = hybrid_search("pizza", top_k=10)

                assert isinstance(results, list)
                assert len(results) == 2

                # Results should be sorted by score
                scores = [r["score"] for r in results]
                assert scores == sorted(scores, reverse=True)

    @pytest.mark.unit
    def test_hybrid_search_filters_by_price(self):
        """
        Test that hybrid_search correctly filters results by price_max.

        Only items with price <= price_max should be included.
        """
        mock_results = [
            {
                "id": "item-1",
                "score": 0.9,
                "metadata": {"text": "Cheap Pizza", "price": 10.0, "city": "SF"}
            },
            {
                "id": "item-2",
                "score": 0.85,
                "metadata": {"text": "Expensive Pizza", "price": 25.0, "city": "SF"}
            }
        ]

        with patch('src.search.hybrid_search.semantic_search', return_value=mock_results):
            with patch('src.search.hybrid_search.keyword_search_whoosh', return_value=[]):
                results = hybrid_search("pizza", top_k=10, price_max=15.0)

                assert len(results) == 1
                assert results[0]["metadata"]["price"] <= 15.0

    @pytest.mark.unit
    def test_hybrid_search_filters_by_dietary(self):
        """
        Test that hybrid_search correctly filters results by dietary restrictions.

        Only items matching dietary term in description or text should be included.
        """
        mock_results = [
            {
                "id": "item-1",
                "score": 0.9,
                "metadata": {
                    "text": "Vegan Buddha Bowl",
                    "description": "vegan ingredients",
                    "price": 12.0,
                    "city": "SF"
                }
            },
            {
                "id": "item-2",
                "score": 0.85,
                "metadata": {
                    "text": "Chicken Bowl",
                    "description": "grilled chicken",
                    "price": 14.0,
                    "city": "SF"
                }
            }
        ]

        with patch('src.search.hybrid_search.semantic_search', return_value=mock_results):
            with patch('src.search.hybrid_search.keyword_search_whoosh', return_value=[]):
                results = hybrid_search("bowl", top_k=10, dietary="vegan")

                assert len(results) == 1
                assert "vegan" in results[0]["metadata"]["description"].lower()

    @pytest.mark.unit
    def test_hybrid_search_filters_by_location(self):
        """
        Test that hybrid_search correctly filters results by location.

        Only items matching location in city/state/address should be included.
        """
        mock_results = [
            {
                "id": "item-1",
                "score": 0.9,
                "metadata": {
                    "text": "SF Pizza",
                    "price": 12.0,
                    "city": "San Francisco",
                    "state": "CA",
                    "address": "123 Market St"
                }
            },
            {
                "id": "item-2",
                "score": 0.85,
                "metadata": {
                    "text": "Oakland Pizza",
                    "price": 12.0,
                    "city": "Oakland",
                    "state": "CA",
                    "address": "456 Broadway"
                }
            }
        ]

        with patch('src.search.hybrid_search.semantic_search', return_value=mock_results):
            with patch('src.search.hybrid_search.keyword_search_whoosh', return_value=[]):
                results = hybrid_search("pizza", top_k=10, location="San Francisco")

                assert len(results) == 1
                assert "San Francisco" in results[0]["metadata"]["city"]

    @pytest.mark.unit
    def test_hybrid_search_combines_all_filters(self):
        """
        Test that hybrid_search can apply multiple filters simultaneously.

        All filter conditions (price, dietary, location) should be AND-ed.
        """
        mock_results = [
            {
                "id": "item-1",
                "score": 0.9,
                "metadata": {
                    "text": "Vegan Tacos",
                    "description": "vegan black beans",
                    "price": 9.99,
                    "city": "San Francisco",
                    "state": "CA",
                    "address": "123 Market St"
                }
            },
            {
                "id": "item-2",
                "score": 0.85,
                "metadata": {
                    "text": "Vegan Tacos",
                    "description": "vegan black beans",
                    "price": 19.99,  # Too expensive
                    "city": "San Francisco",
                    "state": "CA",
                    "address": "456 Market St"
                }
            },
            {
                "id": "item-3",
                "score": 0.8,
                "metadata": {
                    "text": "Vegan Tacos",
                    "description": "vegan black beans",
                    "price": 9.99,
                    "city": "Oakland",  # Wrong city
                    "state": "CA",
                    "address": "789 Broadway"
                }
            }
        ]

        with patch('src.search.hybrid_search.semantic_search', return_value=mock_results):
            with patch('src.search.hybrid_search.keyword_search_whoosh', return_value=[]):
                results = hybrid_search(
                    "tacos",
                    top_k=10,
                    price_max=15.0,
                    dietary="vegan",
                    location="San Francisco"
                )

                assert len(results) == 1
                assert results[0]["id"] == "item-1"

    @pytest.mark.unit
    def test_hybrid_search_respects_top_k(self):
        """
        Test that hybrid_search returns at most top_k results.
        """
        mock_results = [
            {
                "id": f"item-{i}",
                "score": 0.9 - (i * 0.05),
                "metadata": {"text": f"Pizza {i}", "price": 12.0, "city": "SF"}
            }
            for i in range(20)
        ]

        with patch('src.search.hybrid_search.semantic_search', return_value=mock_results):
            with patch('src.search.hybrid_search.keyword_search_whoosh', return_value=[]):
                results = hybrid_search("pizza", top_k=5)

                assert len(results) <= 5


# ============================================================================
# INTEGRATION TESTS - Hybrid Search - Real Services
# ============================================================================

class TestHybridSearchIntegration:
    """Integration tests for hybrid search with real services."""

    @pytest.mark.integration
    @pytest.mark.whoosh
    @pytest.mark.qdrant
    @pytest.mark.postgres
    @pytest.mark.slow
    def test_hybrid_search_with_all_services(self):
        """
        Test hybrid_search with all real services (Whoosh, Qdrant, PostgreSQL).

        Note: This test requires all services to be running and data to be indexed.
        """
        from tests.conftest import is_whoosh_available, is_qdrant_available, is_postgres_available

        if not (is_whoosh_available() and is_qdrant_available() and is_postgres_available()):
            pytest.skip("Not all required services are available")

        results = hybrid_search("vegan tacos under 15", top_k=10)

        assert isinstance(results, list)

        if len(results) > 0:
            # Validate result structure
            for result in results:
                assert "id" in result
                assert "score" in result
                assert "metadata" in result

            # Validate sorting
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True)


# ============================================================================
# UNIT TESTS - Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Unit tests for helper functions used in search."""

    @pytest.mark.unit
    def test_filter_results_by_price(self, mock_multiple_search_results):
        """
        Test filter_results function with price_max filter.
        """
        filtered = filter_results(mock_multiple_search_results, price_max=12.0)

        assert all(r["metadata"]["price"] <= 12.0 for r in filtered)
        assert len(filtered) < len(mock_multiple_search_results)

    @pytest.mark.unit
    def test_filter_results_by_dietary(self, mock_vegan_search_results):
        """
        Test filter_results function with dietary filter.
        """
        filtered = filter_results(mock_vegan_search_results, dietary="vegan")

        assert len(filtered) == 2
        for result in filtered:
            text = result["metadata"]["text"].lower()
            description = result["metadata"]["description"].lower()
            assert "vegan" in text or "vegan" in description

    @pytest.mark.unit
    def test_filter_results_by_location(self, mock_multiple_search_results):
        """
        Test filter_results function with location filter.
        """
        filtered = filter_results(mock_multiple_search_results, location="San Francisco")

        assert all("San Francisco" in r["metadata"]["city"] for r in filtered)

    @pytest.mark.unit
    def test_merge_results_deduplicates_by_id(self):
        """
        Test _merge_results deduplicates results by ID.

        If same item appears in both semantic and lexical results,
        it should appear once with RRF score.
        """
        semantic = [
            {"id": "item-1", "score": 0.9, "metadata": {"text": "Pizza", "price": 12.0}}
        ]
        lexical = [
            {"id": "item-1", "score": 0.7, "metadata": {"text": "Pizza", "restaurant": "Mario's"}}
        ]

        merged = _merge_results(semantic, lexical)

        assert len(merged) == 1
        assert merged[0]["id"] == "item-1"

        # Metadata should be merged from both sources
        metadata = merged[0]["metadata"]
        assert "text" in metadata
        assert "price" in metadata
        assert "restaurant" in metadata

    @pytest.mark.unit
    def test_merge_results_sorts_by_score(self):
        """
        Test _merge_results returns results sorted by score descending.
        """
        semantic = [
            {"id": "item-1", "score": 0.5, "metadata": {}},
            {"id": "item-2", "score": 0.9, "metadata": {}},
        ]
        lexical = [
            {"id": "item-3", "score": 0.7, "metadata": {}}
        ]

        merged = _merge_results(semantic, lexical)

        scores = [r["score"] for r in merged]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestSearchPerformance:
    """Performance tests for search operations."""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_hybrid_search_large_result_set(self):
        """
        Test hybrid_search performance with large result sets.

        Ensures the merge and filter operations scale well.
        """
        # Generate 1000 mock results
        large_semantic = [
            {
                "id": f"sem-{i}",
                "score": 0.9 - (i * 0.0001),
                "metadata": {"text": f"Item {i}", "price": 10.0 + i}
            }
            for i in range(500)
        ]

        large_lexical = [
            {
                "id": f"lex-{i}",
                "score": 0.85 - (i * 0.0001),
                "metadata": {"text": f"Item {i}", "price": 12.0 + i}
            }
            for i in range(500)
        ]

        with patch('src.search.hybrid_search.semantic_search', return_value=large_semantic):
            with patch('src.search.hybrid_search.keyword_search_whoosh', return_value=large_lexical):
                results = hybrid_search("test", top_k=100)

                assert len(results) <= 100
                assert isinstance(results, list)
