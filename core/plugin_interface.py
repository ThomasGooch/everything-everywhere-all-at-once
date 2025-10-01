"""Base plugin interfaces for the AI Development Orchestrator"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Supported plugin types"""
    TASK_MANAGEMENT = "task_management"
    VERSION_CONTROL = "version_control"
    COMMUNICATION = "communication"
    DOCUMENTATION = "documentation"
    AI_PROVIDER = "ai_provider"
    CI_CD = "ci_cd"


class PluginStatus(Enum):
    """Plugin health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PluginError(Exception):
    """Base exception for plugin operations"""
    pass


class PluginValidationError(PluginError):
    """Raised when plugin configuration or implementation is invalid"""
    pass


class PluginConnectionError(PluginError):
    """Raised when plugin cannot connect to external service"""
    pass


class PluginResult(BaseModel):
    """Standard result format for plugin operations"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BasePlugin(ABC):
    """Abstract base class for all plugins"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize plugin with configuration
        
        Args:
            config: Plugin-specific configuration dictionary
        """
        self.config = config
        self.plugin_id = f"{self.get_plugin_type().value}_{self.get_plugin_name()}"
        self._is_initialized = False
        self._connection_established = False
        
    @abstractmethod
    def get_plugin_type(self) -> PluginType:
        """Return the plugin type"""
        pass
    
    @abstractmethod
    def get_plugin_name(self) -> str:
        """Return the specific plugin name (e.g., 'jira', 'github')"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Return plugin version"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin and establish connections
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """Clean up plugin resources
        
        Returns:
            True if cleanup successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> PluginStatus:
        """Check plugin health status
        
        Returns:
            Current plugin health status
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate plugin configuration
        
        Returns:
            True if configuration is valid, False otherwise
            
        Raises:
            PluginValidationError: If configuration is invalid
        """
        pass
    
    def get_required_config_keys(self) -> List[str]:
        """Return list of required configuration keys
        
        Returns:
            List of required configuration key names
        """
        return []
    
    def get_optional_config_keys(self) -> List[str]:
        """Return list of optional configuration keys
        
        Returns:
            List of optional configuration key names
        """
        return []
    
    async def test_connection(self) -> bool:
        """Test connection to external service
        
        Returns:
            True if connection successful, False otherwise
        """
        return True
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get plugin information
        
        Returns:
            Dictionary containing plugin metadata
        """
        return {
            "plugin_id": self.plugin_id,
            "plugin_type": self.get_plugin_type().value,
            "plugin_name": self.get_plugin_name(),
            "version": self.get_version(),
            "initialized": self._is_initialized,
            "connected": self._connection_established,
            "config_keys": {
                "required": self.get_required_config_keys(),
                "optional": self.get_optional_config_keys()
            }
        }


class TaskManagementPlugin(BasePlugin):
    """Base class for task management plugins (Jira, Linear, etc.)"""
    
    @abstractmethod
    async def get_task(self, task_id: str) -> PluginResult:
        """Retrieve task details
        
        Args:
            task_id: External task identifier
            
        Returns:
            PluginResult with task data
        """
        pass
    
    @abstractmethod
    async def create_task(self, project_key: str, task_data: Dict[str, Any]) -> PluginResult:
        """Create a new task
        
        Args:
            project_key: Project identifier
            task_data: Task information
            
        Returns:
            PluginResult with created task ID
        """
        pass
    
    @abstractmethod
    async def update_task_status(self, task_id: str, status: str) -> PluginResult:
        """Update task status
        
        Args:
            task_id: Task identifier
            status: New status
            
        Returns:
            PluginResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def add_comment(self, task_id: str, comment: str) -> PluginResult:
        """Add comment to task
        
        Args:
            task_id: Task identifier
            comment: Comment text
            
        Returns:
            PluginResult indicating success/failure
        """
        pass


class VersionControlPlugin(BasePlugin):
    """Base class for version control plugins (GitHub, GitLab, etc.)"""
    
    @abstractmethod
    async def clone_repository(self, url: str, local_path: str) -> PluginResult:
        """Clone repository to local path
        
        Args:
            url: Repository URL
            local_path: Local directory path
            
        Returns:
            PluginResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def create_branch(self, repo_path: str, branch_name: str, base_branch: str = "main") -> PluginResult:
        """Create a new branch
        
        Args:
            repo_path: Local repository path
            branch_name: Name for new branch
            base_branch: Base branch to create from
            
        Returns:
            PluginResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def commit_changes(self, repo_path: str, message: str, files: List[str]) -> PluginResult:
        """Commit changes to repository
        
        Args:
            repo_path: Local repository path
            message: Commit message
            files: List of files to commit
            
        Returns:
            PluginResult with commit hash
        """
        pass
    
    @abstractmethod
    async def push_branch(self, repo_path: str, branch_name: str) -> PluginResult:
        """Push branch to remote
        
        Args:
            repo_path: Local repository path
            branch_name: Branch to push
            
        Returns:
            PluginResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def create_pull_request(self, repo_path: str, pr_data: Dict[str, Any]) -> PluginResult:
        """Create pull request
        
        Args:
            repo_path: Local repository path
            pr_data: Pull request information
            
        Returns:
            PluginResult with PR URL
        """
        pass


class CommunicationPlugin(BasePlugin):
    """Base class for communication plugins (Slack, Teams, etc.)"""
    
    @abstractmethod
    async def send_message(self, channel: str, message: str, thread_id: Optional[str] = None) -> PluginResult:
        """Send message to channel
        
        Args:
            channel: Channel identifier
            message: Message text
            thread_id: Optional thread ID for replies
            
        Returns:
            PluginResult with message ID
        """
        pass
    
    @abstractmethod
    async def send_direct_message(self, user_id: str, message: str) -> PluginResult:
        """Send direct message to user
        
        Args:
            user_id: User identifier
            message: Message text
            
        Returns:
            PluginResult with message ID
        """
        pass


class DocumentationPlugin(BasePlugin):
    """Base class for documentation plugins (Confluence, Notion, etc.)"""
    
    @abstractmethod
    async def create_page(self, space: str, title: str, content: str) -> PluginResult:
        """Create documentation page
        
        Args:
            space: Documentation space/project
            title: Page title
            content: Page content
            
        Returns:
            PluginResult with page ID
        """
        pass
    
    @abstractmethod
    async def update_page(self, page_id: str, content: str) -> PluginResult:
        """Update existing page
        
        Args:
            page_id: Page identifier
            content: Updated content
            
        Returns:
            PluginResult indicating success/failure
        """
        pass


class AIProviderPlugin(BasePlugin):
    """Base class for AI provider plugins (Claude, OpenAI, etc.)"""
    
    @abstractmethod
    async def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> PluginResult:
        """Generate text from prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            PluginResult with generated text
        """
        pass
    
    @abstractmethod
    async def estimate_cost(self, prompt: str, max_tokens: int = 1000) -> float:
        """Estimate cost for generation request
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Estimated cost in USD
        """
        pass