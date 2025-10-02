"""Unit tests for Claude AI Plugin"""

from unittest.mock import MagicMock, patch

import pytest
from anthropic.types.message import Usage
from anthropic.types.text_block import TextBlock

from core.plugin_interface import PluginStatus, PluginType
from plugins.claude_plugin import ClaudePlugin


class TestClaudePlugin:
    """Test cases for ClaudePlugin"""

    @pytest.fixture
    def valid_config(self):
        """Valid plugin configuration"""
        return {
            "api_key": "sk-ant-api03-test-key",
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1000,
            "temperature": 0.7,
        }

    @pytest.fixture
    def invalid_config(self):
        """Invalid plugin configuration"""
        return {
            "model": "claude-3-5-sonnet-20241022"
            # Missing required api_key
        }

    @pytest.fixture
    def plugin(self, valid_config):
        """Create plugin instance with valid config"""
        return ClaudePlugin(valid_config)

    def test_plugin_metadata(self, plugin):
        """Test plugin metadata methods"""
        assert plugin.get_plugin_type() == PluginType.AI_PROVIDER
        assert plugin.get_plugin_name() == "claude"
        assert plugin.get_version() == "1.0.0"

    def test_required_config_keys(self, plugin):
        """Test required configuration keys"""
        required_keys = plugin.get_required_config_keys()
        assert "api_key" in required_keys

    def test_optional_config_keys(self, plugin):
        """Test optional configuration keys"""
        optional_keys = plugin.get_optional_config_keys()
        expected_keys = ["model", "max_tokens", "temperature"]
        for key in expected_keys:
            assert key in optional_keys

    def test_validate_config_valid(self, plugin):
        """Test configuration validation with valid config"""
        assert plugin.validate_config() is True

    def test_validate_config_missing_api_key(self, invalid_config):
        """Test configuration validation with missing API key"""
        plugin = ClaudePlugin(invalid_config)
        assert plugin.validate_config() is False

    def test_validate_config_invalid_api_key_format(self):
        """Test configuration validation with invalid API key format"""
        config = {"api_key": "invalid-key-format"}
        plugin = ClaudePlugin(config)
        assert plugin.validate_config() is False

    @pytest.mark.asyncio
    async def test_initialize_success(self, plugin):
        """Test successful plugin initialization"""
        with patch.object(plugin, "test_connection", return_value=True):
            with patch("plugins.claude_plugin.Anthropic") as mock_client:
                result = await plugin.initialize()
                assert result is True
                assert plugin._is_initialized is True
                assert plugin._connection_established is True
                mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self, plugin):
        """Test initialization with connection failure"""
        with patch.object(plugin, "test_connection", return_value=False):
            with patch("plugins.claude_plugin.Anthropic") as mock_client:
                result = await plugin.initialize()
                assert result is False
                assert plugin._is_initialized is False

    @pytest.mark.asyncio
    async def test_initialize_invalid_config(self, invalid_config):
        """Test initialization with invalid configuration"""
        plugin = ClaudePlugin(invalid_config)
        result = await plugin.initialize()
        assert result is False
        assert plugin._is_initialized is False

    @pytest.mark.asyncio
    async def test_test_connection_success(self, plugin):
        """Test successful connection test"""
        # Create mock response
        mock_content = [TextBlock(type="text", text="Hello")]
        mock_response = MagicMock()
        mock_response.content = mock_content

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        plugin.client = mock_client

        result = await plugin.test_connection()
        assert result is True
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_no_client(self, plugin):
        """Test connection test without client"""
        plugin.client = None
        result = await plugin.test_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_test_connection_api_error(self, plugin):
        """Test connection test with API error"""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        plugin.client = mock_client

        result = await plugin.test_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_success(self, plugin):
        """Test successful cleanup"""
        plugin.client = MagicMock()
        plugin._is_initialized = True
        plugin._connection_established = True

        result = await plugin.cleanup()
        assert result is True
        assert plugin.client is None
        assert plugin._is_initialized is False
        assert plugin._connection_established is False

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, plugin):
        """Test health check when plugin is healthy"""
        plugin._is_initialized = True
        plugin.client = MagicMock()

        with patch.object(plugin, "test_connection", return_value=True):
            status = await plugin.health_check()
            assert status == PluginStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_not_initialized(self, plugin):
        """Test health check when plugin is not initialized"""
        plugin._is_initialized = False
        status = await plugin.health_check()
        assert status == PluginStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_degraded(self, plugin):
        """Test health check when connection is degraded"""
        plugin._is_initialized = True
        plugin.client = MagicMock()

        with patch.object(plugin, "test_connection", return_value=False):
            status = await plugin.health_check()
            assert status == PluginStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_generate_text_success(self, plugin):
        """Test successful text generation"""
        # Mock response
        mock_content = [TextBlock(type="text", text="Generated response")]
        mock_usage = Usage(input_tokens=100, output_tokens=50)
        mock_response = MagicMock()
        mock_response.content = mock_content
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        plugin.client = mock_client

        result = await plugin.generate_text("Test prompt")

        assert result.success is True
        assert result.data["generated_text"] == "Generated response"
        assert result.data["input_tokens"] == 100
        assert result.data["output_tokens"] == 50
        assert "cost" in result.data
        assert result.metadata["model"] == plugin.default_model

    @pytest.mark.asyncio
    async def test_generate_text_no_client(self, plugin):
        """Test text generation without initialized client"""
        plugin.client = None

        result = await plugin.generate_text("Test prompt")

        assert result.success is False
        assert "not initialized" in result.error

    @pytest.mark.asyncio
    async def test_generate_text_api_error(self, plugin):
        """Test text generation with API error"""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        plugin.client = mock_client

        result = await plugin.generate_text("Test prompt")

        assert result.success is False
        assert "API Error" in result.error

    @pytest.mark.asyncio
    async def test_estimate_cost(self, plugin):
        """Test cost estimation"""
        prompt = "Test prompt for cost estimation"
        max_tokens = 1000

        cost = await plugin.estimate_cost(prompt, max_tokens)

        assert isinstance(cost, float)
        assert cost > 0

    @pytest.mark.asyncio
    async def test_generate_code_success(self, plugin):
        """Test successful code generation"""
        # Mock successful response
        mock_content = [
            TextBlock(
                type="text", text="def hello_world():\n    return 'Hello, World!'"
            )
        ]
        mock_usage = Usage(input_tokens=200, output_tokens=100)
        mock_response = MagicMock()
        mock_response.content = mock_content
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        plugin.client = mock_client

        result = await plugin.generate_code(
            task_description="Create a hello world function",
            programming_language="python",
        )

        assert result.success is True
        assert "def hello_world" in result.data["generated_text"]

        # Verify the prompt was constructed correctly
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "Create a hello world function" in prompt
        assert "python" in prompt

    @pytest.mark.asyncio
    async def test_generate_code_with_framework(self, plugin):
        """Test code generation with framework specification"""
        mock_content = [TextBlock(type="text", text="# FastAPI code here")]
        mock_usage = Usage(input_tokens=200, output_tokens=100)
        mock_response = MagicMock()
        mock_response.content = mock_content
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        plugin.client = mock_client

        result = await plugin.generate_code(
            task_description="Create API endpoint",
            programming_language="python",
            framework="FastAPI",
        )

        assert result.success is True

        # Verify framework was included in prompt
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "FastAPI" in prompt

    @pytest.mark.asyncio
    async def test_analyze_code_success(self, plugin):
        """Test successful code analysis"""
        mock_content = [
            TextBlock(
                type="text",
                text="Code review: The function looks good but could use better error handling.",
            )
        ]
        mock_usage = Usage(input_tokens=150, output_tokens=75)
        mock_response = MagicMock()
        mock_response.content = mock_content
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        plugin.client = mock_client

        code_to_analyze = "def test_function(): pass"
        result = await plugin.analyze_code(code_to_analyze, "review")

        assert result.success is True
        assert "Code review" in result.data["generated_text"]

    @pytest.mark.asyncio
    async def test_analyze_code_invalid_type(self, plugin):
        """Test code analysis with invalid analysis type"""
        result = await plugin.analyze_code("some code", "invalid_type")

        assert result.success is False
        assert "Unknown analysis type" in result.error

    @pytest.mark.asyncio
    async def test_generate_tests_success(self, plugin):
        """Test successful test generation"""
        mock_content = [
            TextBlock(
                type="text",
                text="def test_hello_world():\n    assert hello_world() == 'Hello, World!'",
            )
        ]
        mock_usage = Usage(input_tokens=180, output_tokens=90)
        mock_response = MagicMock()
        mock_response.content = mock_content
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        plugin.client = mock_client

        code_to_test = "def hello_world(): return 'Hello, World!'"
        result = await plugin.generate_tests(code_to_test, "pytest")

        assert result.success is True
        assert "test_hello_world" in result.data["generated_text"]

        # Verify pytest was mentioned in prompt
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "pytest" in prompt
