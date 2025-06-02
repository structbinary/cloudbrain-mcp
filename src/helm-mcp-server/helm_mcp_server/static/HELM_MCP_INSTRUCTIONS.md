# Helm MCP Server Instructions

MCP server specialized in Kubernetes workload management via Helm. This server helps you install, upgrade, list, uninstall, and search Helm charts across clusters, following security-focused and production-grade best practices.

## How to Use This Server (Required Workflow)

### Step 1: Consult and Follow the Helm Development Workflow
ALWAYS use the `helm://workflow_guide` resource to guide your Helm operations. This workflow:

* Provides a step-by-step approach for secure, reliable Helm deployments
* Integrates validation and best practices into the deployment process
* Specifies when and how to use each MCP tool
* Ensures releases are properly validated before handoff to developers or production

### Step 2: Always ensure you're following Helm Best Practices
ALWAYS begin by consulting the `helm://best_practices` resource which contains:

* Chart structure and organization principles
* Security best practices for Kubernetes workloads
* Values file management and secret handling
* Helm-specific implementation guidance

### Step 3: Search for Official or Trusted Charts First
ALWAYS search for official or trusted charts using the `search_repository` tool:

* ArtifactHub and other public sources are supported
* Prefer official charts for common workloads (e.g., nginx, prometheus)
* Review chart maintainers, source, and metadata before installation

### Step 4: Use the Right Cluster Context
When deploying or managing releases:

* Specify the correct kubeconfig path, context, or EKS cluster name
* Use namespace scoping to avoid conflicts
* Validate cluster access and permissions before running operations

## Available Tools and Resources

### Core Resources
1. `helm://workflow_guide`
   * CRITICAL: Follow this guide for all Helm operations
   * Provides a structured workflow for secure, reliable deployments
   * Outlines exactly when and how to use each MCP tool
2. `helm://best_practices`
   * REQUIRED: Reference before starting any Helm deployment
   * Contains Helm-specific best practices for security and architecture
   * Guides organization and structure of Helm charts and values

### Chart and Repository Tools
1. `search_repository`
   * Search ArtifactHub and other sources for Helm charts
   * Returns chart metadata, maintainers, keywords, and documentation
2. `install_chart`
   * Install a Helm chart with custom values, repo, and namespace
   * Supports multiple values files and extra CLI flags
3. `upgrade_release`
   * Upgrade an existing Helm release with new values or chart version
4. `list_releases`
   * List all Helm releases in a namespace or cluster
5. `uninstall_release`
   * Uninstall a Helm release from a namespace

### Command Execution Tools

- All Helm operations are available as MCP tools:
  - `install_chart`, `upgrade_release`, `list_releases`, `uninstall_release`, `search_repository`
- Each tool supports advanced options (values, files, flags, context switching)
- Logging and error reporting are integrated for all operations

## Resource Selection Priority

1. FIRST search for official or trusted charts using `search_repository`
2. THEN review chart metadata and documentation before installation
3. ONLY install charts after validating best practices and workflow steps

Official and trusted charts offer:
* Maintained, secure, and well-documented deployments
* Consistent upgrade and rollback support
* Community and vendor support for common workloads

## Examples

- "Search for nginx charts on ArtifactHub"
- "Install the prometheus-community/kube-prometheus-stack chart in the monitoring namespace"
- "Upgrade the my-app release to the latest chart version with new values"
- "List all Helm releases in the dev namespace"
- "Uninstall the test-release from the staging cluster"
- "Switch to the production cluster context and list all releases"
- "What are the official charts for ingress controllers?"
- "Provide a step-by-step workflow for deploying a new application with Helm"

## Best Practices

When interacting with this server:

1. **ALWAYS** follow the development workflow from `helm://workflow_guide`
2. **ALWAYS** consult best practices from `helm://best_practices`
3. **ALWAYS** validate chart sources and review maintainers/metadata
4. **ALWAYS** use namespace scoping and RBAC for production workloads
5. **ALWAYS** manage secrets securely (avoid plaintext in values files)
6. **ALWAYS** review and test values overrides before applying to production
7. **ALWAYS** use version pinning for critical workloads
8. **ALWAYS** document release names, namespaces, and chart versions
9. **ALWAYS** review logs and error reports after each operation
10. **ALWAYS** keep Helm, kubectl, and dependencies up to date
11. **Explain** each step of the deployment process to users
12. **Be specific** about your requirements and constraints
13. **Provide context** about your cluster, namespace, and use case
14. **Review generated manifests** carefully before applying changes
15. **Organize charts and values files** with clear folder hierarchies and naming

---

For more details, consult the `helm://workflow_guide` and `helm://best_practices` resources, or open an issue in the project repository. 