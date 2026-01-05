"""
Test suite for database operations.

Tests PostgreSQL database functions including:
- Table creation
- Restaurant insertion
- Menu item insertion
- Connection pool usage
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg

from src.db.postgres import (
    create_tables,
    insert_restaurant,
    insert_menu_item,
    _execute_table_creation
)


# ============================================================================
# UNIT TESTS - Database Operations (Mocked)
# ============================================================================

class TestDatabaseOperationsUnit:
    """Unit tests for database operations with mocked connections."""

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_create_tables_with_pool(self):
        """Test create_tables uses connection pool correctly."""
        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Call create_tables with pool
        await create_tables(mock_pool)

        # Verify pool.acquire was called
        mock_pool.acquire.assert_called_once()

        # Verify SQL execution
        assert mock_conn.execute.call_count >= 5  # At least 5 SQL statements

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_create_tables_without_pool_creates_temp_pool(self):
        """Test create_tables creates temporary pool when none provided."""
        with patch('asyncpg.create_pool') as mock_create_pool:
            # Mock temporary pool
            mock_temp_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_temp_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_temp_pool.__aenter__.return_value = mock_temp_pool
            mock_temp_pool.__aexit__.return_value = None

            mock_create_pool.return_value = mock_temp_pool

            # Call create_tables without pool
            await create_tables(None)

            # Verify temporary pool was created
            mock_create_pool.assert_called_once()
            mock_temp_pool.acquire.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_insert_restaurant_returns_id(self):
        """Test insert_restaurant returns restaurant ID."""
        # Mock pool and connection
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock fetchrow to return ID
        mock_conn.fetchrow.return_value = {'id': 123}

        # Restaurant data
        restaurant_data = {
            'name': 'Test Restaurant',
            'address': '123 Test St',
            'city': 'San Francisco',
            'state': 'CA',
            'latitude': 37.7749,
            'longitude': -122.4194,
            'cuisine': 'Italian',
            'rating': 4.5,
            'review_count': 100,
            'on_time_rate': '95%',
            'delivery_fee': 5.0,
            'delivery_minimum': 15.0
        }

        # Call insert_restaurant
        result_id = await insert_restaurant(mock_pool, restaurant_data)

        # Verify result
        assert result_id == 123
        mock_pool.acquire.assert_called_once()
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_insert_restaurant_handles_conflict(self):
        """Test insert_restaurant handles ON CONFLICT properly."""
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock fetchrow to return existing ID (ON CONFLICT scenario)
        mock_conn.fetchrow.return_value = {'id': 456}

        restaurant_data = {
            'name': 'Duplicate Restaurant',
            'address': '123 Test St',
            'city': 'San Francisco',
            'state': 'CA',
            'latitude': 37.7749,
            'longitude': -122.4194,
            'cuisine': 'Mexican',
            'rating': 4.0,
            'review_count': 50,
            'on_time_rate': '90%',
            'delivery_fee': 3.0,
            'delivery_minimum': 10.0
        }

        result_id = await insert_restaurant(mock_pool, restaurant_data)

        # Verify it returns the ID even on conflict
        assert result_id == 456

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_insert_menu_item_executes_query(self):
        """Test insert_menu_item executes insert query."""
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        menu_item_data = {
            'restaurant_id': 123,
            'category': 'Pizza',
            'name': 'Margherita',
            'description': 'Fresh mozzarella and basil',
            'price': 14.99,
            'external_id': 'test-pizza-001'
        }

        # Call insert_menu_item
        await insert_menu_item(mock_pool, menu_item_data)

        # Verify execute was called with correct parameters
        mock_pool.acquire.assert_called_once()
        mock_conn.execute.assert_called_once()

        # Verify the query includes ON CONFLICT
        call_args = mock_conn.execute.call_args
        assert 'ON CONFLICT' in call_args[0][0]
        assert 'external_id' in call_args[0][0]

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_insert_menu_item_with_optional_description(self):
        """Test insert_menu_item handles optional description field."""
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Menu item without description
        menu_item_data = {
            'restaurant_id': 123,
            'category': 'Drinks',
            'name': 'Water',
            'price': 0.0,
            'external_id': 'test-drink-001'
        }

        await insert_menu_item(mock_pool, menu_item_data)

        # Verify it doesn't fail with missing description
        mock_conn.execute.assert_called_once()


# ============================================================================
# INTEGRATION TESTS - Database Operations (Requires PostgreSQL)
# ============================================================================

class TestDatabaseOperationsIntegration:
    """Integration tests for database operations with real PostgreSQL."""

    @pytest.mark.integration
    @pytest.mark.postgres
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_create_tables_integration(self, skip_if_no_postgres):
        """Test create_tables with real PostgreSQL database."""
        from config.db_config import POSTGRES_DSN

        # Create connection pool
        pool = await asyncpg.create_pool(POSTGRES_DSN, min_size=1, max_size=2)

        try:
            # Create tables
            await create_tables(pool)

            # Verify tables exist
            async with pool.acquire() as conn:
                # Check restaurants table
                result = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'restaurants')"
                )
                assert result is True

                # Check menu_items table
                result = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'menu_items')"
                )
                assert result is True

        finally:
            await pool.close()

    @pytest.mark.integration
    @pytest.mark.postgres
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_insert_restaurant_integration(self, skip_if_no_postgres):
        """Test insert_restaurant with real PostgreSQL database."""
        from config.db_config import POSTGRES_DSN
        import time

        pool = await asyncpg.create_pool(POSTGRES_DSN, min_size=1, max_size=2)

        try:
            await create_tables(pool)

            # Insert test restaurant
            restaurant_data = {
                'name': f'Test Restaurant {int(time.time())}',
                'address': '123 Test Street',
                'city': 'San Francisco',
                'state': 'CA',
                'latitude': 37.7749,
                'longitude': -122.4194,
                'cuisine': 'Italian',
                'rating': 4.5,
                'review_count': 100,
                'on_time_rate': '95%',
                'delivery_fee': 5.0,
                'delivery_minimum': 15.0
            }

            restaurant_id = await insert_restaurant(pool, restaurant_data)

            # Verify ID was returned
            assert restaurant_id is not None
            assert isinstance(restaurant_id, int)
            assert restaurant_id > 0

            # Verify restaurant exists in database
            async with pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM restaurants WHERE id = $1",
                    restaurant_id
                )
                assert result is not None
                assert result['name'] == restaurant_data['name']
                assert result['city'] == 'San Francisco'
                assert result['state'] == 'CA'

        finally:
            await pool.close()

    @pytest.mark.integration
    @pytest.mark.postgres
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_insert_menu_item_integration(self, skip_if_no_postgres):
        """Test insert_menu_item with real PostgreSQL database."""
        from config.db_config import POSTGRES_DSN
        import time

        pool = await asyncpg.create_pool(POSTGRES_DSN, min_size=1, max_size=2)

        try:
            await create_tables(pool)

            # First insert a restaurant
            restaurant_data = {
                'name': f'Test Restaurant {int(time.time())}',
                'address': '456 Menu Street',
                'city': 'Oakland',
                'state': 'CA',
                'latitude': 37.8044,
                'longitude': -122.2712,
                'cuisine': 'Mexican',
                'rating': 4.3,
                'review_count': 75,
                'on_time_rate': '92%',
                'delivery_fee': 3.0,
                'delivery_minimum': 10.0
            }

            restaurant_id = await insert_restaurant(pool, restaurant_data)

            # Insert menu item
            menu_item_data = {
                'restaurant_id': restaurant_id,
                'category': 'Tacos',
                'name': 'Vegan Taco',
                'description': 'Black beans, avocado, salsa',
                'price': 9.99,
                'external_id': f'test-taco-{int(time.time())}'
            }

            await insert_menu_item(pool, menu_item_data)

            # Verify menu item exists
            async with pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM menu_items WHERE external_id = $1",
                    menu_item_data['external_id']
                )
                assert result is not None
                assert result['name'] == 'Vegan Taco'
                assert result['category'] == 'Tacos'
                assert float(result['price']) == 9.99
                assert result['restaurant_id'] == restaurant_id

        finally:
            await pool.close()


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestDatabaseEdgeCases:
    """Test edge cases and error handling in database operations."""

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_insert_restaurant_missing_required_fields(self):
        """Test insert_restaurant raises error for missing required fields."""
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Missing required fields
        incomplete_data = {
            'name': 'Test Restaurant'
            # Missing other required fields
        }

        # Should raise KeyError
        with pytest.raises(KeyError):
            await insert_restaurant(mock_pool, incomplete_data)

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_connection_pool_properly_released(self):
        """Test that connection pool connections are properly released."""
        mock_conn = AsyncMock()
        mock_pool = AsyncMock()

        # Track acquire and release
        acquire_context = AsyncMock()
        acquire_context.__aenter__.return_value = mock_conn
        acquire_context.__aexit__.return_value = None
        mock_pool.acquire.return_value = acquire_context

        mock_conn.fetchrow.return_value = {'id': 999}

        restaurant_data = {
            'name': 'Pool Test Restaurant',
            'address': '789 Pool St',
            'city': 'Berkeley',
            'state': 'CA',
            'latitude': 37.8716,
            'longitude': -122.2727,
            'cuisine': 'Thai',
            'rating': 4.6,
            'review_count': 200,
            'on_time_rate': '97%',
            'delivery_fee': 4.0,
            'delivery_minimum': 12.0
        }

        await insert_restaurant(mock_pool, restaurant_data)

        # Verify __aexit__ was called (connection released)
        acquire_context.__aexit__.assert_called_once()
