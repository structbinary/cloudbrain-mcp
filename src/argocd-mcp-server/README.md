# ArgoCD MCP Server

Model Context Protocol (MCP) server for managing Kubernetes applications and resources via ArgoCD using GitOps principles.

## Features

- **GitOps Best Practices**
  - Prescriptive guidance for ArgoCD application management
  - Security and compliance recommendations for Kubernetes workloads
  - Automated sync and self-healing capabilities
  - Comprehensive resource monitoring and management

- **ArgoCD Operations**
  - Create, update, delete, and sync applications
  - Manage application resources and their lifecycle
  - Retrieve logs, events, and resource actions
  - Robust error handling and logging

- **Resource Management**
  - Get resource trees and managed resources
  - Retrieve workload logs and events
  - Execute resource actions
  - Monitor application health and status

- **Documentation and Resources**
  - Access ArgoCD best practices and workflow guides
  - Rich metadata for applications and resources
  - Comprehensive error handling and logging

## MCP Tools and Resources

- **ArgoCD Development Workflow Resource**: `argocd://workflow_guide`
- **ArgoCD Best Practices Resource**: `argocd://best_practices`
- **Application Management Tools**: `manage_argocd_application`
- **Resource Management Tools**: `manage_argocd_resource`

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
4. Run the token fetch script by first setting evironment variable 
   ```sh
   export ARGOCD_PASSWORD=your-argocd-password
   export ARGOCD_USERNAME=admin
   export ARGOCD_SERVER=https://localhost:8080
   export ARGOCD_VERIFY_TLS=false

   and then run:
   python argocd_mcp_server/scripts/fetch_argocd_token.py
   ```

## Installation

### Docker Usage

Build the docker Image:

```sh
docker build -t argocd-mcp-server .
```

Configure MCP Client like Claude Desktop to use Docker:

