from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal


# Get Application Resource Tree
class GetResourceTreeRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application_name: str
    namespace: Optional[str] = None


# Get Application Managed Resources
class GetManagedResourcesRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application_name: str
    namespace: Optional[str] = None


# Get Application Workload Logs
class GetWorkloadLogsRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application_name: str
    resource_name: str
    resource_kind: str
    namespace: Optional[str] = None
    tail_lines: Optional[int] = 100

# Get Resource Events
class GetResourceEventsRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application_name: str
    resource_name: str
    resource_kind: str
    namespace: Optional[str] = None


# Get Resource Actions
class GetResourceActionsRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application_name: str
    resource_name: str
    resource_kind: str
    namespace: Optional[str] = None

# Run Resource Action
class RunResourceActionRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application_name: str
    resource_name: str
    resource_kind: str
    action_name: str
    params: Optional[Dict[str, Any]] = None
    namespace: Optional[str] = None

# Get Application Resource Tree
class GetResourceTreeRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application_name: str
    namespace: Optional[str] = None

class ResourceNode(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "kind": "Deployment",
                "name": "guestbook",
                "namespace": "default",
                "status": "Synced",
                "health": {"status": "Healthy"},
                "children": [],
            }
        }
    )
    kind: str
    name: str
    namespace: Optional[str] = None
    status: Optional[str] = None
    health: Optional[Dict[str, Any]] = None
    children: Optional[List["ResourceNode"]] = None

class GetResourceTreeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Resource tree retrieved successfully"
    root: Optional[ResourceNode] = None
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "GetResourceTreeResponse":
        return cls(
            success=False,
            message=message,
            root=None,
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, root: ResourceNode, message: str = "Resource tree retrieved successfully") -> "GetResourceTreeResponse":
        return cls(
            success=True,
            message=message,
            root=root,
            status_code=200,
            resource="application"
        )

class ManagedResource(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "kind": "Deployment",
                "name": "guestbook",
                "namespace": "default",
                "status": "Synced",
                "health": "Healthy",
                "group": "apps",
                "version": "v1"
            }
        }
    )
    kind: str
    name: str
    namespace: Optional[str] = None
    status: Optional[str] = None
    health: Optional[str] = None
    group: Optional[str] = None
    version: Optional[str] = None

class GetManagedResourcesResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Managed resources retrieved successfully"
    resources: List[ManagedResource] = []
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "GetManagedResourcesResponse":
        return cls(
            success=False,
            message=message,
            resources=[],
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, resources: List[ManagedResource], message: str = "Managed resources retrieved successfully") -> "GetManagedResourcesResponse":
        return cls(
            success=True,
            message=message,
            resources=resources,
            status_code=200,
            resource="application"
        )

class WorkloadLogEntry(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    timestamp: str
    message: str
    container: Optional[str] = None

class GetWorkloadLogsResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Workload logs retrieved successfully"
    logs: List[WorkloadLogEntry] = []
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "GetWorkloadLogsResponse":
        return cls(
            success=False,
            message=message,
            logs=[],
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, logs: List[WorkloadLogEntry], message: str = "Workload logs retrieved successfully") -> "GetWorkloadLogsResponse":
        return cls(
            success=True,
            message=message,
            logs=logs,
            status_code=200,
            resource="application"
        )

class ResourceEvent(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    type: str
    reason: str
    message: str
    timestamp: str
    count: Optional[int] = None
    source: Optional[Dict[str, str]] = None

class GetResourceEventsResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Resource events retrieved successfully"
    events: List[ResourceEvent] = []
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "GetResourceEventsResponse":
        return cls(
            success=False,
            message=message,
            events=[],
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, events: List[ResourceEvent], message: str = "Resource events retrieved successfully") -> "GetResourceEventsResponse":
        return cls(
            success=True,
            message=message,
            events=events,
            status_code=200,
            resource="application"
        )

class ResourceAction(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    name: str
    description: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class GetResourceActionsResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Resource actions retrieved successfully"
    actions: List[ResourceAction] = []
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "GetResourceActionsResponse":
        return cls(
            success=False,
            message=message,
            actions=[],
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, actions: List[ResourceAction], message: str = "Resource actions retrieved successfully") -> "GetResourceActionsResponse":
        return cls(
            success=True,
            message=message,
            actions=actions,
            status_code=200,
            resource="application"
        )



class RunResourceActionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Resource action executed successfully"
    result: Optional[Dict[str, Any]] = None
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "RunResourceActionResponse":
        return cls(
            success=False,
            message=message,
            result=None,
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, result: Dict[str, Any], message: str = "Resource action executed successfully") -> "RunResourceActionResponse":
        return cls(
            success=True,
            message=message,
            result=result,
            status_code=200,
            resource="application"
        )