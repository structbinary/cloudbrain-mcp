from typing import Optional, Dict, Any, List
import os
import signal
import sys

# imports for all tools
from agents_mcp_server.core.tools import (
    FindMCPServersTool, 
    GetMCPServerDetailsTool, 
    ListMCPServersTool, 
    GetAgentDetailsTool, 
    FindA2AAgentsTool
)
from agents_mcp_server.core.tools.find_a2a_agents import FindA2AAgentsInputSchema

# imports for all resources
from agents_mcp_server.core.resources import (
    MCPServersResource, 
    MCPServerResource,
    AgentCardsResource,
    AgentCardResource
)
from agents_mcp_server.models import AgentCard
from agents_mcp_server.utils import setup_logger
from agents_mcp_server.core.registry_manager import RegistryManager

from mcp.server.fastmcp import FastMCP

logger = setup_logger("agents_mcp_server.main")

## Singleton pattern for RegistryManager
class RegistryManagerSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RegistryManager()
            # Load data once at startup
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            agent_cards_path = os.path.join(os.path.dirname(__file__), 'static', 'agent_cards')
            mcp_servers_path = os.path.join(os.path.dirname(__file__), 'static', 'mcp_servers')
            cls._instance.load_agent_cards_from_directory(agent_cards_path)
            cls._instance.load_mcp_servers_from_directory(mcp_servers_path)
        return cls._instance

def create_server(host, port):
    """Creates and returns a FastMCP server instance for Agents MCP operations."""
    return FastMCP(
        'agents-mcp-server',
        instructions=f'This server is central discover server which is used to discover a2a agents and various mcp servers.',
        host=host,
        port=port
    )

def main(host, port, transport):
    logger.info(f"main() starting with host={host}, port={port}, transport={transport}")
    server = create_server(host, port)
    logger.info("FastMCP server instance created.")
    registry_manager = RegistryManagerSingleton.get_instance()