```json
{
  "mcpServers": {
    "argocd-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=INFO",
        "--env",
        "ARGOCD_SERVER_URL=https://host.docker.internal:8080",
        "--env",
        "ARGOCD_TOKEN=your-token-here",
        "argocd-mcp-server:latest",
        "--allow-write",
        "--bypass-tls"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

> **Note:** 
> - `--allow-write`: When enabled, the MCP server can perform CRUD operations on ArgoCD applications. Default is `false` (read-only mode).
> - `--bypass-tls`: Use this flag to bypass SSL certificate verification when your ArgoCD server uses self-signed certificates. Default is `false`.

### Local Development

Configure MCP Client for local development:

```json
{
  "mcpServers": {
    "argocd-mcp-server": {
      "command": "/bin/bash",
      "args": [
        "-c",
        "cd /path/to/argocd-mcp-server && source .venv/bin/activate && uv run argocd_mcp_server/server.py --allow-write --bypass-tls"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "INFO",
        "ARGOCD_SERVER_URL": "https://localhost:8080",
        "ARGOCD_TOKEN": "your-token-here"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Example Prompts

#### Application Management

##### Create Application
Example prompts:
- "I want to create a new ArgoCD application named 'guestbook' with these details -"
```json
{
  "project": "default",
  "repo_url": "https://github.com/argoproj/argocd-example-apps.git",
  "path": "guestbook",
  "destination_server": "https://kubernetes.default.svc",
  "destination_namespace": "default",
  "target_revision": "HEAD",
  "sync_policy": "Automated",
  "sync_options": ["Prune=true"],
  "prune_propagation_policy": "foreground",
  "finalizer": false,
  "namespace": "argocd"
}
```

##### Update Application
Example prompts:
- "I need to update the 'hello-world' application to use a different repository with these details "
```json
{
  "project": "default",
  "repo_url": "https://github.com/argoproj/argocd-example-apps.git",
  "path": "guestbook",
  "destination_server": "https://kubernetes.default.svc",
  "destination_namespace": "default",
  "target_revision": "v2",
  "sync_policy": "Manual",
  "sync_options": ["Prune=true"],
  "prune_propagation_policy": "foreground",
  "finalizer": false,
  "namespace": "argocd"
}
```

##### Sync Application
Example prompts:
- "Can you sync the 'hello-world' application?"
- "I need to trigger a sync for the 'hello-world' application"
- "Please perform a sync operation on the 'hello-world' application"

##### Delete Application
Example prompts:
- "I want to delete the 'hello-world' application"
- "Can you remove the 'hello-world' application from ArgoCD?"
- "Please delete the 'hello-world' application and all its resources"

##### Get Application
Example prompts:
- "Can you show me the details of the 'hello-world' application?"
- "What is the current status of the 'hello-world' application?"
- "I need to see the configuration of the 'hello-world' application"

> **Note:** Parameter Requirements by Operation:
> 
> 1. **Create/Update Application**
>    - Required: `name`, `project`, `repo_url`, `path`, `destination_server`
>    - Optional: 
>      - `destination_namespace`
>      - `target_revision` (default: "HEAD")
>      - `sync_policy` (default: "manual")
>      - `sync_options`
>      - `prune_propagation_policy` (default: "foreground")
>      - `finalizer` (default: false)
>      - `namespace` (default: "argocd")
> 
> 2. **Sync Application**
>    - Required: `name`
> 
> 3. **Delete Application**
>    - Required: `name`
> 
> 4. **Get Application**
>    - Required: `name`

#### Resource Management

##### Get Resource Tree
Example prompts:
- "Show me the resource tree for the application 'hello-world'"
- "Can you display the complete resource hierarchy for 'hello-world'?"
- "I need to see all resources and their relationships in the 'hello-world' application"


##### Get Managed Resources
Example prompts:
- "What resources are currently managed by the application 'hello-world'?"
- "Show me all resources that are being managed by 'hello-world'"
- "List all the Kubernetes resources that 'hello-world' is managing"

##### Get Workload Logs
Example prompts:
- "Can you show me the last 100 lines of logs from the pod 'hello-world-75ddddb654-zmprt'?"
- "I need to see the logs for the pod 'hello-world-75ddddb654-zmprt' in the 'hello-world' application"

##### Get Resource Events
Example prompts:
- "What events have occurred for the pod 'hello-world-75ddddb654-zmprt'?"
- "Show me the event history for the pod 'hello-world-75ddddb654-zmprt'"

##### Get Resource Actions
Example prompts:
- "What actions can I perform on the pod 'hello-world-75ddddb654-zmprt'?"
- "Show me the available operations for the pod 'hello-world-75ddddb654-zmprt'"

##### Run Resource Action
Example prompts:
- "Can you restart the pod 'hello-world-75ddddb654-zmprt'?"
- "I need to execute the restart action on pod 'hello-world-75ddddb654-zmprt'"

##### Get Application Manifest
Example prompts:
- "Show me the manifest for application 'hello-world'"
- "Can you display the current manifest of the 'hello-world' application?"

##### Get Application Parameters
Example prompts:
- "What parameters are configured for the application 'hello-world'?"
- "Show me the current parameters of the 'hello-world' application"
- "I need to see all parameters set for the 'hello-world' application"

> **Note:** Parameter Requirements by Operation:
> 
> 1. **Get Resource Tree**
>    - Required: `application_name`
> 
> 2. **Get Managed Resources**
>    - Required: `application_name`
> 
> 3. **Get Workload Logs**
>    - Required: `application_name`, `resource_name`, `resource_kind`
>    - Optional: 
>      - `namespace`
>      - `tail_lines` (default: 100)
>      - `container`
>      - `since_seconds`
>      - `since_time`
>      - `follow`
> 
> 4. **Get Resource Events**
>    - Required: `application_name`, `resource_name`, `resource_kind`
>    - Optional: `namespace`, `uid`
> 
> 5. **Get Resource Actions**
>    - Required: `application_name`, `resource_name`, `resource_kind`
>    - Optional: `namespace`, `uid`
> 
> 6. **Run Resource Action**
>    - Required: `application_name`, `resource_name`, `resource_kind`, `action_name`
>    - Optional: `namespace`, `uid`, `params`
> 
> 7. **Get Application Manifest**
>    - Required: `application_name`, `revision`
> 
> 8. **Get Application Parameters**
>    - Required: `application_name`

---

For questions or contributions, please open an issue or pull request on the project repository.
