# Helm MCP Server

Model Context Protocol (MCP) server for managing Kubernetes workloads via Helm.
## Features

- **Helm Best Practices**
  - Prescriptive guidance for Helm chart usage and deployment
  - Security and compliance recommendations for Kubernetes workloads
  - Multi-cluster and context-aware operations

- **Helm Operations**
  - Install, upgrade, list, uninstall Helm releases
  - Search public Helm repositories (ArtifactHub, GitHub, etc.)
  - Pass complex/nested values, multiple values files, and extra CLI flags
  - Robust error handling and logging

- **Multi-Cluster Support**
  - Switch between clusters via kubeconfig, context, or EKS cluster name
  - Generic, production-ready Kubernetes authentication

- **Documentation and Resources**
  - Access Helm best practices and workflow guides as MCP resources
  - Rich metadata for Helm charts and repositories

## Tools and Resources

- **Helm Development Workflow**: `helm://workflow_guide`
- **Helm Best Practices**: `helm://best_practices`
- **Helm Chart Search**: `search_repository`
- **Helm Release Management**: `install_chart`, `upgrade_release`, `list_releases`, `uninstall_release`

## Local Development/Modification:

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management
2. Create and activate a virtual environment with Python 3.10:
   ```sh
   uv venv --python=3.10
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate  # On Windows
   ```
3. Install dependencies from pyproject.toml:
   ```sh
   uv pip install -e .
   ```
4. Install [Helm CLI](https://helm.sh/docs/intro/install/) and [kubectl](https://kubernetes.io/docs/tasks/tools/)
5. Access to one or more Kubernetes clusters (kubeconfig or in-cluster)

## Installation

### Docker Usage

After building the image:

```sh
docker build -t helm-mcp-server .
```

Configure MCP Client like Claude Desktop to use Docker:

```json
{
  "mcpServers": {
    "helm-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--volume",
        "/Users/structbinary/.kube/config:/app/.kube/config",
        "helm-mcp-server:latest",
        "--allow-write"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Example Usage

- **Install a Helm chart:**
  - Use the `install_chart` tool with chart name, repo, values, and target cluster/context.
- **Upgrade a release:**
  - Use `upgrade_release` with new values or chart version.
- **List releases:**
  - Use `list_releases` to see all Helm releases in a namespace or cluster.
- **Uninstall a release:**
  - Use `uninstall_release` with release name and namespace.
- **Search for charts:**
  - Use `search_repository` to find charts on ArtifactHub or other sources.
- **Access best practices:**
  - Use the `helm://best_practices` resource for official Helm guidance.

### Examples Prompts
- "can you help me in installing argocd via this repo - https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd"
- "Search for nginx charts on ArtifactHub"
- "Install the prometheus-community/kube-prometheus-stack chart in the monitoring namespace"
- "Upgrade the my-app release to the latest chart version with new values"
- "List all Helm releases in the dev namespace"
- "Uninstall the test-release from the staging cluster"
- "Switch to the production cluster context and list all releases"
- "What are the official charts for ingress controllers?"
- "Provide a step-by-step workflow for deploying a new application with Helm"

## Additional Notes

- Supports both kubeconfig and in-cluster authentication
- Multi-cluster context switching is available via input parameters
- Logging is production-grade and request-aware
- All major Helm operations are available as MCP tools
- For more details, see the best practices and workflow resources exposed by the server

---

For questions or contributions, please open an issue or pull request on the project repository.
