"""ARGOCD MCP Server implementation for managing application and deployments at kubernetes"""
import argparse
from mcp.server.fastmcp import FastMCP
from argocd_mcp_server.core.tools.argocd_application_handler import ArgoCDApplicationHandler
from argocd_mcp_server.core.tools.argocd_resource_handler import ArgoCDResourceHandler
from argocd_mcp_server.static import ARGOCD_MCP_INSTRUCTIONS, ARGOCD_BEST_PRACTICES, ARGOCD_WORKFLOW

mcp = FastMCP(
    'argocd_mcp_server',
)

SERVER_DEPENDENCIES = [
    'pydantic',
    'requests',
    'loguru',
]

def create_server():
    """Creates and returns a FastMCP server instance for ArgoCD operations."""
    return FastMCP(
        'argocd-mcp-server',
        instructions=f'{ARGOCD_MCP_INSTRUCTIONS}',
        dependencies=SERVER_DEPENDENCIES,
    )

def main():
    """Initialize and run the ArgoCD MCP server."""
    parser = argparse.ArgumentParser(description='Model Context Protocol (MCP) server for ArgoCD')
    parser.add_argument(
        '--allow-write',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable write access mode (allow crud operations at argocd)',
    )
    parser.add_argument(
        '--bypass-tls',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Bypass TLS verification',
    )
    args = parser.parse_args()
    allow_write = args.allow_write
    bypass_tls = args.bypass_tls
    mcp = create_server()

    ArgoCDApplicationHandler(mcp, allow_write=allow_write, bypass_tls=bypass_tls)
    ArgoCDResourceHandler(mcp, allow_write=allow_write, bypass_tls=bypass_tls)
    
    @mcp.resource(
        name='argocd_best_practices',
        uri='argocd://best_practices',
        description='ArgoCD Best Practices from the official ArgoCD documentation',
        mime_type='text/markdown',
    )
    async def argocd_best_practices() -> str:
        """Provides ArgoCD Best Practices guidance."""
        return ARGOCD_BEST_PRACTICES

    @mcp.resource(
        name='argocd_workflow_guide',
        uri='argocd://workflow_guide',
        description='ArgoCD Development Workflow Guide for using the ArgoCD MCP server',
        mime_type='text/markdown',
    )
    async def argocd_workflow_guide() -> str:
        """Provides the ArgoCD Development Workflow guide."""
        return ARGOCD_WORKFLOW
    
    mcp.run()

if __name__ == '__main__':
    main()

