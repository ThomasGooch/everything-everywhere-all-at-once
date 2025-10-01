"""Jira plugin implementation for task management"""

import asyncio
import base64
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
