"""
Test suite for agent functionality.

Tests multi-agent orchestration and individual agents.
Note: Some tests require LLM API keys to be set.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# UNIT TESTS - Orchestrator (Mocked)
# ============================================================================

class TestOrchestratorUnit:
    """Unit tests for Orchestrator with mocked dependencies."""

    @pytest.mark.unit
    @pytest.mark.agents
    def test_orchestrator_initialization(self):
        """Test that Orchestrator initializes with pool and client."""
        from src.agents.orchestrator import Orchestrator

        mock_pool = AsyncMock()
        mock_client = MagicMock()

        orchestrator = Orchestrator(
            db_pool=mock_pool,
            qdrant_client=mock_client
        )

        # Verify orchestrator created agents
        assert orchestrator.parser is not None
        assert orchestrator.searcher is not None
        assert orchestrator.quality is not None
        assert orchestrator.verification is not None
        assert orchestrator.ranker is not None

    @pytest.mark.unit
    @pytest.mark.agents
    def test_orchestrator_accepts_none_parameters(self):
        """Test that Orchestrator handles None pool and client."""
        from src.agents.orchestrator import Orchestrator

        # Should not raise error with None parameters
        orchestrator = Orchestrator(db_pool=None, qdrant_client=None)

        assert orchestrator is not None


class TestSearchAgentUnit:
    """Unit tests for SearchAgent with mocked dependencies."""

    @pytest.mark.unit
    @pytest.mark.agents
    def test_search_agent_initialization_with_pool(self):
        """Test SearchAgent initializes with connection pool."""
        mock_pool = AsyncMock()
        mock_client = MagicMock()

        with patch('src.agents.search_agent.settings') as mock_settings:
            # Mock API key settings
            from pydantic import SecretStr
            mock_settings.deepseek_api_key = SecretStr('test-key')
            mock_settings.deepseek_base_url = 'https://api.deepseek.com'
            mock_settings.openai_api_key = None

            from src.agents.search_agent import SearchAgent

            agent = SearchAgent(db_pool=mock_pool, qdrant_client=mock_client)

            # Verify agent stored pool and client
            assert agent.db_pool is mock_pool
            assert agent.qdrant_client is mock_client

    @pytest.mark.unit
    @pytest.mark.agents
    @pytest.mark.asyncio
    async def test_search_agent_perform_search_applies_filters(self):
        """Test SearchAgent applies price, dietary, and location filters."""
        mock_pool = AsyncMock()
        mock_client = MagicMock()

        with patch('src.agents.search_agent.settings') as mock_settings:
            from pydantic import SecretStr
            mock_settings.deepseek_api_key = SecretStr('test-key')
            mock_settings.deepseek_base_url = 'https://api.deepseek.com'
            mock_settings.openai_api_key = None

            with patch('src.agents.search_agent.get_embedding') as mock_embed:
                with patch('src.agents.search_agent.search_menu_items') as mock_search:
                    # Mock search results
                    mock_search.return_value = [
                        {
                            'id': 'item-1',
                            'score': 0.9,
                            'metadata': {
                                'name': 'Vegan Taco',
                                'price': 9.99,
                                'description': 'Delicious vegan taco',
                                'address': '123 Main St, San Francisco, CA',
                                'city': 'San Francisco',
                                'state': 'CA'
                            }
                        },
                        {
                            'id': 'item-2',
                            'score': 0.85,
                            'metadata': {
                                'name': 'Chicken Burrito',
                                'price': 12.99,
                                'description': 'Grilled chicken burrito',
                                'address': '456 Oak St, Oakland, CA',
                                'city': 'Oakland',
                                'state': 'CA'
                            }
                        },
                        {
                            'id': 'item-3',
                            'score': 0.8,
                            'metadata': {
                                'name': 'Vegan Bowl',
                                'price': 15.99,
                                'description': 'Healthy vegan bowl',
                                'address': '789 Pine St, Berkeley, CA',
                                'city': 'Berkeley',
                                'state': 'CA'
                            }
                        }
                    ]

                    mock_embed.return_value = [0.1] * 384

                    from src.agents.search_agent import SearchAgent
                    agent = SearchAgent(db_pool=mock_pool, qdrant_client=mock_client)

                    # Test with filters
                    results = await agent.perform_search(
                        keywords='vegan',
                        top_k=10,
                        price_max=11.0,
                        dietary='vegan',
                        location='San Francisco'
                    )

                    # Should only return vegan items under $11 in San Francisco
                    assert len(results) == 1
                    assert results[0].id == 'item-1'
                    assert results[0].metadata['price'] <= 11.0
                    assert 'vegan' in results[0].metadata['description'].lower()


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestAgentEdgeCases:
    """Test edge cases in agent behavior."""

    @pytest.mark.unit
    @pytest.mark.agents
    def test_search_agent_raises_error_without_api_key(self):
        """Test SearchAgent raises error when no API key is configured."""
        mock_pool = AsyncMock()
        mock_client = MagicMock()

        with patch('src.agents.search_agent.settings') as mock_settings:
            # No API keys set
            mock_settings.deepseek_api_key = None
            mock_settings.openai_api_key = None

            from src.agents.search_agent import SearchAgent

            with pytest.raises(ValueError, match="No API key set for LLM"):
                SearchAgent(db_pool=mock_pool, qdrant_client=mock_client)

    @pytest.mark.unit
    @pytest.mark.agents
    def test_search_agent_uses_openai_fallback(self):
        """Test SearchAgent uses OpenAI when DeepSeek key not available."""
        mock_pool = AsyncMock()
        mock_client = MagicMock()

        with patch('src.agents.search_agent.settings') as mock_settings:
            from pydantic import SecretStr

            # Only OpenAI key set
            mock_settings.deepseek_api_key = None
            mock_settings.openai_api_key = SecretStr('openai-test-key')
            mock_settings.openai_base_url = 'https://api.openai.com/v1'

            from src.agents.search_agent import SearchAgent

            # Should initialize with OpenAI
            agent = SearchAgent(db_pool=mock_pool, qdrant_client=mock_client)
            assert agent is not None

    @pytest.mark.unit
    @pytest.mark.agents
    @pytest.mark.asyncio
    async def test_search_agent_returns_empty_when_no_results(self):
        """Test SearchAgent returns empty list when no results match filters."""
        mock_pool = AsyncMock()
        mock_client = MagicMock()

        with patch('src.agents.search_agent.settings') as mock_settings:
            from pydantic import SecretStr
            mock_settings.deepseek_api_key = SecretStr('test-key')
            mock_settings.deepseek_base_url = 'https://api.deepseek.com'
            mock_settings.openai_api_key = None

            with patch('src.agents.search_agent.get_embedding') as mock_embed:
                with patch('src.agents.search_agent.search_menu_items') as mock_search:
                    # Mock search returns results, but none match filters
                    mock_search.return_value = [
                        {
                            'id': 'item-1',
                            'score': 0.9,
                            'metadata': {
                                'name': 'Expensive Item',
                                'price': 99.99,
                                'description': 'Very expensive',
                                'address': '123 Main St',
                                'city': 'San Francisco',
                                'state': 'CA'
                            }
                        }
                    ]

                    mock_embed.return_value = [0.1] * 384

                    from src.agents.search_agent import SearchAgent
                    agent = SearchAgent(db_pool=mock_pool, qdrant_client=mock_client)

                    # Test with strict filters
                    results = await agent.perform_search(
                        keywords='item',
                        top_k=10,
                        price_max=10.0  # Nothing should match this
                    )

                    # Should return empty list
                    assert len(results) == 0


# ============================================================================
# INTEGRATION TESTS - Agents (Requires API Keys)
# ============================================================================

class TestAgentsIntegration:
    """Integration tests for agents with real LLM APIs."""

    @pytest.mark.integration
    @pytest.mark.agents
    @pytest.mark.slow
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-llm-tests", default=False),
        reason="Requires LLM API keys and --run-llm-tests flag"
    )
    @pytest.mark.asyncio
    async def test_search_agent_real_search(self, skip_if_no_postgres, skip_if_no_qdrant):
        """Test SearchAgent with real database and LLM.

        Note: This test is skipped by default as it requires:
        - LLM API keys (DeepSeek or OpenAI)
        - PostgreSQL database
        - Qdrant vector store

        Run with: pytest --run-llm-tests
        """
        from config.settings import settings

        # Verify API keys are set
        if not settings.deepseek_api_key and not settings.openai_api_key:
            pytest.skip("No LLM API keys configured")

        import asyncpg
        from qdrant_client import QdrantClient
        from config.db_config import POSTGRES_DSN, QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY

        # Create real connections
        pool = await asyncpg.create_pool(POSTGRES_DSN, min_size=1, max_size=2)
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY)

        try:
            from src.agents.search_agent import SearchAgent

            agent = SearchAgent(db_pool=pool, qdrant_client=client)

            # Perform real search
            results = await agent.perform_search(
                keywords='pizza',
                top_k=5
            )

            # Should return results (if data exists)
            assert isinstance(results, list)

        finally:
            await pool.close()
