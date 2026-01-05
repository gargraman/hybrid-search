"""
PostgreSQL database operations.

This module provides functions for creating tables and inserting data into PostgreSQL.
All functions accept an optional connection pool parameter for efficient connection management.
"""
from typing import Optional, Any, Dict
import asyncpg
from asyncpg import Pool, Connection
from config.db_config import POSTGRES_DSN


async def _execute_table_creation(conn: Connection) -> None:
    """
    Execute database table creation and migration DDL statements.

    Args:
        conn: Active database connection
    """
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id SERIAL PRIMARY KEY,
            name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            cuisine TEXT,
            rating FLOAT,
            review_count INT,
            on_time_rate TEXT,
            delivery_fee FLOAT,
            delivery_minimum FLOAT
        );
        CREATE TABLE IF NOT EXISTS menu_items (
            id SERIAL PRIMARY KEY,
            restaurant_id INT REFERENCES restaurants(id),
            category TEXT,
            name TEXT,
            description TEXT,
            price FLOAT,
            external_id TEXT UNIQUE
        );
    ''')
    await conn.execute('''
        ALTER TABLE restaurants
            ADD COLUMN IF NOT EXISTS city TEXT,
            ADD COLUMN IF NOT EXISTS state TEXT,
            ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS cuisine TEXT;
    ''')
    await conn.execute('''
        ALTER TABLE menu_items
            ADD COLUMN IF NOT EXISTS external_id TEXT;
    ''')
    await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_menu_items_external_id ON menu_items(external_id);
    ''')
    await conn.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_restaurants_name_address ON restaurants(name, address);
    ''')


async def create_tables(pool: Optional[Pool] = None) -> None:
    """
    Create database tables if they don't exist.

    Args:
        pool: Optional connection pool. If not provided, creates a temporary connection.
              For production use, always pass a pool for better resource management.

    Raises:
        asyncpg.PostgresError: If database operation fails
    """
    if pool:
        async with pool.acquire() as conn:
            await _execute_table_creation(conn)
    else:
        # Fallback for standalone script execution (not recommended for production)
        async with asyncpg.create_pool(
            POSTGRES_DSN,
            min_size=1,
            max_size=2,
            timeout=30
        ) as temp_pool:
            async with temp_pool.acquire() as conn:
                await _execute_table_creation(conn)


async def insert_restaurant(pool: Pool, data: Dict[str, Any]) -> int:
    """
    Insert or update a restaurant record.

    Uses ON CONFLICT to update existing records based on (name, address) unique constraint.

    Args:
        pool: Database connection pool
        data: Restaurant data dictionary with keys:
            - name (str): Restaurant name
            - address (str): Restaurant address
            - city (str, optional): City
            - state (str, optional): State
            - latitude (float, optional): Latitude coordinate
            - longitude (float, optional): Longitude coordinate
            - cuisine (str, optional): Cuisine type
            - rating (float): Rating score
            - review_count (int): Number of reviews
            - on_time_rate (str): On-time delivery rate
            - delivery_fee (float): Delivery fee
            - delivery_minimum (float): Minimum order for delivery

    Returns:
        The restaurant ID (int)

    Raises:
        asyncpg.PostgresError: If database operation fails
        KeyError: If required keys are missing from data dict
    """
    async with pool.acquire() as conn:
        result = await conn.fetchrow('''
            INSERT INTO restaurants (name, address, city, state, latitude, longitude,
                                     cuisine, rating, review_count, on_time_rate,
                                     delivery_fee, delivery_minimum)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (name, address) DO UPDATE
            SET city = EXCLUDED.city,
                state = EXCLUDED.state,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                cuisine = EXCLUDED.cuisine,
                rating = EXCLUDED.rating,
                review_count = EXCLUDED.review_count,
                on_time_rate = EXCLUDED.on_time_rate,
                delivery_fee = EXCLUDED.delivery_fee,
                delivery_minimum = EXCLUDED.delivery_minimum
            RETURNING id
        ''',
            data['name'],
            data['address'],
            data.get('city'),
            data.get('state'),
            data.get('latitude'),
            data.get('longitude'),
            data.get('cuisine'),
            data['rating'],
            data['review_count'],
            data['on_time_rate'],
            data['delivery_fee'],
            data['delivery_minimum']
        )
        return result['id']


async def insert_menu_item(pool: Pool, data: Dict[str, Any]) -> None:
    """
    Insert or update a menu item record.

    Uses ON CONFLICT to update existing records based on external_id unique constraint.

    Args:
        pool: Database connection pool
        data: Menu item data dictionary with keys:
            - restaurant_id (int): Foreign key to restaurants table
            - category (str): Menu item category
            - name (str): Menu item name
            - description (str, optional): Item description
            - price (float): Item price
            - external_id (str): Unique external identifier (for Qdrant join)

    Raises:
        asyncpg.PostgresError: If database operation fails
        KeyError: If required keys are missing from data dict
    """
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO menu_items (restaurant_id, category, name, description, price, external_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (external_id) DO UPDATE
            SET category = EXCLUDED.category,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                price = EXCLUDED.price,
                restaurant_id = EXCLUDED.restaurant_id
        ''',
            data['restaurant_id'],
            data['category'],
            data['name'],
            data.get('description'),
            data['price'],
            data['external_id']
        )
