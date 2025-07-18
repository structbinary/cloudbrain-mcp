from typing import Any, Dict
import re
from agents_mcp_server.utils import MCPResource, setup_logger
from agents_mcp_server.models import AgentCardResponse, ErrorResponse

logger = setup_logger("agents_mcp_server.core.resources.agent_card")

class AgentCardResource(MCPResource):
    """
    MCP Resource for retrieving a specific agent card by ID.
    Follows the Anthropic Model Context Protocol (MCP) specification.
    Exposes the resource at /agent_cards/{agent_id}.
    Validates agent_id and exposes only safe fields.
    """

    def __init__(self, registry_manager):
        self.registry_manager = registry_manager

    async def get(self, agent_id: str, **kwargs) -> Dict[str, Any]:
        """
        Retrieve details for a specific agent card by its ID.
        Args:
            agent_id (str): Unique agent card identifier.
            **kwargs: Additional keyword arguments.
        Returns:
            Dict[str, Any]: Response with agent card details or error info.
        """
        logger.info(f"Retrieving agent card with ID: {agent_id}")
        # Validate agent_id format (alphanumeric, underscore, hyphen)
        if not re.match(r"^[a-zA-Z0-9_\-]+$", agent_id):
            logger.error(f"Invalid agent_id format: {agent_id}")
            error_response = ErrorResponse(message=f"Invalid agent_id format: {agent_id}")
            return error_response.model_dump(exclude_none=True)
        try:
            card = self.registry_manager.get_agent_card(agent_id)
            if not card:
                logger.error(f"Agent card not found: {agent_id}")
                error_response = ErrorResponse(message=f"Agent card {agent_id} not found")
                return error_response.model_dump(exclude_none=True)
            # Return the full AgentCard model in the ApiResponse
            response = AgentCardResponse(
                status="success",
                data=card,
                message=f"Agent card '{agent_id}' retrieved successfully"
            )
            return response.model_dump(exclude_none=True)
        except Exception as ex:
            logger.error(f"Error retrieving agent card {agent_id}: {ex}")
            error_response = ErrorResponse(message=f"Error retrieving agent card {agent_id}: {ex}")
            return error_response.model_dump(exclude_none=True) 