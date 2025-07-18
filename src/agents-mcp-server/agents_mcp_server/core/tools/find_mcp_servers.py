from typing import List, Optional, Type, Any
from pydantic import BaseModel
from agents_mcp_server.utils import MCPTool, setup_logger
from agents_mcp_server.utils import ResourceNotFoundError

logger = setup_logger("agents_mcp_server.core.tools.find_mcp_servers")

class FindMCPServersInputSchema(BaseModel):
    agent_type: Optional[str] = None
    required_capabilities: Optional[List[str]] = None
    class Config:
        extra = "forbid"

class FindMCPServersTool(MCPTool):
    """Tool for finding compatible MCP servers."""

    def __init__(self, registry_manager):
        """Initialize the FindMCPServersTool.
        Args:
            registry_manager: Manager for accessing the MCP server registry
        Raises:
            ValueError: If registry_manager is None
        """
        if registry_manager is None:
            logger.error("Registry manager cannot be None")
            raise ValueError("Registry manager cannot be None")
        self.registry_manager = registry_manager
        self._scoring_config = {}  # For future extensibility
        logger.info("Initialized FindMCPServersTool.")

    @property
    def name(self) -> str:
        """Name of the tool.
        Returns:
            str: The name of the tool
        """
        return "find_mcp_servers"

    @property
    def description(self) -> str:
        """Description of the tool.
        Returns:
            str: A description of what the tool does
        """
        return "Finds compatible MCP servers based on agent type and required capabilities"

    @property
    def args_schema(self) -> Type[BaseModel]:
        """
        Returns the schema for validating input arguments.
        Returns:
            Type[BaseModel]: A Pydantic model class that defines the expected input structure.
        """
        return FindMCPServersInputSchema

    @property
    def is_single_input(self) -> bool:
        """
        Indicates whether the tool expects a single input value.
        Returns:
            bool: False, as this tool accepts a structured input object.
        """
        return False

    async def execute(
        self,
        agent_type: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
        **filters
    ) -> List[dict]:
        """
        Find and rank compatible MCP servers based on agent type and required capabilities.
        Args:
            agent_type (Optional[str]): Agent type to match.
            required_capabilities (Optional[List[str]]): List of required capabilities.
            page (int): Page number for pagination.
            page_size (int): Number of results per page.
            **filters: Additional filter parameters.
        Returns:
            List[dict]: Ranked list of compatible MCP servers with scores.
        """
        logger.info(f"Executing find_mcp_servers: agent_type={agent_type}, required_capabilities={required_capabilities}, page={page}, page_size={page_size}, filters={filters}")
        try:
            # Retrieve all MCP servers
            all_servers = self.registry_manager.list_mcp_servers()
            if not all_servers:
                logger.warning("No MCP servers found in registry.")
                raise ResourceNotFoundError("No MCP servers found in registry.")

            results = []
            for server in all_servers:
                # Check agent type compatibility
                if agent_type and not self._supports_agent_type(server, agent_type):
                    continue
                # Calculate compatibility score
                score = self._calculate_compatibility_score(
                    server, agent_type, required_capabilities, filters)
                if score > 0:
                    # Return a direct serialization of the validated MCPServer Pydantic model
                    results.append({
                        "server": server.model_dump(exclude_none=True),
                        "compatibility_score": score
                    })
            if not results:
                logger.info("No compatible MCP servers found for the given criteria.")
                return []
            # Sort by compatibility score (descending)
            results.sort(key=lambda x: x["compatibility_score"], reverse=True)
            # Pagination
            start = (page - 1) * page_size
            end = start + page_size
            paginated = results[start:end]
            logger.info(f"Returning {len(paginated)} MCP servers (from {len(results)} compatible)")
            return paginated
        except Exception as ex:
            logger.exception(f"Error in find_mcp_servers execute: {ex}")
            raise

    def _supports_agent_type(self, server, agent_type: str) -> bool:
        """
        Determine if the given MCP server supports the specified agent type.

        Compatibility is defined as a case-insensitive match between the provided agent_type
        and any entry in the server's compatibility.agent_types list.

        Edge cases handled:
        - If the server or its compatibility/agent_types field is missing or malformed, returns False.
        - If agent_types is empty or not a list, logs a warning and returns False.
        - If the agent_type is not found, logs at debug level.
        - Unknown/legacy agent types are treated as incompatible, but a warning is logged for traceability.

        Args:
            server: The MCPServer instance to check.
            agent_type: The agent type string to check for compatibility.
        Returns:
            bool: True if compatible, False otherwise.
        """
        try:
            agent_types = getattr(getattr(server, 'compatibility', None), 'agent_types', None)
            logger.debug(f"[DEBUG] Checking server {getattr(server, 'id', None)}: agent_types={agent_types}, query agent_type={agent_type}")
            if not agent_types or not isinstance(agent_types, list):
                logger.warning(f"Server {getattr(server, 'id', None)} has missing or malformed agent_types: {agent_types}")
                return False
            # Case-insensitive match
            for t in agent_types:
                if not isinstance(t, str):
                    logger.warning(f"Non-string agent_type in server {getattr(server, 'id', None)}: {t}")
                    continue
                if agent_type.lower() == t.lower():
                    logger.debug(f"Server {getattr(server, 'id', None)} supports agent_type '{agent_type}' (matched '{t}')")
                    return True
            logger.debug(f"Server {getattr(server, 'id', None)} does not support agent_type '{agent_type}'. Known types: {agent_types}")
            # Optionally, log a warning for unknown/legacy types
            if agent_type.lower() not in [t.lower() for t in agent_types]:
                logger.warning(f"Unknown or unsupported agent_type '{agent_type}' for server {getattr(server, 'id', None)}")
            return False
        except Exception as ex:
            logger.error(f"Error checking agent type compatibility for server {getattr(server, 'id', None)}: {ex}")
            return False

    def _calculate_compatibility_score(self, server, agent_type: Optional[str], required_capabilities: Optional[List[str]] = None, filters: Optional[dict] = None) -> float:
        """
        Calculate a compatibility score between 0.0 and 1.0 for a given server and requirements.

        Scoring factors (default weights, configurable via self._scoring_config):
        - agent_type match: 0.5
        - required_capabilities match: 0.5
        - (future) server load, uptime, latency, etc.

        The score is the sum of weighted factors, normalized to [0.0, 1.0].
        If a required factor is missing (e.g., no agent type match or no capabilities), returns 0.0.
        If no requirements are specified, returns a default base score.
        Handles missing/malformed server data gracefully and logs as needed.

        Args:
            server: The MCPServer instance to score.
            agent_type: The agent type string to check for compatibility.
            required_capabilities: List of required capabilities.
            filters: Additional filter parameters (future extensibility).
        Returns:
            float: Compatibility score between 0.0 and 1.0.
        """
        # Default weights (can be overridden by self._scoring_config)
        weights = {
            'agent_type': 0.5,
            'capabilities': 0.5,
            # 'load': 0.0,  # Example for future extensibility
        }
        weights.update(self._scoring_config)
        score = 0.0
        total_weight = 0.0

        # 1. Agent type match
        if agent_type:
            total_weight += weights['agent_type']
            if self._supports_agent_type(server, agent_type):
                score += weights['agent_type']
            else:
                # Required agent type not supported: hard fail
                logger.debug(f"Server {getattr(server, 'id', None)}: agent_type '{agent_type}' not supported. Score=0.0")
                return 0.0
        else:
            # No agent_type specified: partial base score
            score += 0.3 * weights['agent_type']
            total_weight += weights['agent_type']

        # 2. Capabilities match
        if required_capabilities:
            total_weight += weights['capabilities']
            server_caps = [cap.lower() for cap in getattr(server, 'capabilities', [])]
            logger.debug(f"Server {getattr(server, 'id', None)} capabilities: {server_caps}, required: {required_capabilities}")
            # Require ALL required_capabilities to be present in server_caps
            if not all(cap.lower() in server_caps for cap in required_capabilities):
                logger.debug(f"Server {getattr(server, 'id', None)}: does not match all required capabilities. Score=0.0")
                return 0.0
            # All required capabilities matched
            score += weights['capabilities']
        else:
            # No required capabilities specified: partial base score
            score += 0.3 * weights['capabilities']
            total_weight += weights['capabilities']

        # 3. (Future) Additional factors (e.g., load, latency, etc.)
        # Example:
        # if 'load' in weights and hasattr(server, 'load'):
        #     total_weight += weights['load']
        #     score += (1.0 - min(server.load, 1.0)) * weights['load']

        # Normalize score to [0.0, 1.0] based on total_weight
        if total_weight > 0:
            normalized_score = min(score / total_weight, 1.0)
        else:
            # No requirements specified: return a small default score
            normalized_score = 0.1
        logger.debug(f"Server {getattr(server, 'id', None)}: final compatibility score={normalized_score:.3f}")
        return normalized_score 