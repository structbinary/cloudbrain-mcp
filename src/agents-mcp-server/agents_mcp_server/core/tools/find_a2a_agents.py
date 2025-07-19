from typing import List, Any, Optional, Callable, Type
from agents_mcp_server.utils import MCPTool
from agents_mcp_server.models import AgentCard
from collections.abc import Iterable
from agents_mcp_server.utils import setup_logger
import re
from pydantic import BaseModel

logger = setup_logger("agents_mcp_server.core.tools.find_a2a_agents")

class FindA2AAgentsInputSchema(BaseModel):
    query: str
    limit: Optional[int] = None
    offset: int = 0
    # Allow extra filters for extensibility
    class Config:
        extra = "allow"

class FindA2AAgentsTool(MCPTool):
    """
    MCP Tool for finding relevant agent cards based on a natural language query.
    Compatible with the MCPTool interface. Designed for extensibility.
    """
    @property
    def name(self) -> str:
        """
        The name of the tool.
        Returns:
            str: The unique name of the tool.
        """
        return "find_a2a_agents"

    @property
    def description(self) -> str:
        """
        The description of the tool.
        Returns:
            str: A concise description of the tool's purpose.
        """
        return "Find relevant agent cards based on a natural language query."

    @property
    def args_schema(self) -> Type[BaseModel]:
        """
        Returns the schema for validating input arguments.
        Returns:
            Type[BaseModel]: A Pydantic model class that defines the expected input structure.
        """
        return FindA2AAgentsInputSchema

    @property
    def is_single_input(self) -> bool:
        """
        Indicates whether the tool expects a single input value.
        Returns:
            bool: False, as this tool accepts a structured input object.
        """
        return False

    def __init__(self, registry_manager):
        """
        Initialize the FindA2AAgentsTool.
        Logs the initialization event.
        """
        logger.info("Initialized FindA2AAgentsTool.")
        if registry_manager is None:
            logger.error("Registry manager cannot be None")
            raise ValueError("Registry manager cannot be None")
        self.registry_manager = registry_manager

    async def execute(
        self,
        query: str,
        filter_func: Optional[Callable[[AgentCard], bool]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        **filters
    ) -> List[AgentCard]:
        """
        Search and return relevant agent cards based on a natural language query and optional filters.
        Args:
            query (str): Natural language search query.
            filter_func (Optional[Callable]): Optional advanced filter function.
            limit (Optional[int]): Max number of results to return.
            offset (int): Number of results to skip (pagination).
            **filters: Field-based filters (e.g., status="active").
        Returns:
            List[AgentCard]: List of matching agent cards, sorted by relevance.
        """
        logger.info(f"Executing find_a2a_agents with query: '{query}', filters: {filters}, limit: {limit}, offset: {offset}")
        try:
            # Defensive: Remove 'filters' key if present (prevents double-wrapping)
            filters.pop('filters', None)
            # Retrieve all agent cards
            agent_cards = self.registry_manager.list_agent_cards()
            # logger.info(f"Found {len(agent_cards)} agent cards")
            # logger.info(f"Agent cards: {agent_cards}")
            # Apply filtering by kwargs
            if filters:
                def matches(card):
                    for k, v in filters.items():
                        parts = k.split('__')
                        attr = card
                        for part in parts:
                            # Support list indexing if part is an integer
                            if isinstance(attr, list) and part.isdigit():
                                idx = int(part)
                                if idx < len(attr):
                                    attr = attr[idx]
                                else:
                                    attr = None
                                    break
                            else:
                                attr = getattr(attr, part, None)
                            if attr is None:
                                break
                        if attr != v:
                            return False
                    return True
                agent_cards = [card for card in agent_cards if matches(card)]
                # logger.info(f"Filtered agent cards: {agent_cards}")
            logger.info(f"Filtered function: {filter_func}")
            # Apply filter_func if provided
            if filter_func:
                agent_cards = [card for card in agent_cards if filter_func(card)]
                # logger.info(f"Filtered agent cards: {agent_cards}")
                # logger.info(f"Filtered function: {filter_func}")
            # --- WILDCARD HANDLING ---
            if not query.strip() or query.strip() == "*":
                logger.info("Wildcard or empty query detected; returning all agent cards after filtering and pagination.")
                paginated = agent_cards[offset:offset+limit] if limit is not None else agent_cards[offset:]
                # logger.info(f"Paginated agent cards: {paginated}")
                return [card.model_dump(exclude_none=True) for card in paginated]
            if not agent_cards:
                logger.info("No agent cards matched the filters.")
                return []
            # Score and sort
            ranked = self.rank_agent_cards(query, agent_cards)
            # Filter out zero-score agents
            ranked = [item for item in ranked if item[1] > 0]
            # Pagination
            paginated = ranked[offset:offset+limit] if limit is not None else ranked[offset:]
            logger.info(f"Query returned {len(paginated)} results (from {len(agent_cards)} filtered cards)")
            return [card for card, score in paginated]
        except Exception as ex:
            logger.error(f"Error during find_a2a_agents execution: {ex}")
            return []

    @staticmethod
    def score_agent_card(query: str, agent_card: AgentCard, field_weights: Optional[dict] = None) -> float:
        """
        Compute a relevance score for an agent card given a query using keyword matching and field weighting.
        Args:
            query (str): The user query.
            agent_card (AgentCard): The agent card to score.
            field_weights (dict): Optional field weights (default: name=3, description=2, skills=2, capabilities=1).
        Returns:
            float: The relevance score.
        """
        if field_weights is None:
            field_weights = {"name": 3, "description": 2, "skills": 2, "capabilities": 1}
        # Tokenize and lowercase query
        query_tokens = set(re.findall(r"\w+", query.lower()))
        score = 0.0
        # Score name
        name_tokens = set(re.findall(r"\w+", getattr(agent_card, "name", "").lower()))
        name_matches = len(query_tokens & name_tokens)
        score += field_weights["name"] * name_matches
        logger.debug(f"[Scoring] Name matches: {name_matches} (weight {field_weights['name']})")
        # Score description
        desc_tokens = set(re.findall(r"\w+", getattr(agent_card, "description", "").lower()))
        desc_matches = len(query_tokens & desc_tokens)
        score += field_weights["description"] * desc_matches
        logger.debug(f"[Scoring] Description matches: {desc_matches} (weight {field_weights['description']})")
        # Score skills
        skills = getattr(agent_card, "skills", [])
        skill_tokens = set()
        if isinstance(skills, Iterable):
            for skill in skills:
                skill_tokens |= set(re.findall(r"\w+", getattr(skill, "name", "").lower()))
                skill_tokens |= set(re.findall(r"\w+", getattr(skill, "description", "").lower()))
                for tag in getattr(skill, "tags", []) or []:
                    skill_tokens |= set(re.findall(r"\w+", tag.lower()))
        skill_matches = len(query_tokens & skill_tokens)
        score += field_weights["skills"] * skill_matches
        logger.debug(f"[Scoring] Skills matches: {skill_matches} (weight {field_weights['skills']})")
        # Score capabilities
        capabilities = getattr(agent_card, "capabilities", None)
        cap_tokens = set()
        if capabilities:
            for cap_name, cap_value in capabilities.model_dump(exclude_none=True).items():
                if isinstance(cap_value, bool) and cap_value:
                    cap_tokens.add(cap_name.lower())
        cap_matches = len(query_tokens & cap_tokens)
        score += field_weights["capabilities"] * cap_matches
        logger.debug(f"[Scoring] Capabilities matches: {cap_matches} (weight {field_weights['capabilities']})")
        logger.debug(f"[Scoring] Total score for agent '{getattr(agent_card, 'name', '')}': {score}")
        return score

    def rank_agent_cards(self, query: str, agent_cards: List[AgentCard], field_weights: Optional[dict] = None) -> List[tuple[AgentCard, float]]:
        """
        Rank agent cards by relevance to the query using the scoring function.
        Args:
            query (str): The user query.
            agent_cards (List[AgentCard]): List of agent cards to rank.
            field_weights (dict): Optional field weights.
        Returns:
            List[tuple[AgentCard, float]]: List of (agent_card, score) tuples sorted by score descending.
        """
        scored = []
        for card in agent_cards:
            score = self.score_agent_card(query, card, field_weights)
            scored.append((card, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Ranked {len(agent_cards)} agent cards for query '{query}'. Top score: {scored[0][1] if scored else 0}")
        return scored

# --- Usage Example ---
# tool = FindA2AAgentsTool()
# results = tool.execute("Find agents that support streaming and NLP tasks") 