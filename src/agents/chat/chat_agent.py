"""
ChatAgent - Conversational chat agent using BeeAI ReActAgent.

This agent handles user messages, determines intent, and generates
appropriate responses using the existing search pipeline.
"""
from typing import Tuple, List, Optional, Any
from uuid import UUID
from loguru import logger

from config.settings import settings
from src.agents.chat.memory_manager import ChatSessionManager
from src.agents.chat.tools import (
    search_menu_items_impl,
    get_result_details_impl,
    get_last_search_results,
    format_results_for_display
)

# Try to import BeeAI components
try:
    from beeai_framework.agents.react import ReActAgent
    from beeai_framework import LLM, AgentExecutionConfig
    from beeai_framework.tools import Tool
    from beeai_framework.tools.types import StringToolOutput
    BEEAI_REACT_AVAILABLE = True
except ImportError:
    BEEAI_REACT_AVAILABLE = False
    logger.warning("BeeAI ReActAgent not available, using fallback implementation")

# Try to import OpenAI for fallback
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


CHAT_SYSTEM_PROMPT = """You are a helpful restaurant search assistant for a culinary search engine.
Your role is to help users find menu items, answer questions about restaurants, and provide recommendations.

Guidelines:
- When users ask to search for food items, use the search_menu_items tool
- Include any filters they mention (price, dietary restrictions, location)
- When users ask about a specific result (e.g., "tell me about the first one"), use get_result_details
- For general questions or greetings, respond conversationally without using tools
- Be helpful, concise, and friendly
- If you're unsure what the user wants, ask clarifying questions

Remember: You have access to a restaurant menu database. Help users discover great food!"""


