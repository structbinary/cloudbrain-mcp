from typing import Optional, Dict, Any
from agents_mcp_server.utils import MCPTool, setup_logger
from agents_mcp_server.utils import ResourceNotFoundError

logger = setup_logger("agents_mcp_server.core.tools.get_agent_capabilities")

class GetAgentDetailsTool(MCPTool):
    """Tool for retrieving detailed capability information for specific agents."""

    def __init__(self, registry_manager):
        self.registry_manager = registry_manager
        logger.info("Initialized GetAgentCapabilitiesTool.")

    @property
    def name(self) -> str:
        """Name of the tool."""
        return "get_agent_details"

    @property
    def description(self) -> str:
        """Description of the tool."""
        return "Retrieves detailed information for specific agents"

    async def execute(
        self,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve detailed information for a specific agent by ID or name.
        Args:
            agent_id (Optional[str]): Unique agent ID (preferred).
            agent_name (Optional[str]): Agent name (used if ID not provided or not found).
        Returns:
            Dict[str, Any]: Serialized agent information.
        """
        if not agent_id and not agent_name:
            raise ValueError("Either agent_id or agent_name must be provided")
        agent = None
        # Try lookup by ID
        if agent_id:
            logger.info(f"Looking up agent by ID: {agent_id}")
            try:
                agent = self.registry_manager.get_agent_card_by_id(agent_id)
            except ResourceNotFoundError:
                logger.warning(f"No agent found with ID: {agent_id}")
                if not agent_name:
                    raise
        # Try lookup by name if not found by ID
        if agent is None and agent_name:
            logger.info(f"Looking up agent by name: {agent_name}")
            all_agents = self.registry_manager.find_agent_cards_by_name(agent_name)
            if not all_agents:
                logger.error(f"No agent found with name: {agent_name}")
                raise ResourceNotFoundError(f"No agent found with name: {agent_name}")
            if len(all_agents) > 1:
                logger.warning(f"Multiple agents found with name '{agent_name}'. Using the first one.")
            agent = all_agents[0]
        if agent is None:
            logger.error("Agent lookup failed by both ID and name.")
            raise ResourceNotFoundError("Agent not found by ID or name.")
        # Return a direct serialization of the validated AgentCard Pydantic model
        return agent.model_dump(exclude_none=True) 