# def register_tools(server: FastMCP, registry_manager: RegistryManager):
    @server.tool(name="find_a2a_agents", description="Find A2A agents by query")
    async def find_a2a_agents(input: FindA2AAgentsInputSchema) -> List[AgentCard]:
        """
        Asynchronously execute the agent card search based on the provided query and filters.

        This tool finds relevant agent cards by scoring and ranking them according to a natural language query, with support for advanced filtering and pagination. Designed for extensibility and integration in async workflows.

        ## Arguments
        - query (str): The natural language query to search for relevant agent cards.
        - filter_func (Optional[Callable[[AgentCard], bool]]): Optional callable for advanced filtering (applied after field filters).
        - limit (Optional[int]): Maximum number of results to return (after filtering and sorting).
        - offset (int): Number of results to skip (for pagination).
        - **filters: Additional keyword filters (equality on AgentCard fields, e.g., status="active").

        ## Usage Tips
        - Use `query` to describe the agent capabilities or features you are looking for.
        - Use keyword arguments (e.g., `status="active"`) to filter by AgentCard fields.
        - Provide a `filter_func` for custom, advanced filtering logic.
        - Use `limit` and `offset` for pagination of large result sets.

        ## Response Information
        - Returns a list of AgentCard objects matching the query and filters, sorted by relevance.
        - If no agent cards match, returns an empty list.
        - Logs all major steps and errors for traceability.

        Example:
            results = await tool.execute(
                query="NLP streaming agents",
                status="active",
                limit=10
            )
        """
        filters = {k: v for k, v in input.model_dump().items() if k not in {"query", "limit", "offset"}}
        return await FindA2AAgentsTool(registry_manager).execute(
            input.query,
            None,
            input.limit,
            input.offset,
            **filters
        )

    @server.tool(name="find_mcp_servers", description="Find MCP servers by agent type and required capabilities")
    async def find_mcp_servers(
        agent_type: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
        **filters
    ) -> List[dict]:

        """
        Asynchronously find and rank compatible MCP servers based on agent type and required capabilities.

        This tool finds compatible MCP servers by scoring and ranking them according to the specified agent type and required capabilities, with support for advanced filtering and pagination. Designed for extensibility and integration in async workflows.

        ## Arguments
        - agent_type (Optional[str]): The type of agent to match (case-insensitive).
        - required_capabilities (Optional[List[str]]): List of required capabilities (case-insensitive).
        - page (int): Page number for pagination (1-based).
        - page_size (int): Number of results per page.
        - **filters: Additional filter parameters for future extensibility.

        ## Usage Tips
        - Use `agent_type` to filter servers that support a specific agent type.
        - Use `required_capabilities` to require servers with specific capabilities.
        - Use `page` and `page_size` for paginated results.
        - Provide additional keyword arguments for future extensibility.

        ## Response Information
        - Returns a list of ranked server summaries (dicts) with compatibility scores, paginated.
        - Each result contains:
            - 'server': Serialized MCPServer Pydantic model (dict)
            - 'compatibility_score': Score between 0.0 and 1.0
        - If no compatible servers are found, returns an empty list.
        - Logs all major steps and errors for traceability.

        Example:
            results = await tool.execute(
                agent_type="nlp-agent",
                required_capabilities=["streaming", "secure"],
                page=1,
                page_size=10
            )
        """
        return await FindMCPServersTool(registry_manager).execute(agent_type, required_capabilities, page, page_size, **filters)

    @server.tool("get_mcp_server_details")
    async def get_mcp_server_details(
        server_id: Optional[str] = None,
        server_name: Optional[str] = None
    ) -> Dict[str, Any]:

        """
        Asynchronously retrieve detailed configuration for a specific MCP server.

        This tool fetches and returns the configuration, endpoints, and metadata for a given MCP server, identified by either its unique ID or name. Designed for extensibility and integration in async workflows.

        ## Arguments
        - server_id (Optional[str]): ID of the MCP server (preferred for lookup).
        - server_name (Optional[str]): Name of the MCP server (used as a fallback if ID is not provided or not found).

        ## Usage Tips
        - Provide `server_id` for the most reliable and efficient lookup.
        - If `server_id` is not known, use `server_name` (case-insensitive match).
        - If both are provided, lookup by ID is attempted first, then by name if not found.

        ## Response Information
        - Returns a dictionary containing the server's configuration, endpoints, and metadata, serialized from the MCPServer Pydantic model.
        - If no server is found, raises ResourceNotFoundError.
        - Logs all major steps and errors for traceability.

        Example:
            result = await tool.execute(server_id="server-1234")
            result = await tool.execute(server_name="Main MCP Server")
        """
        return await GetMCPServerDetailsTool(registry_manager).execute(server_id, server_name)

    @server.tool("list_mcp_servers")
    async def list_mcp_servers(
        category: Optional[str] = None,
        status: Optional[str] = None,
        capabilities: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Asynchronously list all MCP servers with optional filtering.

        This tool returns a list of all currently available MCP servers, with support for filtering by category, status, and required capabilities. Designed for extensibility and integration in async workflows.

        ## Arguments
        - category (Optional[str]): Filter by server category (matches server name or any capability, case-insensitive).
        - status (Optional[str]): Filter by server status (e.g., 'active', 'inactive').
        - capabilities (Optional[List[str]]): Filter by required capabilities (server must have all, case-insensitive).

        ## Usage Tips
        - Use `category` to quickly find servers by name or capability group.
        - Use `status` to filter for only active or inactive servers.
        - Use `capabilities` to require servers with specific features.
        - Combine filters for more precise results.

        ## Response Information
        - Returns a list of MCP server summaries (dicts) passing all filters, serialized from the MCPServer Pydantic model.
        - If no servers match, returns an empty list.
        - Logs all major steps and errors for traceability.
        Example:
            results = await tool.execute(category="nlp", status="active", capabilities=["streaming"])
        """
        return await ListMCPServersTool(registry_manager).execute(category, status, capabilities)

    @server.tool("get_agent_details")
    async def get_agent_details(
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously retrieve detailed information for a specific agent.

        This tool fetches and returns the information for a given agent, identified by either its unique ID or name. Designed for extensibility and integration in async workflows.

        ## Arguments
        - agent_id (Optional[str]): ID of the agent (preferred for lookup).
        - agent_name (Optional[str]): Name of the agent (used as a fallback if ID is not provided or not found).

        ## Usage Tips
        - Provide `agent_id` for the most reliable and efficient lookup.
        - If `agent_id` is not known, use `agent_name` (case-insensitive match).
        - If both are provided, lookup by ID is attempted first, then by name if not found.

        ## Response Information
        - Returns a dictionary containing the agent's information, serialized from the AgentCard Pydantic model.
        - If no agent is found, raises ResourceNotFoundError.
        - Logs all major steps and errors for traceability.

        Example:
            result = await tool.execute(agent_id="agent-1234")
            result = await tool.execute(agent_name="NLP Agent")
        """
        return await GetAgentDetailsTool(registry_manager).execute(agent_id, agent_name)

# def register_resources(server: FastMCP, registry_manager: RegistryManager):
    @server.resource("resource://agent_cards/{agent_id}", mime_type="application/json")
    async def agent_card(agent_id: str) -> Dict[str, Any]:
        """
        Retrieve details for a specific agent card by its ID.
        Args:
            agent_id (str): Unique agent card identifier.
            **kwargs: Additional keyword arguments.
        Returns:
            Dict[str, Any]: Response with agent card details or error info.
        """
        return await AgentCardResource(registry_manager).get(agent_id)

    @server.resource("resource://mcp_servers/{server_id}", mime_type="application/json")
    async def mcp_server(server_id: str) -> Dict[str, Any]:
        """
        Retrieve details for a specific MCP server by its ID.
        Args:
            server_id (str): Unique server identifier.
            **kwargs: Additional keyword arguments.
        Returns:
            Dict[str, Any]: Response with MCP server details or error info.
        """
        return await MCPServerResource(registry_manager).get(server_id)

    @server.resource("resource://agent_cards", mime_type="application/json")
    async def agent_cards() -> Dict[str, Any]:
        """
        Retrieve a paginated list of all loaded agent cards.
        Args:
            limit (int): Max number of agent cards to return (default 20).
            offset (int): Number of agent cards to skip (default 0).
            **kwargs: Additional keyword arguments.
        Returns:
            Dict[str, Any]: Response with list of agent cards and metadata, or error info.
        """
        return await AgentCardsResource(registry_manager).get()

    @server.resource("resource://mcp_servers", mime_type="application/json")
    async def mcp_servers() -> Dict[str, Any]:
        """
        Retrieve a paginated list of all registered MCP servers.
        Args:
            limit (int): Max number of servers to return (default 20).
            offset (int): Number of servers to skip (default 0).
            **kwargs: Additional keyword arguments.
        Returns:
            Dict[str, Any]: Response with list of MCP servers and metadata, or error info.
        """
        return await MCPServersResource(registry_manager).get()

    # 6. Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda signum, frame: handle_shutdown(registry_manager, signum, frame))
    signal.signal(signal.SIGTERM, lambda signum, frame: handle_shutdown(registry_manager, signum, frame))

    server.run(transport=transport)
    logger.info("FastMCP server run() has returned (should not happen unless server exits)")


def handle_shutdown(registry_manager, signum, frame):
    logger.info(f'Received signal {signum}, initiating shutdown...')
    shutdown(registry_manager)

def shutdown(registry_manager):
    """
    Gracefully shut down the Cloudbrain MCP Server, cleaning up resources.
    """
    try:
        logger.info('Shutting down Agents MCP Server...')
        # Clean up registry manager and other resources
        if registry_manager and hasattr(registry_manager, 'close'):
            registry_manager.close()
        logger.info('Shutdown complete.')
    except Exception as e:
        logger.error(f'Error during shutdown: {e}', exc_info=True)
    finally:
        sys.exit(0)