class ChatAgent:
    """
    Conversational chat agent using BeeAI ReActAgent.

    Features:
    - Uses ReActAgent for reasoning and tool selection (when available)
    - Falls back to direct LLM calls when BeeAI is not available
    - SummarizeMemory for smart context management
    - Tools for search and follow-up queries
    - Automatic retry and error handling
    """

    def __init__(self, session_manager: ChatSessionManager, session_id: str):
        """
        Initialize the ChatAgent.

        Args:
            session_manager: ChatSessionManager instance
            session_id: Session identifier
        """
        self.session_manager = session_manager
        self.session_id = session_id
        self.llm = self._create_llm()
        self._openai_client = self._create_openai_client() if not BEEAI_REACT_AVAILABLE else None

    def _create_llm(self) -> Optional[Any]:
        """Create BeeAI LLM instance."""
        if not BEEAI_REACT_AVAILABLE:
            return None

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
            logger.error(f"Failed to create BeeAI LLM: {e}")
        return None

    def _create_openai_client(self) -> Optional[Any]:
        """Create OpenAI client for fallback."""
        if not OPENAI_AVAILABLE:
            return None

        try:
            if settings.deepseek_api_key:
                return OpenAI(
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url
                )
            elif settings.openai_api_key:
                return OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url
                )
        except Exception as e:
            logger.error(f"Failed to create OpenAI client: {e}")
        return None

    async def process_message(
        self,
        user_message: str,
        conversation_id: Optional[UUID] = None
    ) -> Tuple[str, bool, Optional[List[dict]]]:
        """
        Process a user message and generate a response.

        Args:
            user_message: The user's input message
            conversation_id: Optional conversation ID for persistence

        Returns:
            Tuple of (response_text, search_performed, search_results)
        """
        logger.info(f"Processing message for session {self.session_id}: {user_message[:50]}...")

        try:
            # Add user message to memory
            await self.session_manager.add_user_message(
                self.session_id,
                user_message,
                str(conversation_id) if conversation_id else None
            )

            # Process based on available framework
            if BEEAI_REACT_AVAILABLE and self.llm:
                response_text, search_performed, search_results = await self._process_with_react(
                    user_message
                )
            else:
                response_text, search_performed, search_results = await self._process_with_fallback(
                    user_message
                )

            # Add assistant response to memory
            await self.session_manager.add_assistant_message(
                self.session_id,
                response_text,
                str(conversation_id) if conversation_id else None,
                search_results
            )

            return response_text, search_performed, search_results

        except Exception as e:
            logger.error(f"ChatAgent error: {e}")
            return await self._error_response(str(e))

    async def _process_with_react(
        self,
        user_message: str
    ) -> Tuple[str, bool, Optional[List[dict]]]:
        """
        Process message using BeeAI ReActAgent.

        Args:
            user_message: User's message

        Returns:
            Tuple of (response, search_performed, results)
        """
        try:
            # Get session memory
            memory = await self.session_manager.get_or_create_memory(self.session_id)

            # Create tools with session context
            tools = self._create_tools()

            # Create ReActAgent
            agent = ReActAgent(
                llm=self.llm,
                tools=tools,
                memory=memory,
                instructions=CHAT_SYSTEM_PROMPT
            )

            # Run agent
            result = await agent.run(
                user_message,
                execution=AgentExecutionConfig(
                    max_iterations=settings.chat_max_iterations,
                    total_max_retries=settings.chat_max_retries
                )
            )

            response_text = result.result.text if hasattr(result, 'result') else str(result)
            search_performed = self._check_search_performed(result)
            search_results = get_last_search_results(self.session_id) if search_performed else None

            return response_text, search_performed, search_results

        except Exception as e:
            logger.error(f"ReActAgent failed: {e}")
            # Fall back to simple processing
            return await self._process_with_fallback(user_message)

    def _create_tools(self) -> List[Any]:
        """Create BeeAI tools with session context."""
        session_id = self.session_id

        @Tool.create(
            name="search_menu_items",
            description="Search restaurant menu items. Use when user wants to find food."
        )
        async def search_tool(
            query: str,
            price_max: float = None,
            dietary: str = None,
            location: str = None
        ) -> StringToolOutput:
            result = await search_menu_items_impl(
                query=query,
                price_max=price_max,
                dietary=dietary,
                location=location,
                session_id=session_id
            )
            return StringToolOutput(result)

        @Tool.create(
            name="get_result_details",
            description="Get details about a specific result. Use when user asks about 'the first one', etc."
        )
        def details_tool(result_number: int) -> StringToolOutput:
            result = get_result_details_impl(result_number, session_id)
            return StringToolOutput(result)

        return [search_tool, details_tool]

    def _check_search_performed(self, result: Any) -> bool:
        """Check if search tool was called during agent execution."""
        try:
            if hasattr(result, 'steps'):
                for step in result.steps:
                    if hasattr(step, 'tool_name') and 'search' in step.tool_name.lower():
                        return True
            # Also check if we have stored results for this session
            return get_last_search_results(self.session_id) is not None
        except Exception:
            return False

    async def _process_with_fallback(
        self,
        user_message: str
    ) -> Tuple[str, bool, Optional[List[dict]]]:
        """
        Process message using fallback (direct LLM + intent detection).

        Args:
            user_message: User's message

        Returns:
            Tuple of (response, search_performed, results)
        """
        if not self._openai_client and not OPENAI_AVAILABLE:
            return await self._simple_search_response(user_message)

        try:
            # Get conversation context
            context = await self.session_manager.get_context(self.session_id)

            # Detect intent
            intent = await self._detect_intent(user_message, context)

            if intent == "search":
                # Perform search
                search_results_text = await search_menu_items_impl(
                    query=user_message,
                    session_id=self.session_id
                )
                search_results = get_last_search_results(self.session_id)

                # Generate response with results
                response = await self._generate_response_with_results(
                    user_message,
                    search_results_text,
                    context
                )
                return response, True, search_results

            elif intent == "followup":
                # Check for result number in message
                result_num = self._extract_result_number(user_message)
                if result_num:
                    details = get_result_details_impl(result_num, self.session_id)
                    return details, False, None
                else:
                    # General follow-up about previous results
                    search_results = get_last_search_results(self.session_id)
                    response = await self._generate_followup_response(
                        user_message,
                        search_results,
                        context
                    )
                    return response, False, search_results

            else:
                # General conversation
                response = await self._generate_general_response(user_message, context)
                return response, False, None

        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return await self._simple_search_response(user_message)

    async def _detect_intent(self, message: str, context: str) -> str:
        """Detect user intent from message."""
        # Simple keyword-based intent detection
        message_lower = message.lower()

        # Search indicators
        search_keywords = ['find', 'search', 'looking for', 'want', 'need', 'show me',
                          'where can i', 'recommendations', 'suggest']
        if any(kw in message_lower for kw in search_keywords):
            return "search"

        # Follow-up indicators
        followup_keywords = ['first', 'second', 'third', 'that one', 'more about',
                            'tell me about', 'details', 'number']
        if any(kw in message_lower for kw in followup_keywords):
            return "followup"

        # Check if we have recent search results
        if get_last_search_results(self.session_id):
            # Questions about results are follow-ups
            question_words = ['what', 'which', 'how', 'is', 'does', 'can']
            if any(message_lower.startswith(w) for w in question_words):
                return "followup"

        return "general"

    def _extract_result_number(self, message: str) -> Optional[int]:
        """Extract result number from message like 'first one' or 'number 3'."""
        message_lower = message.lower()

        ordinals = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
                   '1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5}

        for word, num in ordinals.items():
            if word in message_lower:
                return num

        # Check for "number X" pattern
        import re
        match = re.search(r'number\s*(\d+)', message_lower)
        if match:
            return int(match.group(1))

        # Check for standalone digits
        match = re.search(r'\b(\d+)\b', message)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 10:  # Reasonable result number
                return num

        return None

    async def _generate_response_with_results(
        self,
        query: str,
        results_text: str,
        context: str
    ) -> str:
        """Generate a conversational response that includes search results."""
        if not self._openai_client:
            return results_text

        try:
            prompt = f"""Based on the user's query and search results, provide a helpful response.

Previous conversation:
{context}

User query: {query}

Search results:
{results_text}

Generate a brief, friendly response that summarizes the results and offers to provide more details."""

            response = self._openai_client.chat.completions.create(
                model="deepseek-chat" if settings.deepseek_api_key else "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return results_text

    async def _generate_followup_response(
        self,
        message: str,
        results: Optional[List[dict]],
        context: str
    ) -> str:
        """Generate response for follow-up questions."""
        if not self._openai_client or not results:
            return "I don't have any previous search results to reference. Would you like to search for something?"

        try:
            results_summary = format_results_for_display(results)

            prompt = f"""The user is asking a follow-up question about previous search results.

Previous conversation:
{context}

Previous search results:
{results_summary}

User question: {message}

Provide a helpful response addressing their question about the results."""

            response = self._openai_client.chat.completions.create(
                model="deepseek-chat" if settings.deepseek_api_key else "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate followup response: {e}")
            return "I can help you with more details about any of the results. Just let me know which one interests you!"

    async def _generate_general_response(self, message: str, context: str) -> str:
        """Generate response for general conversation."""
        if not self._openai_client:
            return "Hello! I'm your restaurant search assistant. How can I help you find something delicious today?"

        try:
            prompt = f"""Previous conversation:
{context}

User message: {message}

Respond naturally and offer to help with restaurant/food searches if appropriate."""

            response = self._openai_client.chat.completions.create(
                model="deepseek-chat" if settings.deepseek_api_key else "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate general response: {e}")
            return "Hello! How can I help you find something to eat today?"

    async def _simple_search_response(
        self,
        user_message: str
    ) -> Tuple[str, bool, Optional[List[dict]]]:
        """
        Simple fallback: just search and return results.

        Args:
            user_message: User's message as search query

        Returns:
            Tuple of (response, search_performed, results)
        """
        try:
            results_text = await search_menu_items_impl(
                query=user_message,
                session_id=self.session_id
            )
            search_results = get_last_search_results(self.session_id)
            return results_text, True, search_results
        except Exception as e:
            logger.error(f"Simple search failed: {e}")
            return f"I encountered an error while searching. Please try again.", False, None

    async def _error_response(
        self,
        error_message: str
    ) -> Tuple[str, bool, None]:
        """Generate error response."""
        return (
            "I'm sorry, I encountered an issue processing your request. "
            "Please try again or rephrase your query.",
            False,
            None
        )
