"""
Chat session memory manager.

Manages BeeAI Memory instances per session with PostgreSQL backup
for persistence across server restarts.
"""
from typing import Dict, List, Optional, Any
import asyncpg
from loguru import logger

from config.settings import settings
from src.models.conversation import MessageRole

# Try to import BeeAI memory components
try:
    from beeai_framework.memory import UnconstrainedMemory
    from beeai_framework import LLM
    from beeai_framework.messages import UserMessage, AssistantMessage, SystemMessage
    BEEAI_MEMORY_AVAILABLE = True
except ImportError:
    BEEAI_MEMORY_AVAILABLE = False
    logger.warning("BeeAI memory module not available, using fallback implementation")


class FallbackMemory:
    """
    Simple fallback memory implementation when BeeAI is not available.

    Stores messages in a list for basic context management.
    """

    def __init__(self):
        self.messages: List[Dict[str, str]] = []

    async def add(self, message: Any) -> None:
        """Add a message to memory."""
        if hasattr(message, 'content'):
            role = "user" if "User" in type(message).__name__ else "assistant"
            self.messages.append({
                "role": role,
                "content": message.content
            })
        elif isinstance(message, dict):
            self.messages.append(message)

    def get_context(self, max_messages: int = 10) -> str:
        """Get formatted context from recent messages."""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        lines = []
        for msg in recent:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []


class ChatSessionManager:
    """
    Manages BeeAI Memory instances per session.

    Features:
    - Uses BeeAI UnconstrainedMemory for in-memory storage
    - Persists to PostgreSQL for session recovery
    - Handles session lifecycle (create, restore, cleanup)
    - Provides context building for LLM prompts
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize the session manager.

        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool
        self.sessions: Dict[str, Any] = {}  # session_id -> Memory instance
        self.llm = self._create_llm() if BEEAI_MEMORY_AVAILABLE else None

    def _create_llm(self) -> Optional[Any]:
        """Create LLM instance for memory operations."""
        try:
            if settings.deepseek_api_key:
                return LLM(
                    model="deepseek-chat",
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url
                )
            elif settings.openai_api_key:
                return LLM(
                    model="gpt-3.5-turbo",
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url
                )
        except Exception as e:
            logger.warning(f"Failed to create LLM for memory: {e}")
        return None

    async def get_or_create_memory(self, session_id: str) -> Any:
        """
        Get existing memory or create new one for a session.

        If the session has been restored from PostgreSQL, the memory
        will be populated with previous messages.

        Args:
            session_id: Session identifier

        Returns:
            Memory instance (BeeAI UnconstrainedMemory or FallbackMemory)
        """
        if session_id not in self.sessions:
            # Create new memory
            if BEEAI_MEMORY_AVAILABLE:
                memory = UnconstrainedMemory()
            else:
                memory = FallbackMemory()

            # Restore from PostgreSQL if exists
            await self._restore_from_db(session_id, memory)
            self.sessions[session_id] = memory

            logger.debug(f"Created memory for session {session_id}")

        return self.sessions[session_id]

    async def add_user_message(
        self,
        session_id: str,
        content: str,
        conversation_id: Optional[str] = None
    ) -> None:
        """
        Add a user message to session memory and persist to DB.

        Args:
            session_id: Session identifier
            content: Message content
            conversation_id: Optional conversation ID for DB persistence
        """
        memory = await self.get_or_create_memory(session_id)

        if BEEAI_MEMORY_AVAILABLE:
            await memory.add(UserMessage(content=content))
        else:
            await memory.add({"role": "user", "content": content})

        # Persist to DB if we have a conversation ID
        if conversation_id and self.db_pool:
            await self._persist_message(conversation_id, "user", content)

    async def add_assistant_message(
        self,
        session_id: str,
        content: str,
        conversation_id: Optional[str] = None,
        search_results: Optional[List[dict]] = None
    ) -> None:
        """
        Add an assistant message to session memory and persist to DB.

        Args:
            session_id: Session identifier
            content: Message content
            conversation_id: Optional conversation ID for DB persistence
            search_results: Optional search results to store with message
        """
        memory = await self.get_or_create_memory(session_id)

        if BEEAI_MEMORY_AVAILABLE:
            await memory.add(AssistantMessage(content=content))
        else:
            await memory.add({"role": "assistant", "content": content})

        # Persist to DB if we have a conversation ID
        if conversation_id and self.db_pool:
            await self._persist_message(conversation_id, "assistant", content, search_results)

    async def get_context(
        self,
        session_id: str,
        max_messages: int = None
    ) -> str:
        """
        Get formatted context from session memory for LLM prompts.

        Args:
            session_id: Session identifier
            max_messages: Maximum messages to include (default from settings)

        Returns:
            Formatted context string
        """
        if max_messages is None:
            max_messages = settings.chat_recent_messages_count

        memory = await self.get_or_create_memory(session_id)

        if BEEAI_MEMORY_AVAILABLE and hasattr(memory, 'messages'):
            messages = memory.messages[-max_messages:] if len(memory.messages) > max_messages else memory.messages
            lines = []
            for msg in messages:
                role = getattr(msg, 'role', 'unknown')
                content = getattr(msg, 'content', str(msg))
                lines.append(f"{role}: {content}")
            return "\n".join(lines)
        elif isinstance(memory, FallbackMemory):
            return memory.get_context(max_messages)
        else:
            return ""

    async def _restore_from_db(self, session_id: str, memory: Any) -> None:
        """
        Restore memory state from PostgreSQL.

        Args:
            session_id: Session identifier
            memory: Memory instance to populate
        """
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                # Get the most recent conversation for this session
                conv_row = await conn.fetchrow(
                    """SELECT id, summary FROM conversations
                       WHERE session_id = $1
                       ORDER BY created_at DESC
                       LIMIT 1""",
                    session_id
                )

                if not conv_row:
                    return

                # Get messages for this conversation
                message_rows = await conn.fetch(
                    """SELECT role, content FROM messages
                       WHERE conversation_id = $1
                       ORDER BY created_at ASC
                       LIMIT $2""",
                    conv_row['id'],
                    settings.chat_summarization_threshold
                )

                # Add messages to memory
                for row in message_rows:
                    if BEEAI_MEMORY_AVAILABLE:
                        if row['role'] == 'user':
                            await memory.add(UserMessage(content=row['content']))
                        elif row['role'] == 'assistant':
                            await memory.add(AssistantMessage(content=row['content']))
                    else:
                        await memory.add({
                            "role": row['role'],
                            "content": row['content']
                        })

                logger.debug(f"Restored {len(message_rows)} messages for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to restore memory from DB: {e}")

    async def _persist_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        search_results: Optional[List[dict]] = None
    ) -> None:
        """
        Persist a message to PostgreSQL.

        Args:
            conversation_id: Conversation UUID
            role: Message role
            content: Message content
            search_results: Optional search results
        """
        if not self.db_pool:
            return

        try:
            from src.db.conversations import add_message
            await add_message(
                self.db_pool,
                conversation_id,
                MessageRole(role),
                content,
                search_results
            )
        except Exception as e:
            logger.error(f"Failed to persist message: {e}")

    async def cleanup_session(self, session_id: str) -> None:
        """
        Remove session from in-memory storage.

        Note: This does not delete DB records, only clears the in-memory cache.

        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug(f"Cleaned up memory for session {session_id}")

    def get_session_count(self) -> int:
        """Get the number of active sessions in memory."""
        return len(self.sessions)
