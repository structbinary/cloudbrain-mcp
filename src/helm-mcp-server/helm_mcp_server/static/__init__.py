from importlib import resources

with (
    resources.files('helm_mcp_server.static')
    .joinpath('HELM_BEST_PRACTICES.md')
    .open('r', encoding='utf-8') as f
):
    HELM_BEST_PRACTICES = f.read()

with (
    resources.files('helm_mcp_server.static')
    .joinpath('HELM_WORKFLOW_GUIDE.md')
    .open('r', encoding='utf-8') as f
):
    HELM_WORKFLOW_GUIDE = f.read()

with (
    resources.files('helm_mcp_server.static')
    .joinpath('HELM_MCP_INSTRUCTIONS.md')
    .open('r', encoding='utf-8') as f
):
    HELM_MCP_INSTRUCTIONS = f.read()

__all__ = [
    'HELM_BEST_PRACTICES',
    'HELM_WORKFLOW_GUIDE',
    'HELM_MCP_INSTRUCTIONS',
]