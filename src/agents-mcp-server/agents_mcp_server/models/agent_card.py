from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import List, Optional, Any

class Capabilities(BaseModel):
    streaming: Optional[bool] = None
    pushNotifications: Optional[bool] = None
    stateTransitionHistory: Optional[bool] = None

    @field_validator('stateTransitionHistory', mode='before')
    @classmethod
    def at_least_one_present(cls, v, info):
        data = info.data or {}
        if not any([
            data.get('streaming'),
            data.get('pushNotifications'),
            v
        ]):
            raise ValueError('At least one capability field must be present in Capabilities')
        return v

class Authentication(BaseModel):
    credentials: Optional[Any] = None
    schemes: Optional[List[str]] = None

class Skill(BaseModel):
    id: str
    name: str
    description: str
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    inputModes: Optional[List[str]] = None
    outputModes: Optional[List[str]] = None

    @field_validator('id', 'name', 'description', mode='before')
    @classmethod
    def not_empty(cls, v, info):
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} must not be empty in Skill")
        return v

class AgentCard(BaseModel):
    """
    Agent Card metadata matching the google a2a agent card schema.
    """
    name: str
    description: Optional[str] = None
    url: Optional[HttpUrl] = None
    provider: Optional[str] = None
    version: str
    documentationUrl: Optional[str] = None
    capabilities: Optional[Capabilities] = None
    authentication: Optional[Authentication] = None
    defaultInputModes: Optional[List[str]] = None
    defaultOutputModes: Optional[List[str]] = None
    skills: Optional[List[Skill]] = None

    @field_validator('name', 'version', mode='before')
    @classmethod
    def not_empty(cls, v, info):
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} must not be empty")
        return v

    def serialize(self) -> dict:
        """Return a JSON-compatible dict, omitting None values."""
        return self.model_dump(exclude_none=True) 