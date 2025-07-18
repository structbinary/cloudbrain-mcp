from typing import List, Dict, Any, Optional
from agents_mcp_server.utils import MCPTool, setup_logger

logger = setup_logger("agents_mcp_server.core.tools.list_mcp_servers")

class ListMCPServersTool(MCPTool):
    """Tool for listing all currently available MCP servers."""

    def __init__(self, registry_manager):
        self.registry_manager = registry_manager
        logger.info("Initialized ListMCPServersTool.")

    @property
    def name(self) -> str:
        """Name of the tool."""
        return "list_mcp_servers"

    @property
    def description(self) -> str:
        """Description of the tool."""
        return "Lists all currently available MCP servers"

    def _matches_category(self, server, category: str) -> bool:
        """
        Check if server matches the specified category.
        Category can match server name or any capability (case-insensitive).
        """
        name = getattr(server, 'name', '').lower()
        caps = [c.lower() for c in getattr(server, 'capabilities', [])]
        match = category.lower() in name or category.lower() in caps
        logger.debug(f"Category filter: server='{name}', category='{category}', match={match}")
        return match

    def _matches_status(self, server, status: str) -> bool:
        """
        Check if server matches the specified status.
        Defaults to 'active' if status attribute is missing.
        """
        server_status = getattr(server, 'status', 'active').lower()
        match = status.lower() == server_status
        logger.debug(f"Status filter: server_status='{server_status}', status='{status}', match={match}")
        return match

    def _matches_capabilities(self, server, capabilities: List[str]) -> bool:
        """
        Check if server has all the specified capabilities (case-insensitive).
        """
        server_caps = [c.lower() for c in getattr(server, 'capabilities', [])]
        match = all(cap.lower() in server_caps for cap in capabilities)
        logger.debug(f"Capabilities filter: server_caps={server_caps}, required={capabilities}, match={match}")
        return match

    async def execute(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        capabilities: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List all available MCP servers, with optional filtering by category, status, and capabilities.
        Args:
            category (Optional[str]): Filter by server category (name or capability).
            status (Optional[str]): Filter by server status (e.g., 'active').
            capabilities (Optional[List[str]]): Filter by required capabilities.
        Returns:
            List[Dict[str, Any]]: List of matching MCP server summaries.
        """
        logger.info(f"Listing MCP servers with filters: category={category}, status={status}, capabilities={capabilities}")
        all_servers = self.registry_manager.list_mcp_servers()
        filtered_servers = []
        for server in all_servers:
            if category and not self._matches_category(server, category):
                logger.debug(f"Server '{getattr(server, 'name', None)}' excluded by category filter.")
                continue
            if status and not self._matches_status(server, status):
                logger.debug(f"Server '{getattr(server, 'name', None)}' excluded by status filter.")
                continue
            if capabilities and not self._matches_capabilities(server, capabilities):
                logger.debug(f"Server '{getattr(server, 'name', None)}' excluded by capabilities filter.")
                continue
            filtered_servers.append(server.model_dump(exclude_none=True))
        logger.info(f"Found {len(filtered_servers)} MCP servers after filtering")
        return filtered_servers 