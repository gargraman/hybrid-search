"""
BeeAI Tool definitions for the chat agent.

These tools wrap the existing search functionality and provide
structured interfaces for the ReActAgent to use.
"""
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    from beeai_framework.tools import Tool
    from beeai_framework.tools.types import StringToolOutput
    BEEAI_TOOLS_AVAILABLE = True
except ImportError:
    # Fallback if beeai_framework tools not available
    BEEAI_TOOLS_AVAILABLE = False
    logger.warning("BeeAI tools module not available, using fallback implementation")

from src.agents.orchestrator import Orchestrator


# Shared state for storing last search results per session
_last_search_results: Dict[str, List[dict]] = {}


def format_results_for_display(results: List[Any]) -> str:
    """
    Format search results for LLM consumption and display.

    Args:
        results: List of search result objects

    Returns:
        Formatted string representation of results
    """
    if not results:
        return "No results found."

    formatted_lines = [f"Found {len(results)} results:\n"]

    for i, result in enumerate(results, 1):
        # Handle both dict and object results
        if hasattr(result, 'dict'):
            data = result.dict()
        elif isinstance(result, dict):
            data = result
        else:
            data = {'id': str(i), 'metadata': {}}

        metadata = data.get('metadata', {})

        name = metadata.get('text', metadata.get('name', 'Unknown Item'))
        restaurant = metadata.get('restaurant', 'Unknown Restaurant')
        price = metadata.get('price')
        description = metadata.get('description', '')
        city = metadata.get('city', '')
        state = metadata.get('state', '')

        # Format price
        price_str = f"${price:.2f}" if price else "Price N/A"

        # Format location
        location_str = f" in {city}, {state}" if city else ""

        # Truncate description
        desc_str = description[:100] + "..." if len(description) > 100 else description

        formatted_lines.append(
            f"{i}. **{name}** - {restaurant}{location_str}\n"
            f"   Price: {price_str}\n"
            f"   {desc_str}\n"
        )

    return "\n".join(formatted_lines)


def format_single_result(result: dict) -> str:
    """
    Format a single result with full details.

    Args:
        result: Search result dictionary

    Returns:
        Detailed formatted string
    """
    metadata = result.get('metadata', {})

    name = metadata.get('text', metadata.get('name', 'Unknown Item'))
    restaurant = metadata.get('restaurant', 'Unknown Restaurant')
    price = metadata.get('price')
    description = metadata.get('description', 'No description available')
    address = metadata.get('address', '')
    city = metadata.get('city', '')
    state = metadata.get('state', '')
    cuisine = metadata.get('cuisine', '')
    rating = metadata.get('rating')
    category = metadata.get('category', '')

    lines = [f"**{name}**\n"]
    lines.append(f"Restaurant: {restaurant}")

    if cuisine:
        lines.append(f"Cuisine: {cuisine}")
    if category:
        lines.append(f"Category: {category}")
    if price:
        lines.append(f"Price: ${price:.2f}")
    if rating:
        lines.append(f"Rating: {rating}/5")

    lines.append(f"\nDescription: {description}")

    if address or city:
        location_parts = [p for p in [address, city, state] if p]
        lines.append(f"\nLocation: {', '.join(location_parts)}")

    return "\n".join(lines)


async def search_menu_items_impl(
    query: str,
    price_max: Optional[float] = None,
    dietary: Optional[str] = None,
    location: Optional[str] = None,
    session_id: Optional[str] = None
) -> str:
    """
    Implementation of menu item search.

    Args:
        query: Natural language search query
        price_max: Maximum price filter
        dietary: Dietary restriction filter
        location: Location filter
        session_id: Session ID for storing results

    Returns:
        Formatted search results string
    """
    try:
        # Build the full query with filters
        full_query = query
        if dietary:
            full_query = f"{dietary} {query}"
        if location:
            full_query = f"{query} in {location}"

        logger.info(f"Executing search: query='{full_query}', price_max={price_max}")

        orchestrator = Orchestrator()
        results = await orchestrator.run_search(full_query, top_k=10)

        # Apply price filter if specified
        if price_max and results:
            results = [
                r for r in results
                if r.metadata.get('price') is None or r.metadata.get('price') <= price_max
            ]

        # Store for follow-up questions
        if session_id:
            _last_search_results[session_id] = [
                r.dict() if hasattr(r, 'dict') else r
                for r in results
            ]

        logger.info(f"Search returned {len(results)} results")

        # Format for LLM consumption
        return format_results_for_display(results)

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"I encountered an error while searching: {str(e)}"


def get_result_details_impl(
    result_number: int,
    session_id: str
) -> str:
    """
    Get detailed information about a specific search result.

    Args:
        result_number: 1-based index of the result
        session_id: Session ID to retrieve stored results

    Returns:
        Detailed result information
    """
    results = _last_search_results.get(session_id, [])

    if not results:
        return "No previous search results found. Please search for something first."

    if result_number < 1 or result_number > len(results):
        return f"Invalid result number. Please choose between 1 and {len(results)}."

    item = results[result_number - 1]
    return format_single_result(item)


def get_last_search_results(session_id: str) -> Optional[List[dict]]:
    """
    Get the last search results for a session.

    Args:
        session_id: Session identifier

    Returns:
        List of result dictionaries or None
    """
    return _last_search_results.get(session_id)


def clear_session_results(session_id: str) -> None:
    """
    Clear stored results for a session.

    Args:
        session_id: Session identifier
    """
    _last_search_results.pop(session_id, None)


# Define BeeAI tools if framework is available
if BEEAI_TOOLS_AVAILABLE:
    @Tool.create(
        name="search_menu_items",
        description="""Search restaurant menu items by query with optional filters.
Use this tool when the user wants to find food items, restaurants, or menu options.
You can filter by price, dietary restrictions, and location."""
    )
    async def search_menu_items(
        query: str,
        price_max: float = None,
        dietary: str = None,
        location: str = None,
        session_id: str = None
    ) -> StringToolOutput:
        """
        Search restaurant menu items by query with optional filters.

        Args:
            query: Natural language search query (e.g., "vegan tacos", "pizza")
            price_max: Maximum price filter (e.g., 15.0)
            dietary: Dietary restriction (e.g., "vegan", "gluten-free", "vegetarian")
            location: Location filter (e.g., "San Francisco", "New York")
            session_id: Session ID for storing results for follow-up

        Returns:
            Formatted search results with restaurant names, items, and prices.
        """
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
        description="""Get detailed information about a specific search result from the last search.
Use this when the user asks about a specific item like "tell me about the first one" or "more info on number 3"."""
    )
    def get_result_details(
        result_number: int,
        session_id: str
    ) -> StringToolOutput:
        """
        Get detailed information about a specific search result.

        Args:
            result_number: The 1-based index of the result (e.g., 1 for first result)
            session_id: Session ID to retrieve stored results

        Returns:
            Detailed information about the selected item.
        """
        result = get_result_details_impl(result_number, session_id)
        return StringToolOutput(result)
else:
    # Fallback: expose the implementation functions directly
    search_menu_items = search_menu_items_impl
    get_result_details = get_result_details_impl
