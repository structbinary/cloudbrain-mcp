import subprocess
import tempfile
import yaml
import requests
import json
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from helm_mcp_server.models import (
    InstallChartOutput,
    UpgradeReleaseOutput,
    UninstallReleaseOutput,
    ListReleasesOutput, 
    ReleaseInfo,
    SearchRepositoryOutput, 
    ChartSearchResult, 
    ChartMaintainer
)
from pydantic import Field
from typing import Optional, Dict, Any, List
import os
from helm_mcp_server.utils.helm_helper import get_kube_config, is_helm_installed, check_for_dangerous_patterns
from helm_mcp_server.utils.logger import LogLevel, log_with_request_id, logger

class HelmHandler:
    """Handler for Helm operations in the Helm MCP Server."""

    def __init__(self, mcp, allow_write: bool = False):
        """
        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        # Register all Helm tools
        self.mcp.tool(name='install_chart')(self.install_chart)
        self.mcp.tool(name='upgrade_release')(self.upgrade_release)
        self.mcp.tool(name='uninstall_release')(self.uninstall_release)
        self.mcp.tool(name='list_releases')(self.list_releases)
        self.mcp.tool(name='search_repository')(self.search_repository)

    async def install_chart(
        self,
        ctx: Context,
        release_name: str = Field(..., description="Name of the Helm release to create."),
        chart: str = Field(..., description="Chart name (e.g., 'bitnami/nginx')."),
        version: Optional[str] = Field(None, description="Chart version to install."),
        namespace: Optional[str] = Field(None, description="Kubernetes namespace to install the chart into."),
        values: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom values for the chart (will be written to a temp YAML file and passed as -f)."),
        values_files: Optional[List[str]] = Field(default_factory=list, description="List of values YAML files (paths or URLs) to use with -f."),
        values_file_content: Optional[str] = Field(None, description="Raw YAML content to use as a values file (will be written to a temp file and passed as -f)."),
        extra_args: Optional[List[str]] = Field(default_factory=list, description="Extra CLI flags to pass to helm install."),
        repo_url: Optional[str] = Field(None, description="Repository URL to add before install (e.g., https://charts.bitnami.com/bitnami)."),
        create_namespace: Optional[bool] = Field(False, description="Whether to create the namespace if it does not exist."),
        atomic: Optional[bool] = Field(False, description="If set, installation process purges chart on fail. Useful for CI/CD."),
        wait: Optional[bool] = Field(False, description="Wait until all resources are in a ready state before marking the release as successful."),
        timeout: Optional[str] = Field(None, description="Time to wait for any individual Kubernetes operation (e.g., 5m, 1h)."),
        kubeconfig_path: Optional[str] = Field(None, description="Path to kubeconfig file for multi-cluster support."),
        context_name: Optional[str] = Field(None, description="Kubeconfig context name for multi-cluster support."),
        eks_cluster_name: Optional[str] = Field(None, description="AWS EKS cluster name for multi-cluster support."),
    ) -> InstallChartOutput:
        """
        Install a Helm chart as a release on a Kubernetes cluster with full production flexibility.

        This tool supports advanced Helm installation scenarios, including complex values, multiple values files, custom repositories, and extra CLI flags. It is suitable for deploying production-grade charts such as ArgoCD, Prometheus, or any other Helm-based application.

        ## Requirements
        - The server must be run with the `--allow-write` flag to enable mutating operations.
        - The Helm CLI must be installed and available in the server's PATH.
        - The Kubernetes cluster must be accessible from the server environment.

        ## Usage Tips
        - Use the `values` field for custom configuration; it will be written to a temporary YAML file and passed to Helm as `-f`.
        - Use `values_files` to specify one or more YAML files (local paths or URLs) for complex or shared configuration.
        - Set `repo_url` to add a custom Helm repository before installation (e.g., for charts not in the default repos).
        - Use `extra_args` for advanced Helm flags (e.g., `--set-string`, `--set-file`, `--debug`).
        - Enable `atomic` and `wait` for CI/CD pipelines to ensure atomic, reliable deployments.
        - Use `create_namespace` to automatically create the target namespace if it does not exist.
        - Set `timeout` to control how long Helm waits for resources to become ready.

        ## Arguments
        - ctx: MCP context (provided by the server)
        - release_name: Name of the Helm release to create
        - chart: Chart name (e.g., 'bitnami/nginx' or 'argo/argo-cd')
        - version: Chart version to install (optional)
        - namespace: Kubernetes namespace to install the chart into (optional)
        - values: Custom values as a dict (optional, written to a temp YAML file and passed as -f)
        - values_files: List of values YAML files (paths or URLs) to use with -f (optional)
        - values_file_content: Raw YAML content to use as a values file (optional)
        - extra_args: List of extra CLI flags to pass to helm install (optional)
        - repo_url: Repository URL to add before install (optional)
        - create_namespace: Whether to create the namespace if it does not exist (optional)
        - atomic: If set, installation process purges chart on fail (optional)
        - wait: Wait until all resources are ready before marking the release as successful (optional)
        - timeout: Time to wait for any individual Kubernetes operation (e.g., '5m', '1h') (optional)
        - kubeconfig_path: Path to kubeconfig file for multi-cluster support (optional)
        - context_name: Kubeconfig context name for multi-cluster support (optional)
        - eks_cluster_name: AWS EKS cluster name for multi-cluster support (optional)

        ## Response Information
        - Returns an InstallChartOutput with:
            - isError: True if the operation failed, False otherwise
            - content: List of TextContent messages (stdout/stderr from Helm)
            - release_name: Name of the Helm release
            - status: 'deployed' on success, 'error' on failure
            - notes: Helm output or error message
            - details: Additional details, including the Helm command and repo status

        Multi-cluster support:
        - Use `kubeconfig_path`, `context_name`, or `eks_cluster_name` to select the target cluster.
        """
        logger.info("install_chart called", extra={
            "operation": "install_chart",
            "release_name": release_name,
            "chart": chart,
            "version": version,
            "namespace": namespace,
            "repo_url": repo_url,
            "create_namespace": create_namespace,
            "atomic": atomic,
            "wait": wait,
            "timeout": timeout
        })
        if not self.allow_write:
            msg = "Helm install is not allowed without write access."
            log_with_request_id(ctx, LogLevel.ERROR, msg)
            return InstallChartOutput(
                isError=True,
                content=[TextContent(type='text', text=msg)],
                release_name=release_name,
                status="error",
                notes=msg,
                details=None,
            )

        # Pre-check: is helm installed?
        if not is_helm_installed():
            msg = "Helm binary is not installed or not found in PATH."
            log_with_request_id(ctx, LogLevel.ERROR, msg)
            return InstallChartOutput(
                isError=True,
                content=[TextContent(type='text', text=msg)],
                release_name=release_name,
                status="error",
                notes=msg,
                details=None,
            )

        # Optionally add repo
        repo_name = chart.split("/")[0] if "/" in chart else chart
        repo_added = False
        if repo_url:
            try:
                subprocess.run(["helm", "repo", "add", repo_name, repo_url], check=True, capture_output=True, text=True)
                subprocess.run(["helm", "repo", "update"], check=True, capture_output=True, text=True)
                repo_added = True
            except Exception as e:
                msg = f"Failed to add/update repo: {e}"
                log_with_request_id(ctx, LogLevel.ERROR, msg)
                return InstallChartOutput(
                    isError=True,
                    content=[TextContent(type='text', text=msg)],
                    release_name=release_name,
                    status="error",
                    notes=msg,
                    details=None,
                )

        # Build the helm install command
        cmd = ["helm", "install", release_name, chart]
        if version:
            cmd += ["--version", version]
        if namespace:
            cmd += ["--namespace", namespace]
        if create_namespace:
            cmd += ["--create-namespace"]
        if atomic:
            cmd += ["--atomic"]
        if wait:
            cmd += ["--wait"]
        if timeout:
            cmd += ["--timeout", timeout]
        temp_files = []
        try:
            # Handle raw YAML content as a temp file
            if values_file_content:
                with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".yaml") as f:
                    f.write(values_file_content)
                    temp_files.append(f.name)
                    cmd += ["-f", f.name]
            # Handle values dict as a temp YAML file
            if values:
                with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".yaml") as f:
                    yaml.dump(values, f)
                    temp_files.append(f.name)
                    cmd += ["-f", f.name]
            # Add any values files
            if values_files:
                for vf in values_files:
                    cmd += ["-f", vf]
            # Add extra CLI args
            if extra_args:
                cmd += extra_args

            # Pre-check: dangerous patterns
            pattern = check_for_dangerous_patterns(cmd, log_prefix=f"[install_chart][{release_name}] ")
            if pattern:
                msg = f"Dangerous pattern detected in command arguments: '{pattern}'. Aborting install for safety."
                log_with_request_id(ctx, LogLevel.ERROR, msg)
                return InstallChartOutput(
                    isError=True,
                    content=[TextContent(type='text', text=msg)],
                    release_name=release_name,
                    status="error",
                    notes=msg,
                    details={"cmd": " ".join(cmd), "repo_added": repo_added},
                )

            kube_config = get_kube_config(kubeconfig_path=kubeconfig_path, context_name=context_name, eks_cluster_name=eks_cluster_name)
            log_with_request_id(ctx, LogLevel.INFO, f"Running helm install: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            notes = result.stdout
            status = "deployed"
            isError = False
            log_with_request_id(ctx, LogLevel.INFO, f"Helm install succeeded for release {release_name}")
        except subprocess.CalledProcessError as e:
            notes = e.stderr
            status = "error"
            isError = True
            log_with_request_id(ctx, LogLevel.ERROR, f"Helm install failed for release {release_name}: {notes}")
        finally:
            # Clean up temp files
            for tf in temp_files:
                try:
                    os.remove(tf)
                except Exception:
                    pass
        return InstallChartOutput(
            isError=isError,
            content=[TextContent(type='text', text=notes)],
            release_name=release_name,
            status=status,
            notes=notes,
            details={"cmd": " ".join(cmd), "repo_added": repo_added},
        )

    async def upgrade_release(
        self,
        ctx: Context,
        release_name: str = Field(..., description="Name of the Helm release to upgrade."),
        chart: Optional[str] = Field(None, description="Chart name if upgrading to a new chart."),
        version: Optional[str] = Field(None, description="Chart version to upgrade to."),
        namespace: Optional[str] = Field(None, description="Kubernetes namespace of the release."),
        values: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom values for the upgrade (will be written to a temp YAML file and passed as -f)."),
        values_files: Optional[List[str]] = Field(default_factory=list, description="List of values YAML files (paths or URLs) to use with -f."),
        values_file_content: Optional[str] = Field(None, description="Raw YAML content to use as a values file (will be written to a temp file and passed as -f)."),
        extra_args: Optional[List[str]] = Field(default_factory=list, description="Extra CLI flags to pass to helm upgrade."),
        repo_url: Optional[str] = Field(None, description="Repository URL to add before upgrade (e.g., https://charts.bitnami.com/bitnami)."),
        atomic: Optional[bool] = Field(False, description="If set, upgrade process purges chart on fail. Useful for CI/CD."),
        wait: Optional[bool] = Field(False, description="Wait until all resources are in a ready state before marking the release as successful."),
        timeout: Optional[str] = Field(None, description="Time to wait for any individual Kubernetes operation (e.g., 5m, 1h)."),
        kubeconfig_path: Optional[str] = Field(None, description="Path to kubeconfig file for multi-cluster support."),
        context_name: Optional[str] = Field(None, description="Kubeconfig context name for multi-cluster support."),
        eks_cluster_name: Optional[str] = Field(None, description="AWS EKS cluster name for multi-cluster support."),
    ) -> UpgradeReleaseOutput:
        """
        Upgrade a Helm release on a Kubernetes cluster with full production flexibility.

        This tool supports advanced Helm upgrade scenarios, including complex values, multiple values files, custom repositories, and extra CLI flags. It is suitable for upgrading production-grade charts such as ArgoCD, Prometheus, or any other Helm-based application.

        ## Requirements
        - The server must be run with the `--allow-write` flag to enable mutating operations.
        - The Helm CLI must be installed and available in the server's PATH.
        - The Kubernetes cluster must be accessible from the server environment.

        ## Usage Tips
        - Use the `values` field for custom configuration; it will be written to a temporary YAML file and passed to Helm as `-f`.
        - Use `values_files` to specify one or more YAML files (local paths or URLs) for complex or shared configuration.
        - Set `repo_url` to add a custom Helm repository before upgrade (e.g., for charts not in the default repos).
        - Use `extra_args` for advanced Helm flags (e.g., `--set-string`, `--set-file`, `--debug`).
        - Enable `atomic` and `wait` for CI/CD pipelines to ensure atomic, reliable upgrades.
        - Set `timeout` to control how long Helm waits for resources to become ready.

        ## Arguments
        - ctx: MCP context (provided by the server)
        - release_name: Name of the Helm release to upgrade
        - chart: Chart name if upgrading to a new chart (optional)
        - version: Chart version to upgrade to (optional)
        - namespace: Kubernetes namespace of the release (optional)
        - values: Custom values as a dict (optional, written to a temp YAML file and passed as -f)
        - values_files: List of values YAML files (paths or URLs) to use with -f (optional)
        - values_file_content: Raw YAML content to use as a values file (optional)
        - extra_args: List of extra CLI flags to pass to helm upgrade (optional)
        - repo_url: Repository URL to add before upgrade (optional)
        - atomic: If set, upgrade process purges chart on fail (optional)
        - wait: Wait until all resources are ready before marking the release as successful (optional)
        - timeout: Time to wait for any individual Kubernetes operation (e.g., '5m', '1h') (optional)
        - kubeconfig_path: Path to kubeconfig file for multi-cluster support (optional)
        - context_name: Kubeconfig context name for multi-cluster support (optional)
        - eks_cluster_name: AWS EKS cluster name for multi-cluster support (optional)

        ## Response Information
        - Returns an UpgradeReleaseOutput with:
            - isError: True if the operation failed, False otherwise
            - content: List of TextContent messages (stdout/stderr from Helm)
            - release_name: Name of the Helm release
            - status: 'upgraded' on success, 'error' on failure
            - notes: Helm output or error message
            - details: Additional details, including the Helm command and repo status

        Multi-cluster support:
        - Use `kubeconfig_path`, `context_name`, or `eks_cluster_name` to select the target cluster.
        """
        logger.info("upgrade_release called", extra={
            "operation": "upgrade_release",
            "release_name": release_name,
            "chart": chart,
            "version": version,
            "namespace": namespace,
            "repo_url": repo_url,
            "atomic": atomic,
            "wait": wait,
            "timeout": timeout
        })
        if not self.allow_write:
            msg = "Helm upgrade is not allowed without write access."
            log_with_request_id(ctx, LogLevel.ERROR, msg)
            return UpgradeReleaseOutput(
                isError=True,
                content=[TextContent(type='text', text=msg)],
                release_name=release_name,
                status="error",
                notes=msg,
                details=None,
            )

        # Pre-check: is helm installed?
        if not is_helm_installed():
            msg = "Helm binary is not installed or not found in PATH."
            log_with_request_id(ctx, LogLevel.ERROR, msg)
            return UpgradeReleaseOutput(
                isError=True,
                content=[TextContent(type='text', text=msg)],
                release_name=release_name,
                status="error",
                notes=msg,
                details=None,
            )

        repo_name = chart.split("/")[0] if chart and "/" in chart else (chart or release_name)
        repo_added = False
        if repo_url and chart:
            try:
                subprocess.run(["helm", "repo", "add", repo_name, repo_url], check=True, capture_output=True, text=True)
                subprocess.run(["helm", "repo", "update"], check=True, capture_output=True, text=True)
                repo_added = True
            except Exception as e:
                msg = f"Failed to add/update repo: {e}"
                log_with_request_id(ctx, LogLevel.ERROR, msg)
                return UpgradeReleaseOutput(
                    isError=True,
                    content=[TextContent(type='text', text=msg)],
                    release_name=release_name,
                    status="error",
                    notes=msg,
                    details=None,
                )

        cmd = ["helm", "upgrade", release_name]
        if chart:
            cmd.append(chart)
        if version:
            cmd += ["--version", version]
        if namespace:
            cmd += ["--namespace", namespace]
        if atomic:
            cmd += ["--atomic"]
        if wait:
            cmd += ["--wait"]
        if timeout:
            cmd += ["--timeout", timeout]
        temp_files = []
        try:
            # Handle raw YAML content as a temp file
            if values_file_content:
                with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".yaml") as f:
                    f.write(values_file_content)
                    temp_files.append(f.name)
                    cmd += ["-f", f.name]
            # Handle values dict as a temp YAML file
            if values:
                with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".yaml") as f:
                    yaml.dump(values, f)
                    temp_files.append(f.name)
                    cmd += ["-f", f.name]
            # Add any values files
            if values_files:
                for vf in values_files:
                    cmd += ["-f", vf]
            # Add extra CLI args
            if extra_args:
                cmd += extra_args

            # Pre-check: dangerous patterns
            pattern = check_for_dangerous_patterns(cmd, log_prefix=f"[upgrade_release][{release_name}] ")
            if pattern:
                msg = f"Dangerous pattern detected in command arguments: '{pattern}'. Aborting upgrade for safety."
                log_with_request_id(ctx, LogLevel.ERROR, msg)
                return UpgradeReleaseOutput(
                    isError=True,
                    content=[TextContent(type='text', text=msg)],
                    release_name=release_name,
                    status="error",
                    notes=msg,
                    details={"cmd": " ".join(cmd), "repo_added": repo_added},
                )

            kube_config = get_kube_config(kubeconfig_path=kubeconfig_path, context_name=context_name, eks_cluster_name=eks_cluster_name)
            log_with_request_id(ctx, LogLevel.INFO, f"Running helm upgrade: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            notes = result.stdout
            status = "upgraded"
            isError = False
            log_with_request_id(ctx, LogLevel.INFO, f"Helm upgrade succeeded for release {release_name}")
        except subprocess.CalledProcessError as e:
            notes = e.stderr
            status = "error"
            isError = True
            log_with_request_id(ctx, LogLevel.ERROR, f"Helm upgrade failed for release {release_name}: {notes}")
        finally:
            for tf in temp_files:
                try:
                    os.remove(tf)
                except Exception:
                    pass
        return UpgradeReleaseOutput(
            isError=isError,
            content=[TextContent(type='text', text=notes)],
            release_name=release_name,
            status=status,
            notes=notes,
            details={"cmd": " ".join(cmd), "repo_added": repo_added},
        )

    async def uninstall_release(
        self,
        ctx: Context,
        release_name: str = Field(..., description="Name of the Helm release to uninstall."),
        namespace: Optional[str] = Field(None, description="Namespace of the release."),
        keep_history: Optional[bool] = Field(False, description="Whether to keep release history."),
        kubeconfig_path: Optional[str] = Field(None, description="Path to kubeconfig file for multi-cluster support."),
        context_name: Optional[str] = Field(None, description="Kubeconfig context name for multi-cluster support."),
        eks_cluster_name: Optional[str] = Field(None, description="AWS EKS cluster name for multi-cluster support."),
    ) -> UninstallReleaseOutput:
        """
        Uninstall a Helm release from the Kubernetes cluster with optional history retention.

        This tool removes a Helm release and its associated resources from the cluster. You can optionally retain the release history for future reference or auditing.

        ## Requirements
        - The server must be run with the `--allow-write` flag to enable mutating operations.
        - The Helm CLI must be installed and available in the server's PATH.
        - The Kubernetes cluster must be accessible from the server environment.

        ## Usage Tips
        - Use the `namespace` argument to specify the namespace of the release (recommended for clarity).
        - Set `keep_history` to retain the release history after uninstall (useful for auditing or troubleshooting).
        - The output provides details on the uninstall operation, including command and status.

        ## Arguments
        - ctx: MCP context (provided by the server)
        - release_name: Name of the Helm release to uninstall
        - namespace: Namespace of the release (optional)
        - keep_history: Whether to keep release history (optional)
        - kubeconfig_path: Path to kubeconfig file for multi-cluster support (optional)
        - context_name: Kubeconfig context name for multi-cluster support (optional)
        - eks_cluster_name: AWS EKS cluster name for multi-cluster support (optional)

        ## Response Information
        - Returns an UninstallReleaseOutput with:
            - isError: True if the operation failed, False otherwise
            - content: List of TextContent messages (stdout/stderr from Helm)
            - release_name: Name of the Helm release
            - status: 'uninstalled' on success, 'error' on failure
            - details: Additional details, including the Helm command

        Multi-cluster support:
        - Use `kubeconfig_path`, `context_name`, or `eks_cluster_name` to select the target cluster.
        """
        logger.info("uninstall_release called", extra={
            "operation": "uninstall_release",
            "release_name": release_name,
            "namespace": namespace,
            "keep_history": keep_history
        })
        if not self.allow_write:
            msg = "Helm uninstall is not allowed without write access."
            log_with_request_id(ctx, LogLevel.ERROR, msg)
            return UninstallReleaseOutput(
                isError=True,
                content=[TextContent(type='text', text=msg)],
                release_name=release_name,
                status="error",
                details=None,
            )

        # Pre-check: is helm installed?
        if not is_helm_installed():
            msg = "Helm binary is not installed or not found in PATH."
            log_with_request_id(ctx, LogLevel.ERROR, msg)
            return UninstallReleaseOutput(
                isError=True,
                content=[TextContent(type='text', text=msg)],
                release_name=release_name,
                status="error",
                details=None,
            )

        cmd = ["helm", "uninstall", release_name]
        if namespace:
            cmd += ["--namespace", namespace]
        if keep_history:
            cmd += ["--keep-history"]

        # Pre-check: dangerous patterns
        pattern = check_for_dangerous_patterns(cmd, log_prefix=f"[uninstall_release][{release_name}] ")
        if pattern:
            msg = f"Dangerous pattern detected in command arguments: '{pattern}'. Aborting uninstall for safety."
            log_with_request_id(ctx, LogLevel.ERROR, msg)
            return UninstallReleaseOutput(
                isError=True,
                content=[TextContent(type='text', text=msg)],
                release_name=release_name,
                status="error",
                details={"cmd": " ".join(cmd)},
            )

        try:
            kube_config = get_kube_config(kubeconfig_path=kubeconfig_path, context_name=context_name, eks_cluster_name=eks_cluster_name)
            log_with_request_id(ctx, LogLevel.INFO, f"Running helm uninstall: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            notes = result.stdout
            status = "uninstalled"
            isError = False
            log_with_request_id(ctx, LogLevel.INFO, f"Helm uninstall succeeded for release {release_name}")
        except subprocess.CalledProcessError as e:
            notes = e.stderr
            status = "error"
            isError = True
            log_with_request_id(ctx, LogLevel.ERROR, f"Helm uninstall failed for release {release_name}: {notes}")
        return UninstallReleaseOutput(
            isError=isError,
            content=[TextContent(type='text', text=notes)],
            release_name=release_name,
            status=status,
            details={"cmd": " ".join(cmd)},
        )

    async def list_releases(
        self,
        ctx: Context,
        namespace: Optional[str] = Field(None, description="Namespace to list releases from."),
        kubeconfig_path: Optional[str] = Field(None, description="Path to kubeconfig file for multi-cluster support."),
        context_name: Optional[str] = Field(None, description="Kubeconfig context name for multi-cluster support."),
        eks_cluster_name: Optional[str] = Field(None, description="AWS EKS cluster name for multi-cluster support."),
    ) -> ListReleasesOutput:
        """
        List Helm releases in the Kubernetes cluster with optional namespace filtering.

        This tool retrieves all Helm releases currently deployed in the cluster, optionally filtered by namespace. It returns structured information for each release, including name, chart, version, namespace, and status.

        ## Requirements
        - The Helm CLI must be installed and available in the server's PATH.
        - The Kubernetes cluster must be accessible from the server environment.

        ## Usage Tips
        - Use the `namespace` argument to filter releases by a specific Kubernetes namespace.
        - If no namespace is provided, releases from all namespaces will be listed (subject to Helm/Kubernetes permissions).
        - The output includes detailed information for each release, suitable for automation or reporting.

        ## Arguments
        - ctx: MCP context (provided by the server)
        - namespace: Namespace to list releases from (optional)
        - kubeconfig_path: Path to kubeconfig file for multi-cluster support (optional)
        - context_name: Kubeconfig context name for multi-cluster support (optional)
        - eks_cluster_name: AWS EKS cluster name for multi-cluster support (optional)

        ## Response Information
        - Returns a ListReleasesOutput with:
            - isError: True if the operation failed, False otherwise
            - content: List of TextContent messages (summary or error)
            - count: Number of releases found
            - releases: List of ReleaseInfo objects (name, chart, version, namespace, status)

        Multi-cluster support:
        - Use `kubeconfig_path`, `context_name`, or `eks_cluster_name` to select the target cluster.
        """
        logger.info("list_releases called", extra={
            "operation": "list_releases",
            "namespace": namespace
        })
        cmd = ["helm", "list", "--output", "json"]
        if namespace:
            cmd += ["--namespace", namespace]
        try:
            kube_config = get_kube_config(kubeconfig_path=kubeconfig_path, context_name=context_name, eks_cluster_name=eks_cluster_name)
            log_with_request_id(ctx, LogLevel.INFO, f"Running helm list: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            releases_json = json.loads(result.stdout)
            releases = [
                ReleaseInfo(
                    release_name=item["name"],
                    chart=item["chart"],
                    version=item.get("app_version", ""),
                    namespace=item.get("namespace", "default"),
                    status=item.get("status", "unknown"),
                )
                for item in releases_json
            ]
            isError = False
            notes = f"Found {len(releases)} releases." if releases else "No releases found."
            log_with_request_id(ctx, LogLevel.INFO, notes)
        except Exception as e:
            releases = []
            isError = True
            notes = f"Failed to list releases: {e}"
            log_with_request_id(ctx, LogLevel.ERROR, notes)
        return ListReleasesOutput(
            isError=isError,
            content=[TextContent(type='text', text=notes)],
            count=len(releases),
            releases=releases,
        )

    async def search_repository(
        self,
        ctx: Context,
        query: str = Field(..., description="Search term for the chart."),
        repository_url: Optional[str] = Field(None, description="URL of the Helm repository to search (e.g., ArtifactHub, GitHub)."),
        max_results: Optional[int] = Field(20, description="Max number of results to return."),
        kubeconfig_path: Optional[str] = Field(None, description="Path to kubeconfig file for multi-cluster support."),
        context_name: Optional[str] = Field(None, description="Kubeconfig context name for multi-cluster support."),
        eks_cluster_name: Optional[str] = Field(None, description="AWS EKS cluster name for multi-cluster support."),
    ) -> SearchRepositoryOutput:
        """
        Search for Helm charts in ArtifactHub or a user-provided repository, returning rich metadata for each chart.

        This tool supports advanced Helm chart discovery, including ArtifactHub API integration for public charts and flexible fallback to helm CLI search for custom repositories. Results include maintainers, keywords, home/docs links, icon, license, sources, category, app version, CRDs, screenshots, and more.

        ## Requirements
        - The Helm CLI must be installed and available in the server's PATH (for custom repo search).
        - Internet access is required for ArtifactHub API queries.

        ## Usage Tips
        - Use the `query` field to search for charts by name, keyword, or description.
        - By default, searches ArtifactHub (https://artifacthub.io) for public charts.
        - Set `repository_url` to search a specific Helm repo using the helm CLI (less metadata).
        - Use `max_results` to limit the number of results returned.

        ## Arguments
        - ctx: MCP context (provided by the server)
        - query: Search term for the chart
        - repository_url: URL of the Helm repository to search (optional)
        - max_results: Maximum number of results to return (optional)
        - kubeconfig_path: Path to kubeconfig file for multi-cluster support (optional)
        - context_name: Kubeconfig context name for multi-cluster support (optional)
        - eks_cluster_name: AWS EKS cluster name for multi-cluster support (optional)

        ## Response Information
        - Returns a SearchRepositoryOutput with:
            - isError: True if the operation failed, False otherwise
            - content: List of TextContent messages (summary or error)
            - count: Number of charts found
            - results: List of ChartSearchResult objects (rich chart metadata)

        Multi-cluster support:
        - Use `kubeconfig_path`, `context_name`, or `eks_cluster_name` to select the target cluster.
        """
        logger.info("search_repository called", extra={
            "operation": "search_repository",
            "query": query,
            "repository_url": repository_url,
            "max_results": max_results
        })
        results = []
        notes = ""
        isError = False
        try:
            if not repository_url:
                # ArtifactHub API search
                ah_api = "https://artifacthub.io/api/v1/packages/search"
                params = {
                    "kind": 0,  # 0 = Helm chart
                    "limit": max_results,
                    "offset": 0,
                    "q": query,
                }
                resp = requests.get(ah_api, params=params, timeout=8)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("packages", []):
                    # Log the raw item for debugging
                    logger.debug(f"ArtifactHub item: {json.dumps(item, indent=2)}")
                    # Fetch README if possible
                    readme = None
                    repo_name = item.get('repository', {}).get('name')
                    chart_name = item.get('name')
                    if repo_name and chart_name:
                        try:
                            readme_url = f"https://artifacthub.io/api/v1/packages/helm/{repo_name}/{chart_name}/readme"
                            readme_resp = requests.get(readme_url, timeout=5)
                            if readme_resp.status_code == 200:
                                readme = readme_resp.text
                                if len(readme) > 8000:
                                    readme = readme[:8000] + "...\n[README truncated due to length]"
                        except Exception as e:
                            logger.warning(f"Failed to fetch README for {repo_name}/{chart_name}: {e}")
                            readme = None
                    # Parse maintainers
                    maintainers = [
                        ChartMaintainer(
                            name=m.get("name", ""),
                            email=m.get("email"),
                            url=m.get("url"),
                        ) for m in item.get("maintainers", [])
                    ]
                    # Parse screenshots
                    screenshots = item.get("screenshots", []) or []
                    # Parse links
                    links = item.get("links", []) or []
                    # Parse CRDs
                    crds = item.get("crds", []) or []
                    # Parse keywords
                    keywords = item.get("keywords", []) or []
                    # Parse sources
                    sources = item.get("sources", []) or []
                    # Ensure category is a string or None
                    category = item.get("category")
                    if category is not None and not isinstance(category, str):
                        category = str(category)
                    # Fallback for home and icon fields
                    home = item.get("home_url") or item.get("home") or None
                    icon = item.get("logo_url") or item.get("icon_url") or item.get("icon") or None
                    # Compose result
                    results.append(ChartSearchResult(
                        name=item.get("name", ""),
                        description=item.get("description"),
                        version=item.get("version"),
                        repository=item.get("repository", {}).get("url"),
                        url=f"https://artifacthub.io/packages/helm/{item.get('repository', {}).get('name','')}/{item.get('name','')}",
                        home=home,
                        icon=icon,
                        keywords=keywords,
                        maintainers=maintainers,
                        license=item.get("license"),
                        sources=sources,
                        category=category,
                        app_version=item.get("app_version"),
                        readme=readme,
                        crds=crds,
                        screenshots=screenshots,
                        links=links,
                        operator=item.get("operator", False),
                        category_prediction=item.get("category_prediction"),
                    ))
                notes = f"Found {len(results)} charts from ArtifactHub."
            else:
                # Fallback: helm CLI search for custom repo
                if not is_helm_installed():
                    raise RuntimeError("Helm binary is not installed or not found in PATH.")
                # If repository_url is provided, add the repo first
                if repository_url:
                    repo_name = query.split('/')[0] if '/' in query else 'customrepo'
                    try:
                        subprocess.run(["helm", "repo", "add", repo_name, repository_url], check=True, capture_output=True, text=True)
                        subprocess.run(["helm", "repo", "update"], check=True, capture_output=True, text=True)
                    except Exception as e:
                        logger.error(f"Failed to add/update repo for search: {e}", extra={"operation": "search_repository", "repo_name": repo_name, "repository_url": repository_url})
                        raise RuntimeError(f"Failed to add/update repo: {e}")
                cmd = ["helm", "search", "repo", query, "--output", "json"]
                pattern = check_for_dangerous_patterns(cmd, log_prefix=f"[search_repository][query={query}] ")
                if pattern:
                    raise RuntimeError(f"Dangerous pattern detected in command arguments: '{pattern}'. Aborting search for safety.")
                # Do NOT call get_kube_config() here for helm search repo
                log_with_request_id(ctx, LogLevel.INFO, f"Running helm search repo: {' '.join(cmd)}")
                proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
                charts_json = json.loads(proc.stdout)
                for item in charts_json[:max_results]:
                    results.append(ChartSearchResult(
                        name=item["name"],
                        description=item.get("description", ""),
                        version=item.get("version", ""),
                        repository=repository_url,
                        url=item.get("urls", [None])[0],
                        home=item.get("home", None),
                        icon=item.get("icon", None),
                        keywords=item.get("keywords", []),
                        maintainers=[],  # Not available from helm CLI
                        license=item.get("license", None),
                        sources=item.get("sources", []),
                        category=None,
                        app_version=item.get("app_version", None),
                        readme=None,
                        crds=[],
                        screenshots=[],
                        links=[],
                        operator=None,
                        category_prediction=None,
                    ))
                notes = f"Found {len(results)} charts from custom repo." if results else "No charts found in custom repo."
            isError = False
            log_with_request_id(ctx, LogLevel.INFO, notes)
        except Exception as e:
            results = []
            isError = True
            notes = f"Failed to search charts: {e}"
            log_with_request_id(ctx, LogLevel.ERROR, notes)
        return SearchRepositoryOutput(
            isError=isError,
            content=[TextContent(type='text', text=notes)],
            count=len(results),
            results=results,
        ) 