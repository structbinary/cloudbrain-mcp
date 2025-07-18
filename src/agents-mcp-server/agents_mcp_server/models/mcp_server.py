from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from typing import List, Dict, Any, Optional, Literal

class ServerConnection(BaseModel):
    transport: Literal['streamable_http', 'stdio']
    endpoint: Optional[HttpUrl] = None 
    auth_method: str
    headers: Optional[Dict[str, str]] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    required_env: Optional[List[str]] = None

    @field_validator('auth_method', mode='before')
    @classmethod
    def not_empty(cls, v, info):
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} must not be empty in ServerConnection")
        return v

    @model_validator(mode='after')
    def check_transport_requirements(self):
        if self.transport == 'streamable_http':
            if not self.endpoint:
                raise ValueError("endpoint (url) is required when transport is 'streamable_http'")
            if self.command is not None or self.args is not None or self.required_env is not None:
                raise ValueError("command, args, and required_env must not be set when transport is 'streamable_http'")
        if self.transport == 'stdio':
            if self.endpoint is not None:
                raise ValueError("endpoint (url) should not be set when transport is 'stdio'")
            if self.headers is not None:
                raise ValueError("headers should not be set when transport is 'stdio'")
            if not self.command or not self.args:
                raise ValueError("command and args are required when transport is 'stdio'")
        return self

class ServerCompatibility(BaseModel):
    agent_types: List[str]
    requirements: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('agent_types', mode='before')
    @classmethod
    def not_empty(cls, v, info):
        if not v or (isinstance(v, list) and not v):
            raise ValueError("agent_types must not be empty in ServerCompatibility")
        return v

class Authentication(BaseModel):
    credentials: Optional[Any] = None
    schemes: Optional[List[str]] = None

class MCPServer(BaseModel):
    id: str
    name: str
    version: str
    capabilities: List[str]
    connection: ServerConnection
    compatibility: ServerCompatibility
    description: Optional[str] = None
    authentication: Optional[Authentication] = None

    @field_validator('id', 'name', 'version', mode='before')
    @classmethod
    def not_empty(cls, v, info):
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} must not be empty in MCPServer")
        return v

    @field_validator('capabilities', mode='before')
    @classmethod
    def capabilities_not_empty(cls, v, info):
        if not v or (isinstance(v, list) and not v):
            raise ValueError("capabilities must not be empty in MCPServer")
        return v

    def serialize(self) -> dict:
        """Return a JSON-compatible dict, omitting None values."""
        return self.model_dump(exclude_none=True) 