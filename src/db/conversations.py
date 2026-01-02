"""
Database operations for chat conversations and messages.

Provides CRUD operations for the conversations and messages tables,
following the async pattern established in postgres.py.
"""
import json
import asyncpg
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from loguru import logger

from src.models.conversation import Message, Conversation, MessageRole


# SQL schema for chat tables
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    search_results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
"""


async def create_tables(pool: asyncpg.Pool) -> None:
    """
    Create conversations and messages tables if they don't exist.

    Args:
        pool: PostgreSQL connection pool
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
        logger.info("Chat tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to create chat tables: {e}")
        raise


async def create_conversation(
    pool: asyncpg.Pool,
    session_id: str,
    title: Optional[str] = None
) -> Conversation:
    """
    Create a new conversation for a session.

    Args:
        pool: PostgreSQL connection pool
        session_id: Session identifier
        title: Optional conversation title

    Returns:
        Created Conversation object
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO conversations (session_id, title)
               VALUES ($1, $2)
               RETURNING id, session_id, title, summary, created_at, updated_at""",
            session_id, title
        )
        logger.debug(f"Created conversation for session {session_id}")
        return Conversation(
            id=row['id'],
            session_id=row['session_id'],
            title=row['title'],
            summary=row['summary'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            messages=[]
        )


async def get_conversation(
    pool: asyncpg.Pool,
    conversation_id: UUID
) -> Optional[Conversation]:
    """
    Retrieve a conversation by ID with all its messages.

    Args:
        pool: PostgreSQL connection pool
        conversation_id: Conversation UUID

    Returns:
        Conversation with messages or None if not found
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM conversations WHERE id = $1",
            conversation_id
        )
        if not row:
            return None

        messages = await conn.fetch(
            """SELECT * FROM messages
               WHERE conversation_id = $1
               ORDER BY created_at ASC""",
            conversation_id
        )

        return Conversation(
            id=row['id'],
            session_id=row['session_id'],
            title=row['title'],
            summary=row['summary'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            messages=[_row_to_message(m) for m in messages]
        )


async def get_conversation_by_session(
    pool: asyncpg.Pool,
    session_id: str
) -> Optional[Conversation]:
    """
    Retrieve the most recent conversation for a session.

    Args:
        pool: PostgreSQL connection pool
        session_id: Session identifier

    Returns:
        Most recent Conversation for the session or None
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM conversations
               WHERE session_id = $1
               ORDER BY created_at DESC
               LIMIT 1""",
            session_id
        )
        if not row:
            return None

        messages = await conn.fetch(
            """SELECT * FROM messages
               WHERE conversation_id = $1
               ORDER BY created_at ASC""",
            row['id']
        )

        return Conversation(
            id=row['id'],
            session_id=row['session_id'],
            title=row['title'],
            summary=row['summary'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            messages=[_row_to_message(m) for m in messages]
        )


async def add_message(
    pool: asyncpg.Pool,
    conversation_id: UUID,
    role: MessageRole,
    content: str,
    search_results: Optional[List[dict]] = None
) -> Message:
    """
    Add a message to a conversation.

    Args:
        pool: PostgreSQL connection pool
        conversation_id: Conversation UUID
        role: Message role (user, assistant, system)
        content: Message content
        search_results: Optional search results to store

    Returns:
        Created Message object
    """
    async with pool.acquire() as conn:
        # Insert message
        row = await conn.fetchrow(
            """INSERT INTO messages (conversation_id, role, content, search_results)
               VALUES ($1, $2, $3, $4)
               RETURNING id, conversation_id, role, content, search_results, created_at""",
            conversation_id,
            role.value,
            content,
            json.dumps(search_results) if search_results else None
        )

        # Update conversation's updated_at timestamp
        await conn.execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
            conversation_id
        )

        logger.debug(f"Added {role.value} message to conversation {conversation_id}")
        return _row_to_message(row)


async def get_messages(
    pool: asyncpg.Pool,
    conversation_id: UUID,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Message]:
    """
    Retrieve messages for a conversation with pagination.

    Args:
        pool: PostgreSQL connection pool
        conversation_id: Conversation UUID
        limit: Maximum number of messages to return
        offset: Number of messages to skip

    Returns:
        List of Message objects
    """
    async with pool.acquire() as conn:
        if limit:
            rows = await conn.fetch(
                """SELECT * FROM messages
                   WHERE conversation_id = $1
                   ORDER BY created_at ASC
                   LIMIT $2 OFFSET $3""",
                conversation_id, limit, offset
            )
        else:
            rows = await conn.fetch(
                """SELECT * FROM messages
                   WHERE conversation_id = $1
                   ORDER BY created_at ASC
                   OFFSET $2""",
                conversation_id, offset
            )

        return [_row_to_message(row) for row in rows]


async def get_recent_messages(
    pool: asyncpg.Pool,
    conversation_id: UUID,
    count: int = 5
) -> List[Message]:
    """
    Get the most recent N messages from a conversation.

    Args:
        pool: PostgreSQL connection pool
        conversation_id: Conversation UUID
        count: Number of recent messages to retrieve

    Returns:
        List of recent Message objects (oldest first)
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM (
                   SELECT * FROM messages
                   WHERE conversation_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2
               ) sub
               ORDER BY created_at ASC""",
            conversation_id, count
        )
        return [_row_to_message(row) for row in rows]


async def update_conversation_summary(
    pool: asyncpg.Pool,
    conversation_id: UUID,
    summary: str
) -> None:
    """
    Update the summary field for a conversation.

    Args:
        pool: PostgreSQL connection pool
        conversation_id: Conversation UUID
        summary: New summary text
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE conversations
               SET summary = $1, updated_at = NOW()
               WHERE id = $2""",
            summary, conversation_id
        )
        logger.debug(f"Updated summary for conversation {conversation_id}")


async def delete_conversation(
    pool: asyncpg.Pool,
    conversation_id: UUID
) -> bool:
    """
    Delete a conversation and all its messages (CASCADE).

    Args:
        pool: PostgreSQL connection pool
        conversation_id: Conversation UUID

    Returns:
        True if deleted, False if not found
    """
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM conversations WHERE id = $1",
            conversation_id
        )
        deleted = result == "DELETE 1"
        if deleted:
            logger.info(f"Deleted conversation {conversation_id}")
        return deleted


async def get_conversation_with_context(
    pool: asyncpg.Pool,
    conversation_id: UUID,
    recent_count: int = 5
) -> tuple[Optional[str], List[Message]]:
    """
    Get conversation summary and recent messages for LLM context.

    Args:
        pool: PostgreSQL connection pool
        conversation_id: Conversation UUID
        recent_count: Number of recent messages to include

    Returns:
        Tuple of (summary, recent_messages)
    """
    async with pool.acquire() as conn:
        # Get conversation summary
        row = await conn.fetchrow(
            "SELECT summary FROM conversations WHERE id = $1",
            conversation_id
        )
        summary = row['summary'] if row else None

        # Get recent messages
        recent_messages = await get_recent_messages(pool, conversation_id, recent_count)

        return summary, recent_messages


def _row_to_message(row: asyncpg.Record) -> Message:
    """Convert a database row to a Message object."""
    search_results = None
    if row['search_results']:
        if isinstance(row['search_results'], str):
            search_results = json.loads(row['search_results'])
        else:
            search_results = row['search_results']

    return Message(
        id=row['id'],
        conversation_id=row['conversation_id'],
        role=MessageRole(row['role']),
        content=row['content'],
        search_results=search_results,
        created_at=row['created_at']
    )
