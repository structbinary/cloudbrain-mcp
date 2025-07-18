# Cloudbrain MCP Server

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A central registry service that leverages the Model Context Protocol (MCP) to enable dynamic discovery and interaction between Google A2A (Agent-to-Agent) agents and various MCP servers. This system serves as a discovery hub for DevOps agents, facilitating seamless integration and communication across distributed agent architectures.

## 🚀 Features

- **Dynamic Agent Discovery**: Enable agentic systems to dynamically find and connect with Google A2A agents
- **MCP Server Discovery**: Allow individual agents to discover capability-matched MCP servers
- **Standardized Integration**: Provide a unified interface for agent communication using MCP protocol
- **Scalable Architecture**: Support growing numbers of agents and MCP servers
- **Natural Language Queries**: Find agents and servers using natural language descriptions
- **Compatibility Validation**: Validate compatibility between agents and MCP servers

## 🎯 Use Cases

### For Planner Agents & Orchestrators
- **Dynamic Agent Discovery**: Planner agents query the registry to discover available executor agents (AWS orchestrator, CI/CD agent, monitoring agent, etc.) and their capabilities
- **Intelligent Task Mapping**: Map complex DevOps tasks to the most suitable specialized agents based on their registered capabilities
- **MCP Server Orchestration**: Discover which MCP servers provide tools for specific tasks (terraform, kubectl, AWS CLI, etc.) and ensure proper tool-to-agent-to-task alignment
- **Real-time Registry Updates**: Maintain up-to-date knowledge of available executor agents and MCP servers as they come online or go offline

### For Executor Agents
- **Self-Registration**: Register agent cards with capabilities, endpoints, and metadata for discovery by planner agents
- **MCP Server Discovery**: Find appropriate MCP servers that provide the tools needed for specific task execution
- **Capability Validation**: Validate compatibility between agent requirements and available MCP server tools
- **Dynamic Tool Integration**: Discover and integrate with new MCP servers as they become available

### For DevOps Engineers
- **Centralized Agent Management**: View and manage all available agents and their capabilities through a single registry
- **Workflow Orchestration**: Enable complex multi-agent DevOps workflows with automatic agent discovery and task routing
- **Tool Discovery**: Find and understand which MCP servers provide specific tools for infrastructure automation

## 🏗️ Architecture

### Technology Stack
- **Programming Language**: Python 3.10
- **Primary Dependencies**:
  - `mcp['cli']` by Anthropic - MCP protocol implementation and CLI utilities
  - `pydantic` - Data validation and serialization
  - `json` - JSON parsing and manipulation (standard library)

### Project Structure
```
agents_mcp_server/
├── core/
│   ├── tools/          # MCP tools implementation classes
│   │   ├── find_a2a_agents.py
│   │   ├── get_agent_capabilities.py
│   │   ├── list_mcp_servers.py
│   │   ├── get_mcp_server_details.py
│   │   ├── find_mcp_servers.py
│   ├── resources/      # MCP resources implementation classes
│   │   ├── agent_cards.py
│   │   ├── agent_card.py
│   │   ├── mcp_servers.py
│   │   
│   └── registry_manager.py  # Central registry for agent cards and MCP servers
├── models/             # Pydantic data models for validation
│   ├── agent_card.py
│   ├── mcp_server.py
│   └── api_responses.py
├── static/
│   ├── agent_cards/    # Static storage for A2A agent card JSON files
│   └── agent_details/  # Static storage for MCP server capability JSON files
├── utils/              # Helper methods and utilities
│   ├── logging.py      # Common MCP logging utilities
│   ├── exceptions.py   # Custom exception classes
│   └── abstracts.py    # Abstract base classes
├── __init__.py
└── main.py             # Application entry point
```

## 🚀 Onboarding Guide

### Onboarding A2A Agents

To onboard an A2A agent to the central registry, follow these steps:

1. **Create an A2A agent card** corresponding to the agent you want to onboard
2. **Reference the example format** from the provided template
3. **Place the agent card** in the `agents_mcp_server/static/agent_cards/` directory

