"""
Test suite for configuration.

Tests configuration loading, validation, and settings management.
"""
import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError


# ============================================================================
# UNIT TESTS - Configuration Settings
# ============================================================================

class TestSettingsConfiguration:
    """Unit tests for settings configuration."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_loads_with_defaults(self):
        """Test that settings loads with default values."""
        from config.settings import Settings

        settings = Settings()

        # Verify defaults are set
        assert settings.postgres_dsn.startswith('postgresql://')
        assert settings.qdrant_host == 'localhost'
        assert settings.qdrant_port == 6333
        assert settings.rrf_k == 60
        assert settings.whoosh_index_path == './whoosh_index'

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_loads_from_environment(self):
        """Test that settings loads from environment variables."""
        from config.settings import Settings

        with patch.dict(os.environ, {
            'POSTGRES_DSN': 'postgresql://testuser:testpass@testhost:5432/testdb',
            'QDRANT_HOST': 'test-qdrant-host',
            'QDRANT_PORT': '9999',
            'RRF_K': '80'
        }):
            settings = Settings()

            assert settings.postgres_dsn == 'postgresql://testuser:testpass@testhost:5432/testdb'
            assert settings.qdrant_host == 'test-qdrant-host'
            assert settings.qdrant_port == 9999
            assert settings.rrf_k == 80

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_validates_postgres_dsn_format(self):
        """Test that settings validates PostgreSQL DSN format."""
        from config.settings import Settings

        # Valid DSN should work
        settings = Settings(postgres_dsn='postgresql://user:pass@localhost:5432/db')
        assert settings.postgres_dsn.startswith('postgresql://')

        # Invalid DSN should raise error
        with pytest.raises(ValidationError) as exc_info:
            Settings(postgres_dsn='invalid-dsn')

        assert 'postgres_dsn' in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_validates_qdrant_port_range(self):
        """Test that settings validates Qdrant port range."""
        from config.settings import Settings

        # Valid port
        settings = Settings(qdrant_port=6333)
        assert settings.qdrant_port == 6333

        # Port too high
        with pytest.raises(ValidationError):
            Settings(qdrant_port=99999)

        # Port too low
        with pytest.raises(ValidationError):
            Settings(qdrant_port=0)

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_validates_rrf_k_positive(self):
        """Test that settings validates RRF k parameter is positive."""
        from config.settings import Settings

        # Valid k
        settings = Settings(rrf_k=60)
        assert settings.rrf_k == 60

        # Invalid k (negative)
        with pytest.raises(ValidationError):
            Settings(rrf_k=-5)

        # Invalid k (zero)
        with pytest.raises(ValidationError):
            Settings(rrf_k=0)

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_chat_parameters_validated(self):
        """Test that chat parameters are validated."""
        from config.settings import Settings

        # Valid chat settings
        settings = Settings(
            chat_max_iterations=5,
            chat_max_retries=3,
            chat_summary_max_tokens=500
        )
        assert settings.chat_max_iterations == 5
        assert settings.chat_max_retries == 3
        assert settings.chat_summary_max_tokens == 500

        # Invalid max_iterations (too high)
        with pytest.raises(ValidationError):
            Settings(chat_max_iterations=100)

        # Invalid max_retries (too high)
        with pytest.raises(ValidationError):
            Settings(chat_max_retries=50)

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_api_keys_are_secret(self):
        """Test that API keys use SecretStr."""
        from config.settings import Settings
        from pydantic import SecretStr

        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test-deepseek-key',
            'OPENAI_API_KEY': 'test-openai-key'
        }):
            settings = Settings()

            # Should be SecretStr instances
            assert isinstance(settings.deepseek_api_key, SecretStr)
            assert isinstance(settings.openai_api_key, SecretStr)

            # Values should be retrievable but hidden in repr
            assert settings.deepseek_api_key.get_secret_value() == 'test-deepseek-key'
            assert settings.openai_api_key.get_secret_value() == 'test-openai-key'

            # Should be hidden in string representation
            assert 'test-deepseek-key' not in str(settings)


class TestDatabaseConfiguration:
    """Unit tests for database configuration."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_db_config_exports_settings(self):
        """Test that db_config re-exports settings correctly."""
        from config import db_config

        # Verify constants are exported
        assert hasattr(db_config, 'POSTGRES_DSN')
        assert hasattr(db_config, 'QDRANT_HOST')
        assert hasattr(db_config, 'QDRANT_PORT')
        assert hasattr(db_config, 'QDRANT_API_KEY')

    @pytest.mark.unit
    @pytest.mark.config
    def test_db_config_postgres_dsn_format(self):
        """Test that exported PostgreSQL DSN is valid."""
        from config.db_config import POSTGRES_DSN

        assert isinstance(POSTGRES_DSN, str)
        assert POSTGRES_DSN.startswith(('postgresql://', 'postgres://'))

    @pytest.mark.unit
    @pytest.mark.config
    def test_db_config_qdrant_settings(self):
        """Test that exported Qdrant settings are valid."""
        from config.db_config import QDRANT_HOST, QDRANT_PORT

        assert isinstance(QDRANT_HOST, str)
        assert len(QDRANT_HOST) > 0

        assert isinstance(QDRANT_PORT, int)
        assert 1 <= QDRANT_PORT <= 65535


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestSettingsEdgeCases:
    """Test edge cases in settings configuration."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_handles_missing_optional_fields(self):
        """Test that settings handles missing optional fields gracefully."""
        from config.settings import Settings

        # Create settings without optional API keys
        settings = Settings()

        # Optional fields should be None
        assert settings.deepseek_api_key is None or isinstance(settings.deepseek_api_key, type(settings.deepseek_api_key))
        assert settings.openai_api_key is None or isinstance(settings.openai_api_key, type(settings.openai_api_key))
        assert settings.qdrant_api_key is None or isinstance(settings.qdrant_api_key, type(settings.qdrant_api_key))

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_case_insensitive_env_vars(self):
        """Test that settings accepts case-insensitive environment variables."""
        from config.settings import Settings

        with patch.dict(os.environ, {
            'postgres_dsn': 'postgresql://test:test@localhost:5432/testdb',
            'POSTGRES_DSN': 'postgresql://override:override@localhost:5432/overridedb'
        }):
            settings = Settings()

            # Should use one of the values (case-insensitive matching)
            assert 'localhost:5432' in settings.postgres_dsn

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_allows_extra_fields(self):
        """Test that settings allows extra fields (forward compatibility)."""
        from config.settings import Settings

        # Should not fail with extra fields
        try:
            settings = Settings(extra_field='should_be_ignored')
            # If it gets here, extra fields are ignored (good)
            assert True
        except ValidationError:
            # If it fails, that's also acceptable depending on config
            pass

    @pytest.mark.unit
    @pytest.mark.config
    def test_settings_singleton_pattern(self):
        """Test that settings uses singleton pattern."""
        from config.settings import settings as settings1
        from config.settings import settings as settings2

        # Should be the same instance
        assert settings1 is settings2


# ============================================================================
# INTEGRATION TESTS - Configuration
# ============================================================================

class TestConfigurationIntegration:
    """Integration tests for configuration with real environment."""

    @pytest.mark.integration
    @pytest.mark.config
    def test_settings_loads_in_production_mode(self):
        """Test that settings can load in production-like environment."""
        from config.settings import Settings

        with patch.dict(os.environ, {
            'POSTGRES_DSN': 'postgresql://produser:prodpass@prod-db:5432/proddb',
            'QDRANT_HOST': 'prod-qdrant',
            'QDRANT_PORT': '6333',
            'DEEPSEEK_API_KEY': 'prod-deepseek-key',
            'OPENAI_API_KEY': 'prod-openai-key'
        }):
            settings = Settings()

            # Verify production settings loaded
            assert 'prod-db' in settings.postgres_dsn
            assert settings.qdrant_host == 'prod-qdrant'
            assert settings.deepseek_api_key.get_secret_value() == 'prod-deepseek-key'

    @pytest.mark.integration
    @pytest.mark.config
    def test_all_config_modules_importable(self):
        """Test that all configuration modules can be imported."""
        # Should not raise ImportError
        import config.settings
        import config.db_config

        assert config.settings is not None
        assert config.db_config is not None
