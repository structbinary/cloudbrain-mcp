from mcp.server.fastmcp import FastMCP
from helm_mcp_server.core.tools.helm_handler import HelmHandler
from helm_mcp_server.static import (
    HELM_BEST_PRACTICES, 
    HELM_WORKFLOW_GUIDE, 
    HELM_MCP_INSTRUCTIONS,
)
from helm_mcp_server.utils.logger import configure_logging_from_env

SERVER_DEPENDENCIES = [
    'pydantic',
    'requests',
    'pyyaml',
    'boto3',
    'loguru',
]

def create_server():
    return FastMCP(
        'helm-mcp-server',
        instructions=f'{HELM_MCP_INSTRUCTIONS}',
        dependencies=SERVER_DEPENDENCIES,
    )

def main():
    configure_logging_from_env()
    import argparse
    parser = argparse.ArgumentParser(description='Model Context Protocol (MCP) server for Helm')
    parser.add_argument(
        '--allow-write',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable write access mode (allow mutating operations)',
    )
    args = parser.parse_args()
    allow_write = args.allow_write

    mcp = create_server()
    HelmHandler(mcp, allow_write=allow_write)

    @mcp.resource(
        name='helm_best_practices',
        uri='helm://best_practices',
        description='Helm Best Practices from the official Helm documentation',
        mime_type='text/markdown',
    )
    async def helm_best_practices() -> str:
        """Provides Helm Best Practices guidance."""
        return HELM_BEST_PRACTICES

    @mcp.resource(
        name='helm_workflow_guide',
        uri='helm://workflow_guide',
        description='Helm Development Workflow Guide for using the Helm MCP server',
        mime_type='text/markdown',
    )
    async def helm_workflow_guide() -> str:
        """Provides the Helm Development Workflow guide."""
        return HELM_WORKFLOW_GUIDE
    
    mcp.run()

if __name__ == '__main__':
    main()
