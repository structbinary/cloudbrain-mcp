import aiohttp
from typing import Optional, Dict, Any, List, Union, Tuple
import json
from loguru import logger
import urllib3
from argocd_mcp_server.utils.logger import log_error, log_info
from aiohttp import ClientResponseError

# Disable SSL verification warnings when bypass_tls is True
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Constants
API_BASE_PATH = "/api/v1"
DEFAULT_TIMEOUT = 30
DEFAULT_TAIL_LINES = 100
MAX_RETRIES = 3
CACHE_TTL = 300  # 5 minutes

# HTTP Status Codes
HTTP_STATUS = {
    "OK": 200,
    "CREATED": 201,
    "NO_CONTENT": 204,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "SERVER_ERROR": 500
}

# Error Messages
ERROR_MESSAGES = {
    "TOKEN_REQUIRED": "Authentication token is required",
    "SERVER_URL_REQUIRED": "Server URL is required",
    "INVALID_URL": "Server URL must start with http:// or https://",
    "SSL_ERROR": "SSL verification failed",
    "CONNECTION_ERROR": "Failed to connect to server",
    "TIMEOUT_ERROR": "Request timed out",
    "JSON_PARSE_ERROR": "Failed to parse JSON response",
    "AUTH_FAILED": "Authentication failed",
    "ACCESS_FORBIDDEN": "Access forbidden",
    "NOT_FOUND": "Resource not found",
    "SERVER_ERROR": "Server error occurred"
}

# Response cache
_response_cache = {}

def validate_request_params(token: str, server_url: str) -> None:
    """
    Validate request parameters.
    
    Args:
        token (str): Bearer token for authentication
        server_url (str): Base URL of the ArgoCD server
        
    Raises:
        ValueError: If parameters are invalid
    """
    if not token:
        logger.error("Missing authentication token")
        raise ValueError(ERROR_MESSAGES["TOKEN_REQUIRED"])
    if not server_url:
        logger.error("Missing server URL")
        raise ValueError(ERROR_MESSAGES["SERVER_URL_REQUIRED"])
    if not server_url.startswith(("http://", "https://")):
        logger.error("Invalid server URL format: {}", server_url)
        raise ValueError(ERROR_MESSAGES["INVALID_URL"])


async def validate_response(response: aiohttp.ClientResponse) -> None:
    """Validate the API response."""
    if not response.ok:
        error_msg = f"HTTP {response.status}: {response.reason}"
        try:
            error_data = await response.json()
            if isinstance(error_data, dict):
                error_msg = error_data.get("error", error_msg)
        except:
            pass
        
        if response.status == 403:
            error_msg = "Access forbidden: permission denied"
        elif response.status == 401:
            error_msg = "Authentication failed: invalid or expired token"
        elif response.status == 404:
            error_msg = "Resource not found"
        
        log_error(
            f"API request failed: {error_msg}",
            tool="argocd_api",
            request_id="unknown",
            user="unknown",
            error=error_msg,
            status_code=response.status
        )
        raise aiohttp.ClientError(error_msg, status=response.status)

async def create_session(bypass_tls: bool = False) -> aiohttp.ClientSession:
    """Create an aiohttp client session with appropriate SSL settings."""
    if bypass_tls:
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    return aiohttp.ClientSession()

async def handle_api_error(e: ClientResponseError, tool: str, resource: str) -> None:
    """
    Handle API errors with appropriate error messages and logging.
    
    Args:
        e: The exception that occurred
        tool: The name of the tool/function that failed
        resource: The resource being accessed
    """
    status = getattr(e, 'status', 500)
    message = str(e)
    
    # Try to get the response body for more detailed error information
    try:
        if hasattr(e, 'response') and e.response:
            error_text = await e.response.text()
            try:
                error_json = await e.response.json()
                error_msg = error_json.get("error", error_text)
            except:
                error_msg = error_text
        else:
            error_msg = message
    except:
        error_msg = message
    
    # Check if this is a 403 error for a non-existent application
    if status == 403 and '/api/v1/applications/' in resource:
        # Extract application name from the path
        app_name = resource.split('/')[-1]
        error_msg = f"Application not found: '{app_name}' does not exist"
        status = 404  # Override status to 404
    elif status == 403:
        error_msg = f"Access forbidden: You don't have permission to access {resource}"
    elif status == 404:
        error_msg = f"Resource not found: {resource} does not exist"
    elif status == 401:
        error_msg = "Authentication failed: Invalid or expired token"
    elif status == 400:
        error_msg = f"Invalid request: {error_msg}"
    
    log_error(
        error_msg,
        tool=tool,
        error=error_msg,
        resource=resource,
        status_code=status
    )
    raise ClientResponseError(
        request_info=e.request_info,
        history=e.history,
        status=status,
        message=error_msg,
        headers=e.headers
    )

