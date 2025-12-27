import asyncpg
from config.db_config import POSTGRES_DSN

async def create_tables():
    conn = await asyncpg.connect(POSTGRES_DSN)
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
    await conn.close()

async def insert_restaurant(data):
    conn = await asyncpg.connect(POSTGRES_DSN)
    result = await conn.fetchrow('''
        INSERT INTO restaurants (name, address, city, state, latitude, longitude, cuisine, rating, review_count, on_time_rate, delivery_fee, delivery_minimum)
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
    await conn.close()
    return result['id']

async def insert_menu_item(data):
    conn = await asyncpg.connect(POSTGRES_DSN)
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
    await conn.close()
