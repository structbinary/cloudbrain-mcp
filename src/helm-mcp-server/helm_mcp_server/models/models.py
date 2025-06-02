from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from mcp.types import CallToolResult

# 1. Install Chart
class InstallChartInput(BaseModel):
    release_name: str = Field(..., description="Name of the Helm release to create.")
    chart: str = Field(..., description="Chart name (e.g., 'bitnami/nginx').")
    version: Optional[str] = Field(None, description="Chart version to install.")
    namespace: Optional[str] = Field(None, description="Kubernetes namespace to install the chart into.")
    values: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom values for the chart (will be written to a temp YAML file and passed as -f).")
    values_files: Optional[List[str]] = Field(default_factory=list, description="List of values YAML files (paths or URLs) to use with -f.")
    values_file_content: Optional[str] = Field(None, description="Raw YAML content to use as a values file (will be written to a temp file and passed as -f).")
    extra_args: Optional[List[str]] = Field(default_factory=list, description="Extra CLI flags to pass to helm install.")
    repo_url: Optional[str] = Field(None, description="Repository URL to add before install (e.g., https://charts.bitnami.com/bitnami).")
    create_namespace: Optional[bool] = Field(False, description="Whether to create the namespace if it does not exist.")
    atomic: Optional[bool] = Field(False, description="If set, installation process purges chart on fail. Useful for CI/CD.")
    wait: Optional[bool] = Field(False, description="Wait until all resources are in a ready state before marking the release as successful.")
    timeout: Optional[str] = Field(None, description="Time to wait for any individual Kubernetes operation (e.g., 5m, 1h).")

class InstallChartOutput(CallToolResult):
    release_name: str = Field(..., description="Name of the Helm release created.")
    status: str = Field(..., description="Status of the release after installation.")
    notes: Optional[str] = Field(None, description="Notes or output from Helm install.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details from Helm.")

# 2. Upgrade Release
class UpgradeReleaseInput(BaseModel):
    release_name: str = Field(..., description="Name of the Helm release to upgrade.")
    chart: Optional[str] = Field(None, description="Chart name if upgrading to a new chart.")
    version: Optional[str] = Field(None, description="Chart version to upgrade to.")
    namespace: Optional[str] = Field(None, description="Kubernetes namespace of the release.")
    values: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom values for the upgrade.")

class UpgradeReleaseOutput(CallToolResult):
    release_name: str = Field(..., description="Name of the Helm release upgraded.")
    status: str = Field(..., description="Status of the release after upgrade.")
    notes: Optional[str] = Field(None, description="Notes or output from Helm upgrade.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details from Helm.")

# 3. List Releases
class ListReleasesInput(BaseModel):
    namespace: Optional[str] = Field(None, description="Namespace to list releases from.")

class ReleaseInfo(BaseModel):
    release_name: str = Field(..., description="Name of the Helm release.")
    chart: str = Field(..., description="Chart name.")
    version: str = Field(..., description="Chart version.")
    namespace: str = Field(..., description="Kubernetes namespace.")
    status: str = Field(..., description="Status of the release.")

class ListReleasesOutput(CallToolResult):
    count: int = Field(..., description="Number of releases found.")
    releases: List[ReleaseInfo] = Field(..., description="List of Helm releases.")

# 4. Uninstall Release
class UninstallReleaseInput(BaseModel):
    release_name: str = Field(..., description="Name of the Helm release to uninstall.")
    namespace: Optional[str] = Field(None, description="Namespace of the release.")
    keep_history: Optional[bool] = Field(False, description="Whether to keep release history.")

class UninstallReleaseOutput(CallToolResult):
    release_name: str = Field(..., description="Name of the Helm release uninstalled.")
    status: str = Field(..., description="Status after uninstall operation.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details from Helm.")

# 5. Search Repository
# class SearchRepositoryInput(BaseModel):
#     query: str = Field(..., description="Search term for the chart.")
#     repository_url: Optional[str] = Field(None, description="URL of the Helm repository to search (e.g., ArtifactHub, GitHub).")

class ChartMaintainer(BaseModel):
    name: str = Field(..., description="Maintainer's name.")
    email: Optional[str] = Field(None, description="Maintainer's email address.")
    url: Optional[str] = Field(None, description="Maintainer's profile or homepage URL.")

class ChartSearchResult(BaseModel):
    name: str = Field(..., description="Chart name.")
    description: Optional[str] = Field(None, description="Chart description.")
    version: Optional[str] = Field(None, description="Chart version.")
    repository: Optional[str] = Field(None, description="Repository name or URL.")
    url: Optional[str] = Field(None, description="URL to the chart or its documentation.")
    home: Optional[str] = Field(None, description="Home page for the chart.")
    icon: Optional[str] = Field(None, description="URL to the chart's icon.")
    keywords: Optional[List[str]] = Field(default_factory=list, description="List of keywords for the chart.")
    maintainers: Optional[List[ChartMaintainer]] = Field(default_factory=list, description="List of chart maintainers.")
    license: Optional[str] = Field(None, description="Chart license (SPDX identifier).")
    sources: Optional[List[str]] = Field(default_factory=list, description="List of source URLs for the chart.")
    category: Optional[str] = Field(None, description="Chart category (e.g., security, database, etc.).")
    app_version: Optional[str] = Field(None, description="The version of the application enclosed inside the chart.")
    readme: Optional[str] = Field(None, description="Chart README content (truncated if large).")
    crds: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="List of CRDs provided by the chart.")
    screenshots: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="List of screenshots for the chart.")
    links: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="List of named links (e.g., support, docs, etc.).")
    operator: Optional[bool] = Field(None, description="Whether the chart is an operator.")
    category_prediction: Optional[str] = Field(None, description="Predicted category if not explicitly set.")

class SearchRepositoryOutput(CallToolResult):
    count: int = Field(..., description="Number of charts found.")
    results: List[ChartSearchResult] = Field(..., description="List of chart search results.") 