async def argocd_api_get(
    path: str,
    token: str,
    server_url: str,
    params: Optional[Dict[str, Any]] = None,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Make a GET request to the ArgoCD API.
    
    Args:
        path (str): API endpoint path
        token (str): ArgoCD API token
        server_url (str): ArgoCD server URL
        params (dict, optional): Query parameters
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: API response data or None if request failed
    """
    try:
        session = await create_session(bypass_tls)
        try:
            async with session.get(
                f"{server_url}{path}",
                headers={"Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                params=params,
            ) as response:
                if not response.ok:
                    error_text = await response.text()
                    try:
                        error_json = await response.json()
                        error_msg = error_json.get("error", error_text)
                    except:
                        error_msg = error_text
                    
                    logger.error(f"API request failed: {response.status} - {error_msg}")
                    logger.error(f"Request URL: {server_url}{path}")
                    
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_msg,
                        headers=response.headers
                    )
                
                response_data = await response.json()
                logger.info(f"GET request successful: {server_url}{path}")
                logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
                return response_data
        finally:
            await session.close()
    except aiohttp.ClientError as e:
        await handle_api_error(e, "argocd_api_get", path)
    except Exception as e:
        log_error(
            f"Unexpected error: {str(e)}",
            tool="argocd_api_get",
            error=str(e),
            resource=path,
        )

async def argocd_api_post(
    path: str,
    token: str,
    server_url: str,
    data: Dict[str, Any],
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Make a POST request to the ArgoCD API.
    
    Args:
        path (str): API endpoint path
        token (str): ArgoCD API token
        server_url (str): ArgoCD server URL
        data (dict): Request payload
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: API response data or None if request failed
    """
    try:
        # Log the request details for debugging
        logger.info(f"Starting POST request to {server_url}{path}")
        logger.debug(f"Request payload: {json.dumps(data, indent=2)}")
        logger.debug(f"Bypass TLS: {bypass_tls}")

        session = await create_session(bypass_tls)
        try:
            async with session.post(
                f"{server_url}{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=data,
            ) as response:
                if not response.ok:
                    error_text = await response.text()
                    try:
                        error_json = await response.json()
                        error_msg = error_json.get("error", error_text)
                    except:
                        error_msg = error_text
                    
                    logger.error(f"API request failed: {response.status} - {error_msg}")
                    logger.error(f"Request URL: {server_url}{path}")
                    logger.error(f"Request payload: {json.dumps(data, indent=2)}")
                    
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_msg,
                        headers=response.headers
                    )
                
                response_data = await response.json()
                logger.info(f"POST request successful: {server_url}{path}")
                logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
                return response_data
        finally:
            await session.close()
    except aiohttp.ClientError as e:
        logger.error(f"Client error in POST request: {str(e)}")
        await handle_api_error(e, "argocd_api_post", path)
    except Exception as e:
        logger.error(f"Unexpected error in POST request: {str(e)}")
        log_error(
            f"Unexpected error: {str(e)}",
            tool="argocd_api_post",
            error=str(e),
            resource=path,
            payload=data
        )


