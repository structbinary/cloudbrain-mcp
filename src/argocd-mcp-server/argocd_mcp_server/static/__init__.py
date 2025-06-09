from importlib import resources

with (
    resources.files('argocd_mcp_server.static')
    .joinpath('ARGOCD_MCP_INSTRUCTIONS.md')
    .open('r', encoding='utf-8') as f
):
    ARGOCD_MCP_INSTRUCTIONS = f.read()


with (
    resources.files('argocd_mcp_server.static')
    .joinpath('ARGOCD_WORKFLOW.md')
    .open('r', encoding='utf-8') as f
):
    ARGOCD_WORKFLOW = f.read()

with (
    resources.files('argocd_mcp_server.static')
    .joinpath('ARGOCD_BEST_PRACTICES.md')
    .open('r', encoding='utf-8') as f
):
    ARGOCD_BEST_PRACTICES = f.read()