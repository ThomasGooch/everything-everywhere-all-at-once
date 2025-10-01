"""
Workspace Management System for AI Development Automation
Provides isolated workspaces for concurrent agent operations
"""
import asyncio
import os
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from .exceptions import WorkspaceError, WorkspaceCleanupError

logger = logging.getLogger(__name__)


class WorkspaceStatus(Enum):
    """Workspace status enumeration"""
    ACTIVE = "active"
    CLEANING = "cleaning"
    CLEANED = "cleaned"
    ERROR = "error"


@dataclass
class Workspace:
    """Workspace data model"""
    id: str
    path: str
    repository_url: str
    created_at: datetime
    status: WorkspaceStatus




class WorkspaceManager:
    """Manages isolated workspaces for concurrent agent operations"""
    
    def __init__(self, base_dir: str):
        """Initialize WorkspaceManager with base directory"""
        self.base_dir = base_dir
        self.workspaces: Dict[str, Workspace] = {}
        
        # Create base directory if it doesn't exist
        os.makedirs(base_dir, exist_ok=True)
    
    async def create_workspace(
        self, 
        agent_id: str, 
        repository_url: str, 
        setup_git: bool = False
    ) -> Workspace:
        """Create isolated workspace for an agent"""
        if agent_id in self.workspaces:
            raise WorkspaceError(f"Workspace for agent {agent_id} already exists")
        
        # Create workspace directory
        workspace_path = os.path.join(self.base_dir, agent_id)
        
        if os.path.exists(workspace_path):
            raise WorkspaceError(f"Workspace directory {workspace_path} already exists")
        
        # Create directory with appropriate permissions
        os.makedirs(workspace_path, mode=0o750)
        
        # Create workspace object
        workspace = Workspace(
            id=agent_id,
            path=workspace_path,
            repository_url=repository_url,
            created_at=datetime.utcnow(),
            status=WorkspaceStatus.ACTIVE
        )
        
        # Setup Git if requested
        if setup_git:
            from .git_operations import GitOperations
            git_ops = GitOperations()
            await git_ops.setup_repository()
        
        # Store workspace
        self.workspaces[agent_id] = workspace
        
        logger.info(f"Created workspace for agent {agent_id} at {workspace_path}")
        return workspace
    
    async def get_workspace(self, agent_id: str) -> Workspace:
        """Retrieve workspace for an agent"""
        if agent_id not in self.workspaces:
            raise WorkspaceError(f"Workspace for agent {agent_id} not found")
        
        return self.workspaces[agent_id]
    
    async def list_workspaces(self) -> List[Workspace]:
        """List all active workspaces"""
        return list(self.workspaces.values())
    
    async def cleanup_workspace(
        self, 
        agent_id: str, 
        preserve_logs: bool = True
    ) -> bool:
        """Cleanup workspace and optionally preserve logs"""
        if agent_id not in self.workspaces:
            raise WorkspaceError(f"Workspace for agent {agent_id} not found")
        
        workspace = self.workspaces[agent_id]
        workspace_path = workspace.path
        
        try:
            # Archive logs if requested
            if preserve_logs:
                log_files = list(Path(workspace_path).glob("*.log"))
                if log_files:
                    from .archive_manager import ArchiveManager
                    archive_manager = ArchiveManager()
                    await archive_manager.archive_logs(workspace_path)
            
            # Remove workspace directory
            if os.path.exists(workspace_path):
                shutil.rmtree(workspace_path)
            
            # Update workspace status and remove from tracking
            workspace.status = WorkspaceStatus.CLEANED
            del self.workspaces[agent_id]
            
            logger.info(f"Successfully cleaned up workspace for agent {agent_id}")
            return True
            
        except Exception as e:
            workspace.status = WorkspaceStatus.ERROR
            raise WorkspaceCleanupError(f"Failed to cleanup workspace for {agent_id}: {e}")
    
    async def cleanup_all_workspaces(self, preserve_logs: bool = True) -> Dict[str, bool]:
        """Cleanup all workspaces"""
        results = {}
        agent_ids = list(self.workspaces.keys())
        
        for agent_id in agent_ids:
            try:
                success = await self.cleanup_workspace(agent_id, preserve_logs)
                results[agent_id] = success
            except WorkspaceCleanupError:
                results[agent_id] = False
        
        return results