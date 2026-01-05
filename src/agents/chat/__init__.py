"""
Chat agents package.

This package contains the BeeAI-based chatbot agents for conversational search.
"""
try:
    from src.agents.chat.chat_agent import ChatAgent
    from src.agents.chat.memory_manager import ChatSessionManager
    from src.agents.chat.tools import search_menu_items, get_result_details

    __all__ = [
        'ChatAgent',
        'ChatSessionManager',
        'search_menu_items',
        'get_result_details',
    ]
except ImportError as e:
    # Allow package to be imported even if dependencies are missing
    import logging
    logging.warning(f"Chat package import error: {e}")
    __all__ = []