#### Example A2A Agent Card (`aws_orchestrator_agent.json`)
```json
{
    "name": "AWS Orchestrator Agent",
    "description": "Orchestrates AWS resources",
    "url": "http://localhost:10103/",
    "provider": null,
    "version": "1.0.0",
    "documentationUrl": null,
    "capabilities": {
        "streaming": "True",
        "pushNotifications": "True",
        "stateTransitionHistory": "False"
    },
    "authentication": {
        "credentials": null,
        "schemes": ["public"]
    },
    "defaultInputModes": ["text", "text/plain"],
    "defaultOutputModes": ["text", "text/plain"],
    "skills": [
        {
            "id": "orchestrate_aws_resources",
            "name": "Orchestrate AWS Resources",
            "description": "Orchestrates AWS resources",
            "tags": ["orchestrate_aws_resources"],
            "examples": ["can you help me in provisioning a new aws resource via terraform"],
            "inputModes": null,
            "outputModes": null
        }
    ]
}
```

#### A2A Agent Card Schema
The agent card must conform to the following Pydantic model:
```python
class AgentCard(BaseModel):
    name: str                    # Required: Agent name
    description: Optional[str]   # Optional: Agent description
    url: Optional[HttpUrl]       # Optional: Agent endpoint URL
    provider: Optional[str]      # Optional: Provider information
    version: str                 # Required: Agent version
    documentationUrl: Optional[str]  # Optional: Documentation URL
    capabilities: Optional[Capabilities]  # Optional: Agent capabilities
    authentication: Optional[Authentication]  # Optional: Auth schemes
    defaultInputModes: Optional[List[str]]   # Optional: Input modes
    defaultOutputModes: Optional[List[str]]  # Optional: Output modes
    skills: Optional[List[Skill]]            # Optional: Agent skills
```

### Onboarding MCP Servers

To onboard an MCP server to the central registry, follow these steps:

1. **Create an MCP server details JSON file** following the provided template
2. **Place the server file** in the `agents_mcp_server/static/mcp_servers/` directory

#### Example MCP Server (`terraform_mcp_server.json`)
```json
{
    "id": "terraform-mcp-server",
    "name": "Terraform MCP Server",
    "version": "1.0.0",
    "capabilities": [
        "orchestrate_aws_resources",
        "orchestrate_gcp_resources",
        "run_terraform_plan",
        "run_terraform_apply"
    ],
    "connection": {
        "transport": "stdio",
        "auth_method": "none",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-terraform"],
        "required_env": ["TERRAFORM_API_KEY"]
    },
    "compatibility": {
        "agent_types": ["aws-orchestrator-agent", "gcp-orchestrator-agent"],
        "requirements": {
            "terraform_version": ">=1.0.0"
        }
    },
    "description": "A server for managing Terraform resources via MCP.",
    "authentication": {
        "credentials": null,
        "schemes": ["api_key"]
    }
}
```

#### MCP Server Schema
The MCP server configuration must conform to the following Pydantic model:
```python
class MCPServer(BaseModel):
    id: str                      # Required: Unique server identifier
    name: str                    # Required: Server name
    version: str                 # Required: Server version
    capabilities: List[str]      # Required: List of server capabilities
    connection: ServerConnection # Required: Connection details
    compatibility: ServerCompatibility  # Required: Compatibility info
    description: Optional[str]   # Optional: Server description
    authentication: Optional[Authentication]  # Optional: Auth details
```

### Validation

The registry server will automatically validate all agent cards and MCP server configurations on startup. Any validation errors will be logged, and invalid configurations will be skipped.

## 🔧 MCP Exposed Tools

### Google A2A Agent Card Management

#### `find_a2a_agents`
Discovers relevant agent cards based on natural language queries.

**Input**: Query string describing required agent capabilities  
**Output**: List of matching agent cards with relevance scores  
**Example**: "Find agents capable of AWS resource provisioning"

#### `get_agent_capabilities`
Retrieves detailed capability information for specific agents.

**Input**: Agent ID or name  
**Output**: Comprehensive capability matrix and supported operations

### MCP Server Management

#### `list_mcp_servers`
Lists all currently available MCP servers.

**Input**: Optional filters (category, status, capabilities)  
**Output**: Array of MCP server summaries
**Example**: Can you list down all mcp server which is available

#### `get_mcp_server_details`
Retrieves detailed configuration for specific MCP server.

**Input**: Server ID or name  
**Output**: Complete server configuration, endpoints, and metadata
**Example**: Can you get me details of this mcp server <mcp-server-id>

