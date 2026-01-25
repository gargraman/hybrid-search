"""
Conversation models for the chatbot feature.

These models handle chat sessions, messages, and API request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


class MessageRole(str, Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """A single message in a conversation."""
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    role: MessageRole
    content: str
    search_results: Optional[List[Dict[str, Any]]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Conversation(BaseModel):
    """A conversation session containing multiple messages."""
    id: UUID = Field(default_factory=uuid4)
    session_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Request schema for sending a chat message."""
    message: str
    include_search_results: bool = True


class ChatResponse(BaseModel):
    """Response schema for a chat message."""
    conversation_id: UUID
    message: Message
    search_performed: bool = False
    search_results: Optional[List[Dict[str, Any]]] = None


class SessionCreateRequest(BaseModel):
    """Request schema for creating a new chat session."""
    title: Optional[str] = None


class SessionCreateResponse(BaseModel):
    """Response schema for session creation."""
    session_id: str
    conversation_id: UUID
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history."""
    conversation: Conversation
    message_count: int
