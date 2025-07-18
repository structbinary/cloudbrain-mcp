from typing import Any, Dict, List, Optional
from agents_mcp_server.utils import MCPResource, setup_logger
from agents_mcp_server.models import AgentCard, AgentCardListResponse, ErrorResponse, Meta

logger = setup_logger("agents_mcp_server.core.resources.agent_cards")

class AgentCardsResource(MCPResource):
    """
    MCP Resource for retrieving all loaded agent cards.
    Follows the Anthropic Model Context Protocol (MCP) specification.
    Exposes the resource at /agent_cards and resource://agent_cards.
    Supports pagination and provides resource metadata in the response.
    """

    def __init__(self, registry_manager):
        self.registry_manager = registry_manager

    async def get(self, limit: int = 20, offset: int = 0, **kwargs) -> Dict[str, Any]:
        """
        Retrieve a paginated list of all loaded agent cards.
        Args:
            limit (int): Max number of agent cards to return (default 20).
            offset (int): Number of agent cards to skip (default 0).
            **kwargs: Additional keyword arguments.
        Returns:
            Dict[str, Any]: Response with list of agent cards and metadata, or error info.
        """
        logger.info(f"Retrieving agent cards with limit={limit}, offset={offset}")
        try:
            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise ValueError("limit must be between 1 and 100")
            if offset < 0:
                raise ValueError("offset must be >= 0")

            all_cards = self.registry_manager.list_agent_cards()
            total = len(all_cards)
            # Pagination
            paginated = all_cards[offset:offset+limit]
            # Serialize agent cards
            agent_cards = [card if isinstance(card, AgentCard) else AgentCard.model_validate(card) for card in paginated]
            # Pagination metadata
            next_offset = offset + limit if offset + limit < total else None
            prev_offset = offset - limit if offset - limit >= 0 else None
            meta = Meta(
                page=(offset // limit) + 1,
                per_page=limit,
                total=total
            )
            # Build response using ApiResponse
            response = AgentCardListResponse(
                status="success",
                data=agent_cards,
                message="A list of all agent cards available to the model.",
                meta=meta
            )
            return response.model_dump(exclude_none=True)
        except Exception as ex:
            logger.error(f"Error retrieving agent cards: {ex}")
            error_response = ErrorResponse(
                message=str(ex),
                meta=Meta(page=1, per_page=limit, total=0)
            )
            return error_response.model_dump(exclude_none=True) 