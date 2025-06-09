from typing import List, Optional, Dict, Any, Union
from argocd_mcp_server.models.application import (
    ApplicationModel,
    CreateApplicationRequest,
    CreateApplicationResponse,
    UpdateApplicationRequest,
    UpdateApplicationResponse,
    DeleteApplicationRequest,
    DeleteApplicationResponse,
    ApplicationMetadata,
    ApplicationSpec,
    ApplicationSource,
    ApplicationDestination,
    SyncPolicy,
    SyncPolicyAutomated,
    ApplicationMetadata,
    ApplicationSpec,
    ApplicationSource,
    ApplicationDestination,
    SyncPolicy,
    ApplicationStatus,
    SyncApplicationResponse,
    SyncApplicationRequest,
    GetApplicationRequest,
    GetApplicationResponse,
)
from argocd_mcp_server.utils.argocd_api_helper import (
    argocd_api_get,
    argocd_api_post,
    argocd_api_put,
    argocd_api_delete,
    argocd_api_post_sync,
)

from argocd_mcp_server.utils.logger import log_tool_execution, log_success, log_error, log_info
import os
import requests
import json
from pydantic import Field

class ArgoCDApplicationHandler:
    """
    Handler class for ArgoCD application operations.
    Provides a unified interface for managing ArgoCD applications.
    """
    def __init__(
        self,
        mcp,
        token: Optional[str] = None,
        server_url: Optional[str] = None,
        allow_write: bool = False,
        bypass_tls: bool = False,
    ):
        """
        Initialize the ArgoCD application handler.
        
        Args:
            mcp: MCP instance
            token (str, optional): ArgoCD API token. If not provided, will be fetched from ARGOCD_TOKEN env var
            server_url (str, optional): ArgoCD server URL. If not provided, will be fetched from ARGOCD_SERVER_URL env var
            allow_write (bool): Whether to allow write operations (default: False)
            bypass_tls (bool): Whether to bypass TLS verification
        """
        self.mcp = mcp
        self.token = token or os.environ.get("ARGOCD_TOKEN")
        self.server_url = server_url or os.environ.get("ARGOCD_SERVER_URL")
        self.allow_write = allow_write
        self.bypass_tls = bypass_tls
        
        if not self.token:
            raise ValueError("ArgoCD API token is required. Please provide it or set ARGOCD_TOKEN environment variable.")
        if not self.server_url:
            raise ValueError("ArgoCD server URL is required. Please provide it or set ARGOCD_SERVER_URL environment variable.")
        
        # Log environment variables for debugging
        log_info(
            "ArgoCD environment variables:",
            tool="argocd_application_handler",
            request_id=self.request_id,
            user=self.user,
            server_url=self.server_url,
            token_length=len(self.token) if self.token else 0,
            token_prefix=self.token[:10] + "..." if self.token and len(self.token) > 10 else None,
            allow_write=allow_write
        )

        # Register tools with MCP
        self._register_tools()

    def _register_tools(self):
        """Register all ArgoCD application tools with MCP."""
        self.mcp.tool(name="manage_argocd_application")(self.manage_application)

    def _check_write_permission(self, operation: str) -> None:
        """
        Check if write operations are allowed.
        
        Args:
            operation (str): The operation being attempted
            
        Raises:
            PermissionError: If write operations are not allowed
        """
        write_operations = ["create", "update", "delete", "sync"]
        if operation in write_operations and not self.allow_write:
            raise PermissionError(
                f"Write operation '{operation}' is not allowed. Set allow_write=True to enable write operations."
            )

    def _handle_api_error(self, e: Exception, operation: str, resource: str = None) -> Dict[str, Any]:
        """
        Handle API errors consistently across all operations.
        
        Args:
            e (Exception): The exception that occurred
            operation (str): The operation that failed
            resource (str, optional): The resource that was being operated on
            
        Returns:
            Dict[str, Any]: Error response with appropriate status and message
        """
        error_msg = str(e)
        if isinstance(e, requests.HTTPError):
            status_code = e.response.status_code
            try:
                error_details = e.response.json()
                error_msg = error_details.get("message", error_msg)
            except:
                pass
        elif isinstance(e, PermissionError):
            status_code = 403
        else:
            status_code = 500

        log_error(
            f"{operation} failed: {error_msg}",
            tool=operation,
            request_id=self.request_id,
            user=self.user,
            error=error_msg,
            resource=resource,
        )

        return {
            "isError": True,
            "message": error_msg,
            "status_code": status_code,
            "resource": resource,
        }

    @property
    def request_id(self) -> str:
        """Get the current request ID from MCP instance."""
        return getattr(self.mcp, 'request_id', 'unknown')

    @property
    def user(self) -> str:
        """Get the current user from MCP instance."""
        return getattr(self.mcp, 'user', 'unknown')

    def _map_application_data(self, data: Dict[str, Any]) -> ApplicationModel:
        """
        Map ArgoCD API response data to ApplicationModel.
        
        Args:
            data (dict): Raw API response data
            
        Returns:
            ApplicationModel: Mapped application model
        """
        try:
            metadata = data.get("metadata", {})
            spec = data.get("spec", {})
            status = data.get("status", {})
            
            # Map source data
            source_data = spec.get("source", {})
            source = ApplicationSource(
                repo_url=source_data.get("repoURL", ""),
                path=source_data.get("path", ""),
                target_revision=source_data.get("targetRevision", "HEAD")
            )

            # Map destination data
            dest_data = spec.get("destination", {})
            destination = ApplicationDestination(
                server=dest_data.get("server", ""),
                namespace=dest_data.get("namespace", "")
            )

            # Map sync policy
            sync_policy_data = spec.get("syncPolicy", {})
            sync_policy = None
            if sync_policy_data.get("automated"):
                sync_policy = SyncPolicy(
                    automated=SyncPolicyAutomated(
                        prune=sync_policy_data["automated"].get("prune", True),
                        self_heal=sync_policy_data["automated"].get("selfHeal", True)
                    )
                )

            # Create the application model
            return ApplicationModel(
                metadata=ApplicationMetadata(
                    name=metadata.get("name"),
                    namespace=metadata.get("namespace", "argocd"),
                    project=metadata.get("project", "default"),
                    labels=metadata.get("labels", {}),
                    annotations=metadata.get("annotations", {})
                ),
                spec=ApplicationSpec(
                    source=source,
                    destination=destination,
                    project=spec.get("project", "default"),
                    sync_policy=sync_policy
                ),
                status=ApplicationStatus(
                    sync_status=status.get("sync", {}).get("status"),
                    health_status=status.get("health", {}).get("status"),
                    conditions=status.get("conditions", [])
                ) if status else None
            )
        except Exception as e:
            log_error(
                "Failed to map application data",
                tool="_map_application_data",
                request_id=self.request_id,
                user=self.user,
                error=str(e),
            )
            raise ValueError(f"Failed to map application data: {str(e)}")

    def safe_json_dumps(self, obj: Any) -> str:
        """Safely convert an object to JSON string, handling recursive structures."""
        try:
            return json.dumps(obj, default=str)
        except Exception:
            return str(obj)

    def format_response(self, data: Any) -> str:
        """Format response data for logging, avoiding recursion issues."""
        if data is None:
            return "None"
        if isinstance(data, dict):
            return f"Dict with keys: {list(data.keys())}"
        if isinstance(data, list):
            return f"List with {len(data)} items"
        return str(data)

    async def manage_application(
        self,
        operation: str = Field(
            ...,
            description="Operation to perform on the application. Valid values: create, update, delete"
        ),
        name: str = Field(
            ...,
            description="Name of the application (required)"
        ),
        project: str = Field(
            ...,
            description="Project name (required)"
        ),
        repo_url: str = Field(
            ...,
            description="Repository URL (required)"
        ),
        path: str = Field(
            ...,
            description="Path in the repository (required)"
        ),
        target_revision: Optional[str] = Field(
            "HEAD",
            description="Target revision (optional, defaults to HEAD)"
        ),
        destination_server: str = Field(
            ...,
            description="Destination server URL (required)"
        ),
        destination_namespace: Optional[str] = Field(
            None,
            description="Destination namespace (optional)"
        ),
        sync_policy: Optional[str] = Field(
            "manual",
            description="Sync policy (manual or automated)"
        ),
        sync_options: Optional[List[str]] = Field(
            None,
            description="List of sync options (e.g., skip schema validation, prune last, etc.)"
        ),
        prune_propagation_policy: Optional[str] = Field(
            "foreground",
            description="Prune propagation policy (foreground, background, or orphan)"
        ),
        finalizer: Optional[bool] = Field(
            False,
            description="Set deletion finalizer"
        ),
        namespace: Optional[str] = Field(
            "argocd",
            description="Application namespace (optional, defaults to argocd)"
        ),
    ) -> Any:
        """Manage ArgoCD applications with various operations.

        This tool provides a unified interface for managing ArgoCD applications, supporting
        all basic CRUD operations. It's designed to handle application lifecycle management,
        configuration updates, and deployment control.

        ## Requirements
        - Valid ArgoCD API token must be configured
        - ArgoCD server must be accessible
        - Proper permissions for the requested operations
        - For create/update operations, valid application configuration
        - For write operations (create, update, delete), allow_write must be True
        - For HTTPS endpoints with self-signed certificates, bypass_tls must be True

        ## Operations
        - **create**: Create a new application with specified configuration
        - **update**: Modify an existing application's configuration
        - **delete**: Remove an application (with optional cascade deletion)
        - **sync**: Sync an application
        - **get**: Get an application

        ## Usage Tips
        - For create operation, ensure all required fields are provided:
          - name, project, repo_url, path, destination_server
        - Optional fields with defaults:
          - namespace (defaults to "argocd")
          - target_revision (defaults to "HEAD")
          - sync_policy (defaults to "manual")
          - prune_propagation_policy (defaults to "foreground")
        - Sync options can be specified for fine-grained control
        - Set allow_write=True for write operations
        - Set bypass_tls=True when using self-signed certificates

        Args:
            operation (str): The operation to perform (create, update, delete, sync, get)
            name (str): Name of the application
            project (str): Project name
            repo_url (str): Repository URL
            path (str): Path in the repository
            target_revision (str, optional): Target revision
            destination_server (str): Destination server URL
            destination_namespace (str, optional): Destination namespace
            sync_policy (str, optional): Sync policy (manual or automated)
            sync_options (List[str], optional): List of sync options
            prune_propagation_policy (str, optional): Prune propagation policy
            finalizer (bool, optional): Set deletion finalizer
            namespace (str, optional): Application namespace

        Returns:
            Response object specific to the operation
        """
        try:
            # Check write permissions for write operations
            self._check_write_permission(operation)

            if operation == "create":
                # Required fields validation
                if not all([name, project, repo_url, path, destination_server]):
                    return CreateApplicationResponse.error(
                        message="Missing required fields: name, project, repo_url, path, and destination_server are required",
                        status_code=400
                    )

                # Construct sync policy
                sync_policy_config = None
                if sync_policy == "automated":
                    sync_policy_config = SyncPolicy(
                        automated=SyncPolicyAutomated(),
                        sync_options=sync_options,
                        prune_propagation_policy=prune_propagation_policy,
                        finalizer=finalizer
                    )
                elif sync_options or prune_propagation_policy or finalizer:
                    sync_policy_config = SyncPolicy(
                        sync_options=sync_options,
                        prune_propagation_policy=prune_propagation_policy,
                        finalizer=finalizer
                    )

                # Create application model
                application_model = ApplicationModel(
                    metadata=ApplicationMetadata(
                        name=name,
                        namespace=namespace,
                        project=project
                    ),
                    spec=ApplicationSpec(
                        source=ApplicationSource(
                            repo_url=repo_url,
                            path=path,
                            target_revision=target_revision
                        ),
                        destination=ApplicationDestination(
                            server=destination_server,
                            namespace=destination_namespace
                        ),
                        project=project,
                        sync_policy=sync_policy_config
                    )
                )

                request = CreateApplicationRequest(
                    application=application_model
                )

                # Log the request details
                log_info(f"Creating application with name: {name}")
                log_info(f"Project: {project}")
                log_info(f"Repository URL: {repo_url}")
                log_info(f"Path: {path}")
                log_info(f"Destination Server: {destination_server}")
                if destination_namespace:
                    log_info(f"Destination Namespace: {destination_namespace}")
                
                # Log the full model dump
                model_dump = request.application.model_dump(exclude_none=True)
                log_info(f"Full request payload: {json.dumps(model_dump, indent=2)}")

                log_tool_execution(
                    "Executing create_application",
                    tool="create_application",
                    request_id=self.request_id,
                    user=self.user,
                    params=model_dump,
                )

                # Convert the request to the format expected by ArgoCD API
                api_data = {
                    "metadata": {
                        "name": name,
                        "namespace": namespace,
                        "project": project
                    },
                    "spec": {
                        "source": {
                            "repoURL": repo_url,
                            "path": path,
                            "targetRevision": target_revision
                        },
                        "destination": {
                            "server": destination_server
                        },
                        "project": project
                    }
                }

                # Add optional destination namespace
                if destination_namespace:
                    api_data["spec"]["destination"]["namespace"] = destination_namespace

                # Add sync policy if configured
                if sync_policy_config:
                    api_data["spec"]["syncPolicy"] = {
                        "automated": sync_policy_config.automated.model_dump() if sync_policy_config.automated else None,
                        "syncOptions": sync_policy_config.sync_options,
                        "prunePropagationPolicy": sync_policy_config.prune_propagation_policy,
                        "finalizer": sync_policy_config.finalizer
                    }

                log_info(f"API request payload: {json.dumps(api_data, indent=2)}")

                data = await argocd_api_post(
                    path="/api/v1/applications",
                    token=self.token,
                    server_url=self.server_url,
                    data=api_data,
                    bypass_tls=self.bypass_tls
                )

                return CreateApplicationResponse.success(
                    application=request.application,
                    message=f"Application {name} created successfully"
                )

            elif operation == "update":
                # Required fields validation
                if not all([name, project, repo_url, path, destination_server]):
                    return UpdateApplicationResponse.error(
                        message="Missing required fields: name, project, repo_url, path, and destination_server are required",
                        status_code=400
                    )

                # Construct sync policy
                sync_policy_config = None
                if sync_policy == "automated":
                    sync_policy_config = SyncPolicy(
                        automated=SyncPolicyAutomated(),
                        sync_options=sync_options,
                        prune_propagation_policy=prune_propagation_policy,
                        finalizer=finalizer
                    )
                elif sync_options or prune_propagation_policy or finalizer:
                    sync_policy_config = SyncPolicy(
                        sync_options=sync_options,
                        prune_propagation_policy=prune_propagation_policy,
                        finalizer=finalizer
                    )

                # Create application model
                application_model = ApplicationModel(
                    metadata=ApplicationMetadata(
                        name=name,
                        namespace=namespace,
                        project=project
                    ),
                    spec=ApplicationSpec(
                        source=ApplicationSource(
                            repo_url=repo_url,
                            path=path,
                            target_revision=target_revision
                        ),
                        destination=ApplicationDestination(
                            server=destination_server,
                            namespace=destination_namespace
                        ),
                        project=project,
                        sync_policy=sync_policy_config
                    )
                )

                request = UpdateApplicationRequest(
                    application=application_model
                )

                log_tool_execution(
                    "Executing update_application",
                    tool="update_application",
                    request_id=self.request_id,
                    user=self.user,
                    params=request.model_dump(exclude_none=True),
                )

                # Convert the request to the format expected by ArgoCD API
                api_data = {
                    "metadata": {
                        "name": name,
                        "namespace": namespace,
                        "project": project
                    },
                    "spec": {
                        "source": {
                            "repoURL": repo_url,
                            "path": path,
                            "targetRevision": target_revision
                        },
                        "destination": {
                            "server": destination_server
                        },
                        "project": project
                    }
                }

                # Add optional destination namespace
                if destination_namespace:
                    api_data["spec"]["destination"]["namespace"] = destination_namespace

                # Add sync policy if configured
                if sync_policy_config:
                    api_data["spec"]["syncPolicy"] = {
                        "automated": sync_policy_config.automated.model_dump() if sync_policy_config.automated else None,
                        "syncOptions": sync_policy_config.sync_options,
                        "prunePropagationPolicy": sync_policy_config.prune_propagation_policy,
                        "finalizer": sync_policy_config.finalizer
                    }

                data = await argocd_api_put(
                    f"/api/v1/applications/{name}",
                    self.token,
                    self.server_url,
                    api_data,
                    bypass_tls=self.bypass_tls
                )

                if data is None:
                    return UpdateApplicationResponse.error(
                        message=f"Application '{name}' not found",
                        status_code=404,
                        resource=name
                    )

                app_model = self._map_application_data(data)

                log_success(
                    f"update_application succeeded for {name}",
                    tool="update_application",
                    request_id=self.request_id,
                    user=self.user,
                    result=app_model.model_dump(),
                )
                return UpdateApplicationResponse.success(
                    application=app_model,
                    message="Application updated successfully."
                )

            elif operation == "delete":
                if not name:
                    return DeleteApplicationResponse.error(
                        message="Application name is required",
                        status_code=400
                    )

                request = DeleteApplicationRequest(
                    name=name,
                    namespace=namespace
                )

                log_tool_execution(
                    "Executing delete_application",
                    tool="delete_application",
                    request_id=self.request_id,
                    user=self.user,
                    params=request.model_dump(),
                )

                data = await argocd_api_delete(
                    f"/api/v1/applications/{name}",
                    self.token,
                    self.server_url,
                    bypass_tls=self.bypass_tls
                    
                )

                log_success(
                    f"delete_application succeeded for {name}",
                    tool="delete_application",
                    request_id=self.request_id,
                    user=self.user,
                    resource=name,
                    result=data.model_dump()
                )
                return DeleteApplicationResponse.success(
                    message="Application deleted successfully."
                )

            elif operation == "sync":
                if not name:
                    return SyncApplicationResponse.error(
                        message="Application name is required",
                        status_code=400
                    )

                request = SyncApplicationRequest(
                    name=name,
                    namespace=namespace
                )

                log_tool_execution(
                    "Executing sync_application",
                    tool="sync_application",
                    request_id=self.request_id,
                    user=self.user,
                    params=request.model_dump(),
                )

                data = await argocd_api_post_sync(
                    f"/api/v1/applications/{name}/sync",
                    self.token,
                    self.server_url,
                    bypass_tls=self.bypass_tls
                )

                log_success(
                    f"sync_application succeeded for {name}",
                    tool="sync_application",
                    request_id=self.request_id,
                    user=self.user,
                    resource=name,
                    result=data.model_dump()
                )
                return SyncApplicationResponse.success(
                    message="Application Synced Successfully."
                )


            elif operation == "get":
                if not name:
                    return GetApplicationResponse.error(
                        message="Application name is required",
                        status_code=400
                    )

                request = GetApplicationRequest(
                    name=name
                )

                log_tool_execution(
                    "Executing get_application",
                    tool="get_application",
                    request_id=self.request_id,
                    user=self.user,
                    params=request.model_dump(),
                )

                data = await argocd_api_get(
                    f"/api/v1/applications/{name}",
                    self.token,
                    self.server_url,
                    bypass_tls=self.bypass_tls
                )

                log_success(
                    f"get_application succeeded for {name}",
                    tool="get_application",
                    request_id=self.request_id,
                    user=self.user,
                    resource=name,
                    result=data.model_dump()
                )
                return GetApplicationResponse.success(
                    message="Application Retrieved Successfully."
                )

            else:
                raise ValueError(f"Invalid operation: {operation}")

        except Exception as e:
            return self._handle_api_error(e, operation, name)