#### `find_mcp_servers`
Discovers MCP servers matching agent specifications.

**Input**: Agent type, required capabilities, performance requirements  
**Output**: Ranked list of compatible MCP servers  
**Example**: find mcp server which has capability of writing terraform modules for aws services


## 📡 MCP Resources

### Agent Card Resources

- **`/agent_cards`** - Retrieves all loaded agent cards
- **`/agent_cards/{agent_id}`** - Retrieves specific agent card details

### MCP Server Resources

- **`/mcp_servers`** - Retrieves all MCP server configurations
- **`/mcp_servers/{server_id}`** - Retrieves individual MCP server configuration
- **`/mcp_servers/{server_id}/health`** - Real-time health status of MCP servers

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher


### Installation
1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)** for dependency management
2. **Create and activate a virtual environment with Python 3.12:**
   ```sh
   uv venv --python=3.12
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate  # On Windows
   ```
3. **Install dependencies from pyproject.toml:**
   ```sh
   uv pip install -e .
   ```

4. **Add agent cards and MCP server configurations**
   - Place agent card JSON files in `agents_mcp_server/static/agent_cards/`
   - Place MCP server configuration files in `agents_mcp_server/static/agent_details/`


5. **Run the server**
   ```bash
   uv run -m agents_mcp_server
   ```

### Server Configuration

The server runs with the following default configuration:

- **Host**: `localhost`
- **Port**: `8080`
- **Transport**: `sse` (Server-Sent Events)

You can customize these settings using command-line options:

```bash
uv run -m agents_mcp_server --host 0.0.0.0 --port 9000 --transport stdio
```

**Available Options:**
- `--host`: Host on which the server is started (default: localhost)
- `--port`: Port on which the server is started (default: 8080)
- `--transport`: MCP Transport protocol (default: sse)

### MCP Client Configuration

To connect to the Agents MCP Server from an MCP client (like Cursor), add the following configuration to your MCP client settings:

```json
{
  "agents-mcp-server": {
    "url": "http://127.0.0.1:8080/sse",
    "transport": "sse",
    "disabled": false,
    "autoApprove": []
  }
}
```

**Configuration Parameters:**
- `url`: The SSE endpoint URL for the server (default: http://127.0.0.1:8080/sse)
- `transport`: Transport protocol (sse for Server-Sent Events)
- `disabled`: Set to `true` to disable this MCP server connection
- `autoApprove`: Array of tool names that should be auto-approved (empty for manual approval)

## 🚀 Future Enhancements

### Phase 2 Features
- AI-powered agent recommendation engine
- Dynamic agent card loading (hot reload from static folder)
- Advanced filtering and search capabilities
- Semantic search using embeddings for better agent/server matching


## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the Apache License, Version 2.0 - see the [LICENSE](LICENSE) file for details.

## 📋 Implementation Status

### ✅ Completed Components
- **Project Structure**: Complete directory structure and base files
- **Pydantic Data Models**: AgentCard, MCPServer, and API response models
- **Utility Classes**: Logging, exceptions, and abstract base classes
- **Core MCP Tools**: 
  - `find_a2a_agents` - Natural language agent discovery
  - `get_agent_capabilities` - Detailed agent capability retrieval
  - `list_mcp_servers` - MCP server listing with filtering
  - `get_mcp_server_details` - Individual server configuration retrieval
  - `find_mcp_servers` - Compatibility-based server discovery
- **Core MCP Resources**:
  - `/agent_cards` - All agent cards retrieval
  - `/agent_cards/{agent_id}` - Individual agent card details
  - `/mcp_servers` - All MCP servers retrieval
  - `/mcp_servers/{server_id}` - Individual MCP server details
- **Registry Manager**: Central data management for agent cards and MCP servers
- **Application Entry Point**: Main server initialization and startup
- **Pydantic Integration**: Ensuring all components use validated models
- **Error Handling**: Enhanced error handling and recovery mechanisms

### 🔄 In Progress
- **Testing**: Comprehensive unit and integration test suites


## 🙏 Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) for the MCP specification
- [Anthropic](https://www.anthropic.com/) for the MCP CLI implementation
- The open-source community for inspiration and contributions

---

**Built with ❤️ for the DevOps community**
