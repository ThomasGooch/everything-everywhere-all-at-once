"""
Code Modifier for safe code changes with validation and backup
Provides secure code modification with proper error handling and rollback capabilities
"""
import asyncio
import ast
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

from .exceptions import BaseSystemError

logger = logging.getLogger(__name__)


class ModificationError(BaseSystemError):
    """Exception raised for code modification errors"""
    pass


class ValidationError(ModificationError):
    """Exception raised for code validation errors"""
    pass


@dataclass
class FileChange:
    """Represents a single file change"""
    path: str
    action: str  # create, modify, delete
    content: Optional[str] = None
    backup_path: Optional[str] = None


@dataclass
class Implementation:
    """Complete implementation with all file changes"""
    task_id: str
    description: str
    files: List[FileChange]
    commit_message: str
    pr_description: Optional[str] = None
    breaking_changes: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of code validation"""
    is_valid: bool
    syntax_errors: List[str] = field(default_factory=list)
    linting_issues: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ModificationResult:
    """Result of code modification operation"""
    success: bool
    files_modified: int = 0
    backup_created: bool = False
    backup_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BackupResult:
    """Result of backup operation"""
    success: bool
    backup_id: Optional[str] = None
    files_restored: int = 0
    error: Optional[str] = None


class CodeModifier:
    """Safe code modification with validation and backup capabilities"""
    
    # Security patterns to detect
    SECURITY_PATTERNS = {
        'python': [
            (r'eval\s*\(', 'Use of eval() detected - security risk'),
            (r'exec\s*\(', 'Use of exec() detected - security risk'),
            (r'subprocess\.(call|run|Popen).*shell\s*=\s*True', 'Shell injection risk in subprocess'),
            (r'os\.system\s*\(', 'Use of os.system() detected - security risk'),
            (r'__import__\s*\(', 'Dynamic import detected - potential security risk'),
            (r'open\s*\([^)]*[\'"][wax]', 'File write operation detected - review permissions'),
        ],
        'javascript': [
            (r'eval\s*\(', 'Use of eval() detected - security risk'),
            (r'Function\s*\(', 'Dynamic function creation - security risk'),
            (r'innerHTML\s*=', 'innerHTML assignment - XSS risk'),
            (r'document\.write\s*\(', 'document.write usage - XSS risk'),
            (r'setTimeout\s*\(\s*[\'"]', 'String-based setTimeout - security risk'),
            (r'setInterval\s*\(\s*[\'"]', 'String-based setInterval - security risk'),
        ]
    }
    
    def __init__(self):
        """Initialize CodeModifier"""
        pass
    
    async def apply_code_changes(
        self,
        workspace,
        implementation: Implementation
    ) -> ModificationResult:
        """Apply code changes to workspace with validation and backup"""
        try:
            # Validate all changes before applying
            validation_errors = []
            for file_change in implementation.files:
                if file_change.action in ['create', 'modify'] and file_change.content:
                    language = self._detect_language(file_change.path)
                    validation_result = await self.validate_generated_code(
                        file_change.content, language
                    )
                    if not validation_result.is_valid:
                        validation_errors.extend(validation_result.syntax_errors)
                        validation_errors.extend(validation_result.security_issues)
            
            if validation_errors:
                raise ValidationError(f"Code validation failed: {'; '.join(validation_errors)}")
            
            # Create backup of existing files
            files_to_backup = []
            for file_change in implementation.files:
                file_path = Path(workspace.path) / file_change.path
                if file_path.exists() and file_change.action in ['modify', 'delete']:
                    files_to_backup.append(file_change.path)
            
            backup_id = None
            if files_to_backup:
                backup_id = await self.create_backup(workspace, files_to_backup)
            
            # Apply changes atomically
            applied_changes = []
            created_files = []  # Track files we created for rollback
            
            try:
                for file_change in implementation.files:
                    # Track files we're about to create (before attempting to create them)
                    file_path = Path(workspace.path) / file_change.path
                    if file_change.action == 'create' and not file_path.exists():
                        created_files.append(file_path)
                    
                    success = await self._apply_file_change(workspace, file_change)
                    if success:
                        applied_changes.append(file_change)
                    else:
                        raise ModificationError(f"Failed to apply change to {file_change.path}")
                
                logger.info(f"Successfully applied {len(applied_changes)} file changes")
                return ModificationResult(
                    success=True,
                    files_modified=len(applied_changes),
                    backup_created=backup_id is not None,
                    backup_id=backup_id
                )
                
            except Exception as e:
                logger.warning(f"Rolling back due to error: {e}")
                
                # Rollback: restore from backup first
                if backup_id:
                    try:
                        await self.restore_backup(workspace, backup_id)
                    except Exception as restore_error:
                        logger.error(f"Failed to restore backup during rollback: {restore_error}")
                
                # Remove any files we created
                for file_path in created_files:
                    try:
                        if file_path.exists():
                            file_path.unlink()
                    except Exception as cleanup_error:
                        logger.error(f"Failed to cleanup {file_path} during rollback: {cleanup_error}")
                
                raise ModificationError(f"Failed to apply code changes: {e}")
                
        except (ValidationError, ModificationError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in apply_code_changes: {e}")
            raise ModificationError(f"Unexpected error: {e}")
    
    async def validate_generated_code(self, code: str, language: str) -> ValidationResult:
        """Validate generated code for syntax and security issues"""
        result = ValidationResult(is_valid=True)
        
        try:
            # Syntax validation
            if language == 'python':
                await self._validate_python_syntax(code, result)
            elif language in ['javascript', 'typescript']:
                await self._validate_javascript_syntax(code, result)
            
            # Security validation
            await self._validate_security_issues(code, language, result)
            
            # Set overall validity
            result.is_valid = (
                len(result.syntax_errors) == 0 and 
                len(result.security_issues) == 0
            )
            
            logger.debug(f"Code validation result: valid={result.is_valid}, "
                        f"syntax_errors={len(result.syntax_errors)}, "
                        f"security_issues={len(result.security_issues)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during code validation: {e}")
            result.is_valid = False
            result.syntax_errors.append(f"Validation error: {e}")
            return result
    
    async def create_backup(self, workspace, file_paths: List[str]) -> str:
        """Create backup of specified files"""
        backup_id = str(uuid.uuid4())[:8]
        backup_dir = Path(workspace.path) / ".backups" / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            for file_path in file_paths:
                source_path = Path(workspace.path) / file_path
                if source_path.exists():
                    dest_path = backup_dir / file_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
            
            # Create metadata file
            metadata = {
                'backup_id': backup_id,
                'created_at': datetime.utcnow().isoformat(),
                'files': file_paths
            }
            
            metadata_file = backup_dir / '.backup_metadata.json'
            import json
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Created backup {backup_id} with {len(file_paths)} files")
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            # Cleanup partial backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
            raise ModificationError(f"Failed to create backup: {e}")
    
    async def restore_backup(self, workspace, backup_id: str) -> BackupResult:
        """Restore files from backup"""
        backup_dir = Path(workspace.path) / ".backups" / backup_id
        
        if not backup_dir.exists():
            raise ModificationError(f"Backup not found: {backup_id}")
        
        try:
            # Read metadata
            metadata_file = backup_dir / '.backup_metadata.json'
            if metadata_file.exists():
                import json
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                files_to_restore = metadata.get('files', [])
            else:
                # Fallback: restore all files in backup
                files_to_restore = [
                    str(f.relative_to(backup_dir))
                    for f in backup_dir.rglob('*')
                    if f.is_file() and f.name != '.backup_metadata.json'
                ]
            
            restored_count = 0
            for file_path in files_to_restore:
                backup_file = backup_dir / file_path
                dest_file = Path(workspace.path) / file_path
                
                if backup_file.exists():
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, dest_file)
                    restored_count += 1
            
            logger.info(f"Restored {restored_count} files from backup {backup_id}")
            return BackupResult(
                success=True,
                backup_id=backup_id,
                files_restored=restored_count
            )
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return BackupResult(
                success=False,
                error=str(e)
            )
    
    async def _apply_file_change(self, workspace, file_change: FileChange) -> bool:
        """Apply a single file change"""
        file_path = Path(workspace.path) / file_change.path
        
        try:
            if file_change.action == 'create':
                # Create new file
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_change.content, encoding='utf-8')
                
            elif file_change.action == 'modify':
                # Check if file exists and is writable
                if not file_path.exists():
                    # Create file if it doesn't exist
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    # Check permissions
                    if not os.access(file_path, os.W_OK):
                        raise ModificationError(f"No write permission for {file_change.path}")
                
                file_path.write_text(file_change.content, encoding='utf-8')
                
            elif file_change.action == 'delete':
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                # Don't fail if file doesn't exist (idempotent)
                
            else:
                raise ModificationError(f"Unknown action: {file_change.action}")
            
            return True
            
        except ModificationError:
            raise
        except Exception as e:
            logger.error(f"Error applying file change to {file_change.path}: {e}")
            raise ModificationError(f"Failed to apply change to {file_change.path}: {e}")
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        extension = Path(file_path).suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.kt': 'kotlin',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
        }
        
        return language_map.get(extension, 'unknown')
    
    async def _validate_python_syntax(self, code: str, result: ValidationResult):
        """Validate Python code syntax"""
        try:
            ast.parse(code)
        except SyntaxError as e:
            result.syntax_errors.append(f"Python syntax error: {e}")
        except Exception as e:
            result.syntax_errors.append(f"Python parsing error: {e}")
    
    async def _validate_javascript_syntax(self, code: str, result: ValidationResult):
        """Validate JavaScript/TypeScript syntax (basic validation)"""
        try:
            # Basic bracket matching
            brackets = {'(': ')', '[': ']', '{': '}'}
            stack = []
            in_string = False
            string_char = None
            
            for i, char in enumerate(code):
                if not in_string:
                    if char in ['"', "'", '`']:
                        in_string = True
                        string_char = char
                    elif char in brackets:
                        stack.append((char, i))
                    elif char in brackets.values():
                        if not stack:
                            result.syntax_errors.append(f"Unmatched closing bracket '{char}' at position {i}")
                        else:
                            open_char, _ = stack.pop()
                            if brackets[open_char] != char:
                                result.syntax_errors.append(f"Mismatched brackets at position {i}")
                else:
                    if char == string_char and (i == 0 or code[i-1] != '\\'):
                        in_string = False
                        string_char = None
            
            if stack:
                result.syntax_errors.append("Unclosed brackets detected")
                
        except Exception as e:
            result.syntax_errors.append(f"JavaScript validation error: {e}")
    
    async def _validate_security_issues(self, code: str, language: str, result: ValidationResult):
        """Check for security issues in code"""
        if language not in self.SECURITY_PATTERNS:
            return
        
        patterns = self.SECURITY_PATTERNS[language]
        
        for pattern, message in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                result.security_issues.append(message)
        
        # Additional security checks
        if language == 'python':
            # Check for SQL injection patterns
            sql_patterns = [
                r'[\'"].*%s.*[\'"].*%',
                r'[\'"].*\+.*[\'"].*cursor',
                r'execute\s*\([^)]*\+[^)]*\)'
            ]
            for pattern in sql_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    result.security_issues.append("Potential SQL injection vulnerability")
                    break
        
        # Check for hardcoded secrets
        secret_patterns = [
            r'[\'"][a-zA-Z0-9]{20,}[\'"]',  # Long strings that might be secrets
            r'password\s*=\s*[\'"][^\'\"]+[\'"]',
            r'api[_-]?key\s*=\s*[\'"][^\'\"]+[\'"]',
            r'secret\s*=\s*[\'"][^\'\"]+[\'"]',
        ]
        
        for pattern in secret_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                result.security_issues.append("Potential hardcoded secret detected")
                result.recommendations.append("Use environment variables for secrets")