import re
from typing import Any, Dict
from agents_mcp_server.utils import MCPResource, setup_logger
from agents_mcp_server.models import MCPServer, MCPServerListResponse, ErrorResponse, Meta, MCPServerResponse

logger = setup_logger("agents_mcp_server.core.resources.mcp_servers")

class MCPServersResource(MCPResource):
    """
    MCP Resource for retrieving all registered MCP servers.
    Follows the Anthropic Model Context Protocol (MCP) specification.
    Exposes the resource at /mcp_servers and resource://mcp_servers.
    Supports pagination and provides resource metadata in the response.
    """
    RESOURCE_URI = "resource://mcp_servers"

    def __init__(self, registry_manager):
        self.registry_manager = registry_manager

    async def get(self, limit: int = 20, offset: int = 0, **kwargs) -> Dict[str, Any]:
        """
        Retrieve a paginated list of all registered MCP servers.
        Args:
            limit (int): Max number of servers to return (default 20).
            offset (int): Number of servers to skip (default 0).
            **kwargs: Additional keyword arguments.
        Returns:
            Dict[str, Any]: Response with list of MCP servers and metadata, or error info.
        """
        logger.info(f"Retrieving MCP servers with limit={limit}, offset={offset}")
        try:
            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise ValueError("limit must be between 1 and 100")
            if offset < 0:
                raise ValueError("offset must be >= 0")

            all_servers = self.registry_manager.list_mcp_servers()
            total = len(all_servers)
            # Pagination
            paginated = all_servers[offset:offset+limit]
            # Serialize MCP servers
            mcp_servers = [server if isinstance(server, MCPServer) else MCPServer.model_validate(server) for server in paginated]
            # Pagination metadata
            meta = Meta(
                page=(offset // limit) + 1,
                per_page=limit,
                total=total
            )
            # Build response using ApiResponse
            response = MCPServerListResponse(
                status="success",
                data=mcp_servers,
                message="A list of all MCP servers available to the model.",
                meta=meta
            )
            return response.model_dump(exclude_none=True)
        except Exception as ex:
            logger.error(f"Error retrieving MCP servers: {ex}")
            error_response = ErrorResponse(
                message=str(ex),
                meta=Meta(page=1, per_page=limit, total=0)
            )
            return error_response.model_dump(exclude_none=True)

class MCPServerResource(MCPResource):
    """
    MCP Resource for retrieving a specific MCP server by ID.
    Follows the Anthropic Model Context Protocol (MCP) specification.
    Exposes the resource at /mcp_servers/{server_id}.
    Validates server_id and exposes only safe fields.
    """

    def __init__(self, registry_manager):
        self.registry_manager = registry_manager

    async def get(self, server_id: str, **kwargs) -> Dict[str, Any]:
        """
        Retrieve details for a specific MCP server by its ID.
        Args:
            server_id (str): Unique server identifier.
            **kwargs: Additional keyword arguments.
        Returns:
            Dict[str, Any]: Response with MCP server details or error info.
        """
        logger.info(f"Retrieving MCP server with ID: {server_id}")
        # Validate server_id format (alphanumeric, underscore, hyphen)
        if not re.match(r"^[a-zA-Z0-9_\-]+$", server_id):
            logger.error(f"Invalid server_id format: {server_id}")
            error_response = ErrorResponse(message=f"Invalid server_id format: {server_id}")
            return error_response.model_dump(exclude_none=True)
        try:
            server = self.registry_manager.get_mcp_server(server_id)
            if server is None:
                logger.error(f"MCP server not found: {server_id}")
                error_response = ErrorResponse(message=f"MCP server {server_id} not found")
                return error_response.model_dump(exclude_none=True)
            # Return the full MCPServer model in the ApiResponse
            response = MCPServerResponse(
                status="success",
                data=server,
                message=f"MCP server '{server_id}' retrieved successfully"
            )
            return response.model_dump(exclude_none=True)
        except Exception as ex:
            logger.error(f"Unexpected error retrieving MCP server {server_id}: {ex}")
            error_response = ErrorResponse(message=f"Error retrieving MCP server {server_id}: {ex}")
            return error_response.model_dump(exclude_none=True) 