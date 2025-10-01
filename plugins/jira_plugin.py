"""Jira plugin implementation for task management"""

import asyncio
import base64
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientSession

from core.circuit_breaker import CircuitBreakerConfig, circuit_breaker_manager
from core.plugin_interface import (
    PluginConnectionError,
    PluginResult,
    PluginStatus,
    PluginType,
    PluginValidationError,
    TaskManagementPlugin,
)
from core.retry_mechanism import (
    RateLimiter,
    RetryConfig,
    RetryStrategy,
    should_retry_http_error,
    with_retry,
)

logger = logging.getLogger(__name__)

# Constants for Jira API
JIRA_API_VERSION = "2"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_PAGE_SIZE = 50

# HTTP Status codes for better readability
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_NOT_FOUND = 404
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403


class JiraPlugin(TaskManagementPlugin):
    """Jira integration plugin for task management"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Jira plugin

        Args:
            config: Plugin configuration dictionary
        """
        super().__init__(config)
        self._session: Optional[ClientSession] = None
        self._base_url = ""
        self._auth_header = ""

        # Initialize rate limiter and retry configuration
        self._rate_limiter = RateLimiter(
            max_requests_per_second=2.0
        )  # Conservative for Jira
        self._retry_config = RetryConfig(
            max_attempts=self.config.get("options", {}).get("retry_attempts", 3),
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            max_delay=30.0,
            retry_condition=lambda e: self._should_retry_jira_error(e),
        )

        # Initialize circuit breaker
        circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=60.0, success_threshold=2
        )
        self._circuit_breaker = circuit_breaker_manager.get_circuit_breaker(
            f"jira_plugin_{id(self)}", circuit_breaker_config
        )

    def get_plugin_type(self) -> PluginType:
        """Return plugin type"""
        return PluginType.TASK_MANAGEMENT

    def get_plugin_name(self) -> str:
        """Return plugin name"""
        return "jira"

    def get_version(self) -> str:
        """Return plugin version"""
        return "1.0.0"

    def get_required_config_keys(self) -> List[str]:
        """Return required configuration keys"""
        return ["connection.url", "connection.email", "connection.api_token"]

    def get_optional_config_keys(self) -> List[str]:
        """Return optional configuration keys"""
        return [
            "options.timeout",
            "options.retry_attempts",
            "options.page_size",
            "mappings",
            "options.include_subtasks",
            "options.custom_fields",
        ]

    def validate_config(self) -> bool:
        """Validate plugin configuration

        Returns:
            True if configuration is valid

        Raises:
            PluginValidationError: If configuration is invalid
        """
        connection = self.config.get("connection", {})

        # Check required fields
        required_fields = ["url", "email", "api_token"]
        for field in required_fields:
            if not connection.get(field):
                raise PluginValidationError(
                    f"Missing required configuration: connection.{field}"
                )

        # Validate URL format
        url = connection["url"]
        if not url.startswith("https://"):
            raise PluginValidationError("Jira URL must use HTTPS")

        if not url.endswith(".atlassian.net") and "atlassian.net" not in url:
            logger.warning("URL does not appear to be a standard Atlassian Cloud URL")

        return True

    async def initialize(self) -> bool:
        """Initialize plugin and establish connection

        Returns:
            True if initialization successful
        """
        try:
            # Validate configuration first
            self.validate_config()

            # Extract connection details
            connection = self.config["connection"]
            self._base_url = connection["url"].rstrip("/")

            # Create authentication header
            auth_string = f"{connection['email']}:{connection['api_token']}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            self._auth_header = f"Basic {encoded_auth}"

            # Create HTTP session
            timeout = aiohttp.ClientTimeout(
                total=self.config.get("options", {}).get("timeout", 30)
            )
            self._session = ClientSession(timeout=timeout)

            # Test connection
            await self._test_connection()

            self._is_initialized = True
            self._connection_established = True

            logger.info(f"Successfully initialized Jira plugin for {self._base_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Jira plugin: {e}")
            self._is_initialized = False
            self._connection_established = False

            # Cleanup session if created
            if self._session:
                await self._session.close()
                self._session = None

            return False

    async def cleanup(self) -> bool:
        """Clean up plugin resources

        Returns:
            True if cleanup successful
        """
        try:
            if self._session:
                await self._session.close()
                self._session = None

            self._is_initialized = False
            self._connection_established = False

            logger.info("Jira plugin cleanup completed")
            return True

        except Exception as e:
            logger.error(f"Error during Jira plugin cleanup: {e}")
            return False

    async def health_check(self) -> PluginStatus:
        """Check plugin health status

        Returns:
            Current health status
        """
        if (
            not self._is_initialized
            or not self._connection_established
            or not self._session
        ):
            return PluginStatus.UNHEALTHY

        try:
            # Simple health check - get server info
            async with self._session.get(
                self._get_api_url("serverInfo"), headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_OK:
                    return PluginStatus.HEALTHY
                else:
                    logger.warning(
                        f"Jira health check returned status {response.status}"
                    )
                    return PluginStatus.DEGRADED

        except Exception as e:
            logger.error(f"Jira health check failed: {e}")
            return PluginStatus.UNHEALTHY

    def _should_retry_jira_error(self, exception: Exception) -> bool:
        """Determine if a Jira error should trigger a retry

        Args:
            exception: Exception that occurred

        Returns:
            True if should retry, False otherwise
        """
        # Handle aiohttp-specific errors
        if isinstance(exception, aiohttp.ClientError):
            # Always retry connection errors, timeouts, etc.
            return True

        # Handle HTTP response errors based on status code
        if hasattr(exception, "status"):
            return should_retry_http_error(exception.status)

        # Check if it's wrapped in a PluginResult (our custom format)
        if hasattr(exception, "status_code"):
            return should_retry_http_error(exception.status_code)

        # Retry on general network/connection issues
        return isinstance(exception, (asyncio.TimeoutError, ConnectionError, OSError))

    async def get_task(self, task_id: str) -> PluginResult:
        """Retrieve task details with retry mechanism

        Args:
            task_id: Jira issue key (e.g., PROJECT-123)

        Returns:
            PluginResult with task data
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        # Use retry mechanism for the actual API call
        @with_retry(self._retry_config)
        async def _get_task_with_retry():
            # Apply rate limiting
            await self._rate_limiter.acquire()

            # Wrap the actual HTTP call with circuit breaker
            async def _http_call():
                url = self._get_api_url(f"issue/{task_id}")

                async with self._session.get(
                    url, headers=self._get_request_headers()
                ) as response:
                    return (
                        response,
                        await response.text()
                        if response.status != 200
                        else await response.json(),
                    )

            response, data = await self._circuit_breaker.call(_http_call)

            if response.status == HTTP_NOT_FOUND:
                # Don't retry 404 errors - task truly doesn't exist
                raise ValueError(f"Task {task_id} not found")
            elif response.status >= 500 or response.status == 429:
                # Retry server errors and rate limiting
                error = aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=str(data),
                )
                error.status = response.status  # Ensure status is available
                raise error
            elif response.status != HTTP_OK:
                # Don't retry client errors (4xx except 429)
                raise ValueError(f"API error {response.status}: {data}")

            return data  # This is the JSON data

        try:
            issue_data = await _get_task_with_retry()

            # Map Jira fields to standard format
            task_data = self._map_issue_to_standard_format(issue_data)

            return PluginResult(
                success=True, data=task_data, metadata={"raw_issue": issue_data}
            )

        except ValueError as e:
            # Client errors and not found errors
            return PluginResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error retrieving task {task_id}: {e}")
            return PluginResult(
                success=False, error=f"Failed to retrieve task: {str(e)}"
            )

    async def create_task(
        self, project_key: str, task_data: Dict[str, Any]
    ) -> PluginResult:
        """Create a new task

        Args:
            project_key: Jira project key
            task_data: Task information

        Returns:
            PluginResult with created task ID
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            # Build Jira issue payload
            issue_payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": task_data.get("title", ""),
                    "description": task_data.get("description", ""),
                    "issuetype": {"name": task_data.get("issue_type", "Task")},
                }
            }

            # Add optional fields
            if "priority" in task_data:
                issue_payload["fields"]["priority"] = {"name": task_data["priority"]}

            if "assignee" in task_data:
                issue_payload["fields"]["assignee"] = {
                    "emailAddress": task_data["assignee"]
                }

            url = f"{self._base_url}/rest/api/2/issue"

            async with self._session.post(
                url,
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                },
                json=issue_payload,
            ) as response:
                if response.status != 201:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to create task: {response.status} {error_text}",
                    )

                result_data = await response.json()

                return PluginResult(
                    success=True,
                    data={
                        "task_id": result_data["key"],
                        "url": result_data.get("self", ""),
                    },
                    metadata={"raw_response": result_data},
                )

        except Exception as e:
            logger.error(f"Error creating task in project {project_key}: {e}")
            return PluginResult(success=False, error=f"Failed to create task: {e}")

    async def update_task_status(self, task_id: str, status: str) -> PluginResult:
        """Update task status

        Args:
            task_id: Jira issue key
            status: New status name

        Returns:
            PluginResult indicating success/failure
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            # Jira uses transitions to change status
            # First, get available transitions
            transitions_url = f"{self._base_url}/rest/api/2/issue/{task_id}/transitions"

            async with self._session.get(
                transitions_url, headers={"Authorization": self._auth_header}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to get transitions: {response.status} {error_text}",
                    )

                transitions_data = await response.json()

                # Find transition that leads to the desired status
                target_transition = None
                for transition in transitions_data.get("transitions", []):
                    if transition["to"]["name"].lower() == status.lower():
                        target_transition = transition
                        break

                if not target_transition:
                    return PluginResult(
                        success=False, error=f"No transition found to status '{status}'"
                    )

            # Execute the transition
            transition_payload = {"transition": {"id": target_transition["id"]}}

            async with self._session.post(
                transitions_url,
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                },
                json=transition_payload,
            ) as response:
                if response.status != 204:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to transition task: {response.status} {error_text}",
                    )

                return PluginResult(
                    success=True,
                    data={
                        "task_id": task_id,
                        "new_status": status,
                        "transition_id": target_transition["id"],
                    },
                )

        except Exception as e:
            logger.error(f"Error updating task {task_id} status to {status}: {e}")
            return PluginResult(
                success=False, error=f"Failed to update task status: {e}"
            )

    async def add_comment(self, task_id: str, comment: str) -> PluginResult:
        """Add comment to task

        Args:
            task_id: Jira issue key
            comment: Comment text

        Returns:
            PluginResult indicating success/failure
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            comment_payload = {"body": comment}

            url = f"{self._base_url}/rest/api/2/issue/{task_id}/comment"

            async with self._session.post(
                url,
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                },
                json=comment_payload,
            ) as response:
                if response.status != 201:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to add comment: {response.status} {error_text}",
                    )

                result_data = await response.json()

                return PluginResult(
                    success=True,
                    data={
                        "comment_id": result_data["id"],
                        "task_id": task_id,
                        "author": result_data["author"]["displayName"],
                    },
                    metadata={"raw_response": result_data},
                )

        except Exception as e:
            logger.error(f"Error adding comment to task {task_id}: {e}")
            return PluginResult(success=False, error=f"Failed to add comment: {e}")

    async def _test_connection(self) -> None:
        """Test connection to Jira API

        Raises:
            PluginConnectionError: If connection test fails
        """
        try:
            url = self._get_api_url("serverInfo")

            async with self._session.get(
                url, headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_UNAUTHORIZED:
                    raise PluginConnectionError(
                        "Authentication failed - check email and API token"
                    )
                elif response.status == HTTP_FORBIDDEN:
                    raise PluginConnectionError("Access forbidden - check permissions")
                elif response.status != HTTP_OK:
                    error_text = await response.text()
                    raise PluginConnectionError(
                        f"Connection test failed: {response.status} {error_text}"
                    )

                server_info = await response.json()
                logger.info(
                    f"Connected to Jira server version {server_info.get('version', 'unknown')}"
                )

        except aiohttp.ClientError as e:
            raise PluginConnectionError(f"Network error: {e}") from e

    def _map_issue_to_standard_format(
        self, issue_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map Jira issue data to standard task format

        Args:
            issue_data: Raw Jira issue data

        Returns:
            Standardized task data
        """
        mappings = self.config.get("mappings", {})

        # Default mappings if not configured
        default_mappings = {
            "task_id": "key",
            "title": "fields.summary",
            "description": "fields.description",
            "status": "fields.status.name",
            "assignee": "fields.assignee.displayName",
            "priority": "fields.priority.name",
            "created": "fields.created",
            "updated": "fields.updated",
        }

        effective_mappings = {**default_mappings, **mappings}
        task_data = {}

        for standard_field, jira_path in effective_mappings.items():
            task_data[standard_field] = self._extract_field_value(issue_data, jira_path)

        return task_data

    def _get_api_url(self, endpoint: str) -> str:
        """Get full API URL for an endpoint

        Args:
            endpoint: API endpoint path (e.g., "issue/TEST-123")

        Returns:
            Full API URL
        """
        return f"{self._base_url}/rest/api/{JIRA_API_VERSION}/{endpoint.lstrip('/')}"

    def _get_request_headers(
        self, content_type: str = "application/json"
    ) -> Dict[str, str]:
        """Get standard request headers

        Args:
            content_type: Content type header value

        Returns:
            Dictionary of headers
        """
        headers = {"Authorization": self._auth_header}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _extract_field_value(self, issue_data: Dict[str, Any], field_path: str) -> Any:
        """Extract field value from Jira issue data using dot notation

        Args:
            issue_data: Raw Jira issue data
            field_path: Dot-separated field path (e.g., "fields.status.name")

        Returns:
            Field value or None if not found
        """
        try:
            value = issue_data
            parts = field_path.split(".")

            for part in parts:
                value = value.get(part) if isinstance(value, dict) else None
                if value is None:
                    return None

            return value

        except (KeyError, AttributeError, TypeError):
            logger.warning(f"Failed to extract field {field_path} from issue data")
            return None

    # Enhanced Jira Plugin Methods for Phase 4
    
    async def get_task_with_context(
        self, 
        task_id: str,
        include_subtasks: bool = True,
        include_linked_issues: bool = True,
        include_comments: bool = True
    ) -> PluginResult:
        """Get task with full context including subtasks, linked issues, and comments"""
        
        try:
            # Build expand parameter for additional data
            expand_fields = []
            if include_subtasks:
                expand_fields.append("subtasks")
            if include_linked_issues:
                expand_fields.append("issuelinks")
            if include_comments:
                expand_fields.append("comments")
            
            expand_param = ",".join(expand_fields)
            
            # Get task with expanded fields
            url = self._build_api_url(f"issue/{task_id}")
            if expand_param:
                url += f"?expand={expand_param}"
            
            async with self._session.get(
                url, 
                headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_OK:
                    issue_data = await response.json()
                    
                    # Transform the data with custom field mapping
                    transformed_data = self._transform_task_data(issue_data)
                    
                    return PluginResult(
                        success=True,
                        data=transformed_data,
                        metadata={
                            "includes_subtasks": include_subtasks,
                            "includes_linked_issues": include_linked_issues,
                            "includes_comments": include_comments
                        }
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to get task context: {response.status} - {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Error getting task context for {task_id}: {e}")
            return PluginResult(success=False, error=str(e))

    def _transform_task_data(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Jira issue data with custom field mapping"""
        
        fields = issue_data.get("fields", {})
        custom_field_mapping = self.config.get("options", {}).get("custom_fields", {})
        
        # Base task data
        transformed = {
            "id": issue_data.get("id"),
            "key": issue_data.get("key"),
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "status": fields.get("status", {}).get("name"),
            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
            "created": fields.get("created"),
            "updated": fields.get("updated")
        }
        
        # Map custom fields
        for friendly_name, field_id in custom_field_mapping.items():
            if field_id in fields:
                transformed[friendly_name] = fields[field_id]
        
        # Add subtasks if present
        if "subtasks" in fields and fields["subtasks"]:
            transformed["subtasks"] = [
                {
                    "id": subtask.get("id"),
                    "key": subtask.get("key"),
                    "summary": subtask.get("fields", {}).get("summary"),
                    "status": subtask.get("fields", {}).get("status", {}).get("name")
                }
                for subtask in fields["subtasks"]
            ]
        
        # Add linked issues if present
        if "issuelinks" in fields and fields["issuelinks"]:
            transformed["linked_issues"] = []
            for link in fields["issuelinks"]:
                if "inwardIssue" in link:
                    issue = link["inwardIssue"]
                    transformed["linked_issues"].append({
                        "key": issue.get("key"),
                        "summary": issue.get("fields", {}).get("summary"),
                        "relationship": link.get("type", {}).get("inward", "linked")
                    })
                elif "outwardIssue" in link:
                    issue = link["outwardIssue"]
                    transformed["linked_issues"].append({
                        "key": issue.get("key"),
                        "summary": issue.get("fields", {}).get("summary"),
                        "relationship": link.get("type", {}).get("outward", "linked")
                    })
        
        # Add comments if present
        if "comments" in issue_data.get("fields", {}):
            comments_data = issue_data["fields"]["comments"]
            if "comments" in comments_data:
                transformed["comments"] = [
                    {
                        "id": comment.get("id"),
                        "author": comment.get("author", {}).get("displayName"),
                        "body": comment.get("body"),
                        "created": comment.get("created")
                    }
                    for comment in comments_data["comments"]
                ]
        
        return transformed

    async def add_progress_comment(
        self,
        task_id: str,
        progress_data: Dict[str, Any],
        template: str = "ai_agent_progress"
    ) -> PluginResult:
        """Add a progress comment using a template"""
        
        try:
            # Generate comment body using template
            comment_body = self._render_comment_template(template, progress_data)
            
            # Use the existing add_comment method
            return await self.add_comment(task_id, comment_body)
            
        except Exception as e:
            logger.error(f"Error adding progress comment to {task_id}: {e}")
            return PluginResult(success=False, error=str(e))

    def _render_comment_template(self, template_type: str, data: Dict[str, Any]) -> str:
        """Render comment template with data"""
        
        if template_type == "ai_agent_progress":
            return self._render_ai_progress_template(data)
        elif template_type == "ai_agent_start":
            return self._render_ai_start_template(data)
        elif template_type == "ai_agent_completion":
            return self._render_ai_completion_template(data)
        else:
            return f"Progress Update: {data}"

    def _render_ai_progress_template(self, data: Dict[str, Any]) -> str:
        """Render AI agent progress template"""
        
        template = """🤖 **AI Agent Progress Update**

**Current Status:** {current_step}

**Completed Steps:**
{completed_steps}

**In Progress:** {current_step} 🚧

**Estimated Completion:** {estimated_completion}

**Details:**
• AI Cost So Far: ${ai_cost:.2f}
• Files Being Modified: {file_count} files
{file_list}

---
*Automated update from AI Development Agent*"""

        completed_steps_text = "\n".join([
            f"• {step} ✅" for step in data.get("steps_completed", [])
        ])
        
        files_changed = data.get("files_changed", [])
        file_list = "\n".join([f"  - {file}" for file in files_changed[:5]])  # Limit to 5 files
        if len(files_changed) > 5:
            file_list += f"\n  - ... and {len(files_changed) - 5} more files"

        return template.format(
            current_step=data.get("current_step", "Unknown"),
            completed_steps=completed_steps_text,
            estimated_completion=data.get("estimated_completion", "Unknown"),
            ai_cost=data.get("ai_cost", 0.0),
            file_count=len(files_changed),
            file_list=file_list
        )

    def _render_ai_start_template(self, data: Dict[str, Any]) -> str:
        """Render AI agent start template"""
        
        template = """🤖 **AI Agent Started**

**Agent:** {agent_name}
**Workflow:** {workflow_name}
**Estimated Duration:** {estimated_duration}

The AI agent has begun working on this task and will:
1. Analyze the codebase structure
2. Generate an implementation plan
3. Write production-ready code
4. Create comprehensive tests
5. Submit a pull request for review

**Started:** {timestamp}

---
*This task is now being handled by an AI Development Agent*"""

        return template.format(
            agent_name=data.get("agent_name", "Development Agent"),
            workflow_name=data.get("workflow_name", "Standard Development"),
            estimated_duration=data.get("estimated_duration", "30-60 minutes"),
            timestamp=data.get("timestamp", "now")
        )

    def _render_ai_completion_template(self, data: Dict[str, Any]) -> str:
        """Render AI agent completion template"""
        
        template = """🚀 **AI Implementation Completed!**

**Pull Request:** [{pr_number}]({pr_url})
**Branch:** `{branch_name}`
**Commit:** [{commit_hash}]({commit_url})

**Summary:**
• Files Modified: {files_modified}
• Files Created: {files_created}
• Tests: {test_status}

**Ready for Review!** 👀

{review_notes}

---
*Implementation completed by AI Development Agent*"""

        return template.format(
            pr_number=data.get("pr_number", "N/A"),
            pr_url=data.get("pr_url", "#"),
            branch_name=data.get("branch_name", "feature-branch"),
            commit_hash=data.get("commit_hash", "abc123")[:7],
            commit_url=data.get("commit_url", "#"),
            files_modified=data.get("files_modified", 0),
            files_created=data.get("files_created", 0),
            test_status=data.get("test_status", "Pending"),
            review_notes=data.get("review_notes", "Please review the implementation and provide feedback.")
        )

    async def update_custom_fields(
        self, 
        task_id: str,
        custom_fields: Dict[str, Any]
    ) -> PluginResult:
        """Update custom fields using friendly names"""
        
        try:
            # Map friendly names to actual field IDs
            custom_field_mapping = self.config.get("options", {}).get("custom_fields", {})
            
            fields_data = {}
            for friendly_name, value in custom_fields.items():
                if friendly_name in custom_field_mapping:
                    field_id = custom_field_mapping[friendly_name]
                    fields_data[field_id] = value
                else:
                    logger.warning(f"Unknown custom field: {friendly_name}")
            
            if not fields_data:
                return PluginResult(
                    success=False,
                    error="No valid custom fields to update"
                )
            
            # Make API call to update fields
            url = self._build_api_url(f"issue/{task_id}")
            data = {"fields": fields_data}
            
            async with self._session.put(
                url,
                headers=self._get_request_headers(),
                data=json.dumps(data)
            ) as response:
                if response.status in [HTTP_NO_CONTENT, HTTP_OK]:
                    return PluginResult(
                        success=True,
                        data={"updated_fields": list(custom_fields.keys())}
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to update custom fields: {response.status} - {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Error updating custom fields for {task_id}: {e}")
            return PluginResult(success=False, error=str(e))

    async def get_available_transitions(self, task_id: str) -> PluginResult:
        """Get available status transitions for a task"""
        
        try:
            url = self._build_api_url(f"issue/{task_id}/transitions")
            
            async with self._session.get(
                url,
                headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_OK:
                    transitions_data = await response.json()
                    
                    transitions = []
                    for transition in transitions_data.get("transitions", []):
                        transitions.append({
                            "id": transition.get("id"),
                            "name": transition.get("name"),
                            "to_status": transition.get("to", {}).get("name")
                        })
                    
                    return PluginResult(
                        success=True,
                        data={"transitions": transitions}
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to get transitions: {response.status} - {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Error getting transitions for {task_id}: {e}")
            return PluginResult(success=False, error=str(e))

    async def transition_task_with_validation(
        self,
        task_id: str,
        status: str,
        validate_transition: bool = True
    ) -> PluginResult:
        """Transition task with optional validation of allowed transitions"""
        
        try:
            if validate_transition:
                # First check if transition is allowed
                transitions_result = await self.get_available_transitions(task_id)
                if not transitions_result.success:
                    return transitions_result
                
                available_transitions = transitions_result.data["transitions"]
                valid_transition = next(
                    (t for t in available_transitions if t["to_status"] == status),
                    None
                )
                
                if not valid_transition:
                    return PluginResult(
                        success=False,
                        error=f"Invalid transition to '{status}'. Available: {[t['to_status'] for t in available_transitions]}"
                    )
                
                transition_id = valid_transition["id"]
            else:
                # Use the basic update_task_status method
                return await self.update_task_status(task_id, status)
            
            # Perform the transition
            url = self._build_api_url(f"issue/{task_id}/transitions")
            data = {
                "transition": {"id": transition_id}
            }
            
            async with self._session.post(
                url,
                headers=self._get_request_headers(),
                data=json.dumps(data)
            ) as response:
                if response.status == HTTP_NO_CONTENT:
                    return PluginResult(
                        success=True,
                        data={"transitioned_to": status}
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to transition task: {response.status} - {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Error transitioning {task_id} to {status}: {e}")
            return PluginResult(success=False, error=str(e))

    async def create_subtask(
        self,
        project_key: str,
        subtask_data: Dict[str, Any]
    ) -> PluginResult:
        """Create a subtask linked to parent task"""
        
        try:
            # Build subtask creation data
            parent_key = subtask_data.get("parent_key")
            if not parent_key:
                return PluginResult(
                    success=False,
                    error="parent_key is required for subtask creation"
                )
            
            fields = {
                "project": {"key": project_key},
                "parent": {"key": parent_key},
                "summary": subtask_data.get("summary"),
                "description": subtask_data.get("description", ""),
                "issuetype": {"name": "Subtask"}  # Use Subtask issue type
            }
            
            # Add any custom fields
            if "custom_fields" in subtask_data:
                custom_field_mapping = self.config.get("options", {}).get("custom_fields", {})
                for friendly_name, value in subtask_data["custom_fields"].items():
                    if friendly_name in custom_field_mapping:
                        field_id = custom_field_mapping[friendly_name]
                        fields[field_id] = value
            
            data = {"fields": fields}
            
            url = self._build_api_url("issue")
            async with self._session.post(
                url,
                headers=self._get_request_headers(),
                data=json.dumps(data)
            ) as response:
                if response.status == HTTP_CREATED:
                    result_data = await response.json()
                    return PluginResult(
                        success=True,
                        data={
                            "key": result_data.get("key"),
                            "id": result_data.get("id"),
                            "parent_key": parent_key
                        }
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Failed to create subtask: {response.status} - {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Error creating subtask: {e}")
            return PluginResult(success=False, error=str(e))

    async def link_to_epic(self, task_id: str, epic_key: str) -> PluginResult:
        """Link a task to an epic"""
        
        try:
            # Get epic link custom field ID from configuration
            custom_field_mapping = self.config.get("options", {}).get("custom_fields", {})
            epic_link_field = custom_field_mapping.get("epic_link")
            
            if not epic_link_field:
                return PluginResult(
                    success=False,
                    error="Epic link custom field not configured"
                )
            
            # Update the epic link field
            fields = {epic_link_field: epic_key}
            return await self.update_custom_fields(task_id, {"epic_link": epic_key})
            
        except Exception as e:
            logger.error(f"Error linking {task_id} to epic {epic_key}: {e}")
            return PluginResult(success=False, error=str(e))

    async def add_templated_comment(
        self,
        task_id: str,
        template_type: str,
        template_data: Dict[str, Any]
    ) -> PluginResult:
        """Add a comment using a specific template"""
        
        try:
            comment_body = self._render_comment_template(template_type, template_data)
            return await self.add_comment(task_id, comment_body)
            
        except Exception as e:
            logger.error(f"Error adding templated comment to {task_id}: {e}")
            return PluginResult(success=False, error=str(e))

    async def batch_update_status(self, task_updates: List[Dict[str, str]]) -> PluginResult:
        """Update status for multiple tasks in batch"""
        
        try:
            results = {
                "updated": [],
                "failed": []
            }
            
            for update in task_updates:
                task_id = update.get("task_id")
                status = update.get("status")
                
                if not task_id or not status:
                    results["failed"].append({
                        "task_id": task_id,
                        "error": "Missing task_id or status"
                    })
                    continue
                
                result = await self.update_task_status(task_id, status)
                if result.success:
                    results["updated"].append(task_id)
                else:
                    results["failed"].append({
                        "task_id": task_id,
                        "error": result.error
                    })
            
            return PluginResult(
                success=True,
                data={
                    "updated_count": len(results["updated"]),
                    "failed_count": len(results["failed"]),
                    "details": results
                }
            )
            
        except Exception as e:
            logger.error(f"Error in batch status update: {e}")
            return PluginResult(success=False, error=str(e))

    async def search_tasks(self, search_criteria: Dict[str, Any]) -> PluginResult:
        """Search tasks using JQL with advanced criteria"""
        
        try:
            # Build JQL query from search criteria
            jql_parts = []
            
            if "project" in search_criteria:
                jql_parts.append(f"project = {search_criteria['project']}")
            
            if "assignee" in search_criteria:
                jql_parts.append(f"assignee = {search_criteria['assignee']}")
            
            if "status" in search_criteria:
                statuses = search_criteria["status"]
                if isinstance(statuses, list):
                    status_list = ", ".join([f'"{s}"' for s in statuses])
                    jql_parts.append(f"status IN ({status_list})")
                else:
                    jql_parts.append(f'status = "{statuses}"')
            
            if "labels" in search_criteria:
                labels = search_criteria["labels"]
                if isinstance(labels, list):
                    for label in labels:
                        jql_parts.append(f'labels = "{label}"')
                else:
                    jql_parts.append(f'labels = "{labels}"')
            
            # Handle custom fields
            if "custom_fields" in search_criteria:
                custom_field_mapping = self.config.get("options", {}).get("custom_fields", {})
                for friendly_name, value in search_criteria["custom_fields"].items():
                    if friendly_name in custom_field_mapping:
                        field_id = custom_field_mapping[friendly_name]
                        jql_parts.append(f'{field_id} = "{value}"')
            
            jql = " AND ".join(jql_parts)
            
            # Make search API call
            url = self._build_api_url("search")
            params = {
                "jql": jql,
                "maxResults": search_criteria.get("max_results", 50),
                "startAt": search_criteria.get("start_at", 0)
            }
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{url}?{query_string}"
            
            async with self._session.get(
                full_url,
                headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_OK:
                    search_results = await response.json()
                    
                    tasks = []
                    for issue in search_results.get("issues", []):
                        tasks.append(self._transform_task_data(issue))
                    
                    return PluginResult(
                        success=True,
                        data={
                            "tasks": tasks,
                            "total_count": search_results.get("total", 0),
                            "jql_used": jql
                        }
                    )
                else:
                    error_text = await response.text()
                    return PluginResult(
                        success=False,
                        error=f"Search failed: {response.status} - {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"Error searching tasks: {e}")
            return PluginResult(success=False, error=str(e))
