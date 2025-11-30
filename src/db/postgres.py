import asyncpg
from config.db_config import POSTGRES_DSN

async def create_tables():
    conn = await asyncpg.connect(POSTGRES_DSN)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id SERIAL PRIMARY KEY,
            name TEXT,
            address TEXT,
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
            price FLOAT
        );
    ''')
    await conn.close()

async def insert_restaurant(data):
    conn = await asyncpg.connect(POSTGRES_DSN)
    result = await conn.fetchrow('''
        INSERT INTO restaurants (name, address, rating, review_count, on_time_rate, delivery_fee, delivery_minimum)
        VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
    ''', data['name'], data['address'], data['rating'], data['review_count'], data['on_time_rate'], data['delivery_fee'], data['delivery_minimum'])
    await conn.close()
    return result['id']

async def insert_menu_item(data):
    conn = await asyncpg.connect(POSTGRES_DSN)
    await conn.execute('''
        INSERT INTO menu_items (restaurant_id, category, name, description, price)
        VALUES ($1, $2, $3, $4, $5)
    ''', data['restaurant_id'], data['category'], data['name'], data.get('description'), data['price'])
    await conn.close()
