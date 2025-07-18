from typing import Dict, Any, Optional
from agents_mcp_server.utils import MCPTool, setup_logger, ResourceNotFoundError

logger = setup_logger("agents_mcp_server.core.tools.get_mcp_server_details")

class GetMCPServerDetailsTool(MCPTool):
    """Tool for retrieving detailed configuration for a specific MCP server."""

    def __init__(self, registry_manager):
        self.registry_manager = registry_manager
        logger.info("Initialized GetMCPServerDetailsTool.")

    @property
    def name(self) -> str:
        """Name of the tool."""
        return "get_mcp_server_details"

    @property
    def description(self) -> str:
        """Description of the tool."""
        return "Retrieves detailed configuration for specific MCP server"

    async def execute(
        self,
        server_id: Optional[str] = None,
        server_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve detailed configuration for a specific MCP server by ID or name.
        Args:
            server_id (Optional[str]): Unique server ID (preferred).
            server_name (Optional[str]): Server name (used if ID not provided or not found).
        Returns:
            Dict[str, Any]: Serialized server configuration and metadata.
        """
        if not server_id and not server_name:
            logger.error("Missing required parameters: either server_id or server_name must be provided")
            raise ValueError("Either server_id or server_name must be provided")
        if server_id:
            logger.info(f"Looking up MCP server by ID: {server_id}")
            try:
                server = self.registry_manager.get_mcp_server_by_id(server_id)
                if server is None:
                    logger.error(f"No MCP server found with ID: {server_id}")
                    raise ResourceNotFoundError(f"No MCP server found with ID: {server_id}")
                logger.info(f"Successfully retrieved server with ID: {server_id}")
                # Return a direct serialization of the validated MCPServer Pydantic model
                return server.model_dump(exclude_none=True)
            except ResourceNotFoundError:
                logger.error(f"No MCP server found with ID: {server_id}")
                # Do not raise here; allow fallback to name lookup if provided
            except Exception as e:
                logger.exception(f"Unexpected error retrieving server with ID {server_id}: {str(e)}")
                raise
        if server_name:
            logger.info(f"Looking up MCP server by name: {server_name}")
            server = self.registry_manager.get_mcp_server_by_name(server_name)
            if server is None:
                logger.error(f"No MCP server found with name: {server_name}")
                raise ResourceNotFoundError(f"No MCP server found with name: {server_name}")
            logger.info(f"Successfully retrieved server with name: {server_name}")
            return server.model_dump(exclude_none=True)
        logger.error("MCP server not found by ID or name.")
        raise ResourceNotFoundError("MCP server not found by ID or name.") 