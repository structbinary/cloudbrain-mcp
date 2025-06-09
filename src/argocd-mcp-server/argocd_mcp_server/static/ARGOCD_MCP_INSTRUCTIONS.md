# ArgoCD MCP Server Instructions

MCP server specialized in GitOps application and resource management using ArgoCD. This server provides a unified interface for managing ArgoCD applications and their resources using best practices for GitOps, security, and automation.

## Core Handlers

### 1. ArgoCD Application Handler
Manages ArgoCD applications with a unified interface for all application operations.

#### Tool: `manage_argocd_application`
A unified interface for all application operations with the following capabilities:

##### Operations:
- **create**: Create a new application
  ```python
  manage_argocd_application(
      operation="create",
      name="my-app",
      namespace="argocd",
      project="default",
      repo_url="https://github.com/org/repo.git",
      path="k8s/overlays/production",
      target_revision="v1.2.3",
      destination_server="https://kubernetes.default.svc",
      destination_namespace="production",
      sync_policy="Automated"
  )
  ```

- **update**: Update an existing application
  ```python
  manage_argocd_application(
      operation="update",
      name="my-app",
      repo_url="https://github.com/org/repo.git",
      path="k8s/overlays/production",
      target_revision="v2.0.0",
      destination_server="https://kubernetes.default.svc",
      destination_namespace="production",
      sync_policy="Manual"
  )
  ```

- **delete**: Delete an application
  ```python
  manage_argocd_application(
      operation="delete",
      name="my-app",
      cascade=True
  )
  ```

- **Sync**: Sync an application
  ```python
  manage_argocd_application(
      operation="sync",
      name="my-app"
  )
  ```

- **Get**: Get an application
  ```python
  manage_argocd_application(
      operation="get",
      name="my-app"
  )
  ```


### 2. ArgoCD Resource Handler
Manages ArgoCD application resources with a unified interface for all resource operations.

#### Tool: `manage_argocd_resource`
A unified interface for all resource operations with the following capabilities:

##### Operations:
- **get_resource_tree**: Get application resource tree
  ```python
  manage_argocd_resource(
      operation="get_resource_tree",
      application_name="my-app"
  )
  ```

- **get_managed_resources**: Get managed resources
  ```python
  manage_argocd_resource(
      operation="get_managed_resources",
      application_name="my-app"
  )
  ```

- **get_workload_logs**: Get workload logs
  ```python
  manage_argocd_resource(
      operation="get_workload_logs",
      application_name="my-app",
      resource_name="my-pod",
      resource_kind="Pod",
      tail_lines=100,
      container="main"
  )
  ```

- **get_resource_events**: Get resource events
  ```python
  manage_argocd_resource(
      operation="get_resource_events",
      application_name="my-app",
      resource_name="my-deployment",
      resource_kind="Deployment"
  )
  ```

- **get_resource_actions**: Get resource actions
  ```python
  manage_argocd_resource(
      operation="get_resource_actions",
      application_name="my-app",
      resource_name="my-deployment",
      resource_kind="Deployment"
  )
  ```

- **run_resource_action**: Run resource action
  ```python
  manage_argocd_resource(
      operation="run_resource_action",
      application_name="my-app",
      resource_name="my-deployment",
      resource_kind="Deployment",
      action_name="restart",
      action_params={"force": True}
  )
  ```

- **get_application_manifest**: Get application manifest
  ```python
  manage_argocd_resource(
      operation="get_application_manifest",
      application_name="my-app",
      revision="v1.2.3"
  )
  ```

- **get_application_parameters**: Get application parameters
  ```python
  manage_argocd_resource(
      operation="get_application_parameters",
      application_name="my-app"
  )
  ```

## Security and Configuration

### Authentication
* ArgoCD API token is required
* Can be provided directly or via ARGOCD_TOKEN environment variable
* Server URL can be provided directly or via ARGOCD_SERVER_URL environment variable

### Write Operations
* Write operations require explicit permission via `allow_write=True`
* Write operations include:
  - Application: create, update, delete
  - Resource: run_resource_action

### TLS Configuration
* TLS verification is enabled by default
* Can be bypassed with `bypass_tls=True` for development environments
* Always use proper TLS certificates in production

## Error Handling

### Common Error Types
* Authentication errors (401)
* Permission errors (403)
* Resource not found errors (404)
* Server errors (500)

### Error Response Format
```python
{
    "isError": True,
    "message": "Error message",
    "status_code": 400,
    "resource": "resource-name"
}
```

### Logging
* All operations are logged with:
  - Operation type
  - Request ID
  - User
  - Resource details
  - Error information (if any)

## Best Practices

### When Interacting with This Server

1. **ALWAYS** follow the GitOps workflow from `argocd_workflow_guide`
2. **ALWAYS** consult best practices from `argocd_best_practices` resource
3. **ALWAYS** validate and review application and resource changes before syncing
4. **ALWAYS** use example workflows and templates when available
5. **ALWAYS** check write permissions before attempting write operations
6. **ALWAYS** use proper TLS configuration
7. Provide **secure, declarative, and auditable** configurations by default
8. **Explain** each step of the GitOps process to users
9. **Be specific** about your requirements and constraints
10. **Specify Kubernetes namespace and context** when relevant
11. **Provide context** about your application architecture and deployment goals
12. **Review generated manifests and changes** carefully before applying or syncing
13. **Organize GitOps repos with clear folder hierarchies** (e.g. apps/, environments/, base/overlays/) and consistent naming
14. **Monitor operation states** and handle errors appropriately
15. **Use appropriate sync strategies** based on deployment requirements

### Implementation Best Practices

1. **Authentication**
   * Always provide valid ArgoCD API token
   * Use environment variables for sensitive data
   * Validate token before operations

2. **Write Operations**
   * Explicitly enable write operations when needed
   * Validate permissions before write operations
   * Use cascade delete carefully

3. **Resource Management**
   * Use appropriate resource kind and name
   * Specify container name for multi-container pods
   * Use tail_lines to limit log size
   * Check available actions before running them

4. **Error Handling**
   * Handle all error responses
   * Check operation status
   * Log errors appropriately
   * Provide meaningful error messages

5. **Security**
   * Use TLS in production
   * Follow least privilege principle
   * Validate all inputs
   * Secure token management

6. **Performance**
   * Use appropriate tail_lines for logs
   * Cache responses when possible
   * Handle timeouts appropriately
   * Monitor resource usage 