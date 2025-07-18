import threading
import logging
from typing import Dict, Any, Optional, Callable, List
import os
import json
from pydantic import ValidationError

# Import the project logger setup (assume logging.py provides setup_logger)
from agents_mcp_server.utils import setup_logger
from agents_mcp_server.models import AgentCard
from agents_mcp_server.models import MCPServer

logger = setup_logger("agents_mcp_server.core.registry_manager")

class RegistryManager:
    """
    Central, thread-safe registry for managing agent cards and MCP servers in memory.
    All agent cards and MCP servers are validated Pydantic model instances (AgentCard, MCPServer).
    Provides registration, lookup, and removal methods for both resource types.
    Extensible for future features (e.g., hot reloading, advanced queries).
    """
    def __init__(self) -> None:
        """
        Initialize the RegistryManager with empty internal data structures and a reentrant lock.
        Logs the initialization event.
        All data is stored as validated Pydantic model instances.
        """
        self._agent_cards: Dict[str, AgentCard] = {}
        self._mcp_servers: Dict[str, MCPServer] = {}
        self._lock = threading.RLock()
        logger.info("RegistryManager initialized with empty registries.")

    # --- Agent Card Methods ---
    def register_agent_card(self, agent_id: str, agent_card: AgentCard) -> None:
        """
        Register or update an agent card in the registry. Only accepts AgentCard instances.
        """
        assert isinstance(agent_card, AgentCard), "agent_card must be an AgentCard instance"
        with self._lock:
            self._agent_cards[agent_id] = agent_card
            logger.info(f"Registered agent card: {agent_id}")

    def get_agent_card(self, agent_id: str) -> Optional[AgentCard]:
        """
        Retrieve an agent card by ID. Returns None if not found.
        """
        with self._lock:
            card = self._agent_cards.get(agent_id)
            if card is None:
                logger.warning(f"Agent card not found: {agent_id}")
            return card

    def unregister_agent_card(self, agent_id: str) -> None:
        """
        Remove an agent card from the registry.
        """
        with self._lock:
            if agent_id in self._agent_cards:
                del self._agent_cards[agent_id]
                logger.info(f"Unregistered agent card: {agent_id}")
            else:
                logger.warning(f"Tried to unregister non-existent agent card: {agent_id}")

    def get_agent_card_by_id(self, agent_id: str) -> Optional[AgentCard]:
        """
        Retrieve an agent card by its unique ID. Returns None if not found.
        Logs the query and result.
        """
        with self._lock:
            card = self._agent_cards.get(agent_id)
            if card is None:
                logger.warning(f"Agent card not found: {agent_id}")
            else:
                logger.info(f"Queried agent card by ID: {agent_id}")
            return card

    def find_agent_cards_by_name(self, name: str) -> List[AgentCard]:
        """
        Find all agent cards with the given name.
        Returns a list (may be empty). Logs the query and result count.
        """
        with self._lock:
            results = [card for card in self._agent_cards.values() if getattr(card, 'name', None) == name]
            logger.info(f"Queried agent cards by name: {name}, found: {len(results)}")
            return results

    def find_agent_cards_by_capability(self, capability: str) -> List[AgentCard]:
        """
        Find all agent cards that have the specified capability.
        Returns a list (may be empty). Logs the query and result count.
        """
        with self._lock:
            results = [card for card in self._agent_cards.values()
                       if card.capabilities and getattr(card.capabilities, capability, False)]
            logger.info(f"Queried agent cards by capability: {capability}, found: {len(results)}")
            return results

    def list_agent_cards(self, filter_func: Optional[Callable[[AgentCard], bool]] = None) -> List[AgentCard]:
        """
        List all agent cards, optionally filtered by a provided function.
        Returns a list (may be empty). Logs the query and result count.
        """
        with self._lock:
            if filter_func:
                results = [card for card in self._agent_cards.values() if filter_func(card)]
                logger.info(f"Listed agent cards with filter, found: {len(results)}")
            else:
                results = list(self._agent_cards.values())
                logger.info(f"Listed all agent cards, found: {len(results)}")
            return results

    # --- MCP Server Methods ---
    def register_mcp_server(self, server_id: str, mcp_server: MCPServer) -> None:
        """
        Register or update an MCP server in the registry. Only accepts MCPServer instances.
        If a server with the same id or id:version composite already exists, update it in place.
        """
        assert isinstance(mcp_server, MCPServer), "mcp_server must be a MCPServer instance"
        with self._lock:
            # Remove any existing entry with the same id or id:version
            to_delete = None
            for key, server in self._mcp_servers.items():
                if getattr(server, 'id', None) == mcp_server.id or f"{getattr(server, 'id', None)}:{getattr(server, 'version', None)}" == f"{mcp_server.id}:{mcp_server.version}":
                    to_delete = key
                    break
            if to_delete:
                del self._mcp_servers[to_delete]
                logger.info(f"Removed existing MCP server with key: {to_delete} for update.")
            self._mcp_servers[server_id] = mcp_server
            logger.info(f"Registered MCP server: {server_id}")

    def unregister_mcp_server(self, server_id: str) -> None:
        """
        Remove an MCP server from the registry. Supports both direct key and attribute-based unregistration.
        """
        with self._lock:
            # Try direct key first
            if server_id in self._mcp_servers:
                del self._mcp_servers[server_id]
                logger.info(f"Unregistered MCP server: {server_id}")
                return
            # Fallback: search for matching .id or id:version
            to_delete = None
            for key, server in self._mcp_servers.items():
                if getattr(server, 'id', None) == server_id or f"{getattr(server, 'id', None)}:{getattr(server, 'version', None)}" == server_id:
                    to_delete = key
                    break
            if to_delete:
                del self._mcp_servers[to_delete]
                logger.info(f"Unregistered MCP server by attribute match: {server_id}")
            else:
                logger.warning(f"Tried to unregister non-existent MCP server: {server_id}")

    def get_mcp_server_by_id(self, server_id: str) -> Optional[MCPServer]:
        """
        Retrieve an MCP server by its unique ID. Returns None if not found.
        Logs the query and result.
        """
        with self._lock:
            logger.info(f"Getting MCP server by ID: {server_id}")
            # logger.info(f"MCP servers: {self._mcp_servers}")
            # Try direct key lookup first
            server = self._mcp_servers.get(server_id)
            if server is not None:
                logger.info(f"Queried MCP server by direct key: {server_id}")
                return server
            # Fallback: search by .id or id:version composite
            for s in self._mcp_servers.values():
                if getattr(s, 'id', None) == server_id or f"{getattr(s, 'id', None)}:{getattr(s, 'version', None)}" == server_id:
                    logger.info(f"Queried MCP server by attribute match: {server_id}")
                    return s
            logger.warning(f"MCP server not found: {server_id}")
            return None

    def find_mcp_servers_by_capability(self, capability: str) -> List[MCPServer]:
        """
        Find all MCP servers that have the specified capability.
        Returns a list (may be empty). Logs the query and result count.
        """
        with self._lock:
            results = [server for server in self._mcp_servers.values()
                       if capability in getattr(server, 'capabilities', [])]
            logger.info(f"Queried MCP servers by capability: {capability}, found: {len(results)}")
            return results

    def list_mcp_servers(self, filter_func: Optional[Callable[[MCPServer], bool]] = None) -> List[MCPServer]:
        """
        List all MCP servers, optionally filtered by a provided function.
        Returns a list (may be empty). Logs the query and result count.
        """
        with self._lock:
            if filter_func:
                results = [server for server in self._mcp_servers.values() if filter_func(server)]
                logger.info(f"Listed MCP servers with filter, found: {len(results)}")
            else:
                results = list(self._mcp_servers.values())
                logger.info(f"Listed all MCP servers, found: {len(results)}")
            return results

    def get_mcp_server_by_name(self, server_name: str) -> Optional[MCPServer]:
        """
        Retrieve an MCP server by its name. Returns None if not found.
        Logs the query and result.
        """
        with self._lock:
            for server in self._mcp_servers.values():
                if getattr(server, 'name', None) == server_name:
                    logger.info(f"Queried MCP server by name: {server_name}")
                    return server
            logger.warning(f"MCP server not found by name: {server_name}")
            return None

    # --- Utility Methods ---
    def load_agent_cards_from_directory(self, directory_path: str) -> int:
        """
        Load agent cards from all JSON files in the specified directory.
        Each file should contain a single agent card object.
        Validates with the AgentCard Pydantic model.
        Logs successes and errors, skips invalid files.
        Returns the number of successfully loaded agent cards.
        """
        loaded_count = 0
        logger.info(f"Starting agent card loading from directory: {directory_path}")
        if not os.path.isdir(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return 0
        for filename in os.listdir(directory_path):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = f.read()
                agent_card = AgentCard.model_validate_json(json_data)
                # Use name+version as unique key (or customize as needed)
                agent_id = f"{agent_card.name}:{agent_card.version}"
                self.register_agent_card(agent_id, agent_card)
                logger.info(f"Loaded agent card: {agent_id} from {filename}")
                loaded_count += 1
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to read/parse {filename}: {e}")
            except ValidationError as ve:
                logger.error(f"Validation failed for {filename}: {ve}")
            except Exception as ex:
                logger.error(f"Unexpected error loading {filename}: {ex}")
        logger.info(f"Completed agent card loading. Successfully loaded: {loaded_count}")
        return loaded_count

    def load_mcp_servers_from_directory(self, directory_path: str) -> int:
        """
        Load MCP servers from all JSON files in the specified directory.
        Each file should contain a single MCP server object.
        Validates with the MCPServer Pydantic model.
        Logs successes and errors, skips invalid files.
        Returns the number of successfully loaded MCP servers.
        """
        loaded_count = 0
        logger.info(f"Starting MCP server loading from directory: {directory_path}")
        if not os.path.isdir(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return 0
        for filename in os.listdir(directory_path):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = f.read()
                mcp_server = MCPServer.model_validate_json(json_data)
                # Use id+version as unique key (or customize as needed)
                server_id = f"{mcp_server.id}:{mcp_server.version}"
                self.register_mcp_server(server_id, mcp_server)
                logger.info(f"Loaded MCP server: {server_id} from {filename}")
                loaded_count += 1
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to read/parse {filename}: {e}")
            except ValidationError as ve:
                logger.error(f"Validation failed for {filename}: {ve}")
            except Exception as ex:
                logger.error(f"Unexpected error loading {filename}: {ex}")
        logger.info(f"Completed MCP server loading. Successfully loaded: {loaded_count}")
        return loaded_count

# --- Usage Example ---
# from cloudbrain_mcp_server.core.registry_manager import RegistryManager
# registry = RegistryManager()
# registry.register_agent_card("agent1", agent_card_obj)
# card = registry.get_agent_card("agent1")
# registry.unregister_agent_card("agent1") 