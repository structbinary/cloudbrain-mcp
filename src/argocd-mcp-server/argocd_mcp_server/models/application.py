from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal


class ApplicationMetadata(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "guestbook",
                "namespace": "argocd",
                "project": "default",
                "labels": {"app": "guestbook"},
                "annotations": {"description": "Guestbook application"}
            }
        }
    )
    name: str = Field(..., description="Name of the application (required)")
    namespace: str = Field("argocd", description="Namespace of the application (optional, defaults to argocd)")
    project: str = Field(..., description="Project of the application (required)")
    labels: Optional[Dict[str, str]] = Field(None, description="Labels for the application")
    annotations: Optional[Dict[str, str]] = Field(None, description="Annotations for the application")

class ApplicationSource(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "repo_url": "https://github.com/argoproj/argocd-example-apps",
                "path": "guestbook",
                "target_revision": "HEAD"
            }
        }
    )
    repo_url: str = Field(..., description="Repository URL (required)")
    path: str = Field(..., description="Path in the repository (required)")
    target_revision: str = Field("HEAD", description="Target revision (optional, defaults to HEAD)")
    chart: Optional[str] = None
    helm: Optional[Dict[str, Any]] = None
    kustomize: Optional[Dict[str, Any]] = None
    directory: Optional[Dict[str, Any]] = None
    plugin: Optional[Dict[str, Any]] = None
    jsonnet: Optional[Dict[str, Any]] = None

class ApplicationDestination(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "server": "https://kubernetes.default.svc",
                "namespace": "default"
            }
        }
    )
    server: str = Field(..., description="Destination server URL (required)")
    namespace: Optional[str] = Field(None, description="Destination namespace (optional)")
    name: Optional[str] = Field(None, description="Destination name (optional)")

class SyncPolicyAutomated(BaseModel):
    """Model for automated sync policy configuration."""
    prune: bool = Field(
        default=True,
        description="Whether to automatically prune resources that are no longer in the Git repository"
    )
    self_heal: bool = Field(
        default=True,
        description="Whether to automatically heal resources that have drifted from their desired state"
    )
    allow_empty: bool = Field(
        default=False,
        description="Whether to allow syncing when there are no changes"
    )

class SyncPolicy(BaseModel):
    """Model for sync policy configuration."""
    automated: Optional[SyncPolicyAutomated] = Field(
        None,
        description="Automated sync policy configuration"
    )
    sync_options: Optional[List[str]] = Field(
        None,
        description="List of sync options (e.g., skip schema validation, prune last, etc.)"
    )
    prune_propagation_policy: Optional[Literal["foreground", "background", "orphan"]] = Field(
        "foreground",
        description="Prune propagation policy (foreground, background, or orphan)"
    )
    finalizer: Optional[bool] = Field(
        False,
        description="Whether to set deletion finalizer"
    )
    retry: Optional[Dict[str, Any]] = Field(
        None,
        description="Retry configuration for sync operations"
    )
    hooks: Optional[List[Dict[str, Any]]] = None

class SyncStrategy(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "hook": {
                    "force": True
                }
            }
        }
    )
    apply: Optional[Dict[str, Any]] = None
    hook: Optional[Dict[str, Any]] = None


class SyncOperation(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    initiated_by: Optional[Dict[str, str]] = None
    info: Optional[List[Dict[str, str]]] = None
    sync_strategy: Optional[SyncStrategy] = None
    resources: Optional[List[Dict[str, str]]] = None
    source: Optional[Dict[str, Any]] = None
    manifests: Optional[List[str]] = None
    dry_run: Optional[bool] = False
    prune: Optional[bool] = False
    force: Optional[bool] = False
    apply: Optional[bool] = False


class ApplicationSpec(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    source: ApplicationSource = Field(..., description="Source configuration (required)")
    destination: ApplicationDestination = Field(..., description="Destination configuration (required)")
    project: str = Field(..., description="Project name (required)")
    sync_policy: Optional[SyncPolicy] = Field(
        None,
        description="Sync policy configuration (optional)"
    )
    operation: Optional[Dict[str, Any]] = None


class ApplicationStatus(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    sync_status: Optional[str] = None
    health_status: Optional[str] = None
    operation_state: Optional[Dict[str, Any]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    history: Optional[List[Dict[str, Any]]] = None
    reconciled_at: Optional[str] = None
    source_type: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None


class ApplicationModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    metadata: ApplicationMetadata
    spec: ApplicationSpec
    status: Optional[ApplicationStatus] = None

# Create Application
class CreateApplicationRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application: ApplicationModel

class CreateApplicationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Application created successfully"
    application: Optional[ApplicationModel] = None
    status_code: int = 201
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "CreateApplicationResponse":
        return cls(
            success=False,
            message=message,
            application=None,
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, application: ApplicationModel, message: str = "Application created successfully") -> "CreateApplicationResponse":
        return cls(
            success=True,
            message=message,
            application=application,
            status_code=201,
            resource="application"
        )


# Update Application
class UpdateApplicationRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    application: ApplicationModel

class UpdateApplicationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Application updated successfully"
    application: Optional[ApplicationModel] = None
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "UpdateApplicationResponse":
        return cls(
            success=False,
            message=message,
            application=None,
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, application: ApplicationModel, message: str = "Application updated successfully") -> "UpdateApplicationResponse":
        return cls(
            success=True,
            message=message,
            application=application,
            status_code=200,
            resource="application"
        )

# Delete Application
class DeleteApplicationRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    name: str
    namespace: Optional[str] = None
    cascade: Optional[bool] = True

class DeleteApplicationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Application deleted successfully"
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "DeleteApplicationResponse":
        return cls(
            success=False,
            message=message,
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, message: str = "Application deleted successfully") -> "DeleteApplicationResponse":
        return cls(
            success=True,
            message=message,
            status_code=200,
            resource="application"
        )

# Sync Application
class SyncApplicationRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    name: str
    namespace: Optional[str] = None

class SyncApplicationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Application Synced Successfully"
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "SyncApplicationResponse":
        return cls(
            success=False,
            message=message,
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, message: str = "Application Synced Successfully") -> "SyncApplicationResponse":
        return cls(
            success=True,
            message=message,
            status_code=200,
            resource="application"
        )

# Get Application
class GetApplicationRequest(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    name: str

class GetApplicationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    success: bool = True
    message: str = "Application Retrieved Successfully"
    status_code: int = 200
    resource: str = "application"

    @classmethod
    def error(cls, message: str, status_code: int = 500, resource: str = "application") -> "GetApplicationResponse":
        return cls(
            success=False,
            message=message,
            status_code=status_code,
            resource=resource
        )

    @classmethod
    def success(cls, message: str = "Application Retrieved Successfully") -> "GetApplicationResponse":
        return cls(
            success=True,
            message=message,
            status_code=200,
            resource="application"
        )