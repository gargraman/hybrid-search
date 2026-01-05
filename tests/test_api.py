"""
Test suite for API endpoints.

Tests FastAPI application endpoints including:
- Search endpoint
- Health check endpoints
- Error handling
- Request validation
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg
from qdrant_client import QdrantClient


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    from src.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_app_state():
    """Create mock application state with pool and client."""
    mock_state = MagicMock()
    mock_state.db_pool = AsyncMock()
    mock_state.qdrant_client = MagicMock()
    return mock_state


# ============================================================================
# UNIT TESTS - API Endpoints (Mocked)
# ============================================================================

class TestSearchEndpointUnit:
    """Unit tests for /search endpoint."""

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_accepts_valid_request(self, test_client):
        """Test /search endpoint accepts valid search request."""
        with patch('src.main.USE_ORCHESTRATOR', False):
            with patch('src.main.hybrid_search_func') as mock_search:
                # Mock search results
                mock_search.return_value = [
                    {
                        'id': 'test-001',
                        'score': 0.85,
                        'metadata': {
                            'name': 'Margherita Pizza',
                            'restaurant': 'Mario\'s Bistro',
                            'price': 14.99
                        }
                    }
                ]

                response = test_client.post(
                    "/search",
                    json={"query": "pizza", "top_k": 10}
                )

                assert response.status_code == 200
                results = response.json()
                assert isinstance(results, list)
                assert len(results) == 1
                assert results[0]['id'] == 'test-001'

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_validates_query_length(self, test_client):
        """Test /search endpoint validates query length."""
        response = test_client.post(
            "/search",
            json={"query": "", "top_k": 10}  # Empty query
        )

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_validates_top_k_range(self, test_client):
        """Test /search endpoint validates top_k parameter."""
        # Test top_k too large
        response = test_client.post(
            "/search",
            json={"query": "pizza", "top_k": 500}  # Exceeds max of 100
        )
        assert response.status_code == 422

        # Test top_k negative
        response = test_client.post(
            "/search",
            json={"query": "pizza", "top_k": -5}
        )
        assert response.status_code == 422

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_default_top_k(self, test_client):
        """Test /search endpoint uses default top_k value."""
        with patch('src.main.USE_ORCHESTRATOR', False):
            with patch('src.main.hybrid_search_func') as mock_search:
                mock_search.return_value = []

                response = test_client.post(
                    "/search",
                    json={"query": "pizza"}  # No top_k specified
                )

                assert response.status_code == 200

                # Verify default top_k=10 was used
                mock_search.assert_called_once()
                call_args = mock_search.call_args
                assert call_args[0][1] == 10  # Second arg is top_k

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_handles_errors_gracefully(self, test_client):
        """Test /search endpoint handles errors with fallback."""
        with patch('src.main.USE_ORCHESTRATOR', True):
            with patch('src.main.Orchestrator') as MockOrchestrator:
                # Mock orchestrator to raise error
                mock_orch_instance = AsyncMock()
                mock_orch_instance.run_search.side_effect = ValueError("LLM API unavailable")
                MockOrchestrator.return_value = mock_orch_instance

                # Mock fallback search
                with patch('src.main.hybrid_search_func') as mock_fallback:
                    mock_fallback.return_value = [
                        {
                            'id': 'fallback-001',
                            'score': 0.75,
                            'metadata': {'name': 'Fallback Result'}
                        }
                    ]

                    response = test_client.post(
                        "/search",
                        json={"query": "pizza", "top_k": 5}
                    )

                    # Should succeed with fallback
                    assert response.status_code == 200
                    results = response.json()
                    assert len(results) == 1
                    assert results[0]['id'] == 'fallback-001'


class TestHealthEndpointsUnit:
    """Unit tests for health check endpoints."""

    @pytest.mark.unit
    @pytest.mark.api
    def test_health_endpoint_structure(self, test_client):
        """Test /health endpoint returns correct structure."""
        response = test_client.get("/health")

        assert response.status_code == 200
        health_data = response.json()

        # Verify structure
        assert 'status' in health_data
        assert 'components' in health_data
        assert 'postgres' in health_data['components']
        assert 'qdrant' in health_data['components']

    @pytest.mark.unit
    @pytest.mark.api
    def test_liveness_endpoint_returns_alive(self, test_client):
        """Test /health/live endpoint returns alive status."""
        response = test_client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'alive'

    @pytest.mark.unit
    @pytest.mark.api
    def test_readiness_endpoint_checks_dependencies(self, test_client):
        """Test /health/ready endpoint checks dependencies."""
        response = test_client.get("/health/ready")

        # May return 200 or 503 depending on services availability
        assert response.status_code in [200, 503]

        data = response.json()
        assert 'status' in data

    @pytest.mark.unit
    @pytest.mark.api
    def test_metrics_endpoint_exists(self, test_client):
        """Test /metrics endpoint exists."""
        response = test_client.get("/metrics")

        # Metrics endpoint should exist
        assert response.status_code == 200
        assert 'text/plain' in response.headers['content-type']


# ============================================================================
# INTEGRATION TESTS - API Endpoints (Requires Services)
# ============================================================================

class TestSearchEndpointIntegration:
    """Integration tests for /search endpoint with real services."""

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.slow
    def test_search_endpoint_full_flow(self, test_client, skip_if_no_postgres, skip_if_no_qdrant):
        """Test /search endpoint with real database and vector store."""
        response = test_client.post(
            "/search",
            json={"query": "pizza", "top_k": 5}
        )

        # Should succeed if services are available
        assert response.status_code == 200

        results = response.json()
        assert isinstance(results, list)

        # Verify result structure
        if results:
            result = results[0]
            assert 'id' in result
            assert 'score' in result
            assert 'metadata' in result
            assert 'relevance_score' in result

    @pytest.mark.integration
    @pytest.mark.api
    def test_search_endpoint_with_location_filter(self, test_client, skip_if_no_postgres, skip_if_no_qdrant):
        """Test /search endpoint with location-specific query."""
        response = test_client.post(
            "/search",
            json={"query": "pizza in San Francisco", "top_k": 5}
        )

        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)


class TestHealthEndpointsIntegration:
    """Integration tests for health endpoints with real services."""

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.postgres
    def test_health_endpoint_postgres_healthy(self, test_client, skip_if_no_postgres):
        """Test /health endpoint reports PostgreSQL as healthy."""
        response = test_client.get("/health")

        assert response.status_code == 200
        health_data = response.json()

        # PostgreSQL should be healthy
        assert health_data['components']['postgres'] == 'healthy'

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.qdrant
    def test_health_endpoint_qdrant_healthy(self, test_client, skip_if_no_qdrant):
        """Test /health endpoint reports Qdrant as healthy."""
        response = test_client.get("/health")

        assert response.status_code == 200
        health_data = response.json()

        # Qdrant should be healthy
        assert health_data['components']['qdrant'] == 'healthy'

    @pytest.mark.integration
    @pytest.mark.api
    def test_readiness_endpoint_when_ready(self, test_client, skip_if_no_postgres, skip_if_no_qdrant):
        """Test /health/ready endpoint when all services are ready."""
        response = test_client.get("/health/ready")

        # Should be ready when all services are available
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'ready'
        assert data['postgres'] == 'ready'
        assert data['qdrant'] == 'ready'


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestAPIErrorHandling:
    """Test API error handling and edge cases."""

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_invalid_json(self, test_client):
        """Test /search endpoint with invalid JSON payload."""
        response = test_client.post(
            "/search",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_missing_query_field(self, test_client):
        """Test /search endpoint with missing query field."""
        response = test_client.post(
            "/search",
            json={"top_k": 10}  # Missing query
        )

        assert response.status_code == 422

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_extra_fields_ignored(self, test_client):
        """Test /search endpoint ignores extra fields."""
        with patch('src.main.USE_ORCHESTRATOR', False):
            with patch('src.main.hybrid_search_func') as mock_search:
                mock_search.return_value = []

                response = test_client.post(
                    "/search",
                    json={
                        "query": "pizza",
                        "top_k": 5,
                        "extra_field": "should be ignored"
                    }
                )

                # Should succeed and ignore extra field
                assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.api
    def test_nonexistent_endpoint_returns_404(self, test_client):
        """Test that nonexistent endpoints return 404."""
        response = test_client.get("/nonexistent")

        assert response.status_code == 404

    @pytest.mark.unit
    @pytest.mark.api
    def test_search_endpoint_method_not_allowed(self, test_client):
        """Test /search endpoint only accepts POST."""
        response = test_client.get("/search")

        assert response.status_code == 405  # Method Not Allowed


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestAPIPerformance:
    """Test API performance characteristics."""

    @pytest.mark.unit
    @pytest.mark.api
    @pytest.mark.slow
    def test_search_endpoint_response_time(self, test_client):
        """Test /search endpoint responds within reasonable time."""
        import time

        with patch('src.main.USE_ORCHESTRATOR', False):
            with patch('src.main.hybrid_search_func') as mock_search:
                mock_search.return_value = []

                start = time.time()
                response = test_client.post(
                    "/search",
                    json={"query": "pizza", "top_k": 10}
                )
                elapsed = time.time() - start

                assert response.status_code == 200
                # Should respond within 5 seconds (with mocking)
                assert elapsed < 5.0

    @pytest.mark.unit
    @pytest.mark.api
    def test_health_endpoint_fast_response(self, test_client):
        """Test /health endpoint responds quickly."""
        import time

        start = time.time()
        response = test_client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Health check should be very fast (< 1 second)
        assert elapsed < 1.0
