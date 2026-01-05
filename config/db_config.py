"""
Database configuration module.

This module re-exports database settings from the unified Settings class
for backward compatibility with existing code.
"""
from config.settings import settings

# Re-export database settings for backward compatibility
QDRANT_HOST = settings.qdrant_host
QDRANT_PORT = settings.qdrant_port
QDRANT_API_KEY = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
POSTGRES_DSN = settings.postgres_dsn