async def argocd_api_post_sync(
    path: str,
    token: str,
    server_url: str,
    data: Dict[str, Any],
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Make a POST request to sync an ArgoCD application.
    
    Args:
        path (str): API endpoint path
        token (str): ArgoCD API token
        server_url (str): ArgoCD server URL
        data (dict): Request payload
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: API response data or None if request failed
    """
    try:
        session = await create_session(bypass_tls)
        try:
            async with session.post(
                f"{server_url}{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=data,
            ) as response:
                response.raise_for_status()
                return await response.json()
        finally:
            await session.close()
    except aiohttp.ClientError as e:
        await handle_api_error(e, "argocd_api_post_sync", path)
    except Exception as e:
        log_error(
            f"Unexpected error: {str(e)}",
            tool="argocd_api_post_sync",
            error=str(e),
            resource=path,
        )

async def argocd_api_put(
    path: str,
    token: str,
    server_url: str,
    data: Dict[str, Any],
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Make a PUT request to the ArgoCD API.
    
    Args:
        path (str): API endpoint path
        token (str): ArgoCD API token
        server_url (str): ArgoCD server URL
        data (dict): Request payload
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: API response data or None if request failed
    """
    try:
        session = await create_session(bypass_tls)
        try:
            async with session.put(
                f"{server_url}{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=data,
            ) as response:
                response.raise_for_status()
                return await response.json()
        finally:
            await session.close()
    except aiohttp.ClientError as e:
        await handle_api_error(e, "argocd_api_put", path)
    except Exception as e:
        log_error(
            f"Unexpected error: {str(e)}",
            tool="argocd_api_put",
            error=str(e),
            resource=path,
        )

async def argocd_api_delete(
    path: str,
    token: str,
    server_url: str,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Make a DELETE request to the ArgoCD API.
    
    Args:
        path (str): API endpoint path
        token (str): ArgoCD API token
        server_url (str): ArgoCD server URL
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: API response data or None if request failed
    """
    try:
        session = await create_session(bypass_tls)
        try:
            async with session.delete(
                f"{server_url}{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
            ) as response:
                response.raise_for_status()
                return await response.json()
        finally:
            await session.close()
    except aiohttp.ClientError as e:
        await handle_api_error(e, "argocd_api_delete", path)
    except Exception as e:
        log_error(
            f"Unexpected error: {str(e)}",
            tool="argocd_api_delete",
            error=str(e),
            resource=path,
        )


async def argocd_api_get_resource_tree(
    server_url: str,
    token: str,
    application_name: str,
    namespace: Optional[str] = None,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Get the resource tree for an application.
    
    Args:
        server_url (str): ArgoCD server URL
        token (str): ArgoCD API token
        application_name (str): Name of the application
        namespace (str, optional): Namespace of the application
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: Resource tree data or None if request failed
    """
    path = f"/api/v1/applications/{application_name}/resource-tree"
    return await argocd_api_get(path, token, server_url, bypass_tls=bypass_tls)

async def argocd_api_get_managed_resources(
    server_url: str,
    token: str,
    application_name: str,
    namespace: Optional[str] = None,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Get managed resources for an application.
    
    Args:
        server_url (str): ArgoCD server URL
        token (str): ArgoCD API token
        application_name (str): Name of the application
        namespace (str, optional): Namespace of the application
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: List of managed resources or None if request failed
    """
    path = f"/api/v1/applications/{application_name}/managed-resources"
    return await argocd_api_get(path, token, server_url, bypass_tls=bypass_tls)

async def argocd_api_get_workload_logs(
    server_url: str,
    token: str,
    application_name: str,
    resource_name: str,
    resource_kind: str,
    namespace: Optional[str] = None,
    tail_lines: Optional[int] = 100,
    container: Optional[str] = None,
    since_seconds: Optional[int] = None,
    since_time: Optional[str] = None,
    follow: Optional[bool] = False,
    bypass_tls: bool = False
) -> Dict[str, Any]:
    """Get workload logs for a specific resource in an ArgoCD application."""
    try:
        # Log the parameters being sent
        log_info(
            f"Getting workload logs with parameters:",
            tool="argocd_api_get_workload_logs",
            params={
                "application_name": application_name,
                "resource_name": resource_name,
                "resource_kind": resource_kind,
                "namespace": namespace,
                "tail_lines": tail_lines,
                "container": container,
                "since_seconds": since_seconds,
                "since_time": since_time,
                "follow": follow
            }
        )

        # Prepare query parameters
        params = {
            "resourceName": resource_name,
            "resourceKind": resource_kind,
            "tailLines": tail_lines,
            "follow": follow
        }
        if namespace:
            params["namespace"] = namespace
        if container:
            params["container"] = container
        if since_seconds:
            params["sinceSeconds"] = since_seconds
        if since_time:
            params["sinceTime"] = since_time

        # Construct the URL
        url = f"{server_url}/api/v1/applications/{application_name}/logs"
        
        # Log the full request URL
        log_info(
            f"Making request to URL: {url}",
            tool="argocd_api_get_workload_logs",
            params=params
        )

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                ssl=not bypass_tls
            ) as response:
                # Log the response status
                log_info(
                    f"Response status: {response.status}",
                    tool="argocd_api_get_workload_logs"
                )

                if response.status == 200:
                    try:
                        data = await response.json()
                        # Log the raw response
                        log_info(
                            f"Raw API response:",
                            tool="argocd_api_get_workload_logs",
                            response=data
                        )
                        return data
                    except Exception as e:
                        log_error(
                            f"Failed to parse response as JSON: {str(e)}",
                            tool="argocd_api_get_workload_logs",
                            error=str(e)
                        )
                        return None
                else:
                    error_text = await response.text()
                    log_error(
                        f"API request failed with status {response.status}: {error_text}",
                        tool="argocd_api_get_workload_logs",
                        error=error_text
                    )
                    return None

    except Exception as e:
        log_error(
            f"Error in argocd_api_get_workload_logs: {str(e)}",
            tool="argocd_api_get_workload_logs",
            error=str(e)
        )
        return None

async def argocd_api_get_pod_logs(
    server_url: str,
    token: str,
    application_name: str,
    pod_name: str,
    tail_lines: Optional[int] = 100,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Get logs for a specific pod in an ArgoCD application.
    
    Args:
        server_url (str): ArgoCD server URL
        token (str): ArgoCD API token
        application_name (str): Name of the application
        pod_name (str): Name of the pod
        tail_lines (int, optional): Number of log lines to retrieve
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        Optional[Dict[str, Any]]: The pod logs or None if the request fails
    """
    try:
        url = f"{server_url}/api/v1/applications/{application_name}/pods/{pod_name}/logs"
        params = {
            "follow": False,
            "tailLines": tail_lines
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                ssl=not bypass_tls
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception as e:
        log_error(
            f"Error in argocd_api_get_pod_logs: {str(e)}",
            tool="argocd_api_get_pod_logs",
            error=str(e)
        )
        return None

async def argocd_api_get_resource_events(
    server_url: str,
    token: str,
    application_name: str,
    resource_name: str,
    resource_kind: str,
    namespace: Optional[str] = None,
    bypass_tls: bool = False
) -> Dict[str, Any]:
    """Get events for a specific resource in an ArgoCD application."""
    try:
        # Log the parameters being sent
        log_info(
            f"Getting resource events with parameters:",
            tool="argocd_api_get_resource_events",
            params={
                "application_name": application_name,
                "resource_name": resource_name,
                "resource_kind": resource_kind,
                "namespace": namespace
            }
        )

        # Prepare query parameters
        params = {
            "resourceName": resource_name,
            "resourceKind": resource_kind
        }
        if namespace:
            params["namespace"] = namespace

        # Construct the URL
        url = f"{server_url}/api/v1/applications/{application_name}/events"
        
        # Log the full request URL
        log_info(
            f"Making request to URL: {url}",
            tool="argocd_api_get_resource_events",
            params=params
        )

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                ssl=not bypass_tls
            ) as response:
                # Log the response status
                log_info(
                    f"Response status: {response.status}",
                    tool="argocd_api_get_resource_events"
                )

                if response.status == 200:
                    try:
                        data = await response.json()
                        # Log the raw response
                        log_info(
                            f"Raw API response:",
                            tool="argocd_api_get_resource_events",
                            response=data
                        )
                        return data
                    except Exception as e:
                        log_error(
                            f"Failed to parse response as JSON: {str(e)}",
                            tool="argocd_api_get_resource_events",
                            error=str(e)
                        )
                        return None
                else:
                    error_text = await response.text()
                    log_error(
                        f"API request failed with status {response.status}: {error_text}",
                        tool="argocd_api_get_resource_events",
                        error=error_text
                    )
                    return None

    except Exception as e:
        log_error(
            f"Error in argocd_api_get_resource_events: {str(e)}",
            tool="argocd_api_get_resource_events",
            error=str(e)
        )
        return None

async def argocd_api_get_resource_actions(
    server_url: str,
    token: str,
    application_name: str,
    resource_name: str,
    resource_kind: str,
    namespace: Optional[str] = None,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Get available actions for a resource.
    
    Args:
        server_url (str): ArgoCD server URL
        token (str): ArgoCD API token
        application_name (str): Name of the application
        resource_name (str): Name of the resource
        resource_kind (str): Kind of the resource
        namespace (str, optional): Namespace of the resource
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: List of actions or None if request failed
    """
    path = f"/api/v1/applications/{application_name}/resource/actions"
    params = {
        "resourceName": resource_name,
        "resourceKind": resource_kind
    }
    if namespace:
        params["namespace"] = namespace
    return await argocd_api_get(path, token, server_url, params=params, bypass_tls=bypass_tls)

async def argocd_api_run_resource_action(
    server_url: str,
    token: str,
    application_name: str,
    resource_name: str,
    resource_kind: str,
    action_name: str,
    params: Optional[Dict[str, Any]] = None,
    namespace: Optional[str] = None,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Run an action on a resource.
    
    Args:
        server_url (str): ArgoCD server URL
        token (str): ArgoCD API token
        application_name (str): Name of the application
        resource_name (str): Name of the resource
        resource_kind (str): Kind of the resource
        action_name (str): Name of the action to run
        params (dict, optional): Action parameters
        namespace (str, optional): Namespace of the resource
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: Action result or None if request failed
    """
    path = f"/api/v1/applications/{application_name}/resource/actions"
    data = {
        "resourceName": resource_name,
        "resourceKind": resource_kind,
        "action": action_name
    }
    if params:
        data["params"] = params
    if namespace:
        data["namespace"] = namespace
    return await argocd_api_post(path, token, server_url, data, bypass_tls=bypass_tls)

async def argocd_api_get_application_manifest(
    server_url: str,
    token: str,
    application_name: str,
    revision: Optional[str] = None,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Get the manifest for an application.
    
    Args:
        server_url (str): ArgoCD server URL
        token (str): ArgoCD API token
        application_name (str): Name of the application
        revision (str, optional): Revision to get manifest for
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: Manifest data or None if request failed
    """
    path = f"/api/v1/applications/{application_name}/manifests"
    params = {}
    if revision:
        params["revision"] = revision
    return await argocd_api_get(path, token, server_url, params=params, bypass_tls=bypass_tls)

async def argocd_api_get_application_parameters(
    server_url: str,
    token: str,
    application_name: str,
    bypass_tls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Get parameters for an application.
    
    Args:
        server_url (str): ArgoCD server URL
        token (str): ArgoCD API token
        application_name (str): Name of the application
        bypass_tls (bool): Whether to bypass TLS verification
        
    Returns:
        dict: Parameters data or None if request failed
    """
    path = f"/api/v1/applications/{application_name}/parameters"
    return await argocd_api_get(path, token, server_url, bypass_tls=bypass_tls)

async def cached_api_call(
    url: str,
    headers: Tuple[Tuple[str, str], ...],
    params: Optional[Tuple[Tuple[str, str], ...]] = None
) -> Dict[str, Any]:
    """
    Make a cached API call.
    
    Args:
        url (str): API endpoint URL
        headers (Tuple[Tuple[str, str], ...]): Request headers
        params (Optional[Tuple[Tuple[str, str], ...]]): Query parameters
        
    Returns:
        Dict[str, Any]: Cached response data
    """
    cache_key = f"{url}:{headers}:{params}"
    logger.debug("Checking cache for key: {}", cache_key)
    
    if cache_key in _response_cache:
        logger.debug("Cache hit for key: {}", cache_key)
        return _response_cache[cache_key]
    
    logger.debug("Cache miss for key: {}", cache_key)
    async with create_session() as session:
        async with session.get(
            url,
            headers=dict(headers),
            params=dict(params) if params else None
        ) as resp:
            await validate_response(resp)
            data = await resp.json()
            _response_cache[cache_key] = data
            logger.debug("Cached response for key: {}", cache_key)
            return data
