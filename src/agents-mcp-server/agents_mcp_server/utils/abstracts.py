from abc import ABC, abstractmethod
from typing import Any

class MCPTool(ABC):
    """
    Abstract base class defining the interface for all MCP tools.
    All tool implementations must inherit from this class and implement
    all abstract methods and properties.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the tool.
        Returns:
            str: A unique, descriptive name for the tool.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        The description of the tool.
        Returns:
            str: A detailed description of the tool's functionality.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool's primary function.
        Args:
            **kwargs: Tool-specific parameters.
        Returns:
            Any: The result of the tool execution.
        """
        pass

class MCPResource(ABC):
    """
    Abstract base class for all MCP resources.
    Subclasses must implement the required interface for resource handling.
    """

    @abstractmethod
    def get(self, **kwargs) -> Any:
        """
        Retrieve resource data.
        Args:
            **kwargs: Resource-specific parameters.
        Returns:
            Any: The resource data.
        """
        pass

"""
Usage Example:

class MyTool(MCPTool):
    @property
    def name(self) -> str:
        return "my_tool"
    @property
    def description(self) -> str:
        return "A sample tool."
    def execute(self, **kwargs) -> Any:
        return "Executed!"

class MyResource(MCPResource):
    def get(self, **kwargs) -> Any:
        return {"data": "resource data"}
""" 