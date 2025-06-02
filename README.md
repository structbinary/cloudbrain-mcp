# DevOps MCP Servers

A suite of Model Context Protocol (MCP) servers for DevOps tools, enabling AI assistants and automation to interact with modern infrastructure and deployment technologies.

## Table of Contents

- [DevOps MCP Servers](#devops-mcp-servers)
  - [Table of Contents](#table-of-contents)
  - [Available Servers](#available-servers)
    - [Helm MCP Server](#helm-mcp-server)
  - [Installation and Setup](#installation-and-setup)
  - [Contributing](#contributing)
  - [License](#license)

## Available Servers

### Helm MCP Server

[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://hub.docker.com/)
[![Helm](https://img.shields.io/badge/helm-supported-brightgreen)](https://helm.sh/)

A Model Context Protocol (MCP) server for managing Kubernetes workloads via Helm, inspired by EKS MCP and Terraform MCP architectures.

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

[Learn more](src/helm-mcp-server/README.md)

## Installation and Setup

Each server has specific installation instructions. Generally, you can:

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management
2. Install Python 3.10+ (e.g., `uv python install 3.10`)
3. Install any required CLIs (e.g., [Helm CLI](https://helm.sh/docs/intro/install/), [kubectl](https://kubernetes.io/docs/tasks/tools/))
4. Configure access to your infrastructure (e.g., kubeconfig for Kubernetes)
5. Add the server to your MCP client configuration

See each server's detailed README for specific requirements and configuration options.

## Contributing

Contributions are welcome! Please open an issue or pull request on the project repository.

## License

This project is licensed under the Apache-2.0 License.
