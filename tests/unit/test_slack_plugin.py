"""Unit tests for Slack plugin - TDD Implementation"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.plugin_interface import PluginStatus, PluginType
from plugins.slack_plugin import SlackPlugin


class TestSlackPlugin:
    """Test Slack plugin functionality using TDD approach"""

    @pytest.fixture
    def slack_config(self):
        """Test configuration for Slack plugin"""
        return {
            "type": "communication",
            "provider": "slack",
            "connection": {
                "bot_token": "xoxb-test-bot-token-12345",
                "app_token": "xapp-test-app-token-67890",
                "signing_secret": "test_signing_secret_123",
            },
            "mappings": {
                "channel_id": "channel",
                "message_id": "ts",
                "user_id": "user",
                "thread_id": "thread_ts",
            },
            "options": {
                "timeout": 30,
                "retry_attempts": 3,
                "default_channel": "general",
                "use_threads": True,
                "notify_on_completion": True,
                "include_agent_info": True,
            },
        }

    def test_slack_plugin_initialization(self, slack_config):
        """Test SlackPlugin basic initialization"""
        plugin = SlackPlugin(slack_config)

        assert plugin.get_plugin_type() == PluginType.COMMUNICATION
        assert plugin.get_plugin_name() == "slack"
        assert plugin.get_version() == "1.0.0"
        assert plugin.config == slack_config
        assert not plugin._is_initialized
        assert not plugin._connection_established

    def test_slack_plugin_config_validation_success(self, slack_config):
        """Test successful configuration validation"""
        plugin = SlackPlugin(slack_config)

        assert plugin.validate_config() is True

    def test_slack_plugin_config_validation_missing_bot_token(self, slack_config):
        """Test configuration validation with missing bot token"""
        del slack_config["connection"]["bot_token"]
        plugin = SlackPlugin(slack_config)

        with pytest.raises(Exception):  # Will be PluginValidationError
            plugin.validate_config()

    def test_slack_plugin_config_validation_invalid_bot_token(self, slack_config):
        """Test configuration validation with invalid bot token format"""
        slack_config["connection"]["bot_token"] = "invalid_token_format"
        plugin = SlackPlugin(slack_config)

        with pytest.raises(Exception):  # Will be PluginValidationError
            plugin.validate_config()

    def test_slack_plugin_config_validation_missing_signing_secret(self, slack_config):
        """Test configuration validation with missing signing secret"""
        del slack_config["connection"]["signing_secret"]
        plugin = SlackPlugin(slack_config)

        with pytest.raises(Exception):  # Will be PluginValidationError
            plugin.validate_config()

    def test_required_config_keys(self):
        """Test required configuration keys"""
        plugin = SlackPlugin({})
        required_keys = plugin.get_required_config_keys()

        assert "connection.bot_token" in required_keys
        assert "connection.signing_secret" in required_keys

    def test_optional_config_keys(self):
        """Test optional configuration keys"""
        plugin = SlackPlugin({})
        optional_keys = plugin.get_optional_config_keys()

        assert "connection.app_token" in optional_keys
        assert "options.timeout" in optional_keys
        assert "options.retry_attempts" in optional_keys
        assert "options.default_channel" in optional_keys
        assert "options.use_threads" in optional_keys

    @pytest.mark.asyncio
    async def test_slack_plugin_initialization_success(self, slack_config):
        """Test successful plugin initialization"""
        plugin = SlackPlugin(slack_config)

        # Mock Slack API auth test
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "ok": True,
                "user": "testbot",
                "team": "Test Team",
                "bot_id": "B12345",
            }
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        with patch("plugins.slack_plugin.ClientSession", return_value=mock_session):
            success = await plugin.initialize()

            assert success is True
            assert plugin._is_initialized is True
            assert plugin._connection_established is True

    @pytest.mark.asyncio
    async def test_slack_plugin_initialization_failure(self, slack_config):
        """Test failed plugin initialization due to auth error"""
        plugin = SlackPlugin(slack_config)

        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        with patch("plugins.slack_plugin.ClientSession", return_value=mock_session):
            # Mock failed authentication
            mock_session.post.side_effect = Exception("Authentication failed")

            success = await plugin.initialize()

            assert success is False
            assert plugin._is_initialized is False
            assert plugin._connection_established is False

    @pytest.mark.asyncio
    async def test_send_message_success(self, slack_config):
        """Test successful message sending"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        # Setup mock session
        mock_session = MagicMock()
        plugin._session = mock_session
        plugin._api_url = "https://slack.com/api"

        channel = "#general"
        message = "Hello, world!"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "ok": True,
                "ts": "1234567890.123456",
                "channel": "C1234567890",
                "message": {
                    "text": message,
                    "user": "U1234567890",
                    "ts": "1234567890.123456",
                },
            }
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        result = await plugin.send_message(channel, message)

        assert result.success is True
        assert result.data["message_id"] == "1234567890.123456"
        assert result.data["channel"] == "#general"
        assert result.data["text"] == message

    @pytest.mark.asyncio
    async def test_send_message_with_thread(self, slack_config):
        """Test successful message sending in thread"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        channel = "#general"
        message = "Thread reply"
        thread_id = "1234567890.123456"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "ok": True,
                "ts": "1234567890.123457",
                "channel": "C1234567890",
                "message": {
                    "text": message,
                    "user": "U1234567890",
                    "ts": "1234567890.123457",
                    "thread_ts": thread_id,
                },
            }
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        result = await plugin.send_message(channel, message, thread_id)

        assert result.success is True
        assert result.data["message_id"] == "1234567890.123457"
        assert result.data["thread_id"] == thread_id

    @pytest.mark.asyncio
    async def test_send_message_failure(self, slack_config):
        """Test message sending failure"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"ok": False, "error": "channel_not_found"}
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        result = await plugin.send_message("#nonexistent", "test message")

        assert result.success is False
        assert "Channel not found" in result.error

    @pytest.mark.asyncio
    async def test_send_direct_message_success(self, slack_config):
        """Test successful direct message sending"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        user_id = "U1234567890"
        message = "Private message"

        # Mock conversations.open response
        mock_open_response = MagicMock()
        mock_open_response.status = 200
        mock_open_response.json = AsyncMock(
            return_value={"ok": True, "channel": {"id": "D1234567890"}}
        )

        # Mock chat.postMessage response
        mock_send_response = MagicMock()
        mock_send_response.status = 200
        mock_send_response.json = AsyncMock(
            return_value={
                "ok": True,
                "ts": "1234567890.123456",
                "channel": "D1234567890",
                "message": {
                    "text": message,
                    "user": "U1234567890",
                    "ts": "1234567890.123456",
                },
            }
        )

        # Set up side_effect for different API calls
        def mock_post(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "conversations.open" in url:
                mock_context_manager = MagicMock()
                mock_context_manager.__aenter__ = AsyncMock(
                    return_value=mock_open_response
                )
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                return mock_context_manager
            else:  # chat.postMessage
                mock_context_manager = MagicMock()
                mock_context_manager.__aenter__ = AsyncMock(
                    return_value=mock_send_response
                )
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                return mock_context_manager

        mock_session.post.side_effect = mock_post

        result = await plugin.send_direct_message(user_id, message)

        assert result.success is True
        assert result.data["message_id"] == "1234567890.123456"
        assert result.data["user_id"] == user_id
        assert result.data["text"] == message

    @pytest.mark.asyncio
    async def test_upload_file_success(self, slack_config):
        """Test successful file upload"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        channel = "#general"
        file_content = b"Test file content"
        filename = "test.txt"
        comment = "Test file upload"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "ok": True,
                "file": {
                    "id": "F1234567890",
                    "name": filename,
                    "title": filename,
                    "permalink": "https://files.slack.com/files-pri/T123-F1234567890/test.txt",
                },
            }
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        result = await plugin.upload_file(channel, file_content, filename, comment)

        assert result.success is True
        assert result.data["file_id"] == "F1234567890"
        assert result.data["filename"] == filename
        assert (
            result.data["permalink"]
            == "https://files.slack.com/files-pri/T123-F1234567890/test.txt"
        )

    @pytest.mark.asyncio
    async def test_create_channel_success(self, slack_config):
        """Test successful channel creation"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        channel_data = {
            "name": "test-channel",
            "is_private": False,
            "topic": "Test channel topic",
            "purpose": "Test channel purpose",
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "ok": True,
                "channel": {
                    "id": "C1234567890",
                    "name": "test-channel",
                    "is_channel": True,
                    "is_private": False,
                    "topic": {"value": "Test channel topic"},
                    "purpose": {"value": "Test channel purpose"},
                },
            }
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        result = await plugin.create_channel(channel_data)

        assert result.success is True
        assert result.data["channel_id"] == "C1234567890"
        assert result.data["channel_name"] == "test-channel"
        assert result.data["is_private"] == False

    @pytest.mark.asyncio
    async def test_get_channel_info_success(self, slack_config):
        """Test successful channel info retrieval"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        channel_id = "C1234567890"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "ok": True,
                "channel": {
                    "id": "C1234567890",
                    "name": "general",
                    "is_channel": True,
                    "is_private": False,
                    "num_members": 42,
                    "topic": {
                        "value": "Company-wide announcements and general discussion"
                    },
                    "purpose": {"value": "General discussion"},
                },
            }
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        result = await plugin.get_channel_info(channel_id)

        assert result.success is True
        assert result.data["channel_id"] == "C1234567890"
        assert result.data["channel_name"] == "general"
        assert result.data["member_count"] == 42

    @pytest.mark.asyncio
    async def test_add_reaction_success(self, slack_config):
        """Test successful reaction addition"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        channel = "C1234567890"
        message_ts = "1234567890.123456"
        reaction = "thumbsup"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        result = await plugin.add_reaction(channel, message_ts, reaction)

        assert result.success is True
        assert result.data["channel"] == channel
        assert result.data["message_ts"] == message_ts
        assert result.data["reaction"] == reaction

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, slack_config):
        """Test health check when service is healthy"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = True

        mock_session = MagicMock()
        plugin._session = mock_session

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_context_manager

        status = await plugin.health_check()

        assert status == PluginStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, slack_config):
        """Test health check when service is unhealthy"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._connection_established = False

        status = await plugin.health_check()

        assert status == PluginStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_cleanup_success(self, slack_config):
        """Test successful plugin cleanup"""
        plugin = SlackPlugin(slack_config)
        plugin._is_initialized = True
        plugin._session = AsyncMock()

        success = await plugin.cleanup()

        assert success is True
        assert plugin._is_initialized is False
        assert plugin._session is None

    def test_format_rich_message_blocks(self, slack_config):
        """Test rich message formatting with blocks"""
        plugin = SlackPlugin(slack_config)

        message_data = {
            "text": "Fallback text",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Bold text* and _italic text_"},
                },
                {"type": "divider"},
            ],
        }

        formatted = plugin._format_rich_message(message_data)

        assert "blocks" in formatted
        assert formatted["text"] == "Fallback text"
        assert len(formatted["blocks"]) == 2

    def test_format_rich_message_attachments(self, slack_config):
        """Test rich message formatting with attachments"""
        plugin = SlackPlugin(slack_config)

        message_data = {
            "text": "Message with attachment",
            "attachments": [
                {
                    "color": "good",
                    "title": "Attachment Title",
                    "text": "Attachment content",
                    "fields": [{"title": "Field 1", "value": "Value 1", "short": True}],
                }
            ],
        }

        formatted = plugin._format_rich_message(message_data)

        assert "attachments" in formatted
        assert formatted["text"] == "Message with attachment"
        assert len(formatted["attachments"]) == 1
        assert formatted["attachments"][0]["color"] == "good"

    def test_validate_channel_name(self, slack_config):
        """Test channel name validation"""
        plugin = SlackPlugin(slack_config)

        # Valid channel names
        valid_names = [
            "#general",
            "general",
            "#test-channel",
            "test_channel",
            "#random123",
            "C1234567890",  # Channel ID
        ]

        for name in valid_names:
            assert plugin._validate_channel_name(name) is True

        # Invalid channel names
        invalid_names = [
            "",
            "  ",
            "#channel with spaces",
            "channel@invalid",
            "#UPPERCASE",
            "channel#invalid",
            "toolongchannelnamethatexceedslimit" * 3,
        ]

        for name in invalid_names:
            assert plugin._validate_channel_name(name) is False

    def test_parse_channel_identifier(self, slack_config):
        """Test channel identifier parsing"""
        plugin = SlackPlugin(slack_config)

        test_cases = [
            ("#general", "general"),
            ("general", "general"),
            ("C1234567890", "C1234567890"),  # Channel ID
            ("#test-channel", "test-channel"),
        ]

        for input_channel, expected in test_cases:
            result = plugin._parse_channel_identifier(input_channel)
            assert result == expected
