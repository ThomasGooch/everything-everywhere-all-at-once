"""Slack plugin implementation for team communication"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
from aiohttp import ClientSession, FormData

from core.plugin_interface import (
    CommunicationPlugin,
    PluginConnectionError,
    PluginResult,
    PluginStatus,
    PluginType,
    PluginValidationError,
)

logger = logging.getLogger(__name__)

# Constants for Slack API
SLACK_API_BASE_URL = "https://slack.com/api"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_CHANNEL = "general"

# Slack-specific constants
SLACK_TOKEN_PREFIXES = ("xoxb-", "xoxp-", "xapp-")
SLACK_MAX_MESSAGE_LENGTH = 4000
SLACK_MAX_CHANNEL_NAME_LENGTH = 21
SLACK_MAX_FILE_SIZE = 1024 * 1024 * 1000  # 1GB in bytes

# HTTP Status codes
HTTP_OK = 200
HTTP_TOO_MANY_REQUESTS = 429

# Slack channel name validation pattern
VALID_CHANNEL_NAME_PATTERN = r"^[a-z0-9\-_]+$"

# Slack API rate limits
SLACK_RATE_LIMIT_TIER1 = 1  # 1+ requests per second
SLACK_RATE_LIMIT_TIER2 = 20  # 20+ requests per second
SLACK_RATE_LIMIT_TIER3 = 50  # 50+ requests per second

# Common Slack error codes
SLACK_ERROR_CODES = {
    "channel_not_found": "Channel not found",
    "not_in_channel": "Bot is not in the specified channel",
    "is_archived": "Channel is archived",
    "msg_too_long": "Message exceeds character limit",
    "rate_limited": "API rate limit exceeded",
    "invalid_auth": "Invalid authentication token",
    "account_inactive": "Authentication token is for a deleted user or workspace",
}


class SlackPlugin(CommunicationPlugin):
    """Slack integration plugin for team communication"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Slack plugin

        Args:
            config: Plugin configuration dictionary
        """
        super().__init__(config)
        self._session: Optional[ClientSession] = None
        self._api_url = SLACK_API_BASE_URL
        self._bot_token = ""
        self._app_token = ""
        self._signing_secret = ""

    def get_plugin_type(self) -> PluginType:
        """Return plugin type"""
        return PluginType.COMMUNICATION

    def get_plugin_name(self) -> str:
        """Return plugin name"""
        return "slack"

    def get_version(self) -> str:
        """Return plugin version"""
        return "1.0.0"

    def get_required_config_keys(self) -> List[str]:
        """Return required configuration keys"""
        return ["connection.bot_token", "connection.signing_secret"]

    def get_optional_config_keys(self) -> List[str]:
        """Return optional configuration keys"""
        return [
            "connection.app_token",
            "options.timeout",
            "options.retry_attempts",
            "options.default_channel",
            "options.use_threads",
            "options.notify_on_completion",
            "options.include_agent_info",
            "mappings",
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
        if not connection.get("bot_token"):
            raise PluginValidationError(
                "Missing required configuration: connection.bot_token"
            )

        if not connection.get("signing_secret"):
            raise PluginValidationError(
                "Missing required configuration: connection.signing_secret"
            )

        # Validate bot token format
        bot_token = connection["bot_token"]
        if not any(bot_token.startswith(prefix) for prefix in SLACK_TOKEN_PREFIXES):
            raise PluginValidationError(
                f"Slack bot token should start with one of: {', '.join(SLACK_TOKEN_PREFIXES)}"
            )

        # Validate app token format if provided
        app_token = connection.get("app_token")
        if app_token and not app_token.startswith("xapp-"):
            raise PluginValidationError("Slack app token should start with 'xapp-'")

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
            self._bot_token = connection["bot_token"]
            self._app_token = connection.get("app_token", "")
            self._signing_secret = connection["signing_secret"]

            # Create HTTP session
            timeout = aiohttp.ClientTimeout(
                total=self.config.get("options", {}).get("timeout", DEFAULT_TIMEOUT)
            )
            self._session = ClientSession(timeout=timeout)

            # Test connection
            await self._test_connection()

            self._is_initialized = True
            self._connection_established = True

            logger.info("Successfully initialized Slack plugin")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Slack plugin: {e}")
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

            logger.info("Slack plugin cleanup completed")
            return True

        except Exception as e:
            logger.error(f"Error during Slack plugin cleanup: {e}")
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
            # Simple health check - test auth
            url = f"{self._api_url}/auth.test"

            async with self._session.post(
                url, headers=self._get_request_headers()
            ) as response:
                if response.status == HTTP_OK:
                    response_data = await response.json()
                    if response_data.get("ok"):
                        return PluginStatus.HEALTHY
                    else:
                        logger.warning(
                            f"Slack auth test failed: {response_data.get('error')}"
                        )
                        return PluginStatus.DEGRADED
                else:
                    logger.warning(
                        f"Slack health check returned status {response.status}"
                    )
                    return PluginStatus.DEGRADED

        except Exception as e:
            logger.error(f"Slack health check failed: {e}")
            return PluginStatus.UNHEALTHY

    async def send_message(
        self, channel: str, message: str, thread_id: Optional[str] = None
    ) -> PluginResult:
        """Send message to channel

        Args:
            channel: Channel identifier (name with # or channel ID)
            message: Message text or rich message data
            thread_id: Optional thread ID for replies

        Returns:
            PluginResult with message ID
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            # Parse channel identifier
            channel_id = self._parse_channel_identifier(channel)

            # Prepare message payload
            if isinstance(message, str):
                # Truncate message if too long
                truncated_message = self._truncate_message(message)
                payload = {"text": truncated_message}
            else:
                payload = self._format_rich_message(message)

            payload["channel"] = channel_id

            if thread_id:
                payload["thread_ts"] = thread_id

            # Send message
            url = f"{self._api_url}/chat.postMessage"

            async with self._session.post(
                url, headers=self._get_request_headers(), json=payload
            ) as response:
                response_data = await response.json()

                if not response_data.get("ok"):
                    error_code = response_data.get("error", "unknown_error")
                    return self._handle_slack_error(error_code, "Send message")

                message_data = response_data.get("message", {})

                result_data = {
                    "message_id": response_data.get("ts"),
                    "channel": channel,
                    "text": message_data.get("text", ""),
                    "user": message_data.get("user"),
                }

                if thread_id:
                    result_data["thread_id"] = thread_id

                logger.info(
                    f"Sent message to {channel}: {message_data.get('text', '')[:50]}..."
                )

                return PluginResult(
                    success=True,
                    data=result_data,
                    metadata={"raw_response": response_data},
                )

        except Exception as e:
            logger.error(f"Error sending message to {channel}: {e}")
            return PluginResult(success=False, error=f"Failed to send message: {e}")

    async def send_direct_message(self, user_id: str, message: str) -> PluginResult:
        """Send direct message to user

        Args:
            user_id: User identifier
            message: Message text

        Returns:
            PluginResult with message ID
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            # Open DM channel with user
            open_url = f"{self._api_url}/conversations.open"

            async with self._session.post(
                open_url, headers=self._get_request_headers(), json={"users": user_id}
            ) as response:
                response_data = await response.json()

                if not response_data.get("ok"):
                    return PluginResult(
                        success=False,
                        error=f"Failed to open DM channel: {response_data.get('error')}",
                    )

                dm_channel_id = response_data["channel"]["id"]

            # Send message to DM channel
            result = await self.send_message(dm_channel_id, message)

            if result.success:
                # Update result data with user info
                result.data["user_id"] = user_id
                result.data["channel"] = "DM"

            return result

        except Exception as e:
            logger.error(f"Error sending DM to user {user_id}: {e}")
            return PluginResult(
                success=False, error=f"Failed to send direct message: {e}"
            )

    async def upload_file(
        self,
        channel: str,
        file_content: Union[bytes, str],
        filename: str,
        comment: Optional[str] = None,
    ) -> PluginResult:
        """Upload file to channel

        Args:
            channel: Channel identifier
            file_content: File content (bytes or file path string)
            filename: Name for uploaded file
            comment: Optional comment for the file

        Returns:
            PluginResult with file information
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            channel_id = self._parse_channel_identifier(channel)

            # Prepare file data
            if isinstance(file_content, str):
                # Assume it's a file path
                file_path = Path(file_content)
                if not file_path.exists():
                    return PluginResult(
                        success=False, error=f"File not found: {file_content}"
                    )
                file_data = file_path.read_bytes()
                if not filename:
                    filename = file_path.name
            else:
                file_data = file_content

            # Check file size
            if len(file_data) > SLACK_MAX_FILE_SIZE:
                return PluginResult(
                    success=False,
                    error=f"File too large. Max size: {SLACK_MAX_FILE_SIZE} bytes",
                )

            # Prepare form data
            form_data = FormData()
            form_data.add_field("file", file_data, filename=filename)
            form_data.add_field("channels", channel_id)
            form_data.add_field("filename", filename)

            if comment:
                form_data.add_field("initial_comment", comment)

            url = f"{self._api_url}/files.upload"

            async with self._session.post(
                url,
                headers={"Authorization": f"Bearer {self._bot_token}"},
                data=form_data,
            ) as response:
                response_data = await response.json()

                if not response_data.get("ok"):
                    return PluginResult(
                        success=False,
                        error=f"File upload failed: {response_data.get('error')}",
                    )

                file_info = response_data.get("file", {})

                logger.info(f"Uploaded file '{filename}' to {channel}")

                return PluginResult(
                    success=True,
                    data={
                        "file_id": file_info.get("id"),
                        "filename": file_info.get("name"),
                        "title": file_info.get("title"),
                        "permalink": file_info.get("permalink"),
                        "channel": channel,
                        "size": len(file_data),
                    },
                    metadata={"raw_response": response_data},
                )

        except Exception as e:
            logger.error(f"Error uploading file to {channel}: {e}")
            return PluginResult(success=False, error=f"Failed to upload file: {e}")

    async def create_channel(self, channel_data: Dict[str, Any]) -> PluginResult:
        """Create new channel

        Args:
            channel_data: Channel information containing:
                - name: Channel name
                - is_private: Whether channel is private (default: False)
                - topic: Channel topic (optional)
                - purpose: Channel purpose (optional)

        Returns:
            PluginResult with channel information
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            channel_name = channel_data.get("name")
            if not channel_name:
                return PluginResult(success=False, error="Channel name is required")

            # Validate channel name
            if not self._validate_channel_name(channel_name):
                return PluginResult(
                    success=False, error=f"Invalid channel name: {channel_name}"
                )

            # Prepare payload
            payload = {
                "name": channel_name.lstrip("#"),
                "is_private": channel_data.get("is_private", False),
            }

            # Choose API endpoint based on channel type
            if payload["is_private"]:
                url = f"{self._api_url}/conversations.create"
                payload["is_private"] = True
            else:
                url = f"{self._api_url}/conversations.create"

            async with self._session.post(
                url, headers=self._get_request_headers(), json=payload
            ) as response:
                response_data = await response.json()

                if not response_data.get("ok"):
                    return PluginResult(
                        success=False,
                        error=f"Channel creation failed: {response_data.get('error')}",
                    )

                channel_info = response_data.get("channel", {})
                channel_id = channel_info.get("id")

                # Set topic and purpose if provided
                if channel_data.get("topic"):
                    await self._set_channel_topic(channel_id, channel_data["topic"])

                if channel_data.get("purpose"):
                    await self._set_channel_purpose(channel_id, channel_data["purpose"])

                logger.info(f"Created channel '{channel_name}' (ID: {channel_id})")

                return PluginResult(
                    success=True,
                    data={
                        "channel_id": channel_id,
                        "channel_name": channel_info.get("name"),
                        "is_private": channel_info.get("is_private", False),
                        "topic": channel_data.get("topic", ""),
                        "purpose": channel_data.get("purpose", ""),
                    },
                    metadata={"raw_response": response_data},
                )

        except Exception as e:
            logger.error(f"Error creating channel: {e}")
            return PluginResult(success=False, error=f"Failed to create channel: {e}")

    async def get_channel_info(self, channel: str) -> PluginResult:
        """Get channel information

        Args:
            channel: Channel identifier

        Returns:
            PluginResult with channel information
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            channel_id = self._parse_channel_identifier(channel)

            url = f"{self._api_url}/conversations.info"

            async with self._session.post(
                url, headers=self._get_request_headers(), json={"channel": channel_id}
            ) as response:
                response_data = await response.json()

                if not response_data.get("ok"):
                    return PluginResult(
                        success=False,
                        error=f"Failed to get channel info: {response_data.get('error')}",
                    )

                channel_info = response_data.get("channel", {})

                return PluginResult(
                    success=True,
                    data={
                        "channel_id": channel_info.get("id"),
                        "channel_name": channel_info.get("name"),
                        "is_private": channel_info.get("is_private", False),
                        "member_count": channel_info.get("num_members", 0),
                        "topic": channel_info.get("topic", {}).get("value", ""),
                        "purpose": channel_info.get("purpose", {}).get("value", ""),
                        "created": channel_info.get("created"),
                    },
                    metadata={"raw_response": response_data},
                )

        except Exception as e:
            logger.error(f"Error getting channel info for {channel}: {e}")
            return PluginResult(success=False, error=f"Failed to get channel info: {e}")

    async def add_reaction(
        self, channel: str, message_ts: str, reaction: str
    ) -> PluginResult:
        """Add reaction to message

        Args:
            channel: Channel identifier
            message_ts: Message timestamp
            reaction: Reaction emoji name (without colons)

        Returns:
            PluginResult indicating success/failure
        """
        if not self._session:
            return PluginResult(success=False, error="Plugin not initialized")

        try:
            channel_id = self._parse_channel_identifier(channel)

            # Clean reaction name (remove colons if present)
            clean_reaction = reaction.strip(":")

            payload = {
                "channel": channel_id,
                "timestamp": message_ts,
                "name": clean_reaction,
            }

            url = f"{self._api_url}/reactions.add"

            async with self._session.post(
                url, headers=self._get_request_headers(), json=payload
            ) as response:
                response_data = await response.json()

                if not response_data.get("ok"):
                    return PluginResult(
                        success=False,
                        error=f"Failed to add reaction: {response_data.get('error')}",
                    )

                logger.info(
                    f"Added reaction '{clean_reaction}' to message {message_ts}"
                )

                return PluginResult(
                    success=True,
                    data={
                        "channel": channel,
                        "message_ts": message_ts,
                        "reaction": clean_reaction,
                    },
                )

        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
            return PluginResult(success=False, error=f"Failed to add reaction: {e}")

    async def _test_connection(self) -> None:
        """Test connection to Slack API

        Raises:
            PluginConnectionError: If connection test fails
        """
        try:
            url = f"{self._api_url}/auth.test"

            async with self._session.post(
                url, headers=self._get_request_headers()
            ) as response:
                if response.status != HTTP_OK:
                    raise PluginConnectionError(f"HTTP error: {response.status}")

                response_data = await response.json()

                if not response_data.get("ok"):
                    error = response_data.get("error", "Unknown error")
                    raise PluginConnectionError(f"Slack auth failed: {error}")

                user_info = response_data
                logger.info(
                    f"Connected to Slack as {user_info.get('user')} on team {user_info.get('team')}"
                )

        except aiohttp.ClientError as e:
            raise PluginConnectionError(f"Network error: {e}") from e

    def _get_request_headers(self) -> Dict[str, str]:
        """Get standard request headers

        Returns:
            Dictionary of headers
        """
        return {
            "Authorization": f"Bearer {self._bot_token}",
            "Content-Type": "application/json",
        }

    def _parse_channel_identifier(self, channel: str) -> str:
        """Parse channel identifier from various formats

        Args:
            channel: Channel name with/without # or channel ID

        Returns:
            Clean channel identifier
        """
        if not channel:
            return self.config.get("options", {}).get(
                "default_channel", DEFAULT_CHANNEL
            )

        # If it's already a channel ID (starts with C), return as-is
        if channel.startswith("C") and len(channel) >= 9:
            return channel

        # Remove # prefix if present
        return channel.lstrip("#")

    def _validate_channel_name(self, channel_name: str) -> bool:
        """Validate Slack channel name

        Args:
            channel_name: Channel name to validate

        Returns:
            True if valid channel name
        """
        if not channel_name:
            return False

        # Remove # if present for validation
        name = channel_name.lstrip("#")

        # Check length
        if len(name) > SLACK_MAX_CHANNEL_NAME_LENGTH or len(name) == 0:
            return False

        # Check if it's a channel ID (valid)
        if name.startswith("C") and len(name) >= 9:
            return True

        # Check pattern for channel names
        return bool(re.match(VALID_CHANNEL_NAME_PATTERN, name))

    def _handle_slack_error(self, error_code: str, operation: str) -> PluginResult:
        """Handle common Slack API errors

        Args:
            error_code: Slack error code
            operation: Description of the operation that failed

        Returns:
            PluginResult with appropriate error message
        """
        error_message = SLACK_ERROR_CODES.get(
            error_code, f"Unknown error: {error_code}"
        )

        return PluginResult(success=False, error=f"{operation}: {error_message}")

    def _validate_message_content(self, message: Union[str, Dict[str, Any]]) -> bool:
        """Validate message content

        Args:
            message: Message content to validate

        Returns:
            True if valid message content
        """
        if isinstance(message, str):
            return len(message.strip()) > 0
        elif isinstance(message, dict):
            return bool(
                message.get("text")
                or message.get("blocks")
                or message.get("attachments")
            )

        return False

    def _truncate_message(
        self, message: str, max_length: int = SLACK_MAX_MESSAGE_LENGTH
    ) -> str:
        """Truncate message to fit Slack limits

        Args:
            message: Original message
            max_length: Maximum allowed length

        Returns:
            Truncated message
        """
        if len(message) <= max_length:
            return message

        truncated = message[: max_length - 3] + "..."
        logger.warning(
            f"Message truncated from {len(message)} to {len(truncated)} characters"
        )
        return truncated

    def _format_rich_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format rich message with blocks or attachments

        Args:
            message_data: Message data with blocks/attachments

        Returns:
            Formatted message payload
        """
        payload = {"text": message_data.get("text", "")}

        if "blocks" in message_data:
            payload["blocks"] = message_data["blocks"]

        if "attachments" in message_data:
            payload["attachments"] = message_data["attachments"]

        return payload

    async def _set_channel_topic(self, channel_id: str, topic: str) -> bool:
        """Set channel topic

        Args:
            channel_id: Channel ID
            topic: Topic text

        Returns:
            True if successful
        """
        try:
            url = f"{self._api_url}/conversations.setTopic"

            async with self._session.post(
                url,
                headers=self._get_request_headers(),
                json={"channel": channel_id, "topic": topic},
            ) as response:
                response_data = await response.json()
                return response_data.get("ok", False)

        except Exception as e:
            logger.warning(f"Failed to set channel topic: {e}")
            return False

    async def _set_channel_purpose(self, channel_id: str, purpose: str) -> bool:
        """Set channel purpose

        Args:
            channel_id: Channel ID
            purpose: Purpose text

        Returns:
            True if successful
        """
        try:
            url = f"{self._api_url}/conversations.setPurpose"

            async with self._session.post(
                url,
                headers=self._get_request_headers(),
                json={"channel": channel_id, "purpose": purpose},
            ) as response:
                response_data = await response.json()
                return response_data.get("ok", False)

        except Exception as e:
            logger.warning(f"Failed to set channel purpose: {e}")
            return False
