from typing import List, Optional, Dict, Any, Union
from argocd_mcp_server.utils.logger import log_tool_execution, log_success, log_error, log_info
from argocd_mcp_server.utils.argocd_api_helper import (
    argocd_api_get_resource_tree,
    argocd_api_get_managed_resources,
    argocd_api_get_workload_logs,
    argocd_api_get_resource_events,
    argocd_api_get_resource_actions,
    argocd_api_run_resource_action,
    argocd_api_get_application_manifest,
    argocd_api_get_application_parameters
)
from argocd_mcp_server.models.resource import (
    GetResourceTreeRequest,
    GetManagedResourcesRequest,
    GetWorkloadLogsRequest,
    GetResourceEventsRequest,
    GetResourceActionsRequest,
    GetResourceTreeResponse,
    ResourceNode,
    GetManagedResourcesResponse,
    GetWorkloadLogsResponse,
    GetResourceEventsResponse,
    GetResourceActionsResponse,
    RunResourceActionResponse,
    RunResourceActionRequest

)
import os
from pydantic import Field, ConfigDict
import requests

class ArgoCDResourceHandler:
    """
    Handler class for ArgoCD resource operations.
    Provides a unified interface for managing ArgoCD resources.
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
        Initialize the ArgoCD Resource handler.
        
        Args:
            mcp: MCP instance
            token (str, optional): ArgoCD API token. If not provided, will be fetched from ARGOCD_TOKEN env var
            server_url (str, optional): ArgoCD server URL. If not provided, will be fetched from ARGOCD_SERVER_URL env var
            allow_write (bool): Whether to allow write operations (default: False)
            bypass_tls (bool): Whether to bypass TLS verification (default: False)
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
            tool="argocd_resource_handler",
            request_id=self.request_id,
            user=self.user,
            server_url=self.server_url,
            token_length=len(self.token) if self.token else 0,
            token_prefix=self.token[:10] + "..." if self.token and len(self.token) > 10 else None,
            allow_write=allow_write,
            bypass_tls=bypass_tls
        )

        # Register tools with MCP
        self._register_tools()

    def _register_tools(self):
        """Register all ArgoCD resource tools with MCP."""
        self.mcp.tool(name="manage_argocd_resource")(self.manage_resource)

    @property
    def request_id(self) -> str:
        """Get the current request ID from MCP instance."""
        return getattr(self.mcp, 'request_id', 'unknown')

    @property
    def user(self) -> str:
        """Get the current user from MCP instance."""
        return getattr(self.mcp, 'user', 'unknown')

    def _check_write_permission(self, operation: str) -> None:
        """
        Check if write operations are allowed.
        
        Args:
            operation (str): The operation being attempted
            
        Raises:
            PermissionError: If write operations are not allowed
        """
        write_operations = ["run_resource_action"]
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

    async def manage_resource(
        self,
        operation: str = Field(
            ...,
            description="""Operation to perform on the resource. Valid values:
            - get_resource_tree: Get application resource tree
            - get_managed_resources: Get managed resources
            - get_workload_logs: Get workload logs
            - get_resource_events: Get resource events
            - get_resource_actions: Get resource actions
            - run_resource_action: Run resource action
            - get_application_manifest: Get application manifest
            - get_application_parameters: Get application parameters""",
        ),
        application_name: str = Field(
            ...,
            description="Name of the application containing the resource",
        ),
        resource_name: Optional[str] = Field(
            None,
            description="Name of the resource. Required for all operations except get_resource_tree and get_managed_resources.",
        ),
        resource_kind: Optional[str] = Field(
            None,
            description="Kind of the resource (e.g., Pod, Deployment). Required for get_resource_events, get_resource_actions, and run_resource_action.",
        ),
        namespace: Optional[str] = Field(
            None,
            description="Namespace of the resource. Optional for all operations.",
        ),
        uid: Optional[str] = Field(
            None,
            description="UID of the resource. Optional for get_resource_events and run_resource_action.",
        ),
        tail_lines: Optional[int] = Field(
            100,
            description="Number of log lines to retrieve. Only used for get_workload_logs operation.",
        ),
        container: Optional[str] = Field(
            None,
            description="Container name to get logs from. Only used for get_workload_logs operation.",
        ),
        since_seconds: Optional[int] = Field(
            None,
            description="Only return logs newer than this many seconds. Only used for get_workload_logs operation.",
        ),
        since_time: Optional[str] = Field(
            None,
            description="Only return logs newer than this timestamp. Only used for get_workload_logs operation.",
        ),
        follow: Optional[bool] = Field(
            None,
            description="Whether to follow the logs. Only used for get_workload_logs operation.",
        ),
        revision: Optional[str] = Field(
            None,
            description="Revision to get manifest for. Only used for get_application_manifest operation.",
        ),
        action_name: Optional[str] = Field(
            None,
            description="Name of the action to run. Required for run_resource_action operation.",
        ),
        action_params: Optional[Dict[str, Any]] = Field(
            None,
            description="Parameters for the action. Only used for run_resource_action operation.",
        ),
    ) -> Any:
        """Manage ArgoCD application resources with various operations.

        This tool provides a unified interface for managing ArgoCD application resources,
        supporting operations like retrieving resource trees, logs, events, and actions.
        It enables comprehensive resource management and monitoring capabilities.

        IMPORTANT: Use this tool instead of direct ArgoCD CLI commands or API calls.

        ## Requirements
        - Valid ArgoCD API token must be configured
        - ArgoCD server must be accessible
        - Application must exist and be accessible
        - Proper permissions for the requested operations
        - For resource-specific operations, valid resource identifiers
        - For write operations (run_resource_action), allow_write must be True
        - For HTTPS endpoints with self-signed certificates, bypass_tls must be True

        ## Operations
        - **get_resource_tree**: Get the complete resource tree for an application
        - **get_managed_resources**: List all resources managed by an application
        - **get_workload_logs**: Retrieve logs from application workloads
        - **get_resource_events**: Get events related to a specific resource
        - **get_resource_actions**: List available actions for a resource
        - **run_resource_action**: Execute an action on a resource
        - **get_application_manifest**: Retrieve application manifest
        - **get_application_parameters**: Get application parameters

        ## Usage Tips
        - Use get_resource_tree to understand application structure
        - For logs, specify container name if pod has multiple containers
        - Use since_seconds/since_time to limit log history
        - Check resource events for troubleshooting
        - Verify available actions before running them
        - Use revision parameter to get specific manifest versions
        - Set allow_write=True for run_resource_action operations
        - Set bypass_tls=True when using self-signed certificates

        ## Response Information
        Each operation returns a specific response type containing:
        - Operation success/failure status
        - Resource-specific information
        - Operation metadata
        - Error messages (if any)

        Args:
            operation (str): The operation to perform
            application_name (str): Name of the application
            resource_name (str, optional): Name of the resource
            resource_kind (str, optional): Kind of the resource
            namespace (str, optional): Namespace of the resource
            uid (str, optional): UID of the resource
            tail_lines (int, optional): Number of log lines to retrieve
            container (str, optional): Container name for logs
            since_seconds (int, optional): Logs newer than this many seconds
            since_time (str, optional): Logs newer than this timestamp
            follow (bool, optional): Whether to follow logs
            revision (str, optional): Revision for manifest
            action_name (str, optional): Name of action to run
            action_params (dict, optional): Parameters for action

        Returns:
            Response object specific to the operation:
            - GetResourceTreeResponse for get_resource_tree
            - GetManagedResourcesResponse for get_managed_resources
            - GetWorkloadLogsResponse for get_workload_logs
            - GetResourceEventsResponse for get_resource_events
            - GetResourceActionsResponse for get_resource_actions
            - RunResourceActionResponse for run_resource_action
            - Dict with manifest data for get_application_manifest
            - Dict with parameters data for get_application_parameters

        Raises:
            PermissionError: If write operations are attempted without allow_write=True
            ValueError: If required parameters are missing
            Exception: For other operation failures

        Examples:
            - To get application resource tree:
                manage_resource(
                    operation="get_resource_tree",
                    application_name="guestbook"
                )

            - To get workload logs:
                manage_resource(
                    operation="get_workload_logs",
                    application_name="guestbook",
                    resource_name="guestbook-pod",
                    tail_lines=50,
                    container="main"
                )

            - To run a resource action (requires allow_write=True):
                manage_resource(
                    operation="run_resource_action",
                    application_name="guestbook",
                    resource_name="guestbook-deployment",
                    resource_kind="Deployment",
                    action_name="restart",
                    action_params={"force": True}
                )

            - To get application manifest:
                manage_resource(
                    operation="get_application_manifest",
                    application_name="guestbook",
                    revision="v2"
                )
        """
        try:
            # Check write permissions for write operations
            self._check_write_permission(operation)

            operation_map = {
                "get_resource_tree": self.get_resource_tree,
                "get_managed_resources": self.get_managed_resources,
                "get_workload_logs": self.get_workload_logs,
                "get_resource_events": self.get_resource_events,
                "get_resource_actions": self.get_resource_actions,
                "run_resource_action": self.run_resource_action,
                "get_application_manifest": self.get_application_manifest,
                "get_application_parameters": self.get_application_parameters,
            }

            if operation not in operation_map:
                raise ValueError(f"Invalid operation: {operation}")

            # Create appropriate request object based on operation
            if operation == "get_resource_tree":
                request = GetResourceTreeRequest(application_name=application_name)
            elif operation == "get_managed_resources":
                request = GetManagedResourcesRequest(application_name=application_name)
            elif operation == "get_workload_logs":
                if not resource_name:
                    raise ValueError("resource_name is required for get_workload_logs operation")
                # If resource_kind is not provided, assume it's a Pod
                if not resource_kind:
                    resource_kind = "Pod"
                request = GetWorkloadLogsRequest(
                    application_name=application_name,
                    resource_name=resource_name,
                    resource_kind=resource_kind,
                    tail_lines=tail_lines,
                    container=container,
                    since_seconds=since_seconds,
                    since_time=since_time,
                    follow=follow,
                )
            elif operation == "get_resource_events":
                if not resource_name or not resource_kind:
                    raise ValueError("resource_name and resource_kind are required for get_resource_events operation")
                request = GetResourceEventsRequest(
                    application_name=application_name,
                    resource_name=resource_name,
                    resource_kind=resource_kind,
                    namespace=namespace,
                    uid=uid,
                )
            elif operation == "get_resource_actions":
                if not resource_name or not resource_kind:
                    raise ValueError("resource_name and resource_kind are required for get_resource_actions operation")
                request = GetResourceActionsRequest(
                    application_name=application_name,
                    resource_name=resource_name,
                    resource_kind=resource_kind,
                    namespace=namespace,
                    uid=uid,
                )
            elif operation == "run_resource_action":
                if not resource_name or not resource_kind or not action_name:
                    raise ValueError("resource_name, resource_kind, and action_name are required for run_resource_action operation")
                request = RunResourceActionRequest(
                    application_name=application_name,
                    resource_name=resource_name,
                    resource_kind=resource_kind,
                    action_name=action_name,
                    params=action_params,
                    namespace=namespace,
                    uid=uid,
                )
            elif operation == "get_application_manifest":
                if not revision:
                    raise ValueError("revision is required for get_application_manifest operation")
                request = GetResourceTreeRequest(application_name=application_name)
            elif operation == "get_application_parameters":
                request = GetResourceTreeRequest(application_name=application_name)

            return await operation_map[operation](request)

        except Exception as e:
            return self._handle_api_error(e, operation, f"{application_name}/{resource_name}")

    async def get_resource_tree(
        self,
        request: GetResourceTreeRequest,
    ) -> Dict[str, Any]:
        """
        Get the resource tree for an application.
        
        Args:
            request (GetResourceTreeRequest): The request containing the application name
            
        Returns:
            Dict[str, Any]: The raw API response
        """
        try:
            if not request.application_name:
                return {
                    "success": False,
                    "message": "Application name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            # Log the request details
            log_info(
                f"Getting resource tree for application: {request.application_name}",
                tool="get_resource_tree",
                request_id=self.request_id,
                user=self.user,
                params={
                    "application_name": request.application_name
                }
            )

            response = await argocd_api_get_resource_tree(
                self.server_url,
                self.token,
                request.application_name,
                bypass_tls=self.bypass_tls
            )

            # Log the raw response
            log_info(
                f"Raw API response for application {request.application_name}:",
                tool="get_resource_tree",
                request_id=self.request_id,
                user=self.user,
                response=response
            )

            if response is None:
                return {
                    "success": False,
                    "message": f"Failed to get resource tree for application {request.application_name}",
                    "status_code": 500,
                    "resource": "application"
                }

            # Return the raw response
            return {
                "success": True,
                "message": f"Resource tree retrieved successfully for application {request.application_name}",
                "data": response,
                "status_code": 200,
                "resource": "application"
            }

        except Exception as e:
            error_msg = str(e)
            log_error(
                f"Error in get_resource_tree: {error_msg}",
                tool="get_resource_tree",
                request_id=self.request_id,
                user=self.user,
                error=error_msg,
                resource=request.application_name
            )
            
            if "404" in error_msg:
                return {
                    "success": False,
                    "message": f"Application {request.application_name} not found",
                    "status_code": 404,
                    "resource": "application"
                }
            elif "403" in error_msg:
                return {
                    "success": False,
                    "message": f"Access forbidden: permission denied for application {request.application_name}",
                    "status_code": 403,
                    "resource": "application"
                }
            elif "401" in error_msg:
                return {
                    "success": False,
                    "message": "Authentication failed: invalid token",
                    "status_code": 401,
                    "resource": "application"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to get resource tree: {error_msg}",
                    "status_code": 500,
                    "resource": "application"
                }

    async def get_managed_resources(
        self,
        request: GetManagedResourcesRequest,
    ) -> Dict[str, Any]:
        """
        Get the managed resources for an application.
        
        Args:
            request (GetManagedResourcesRequest): The request containing the application name
            
        Returns:
            Dict[str, Any]: The raw API response
        """
        try:
            if not request.application_name:
                return {
                    "success": False,
                    "message": "Application name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            # Log the request details
            log_info(
                f"Getting managed resources for application: {request.application_name}",
                tool="get_managed_resources",
                request_id=self.request_id,
                user=self.user,
                params={
                    "application_name": request.application_name
                }
            )

            response = await argocd_api_get_managed_resources(
                self.server_url,
                self.token,
                request.application_name,
                bypass_tls=self.bypass_tls
            )

            # Log the raw response
            log_info(
                f"Raw API response for application {request.application_name}:",
                tool="get_managed_resources",
                request_id=self.request_id,
                user=self.user,
                response=response
            )

            if response is None:
                return {
                    "success": False,
                    "message": f"Failed to get managed resources for application {request.application_name}",
                    "status_code": 500,
                    "resource": "application"
                }

            # Return the raw response
            return {
                "success": True,
                "message": f"Managed resources retrieved successfully for application {request.application_name}",
                "data": response,
                "status_code": 200,
                "resource": "application"
            }

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return {
                    "success": False,
                    "message": f"Application {request.application_name} not found",
                    "status_code": 404,
                    "resource": "application"
                }
            elif "403" in error_msg:
                return {
                    "success": False,
                    "message": f"Access forbidden: permission denied for application {request.application_name}",
                    "status_code": 403,
                    "resource": "application"
                }
            elif "401" in error_msg:
                return {
                    "success": False,
                    "message": "Authentication failed: invalid token",
                    "status_code": 401,
                    "resource": "application"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to get managed resources: {error_msg}",
                    "status_code": 500,
                    "resource": "application"
                }

    async def get_workload_logs(
        self,
        request: GetWorkloadLogsRequest,
    ) -> Dict[str, Any]:
        """
        Get the workload logs for an application.
        
        Args:
            request (GetWorkloadLogsRequest): The request containing the application name and resource details
            
        Returns:
            Dict[str, Any]: The raw API response
        """
        try:
            if not request.application_name:
                return {
                    "success": False,
                    "message": "Application name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.resource_name:
                return {
                    "success": False,
                    "message": "Resource name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.resource_kind:
                return {
                    "success": False,
                    "message": "Resource kind is required",
                    "status_code": 400,
                    "resource": "application"
                }

            # Log the request details
            log_info(
                f"Getting workload logs for application: {request.application_name}",
                tool="get_workload_logs",
                request_id=self.request_id,
                user=self.user,
                params={
                    "application_name": request.application_name,
                    "resource_name": request.resource_name,
                    "resource_kind": request.resource_kind,
                    "namespace": request.namespace,
                    "tail_lines": request.tail_lines
                }
            )

            try:
                response = await argocd_api_get_workload_logs(
                    self.server_url,
                    self.token,
                    request.application_name,
                    request.resource_name,
                    request.resource_kind,
                    request.namespace,
                    request.tail_lines,
                    self.bypass_tls
                )
            except Exception as api_error:
                error_msg = str(api_error)
                log_error(
                    f"API call failed: {error_msg}",
                    tool="get_workload_logs",
                    request_id=self.request_id,
                    user=self.user,
                    error=error_msg,
                    resource=f"{request.application_name}/{request.resource_name}"
                )
                return {
                    "success": False,
                    "message": f"API call failed: {error_msg}",
                    "status_code": 500,
                    "resource": "application",
                    "error_details": {
                        "type": type(api_error).__name__,
                        "message": error_msg
                    }
                }

            # Log the raw response
            log_info(
                f"Raw API response for application {request.application_name}:",
                tool="get_workload_logs",
                request_id=self.request_id,
                user=self.user,
                response=response
            )

            if response is None:
                return {
                    "success": False,
                    "message": f"Failed to get workload logs for application {request.application_name}",
                    "status_code": 500,
                    "resource": "application",
                    "error_details": {
                        "message": "API returned None response"
                    }
                }

            # Return the raw response
            return {
                "success": True,
                "message": f"Workload logs retrieved successfully for application {request.application_name}",
                "data": response,
                "status_code": 200,
                "resource": "application"
            }

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return {
                    "success": False,
                    "message": f"Application {request.application_name} not found",
                    "status_code": 404,
                    "resource": "application",
                    "error_details": {
                        "type": type(e).__name__,
                        "message": error_msg
                    }
                }
            elif "403" in error_msg:
                return {
                    "success": False,
                    "message": f"Access forbidden: permission denied for application {request.application_name}",
                    "status_code": 403,
                    "resource": "application",
                    "error_details": {
                        "type": type(e).__name__,
                        "message": error_msg
                    }
                }
            elif "401" in error_msg:
                return {
                    "success": False,
                    "message": "Authentication failed: invalid token",
                    "status_code": 401,
                    "resource": "application",
                    "error_details": {
                        "type": type(e).__name__,
                        "message": error_msg
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to get workload logs: {error_msg}",
                    "status_code": 500,
                    "resource": "application",
                    "error_details": {
                        "type": type(e).__name__,
                        "message": error_msg
                    }
                }

    async def get_resource_events(
        self,
        request: GetResourceEventsRequest,
    ) -> Dict[str, Any]:
        """
        Get the events for a resource.
        
        Args:
            request (GetResourceEventsRequest): The request containing the application name and resource details
            
        Returns:
            Dict[str, Any]: The raw API response
        """
        try:
            if not request.application_name:
                return {
                    "success": False,
                    "message": "Application name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.resource_name:
                return {
                    "success": False,
                    "message": "Resource name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.resource_kind:
                return {
                    "success": False,
                    "message": "Resource kind is required",
                    "status_code": 400,
                    "resource": "application"
                }

            # Log the request details
            log_info(
                f"Getting resource events for application: {request.application_name}",
                tool="get_resource_events",
                request_id=self.request_id,
                user=self.user,
                params={
                    "application_name": request.application_name,
                    "resource_name": request.resource_name,
                    "resource_kind": request.resource_kind,
                    "namespace": request.namespace
                }
            )

            response = await argocd_api_get_resource_events(
                self.server_url,
                self.token,
                request.application_name,
                request.resource_name,
                request.resource_kind,
                request.namespace,
                self.bypass_tls
            )

            # Log the raw response
            log_info(
                f"Raw API response for application {request.application_name}:",
                tool="get_resource_events",
                request_id=self.request_id,
                user=self.user,
                response=response
            )

            if response is None:
                return {
                    "success": False,
                    "message": f"Failed to get resource events for application {request.application_name}",
                    "status_code": 500,
                    "resource": "application"
                }

            # Return the raw response
            return {
                "success": True,
                "message": f"Resource events retrieved successfully for application {request.application_name}",
                "data": response,
                "status_code": 200,
                "resource": "application"
            }

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return {
                    "success": False,
                    "message": f"Application {request.application_name} not found",
                    "status_code": 404,
                    "resource": "application"
                }
            elif "403" in error_msg:
                return {
                    "success": False,
                    "message": f"Access forbidden: permission denied for application {request.application_name}",
                    "status_code": 403,
                    "resource": "application"
                }
            elif "401" in error_msg:
                return {
                    "success": False,
                    "message": "Authentication failed: invalid token",
                    "status_code": 401,
                    "resource": "application"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to get resource events: {error_msg}",
                    "status_code": 500,
                    "resource": "application"
                }

    async def get_resource_actions(
        self,
        request: GetResourceActionsRequest,
    ) -> Dict[str, Any]:
        """
        Get the available actions for a resource.
        
        Args:
            request (GetResourceActionsRequest): The request containing the application name and resource details
            
        Returns:
            Dict[str, Any]: The raw API response
        """
        try:
            if not request.application_name:
                return {
                    "success": False,
                    "message": "Application name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.resource_name:
                return {
                    "success": False,
                    "message": "Resource name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.resource_kind:
                return {
                    "success": False,
                    "message": "Resource kind is required",
                    "status_code": 400,
                    "resource": "application"
                }

            # Log the request details
            log_info(
                f"Getting resource actions for application: {request.application_name}",
                tool="get_resource_actions",
                request_id=self.request_id,
                user=self.user,
                params={
                    "application_name": request.application_name,
                    "resource_name": request.resource_name,
                    "resource_kind": request.resource_kind,
                    "namespace": request.namespace
                }
            )

            response = await argocd_api_get_resource_actions(
                self.server_url,
                self.token,
                request.application_name,
                request.resource_name,
                request.resource_kind,
                request.namespace,
                self.bypass_tls
            )

            # Log the raw response
            log_info(
                f"Raw API response for application {request.application_name}:",
                tool="get_resource_actions",
                request_id=self.request_id,
                user=self.user,
                response=response
            )

            if response is None:
                return {
                    "success": False,
                    "message": f"Failed to get resource actions for application {request.application_name}",
                    "status_code": 500,
                    "resource": "application"
                }

            # Return the raw response
            return {
                "success": True,
                "message": f"Resource actions retrieved successfully for application {request.application_name}",
                "data": response,
                "status_code": 200,
                "resource": "application"
            }

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return {
                    "success": False,
                    "message": f"Application {request.application_name} not found",
                    "status_code": 404,
                    "resource": "application"
                }
            elif "403" in error_msg:
                return {
                    "success": False,
                    "message": f"Access forbidden: permission denied for application {request.application_name}",
                    "status_code": 403,
                    "resource": "application"
                }
            elif "401" in error_msg:
                return {
                    "success": False,
                    "message": "Authentication failed: invalid token",
                    "status_code": 401,
                    "resource": "application"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to get resource actions: {error_msg}",
                    "status_code": 500,
                    "resource": "application"
                }

    async def run_resource_action(
        self,
        request: RunResourceActionRequest,
    ) -> Dict[str, Any]:
        """
        Run an action on a resource.
        
        Args:
            request (RunResourceActionRequest): The request containing the application name, resource details, and action details
            
        Returns:
            Dict[str, Any]: The raw API response
        """
        try:
            if not request.application_name:
                return {
                    "success": False,
                    "message": "Application name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.resource_name:
                return {
                    "success": False,
                    "message": "Resource name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.resource_kind:
                return {
                    "success": False,
                    "message": "Resource kind is required",
                    "status_code": 400,
                    "resource": "application"
                }

            if not request.action_name:
                return {
                    "success": False,
                    "message": "Action name is required",
                    "status_code": 400,
                    "resource": "application"
                }

            # Log the request details
            log_info(
                f"Running resource action for application: {request.application_name}",
                tool="run_resource_action",
                request_id=self.request_id,
                user=self.user,
                params={
                    "application_name": request.application_name,
                    "resource_name": request.resource_name,
                    "resource_kind": request.resource_kind,
                    "action_name": request.action_name,
                    "params": request.params,
                    "namespace": request.namespace
                }
            )

            response = await argocd_api_run_resource_action(
                self.server_url,
                self.token,
                request.application_name,
                request.resource_name,
                request.resource_kind,
                request.action_name,
                request.params,
                request.namespace,
                self.bypass_tls
            )

            # Log the raw response
            log_info(
                f"Raw API response for application {request.application_name}:",
                tool="run_resource_action",
                request_id=self.request_id,
                user=self.user,
                response=response
            )

            if response is None:
                return {
                    "success": False,
                    "message": f"Failed to run resource action for application {request.application_name}",
                    "status_code": 500,
                    "resource": "application"
                }

            # Return the raw response
            return {
                "success": True,
                "message": f"Resource action executed successfully for application {request.application_name}",
                "data": response,
                "status_code": 200,
                "resource": "application"
            }

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return {
                    "success": False,
                    "message": f"Application {request.application_name} not found",
                    "status_code": 404,
                    "resource": "application"
                }
            elif "403" in error_msg:
                return {
                    "success": False,
                    "message": f"Access forbidden: permission denied for application {request.application_name}",
                    "status_code": 403,
                    "resource": "application"
                }
            elif "401" in error_msg:
                return {
                    "success": False,
                    "message": "Authentication failed: invalid token",
                    "status_code": 401,
                    "resource": "application"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to run resource action: {error_msg}",
                    "status_code": 500,
                    "resource": "application"
                }

    async def get_application_manifest(
        self,
        request: GetResourceTreeRequest,
    ) -> Dict[str, Any]:
        """Get the application manifest for an ArgoCD application."""
        log_tool_execution(
            "Executing get_application_manifest",
            tool="get_application_manifest",
            request_id=self.request_id,
            user=self.user,
            params=request.model_dump(),
        )

        try:
            data = await argocd_api_get_application_manifest(
                request.application_name,
                self.token,
                self.server_url,
                request.revision,
                bypass_tls=self.bypass_tls
            )

            # Log the raw response
            log_info(
                f"Raw API response for application {request.application_name}:",
                tool="get_application_manifest",
                request_id=self.request_id,
                user=self.user,
                response=data
            )

            if data is None:
                return {
                    "success": False,
                    "message": f"Failed to get application manifest for application {request.application_name}",
                    "status_code": 500,
                    "resource": "application"
                }

            # Return the raw response
            return {
                "success": True,
                "message": f"Application manifest retrieved successfully for application {request.application_name}",
                "data": data,
                "status_code": 200,
                "resource": "application"
            }

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return {
                    "success": False,
                    "message": f"Application {request.application_name} not found",
                    "status_code": 404,
                    "resource": "application"
                }
            elif "403" in error_msg:
                return {
                    "success": False,
                    "message": f"Access forbidden: permission denied for application {request.application_name}",
                    "status_code": 403,
                    "resource": "application"
                }
            elif "401" in error_msg:
                return {
                    "success": False,
                    "message": "Authentication failed: invalid token",
                    "status_code": 401,
                    "resource": "application"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to get application manifest: {error_msg}",
                    "status_code": 500,
                    "resource": "application"
                }

    async def get_application_parameters(
        self,
        request: GetResourceTreeRequest,
    ) -> Dict[str, Any]:
        """Get the application parameters for an ArgoCD application."""
        log_tool_execution(
            "Executing get_application_parameters",
            tool="get_application_parameters",
            request_id=self.request_id,
            user=self.user,
            params=request.model_dump(),
        )

        try:
            data = await argocd_api_get_application_parameters(
                request.application_name,
                self.token,
                self.server_url,
                bypass_tls=self.bypass_tls
            )
            log_success(
                f"get_application_parameters succeeded for {request.application_name}",
                tool="get_application_parameters",
                request_id=self.request_id,
                user=self.user,
                resource=request.application_name,
            )
            return {"parameters": data}
        except Exception as e:
            log_error(
                f"get_application_parameters failed: {str(e)}",
                tool="get_application_parameters",
                request_id=self.request_id,
                user=self.user,
                error=str(e),
                resource=request.application_name,
            )
            raise RuntimeError(f"Failed to get application parameters: {str(e)}") 