"""
Test suite for the AI Provider system.

This test suite follows TDD methodology to implement the AI Provider
interface and Claude integration with cost tracking and error handling.
"""

from unittest.mock import AsyncMock, Mock

import pytest

# Import the classes we're going to implement
from core.ai_provider import (
    AIProvider,
    AIProviderError,
    AIProviderResult,
    ClaudeProvider,
    CostTracker,
    PromptTemplate,
    TokenUsage,
)


class TestAIProvider:
    """Unit tests for AI Provider interface and base functionality"""

    def test_ai_provider_is_abstract(self):
        """Test that AIProvider cannot be instantiated directly"""
        # RED: This will fail since AIProvider doesn't exist yet
        with pytest.raises(TypeError):
            AIProvider()

    def test_ai_provider_interface_methods(self):
        """Test that AIProvider defines required abstract methods"""
        # RED: This will fail since AIProvider interface doesn't exist yet
        from abc import ABC

        assert issubclass(AIProvider, ABC)

        # Check that required methods are abstract
        abstract_methods = AIProvider.__abstractmethods__
        expected_methods = {
            "generate_text",
            "health_check",
            "get_cost_estimate",
            "validate_config",
        }
        assert expected_methods.issubset(abstract_methods)


class TestClaudeProvider:
    """Unit tests for Claude API integration"""

    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.config = {
            "api_key": "test-api-key",
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 4096,
            "temperature": 0.7,
            "cost_per_input_token": 0.000003,
            "cost_per_output_token": 0.000015,
        }

    def test_claude_provider_initialization(self):
        """Test that ClaudeProvider can be initialized properly"""
        # RED: This will fail since ClaudeProvider doesn't exist yet
        provider = ClaudeProvider(self.config)

        assert provider is not None
        assert provider.model == "claude-3-sonnet-20240229"
        assert provider.max_tokens == 4096
        assert provider.temperature == 0.7

    def test_claude_provider_config_validation(self):
        """Test Claude provider configuration validation"""
        # RED: This will fail since validation doesn't exist yet
        # Test missing API key
        invalid_config = self.config.copy()
        del invalid_config["api_key"]

        with pytest.raises(AIProviderError) as exc_info:
            ClaudeProvider(invalid_config)

        assert "api_key is required" in str(exc_info.value)

    def test_claude_provider_config_validation_invalid_model(self):
        """Test validation with invalid model"""
        # RED: This will fail since model validation doesn't exist yet
        invalid_config = self.config.copy()
        invalid_config["model"] = "invalid-model"

        with pytest.raises(AIProviderError) as exc_info:
            ClaudeProvider(invalid_config)

        assert "invalid model" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_claude_generate_text_simple(self):
        """Test basic text generation with Claude"""
        # Mock the anthropic client
        mock_client = AsyncMock()
        mock_messages = AsyncMock()
        mock_client.messages = mock_messages

        # Mock successful response
        mock_response = Mock()
        mock_response.content = [Mock(text="Generated response")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=25)
        mock_messages.create.return_value = mock_response

        provider = ClaudeProvider(self.config, client=mock_client)
        result = await provider.generate_text("Test prompt")

        assert result.success is True
        assert result.content == "Generated response"
        assert result.token_usage.input_tokens == 50
        assert result.token_usage.output_tokens == 25
        assert result.cost > 0

    @pytest.mark.asyncio
    async def test_claude_generate_text_with_system_prompt(self):
        """Test text generation with system prompt"""
        # Mock the anthropic client
        mock_client = AsyncMock()
        mock_messages = AsyncMock()
        mock_client.messages = mock_messages

        mock_response = Mock()
        mock_response.content = [Mock(text="System-guided response")]
        mock_response.usage = Mock(input_tokens=75, output_tokens=35)
        mock_messages.create.return_value = mock_response

        provider = ClaudeProvider(self.config, client=mock_client)
        result = await provider.generate_text(
            prompt="User prompt", system_prompt="You are a helpful assistant."
        )

        assert result.success is True
        assert result.content == "System-guided response"

        # Verify system prompt was passed correctly
        call_args = mock_messages.create.call_args
        assert call_args[1]["system"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_claude_generate_text_error_handling(self):
        """Test error handling in text generation"""
        # Mock the anthropic client
        mock_client = AsyncMock()
        mock_messages = AsyncMock()
        mock_client.messages = mock_messages

        # Mock API error
        mock_messages.create.side_effect = Exception("API Error")

        provider = ClaudeProvider(self.config, client=mock_client)
        result = await provider.generate_text("Test prompt")

        assert result.success is False
        assert result.error_message == "API Error"
        assert result.content is None

    @pytest.mark.asyncio
    async def test_claude_health_check_success(self):
        """Test successful health check"""
        # Mock the anthropic client
        mock_client = AsyncMock()
        mock_messages = AsyncMock()
        mock_client.messages = mock_messages

        # Mock successful health check response
        mock_response = Mock()
        mock_response.content = [Mock(text="OK")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        mock_messages.create.return_value = mock_response

        provider = ClaudeProvider(self.config, client=mock_client)
        is_healthy = await provider.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_claude_health_check_failure(self):
        """Test health check failure"""
        # Mock the anthropic client
        mock_client = AsyncMock()
        mock_messages = AsyncMock()
        mock_client.messages = mock_messages

        # Mock API failure
        mock_messages.create.side_effect = Exception("Connection failed")

        provider = ClaudeProvider(self.config, client=mock_client)
        is_healthy = await provider.health_check()

        assert is_healthy is False

    def test_claude_get_cost_estimate(self):
        """Test cost estimation for token usage"""
        # RED: This will fail since cost estimation doesn't exist yet
        provider = ClaudeProvider(self.config)

        # Test cost calculation
        input_tokens = 1000
        output_tokens = 500

        cost = provider.get_cost_estimate(input_tokens, output_tokens)

        expected_cost = (1000 * 0.000003) + (500 * 0.000015)
        assert abs(cost - expected_cost) < 0.000001


class TestTokenUsage:
    """Unit tests for TokenUsage tracking"""

    def test_token_usage_creation(self):
        """Test TokenUsage object creation"""
        # RED: This will fail since TokenUsage doesn't exist yet
        usage = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150

    def test_token_usage_auto_total(self):
        """Test automatic total token calculation"""
        # RED: This will fail since auto calculation doesn't exist yet
        usage = TokenUsage(input_tokens=100, output_tokens=50)

        # Should automatically calculate total
        assert usage.total_tokens == 150


class TestCostTracker:
    """Unit tests for cost tracking functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.cost_tracker = CostTracker()

    def test_cost_tracker_initialization(self):
        """Test CostTracker initialization"""
        # RED: This will fail since CostTracker doesn't exist yet
        tracker = CostTracker()

        assert tracker.total_cost == 0
        assert tracker.total_tokens == 0
        assert len(tracker.usage_history) == 0

    def test_cost_tracker_record_usage(self):
        """Test recording token usage and cost"""
        # RED: This will fail since record_usage doesn't exist yet
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        cost = 0.005

        self.cost_tracker.record_usage(usage, cost)

        assert self.cost_tracker.total_cost == 0.005
        assert self.cost_tracker.total_tokens == 150
        assert len(self.cost_tracker.usage_history) == 1

    def test_cost_tracker_multiple_records(self):
        """Test multiple usage records accumulation"""
        # RED: This will fail since accumulation doesn't exist yet
        usage1 = TokenUsage(input_tokens=100, output_tokens=50)
        usage2 = TokenUsage(input_tokens=200, output_tokens=75)

        self.cost_tracker.record_usage(usage1, 0.005)
        self.cost_tracker.record_usage(usage2, 0.008)

        assert abs(self.cost_tracker.total_cost - 0.013) < 0.000001
        assert self.cost_tracker.total_tokens == 425
        assert len(self.cost_tracker.usage_history) == 2

    def test_cost_tracker_get_usage_summary(self):
        """Test getting usage summary statistics"""
        # RED: This will fail since summary doesn't exist yet
        usage1 = TokenUsage(input_tokens=100, output_tokens=50)
        usage2 = TokenUsage(input_tokens=200, output_tokens=75)

        self.cost_tracker.record_usage(usage1, 0.005)
        self.cost_tracker.record_usage(usage2, 0.008)

        summary = self.cost_tracker.get_usage_summary()

        assert abs(summary["total_cost"] - 0.013) < 0.000001
        assert summary["total_tokens"] == 425
        assert summary["total_requests"] == 2
        assert abs(summary["average_cost_per_request"] - 0.0065) < 0.000001

    def test_cost_tracker_reset(self):
        """Test resetting cost tracker"""
        # RED: This will fail since reset doesn't exist yet
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        self.cost_tracker.record_usage(usage, 0.005)

        self.cost_tracker.reset()

        assert self.cost_tracker.total_cost == 0
        assert self.cost_tracker.total_tokens == 0
        assert len(self.cost_tracker.usage_history) == 0


class TestPromptTemplate:
    """Unit tests for prompt template system"""

    def test_prompt_template_creation(self):
        """Test basic prompt template creation"""
        # RED: This will fail since PromptTemplate doesn't exist yet
        template = PromptTemplate(
            name="test_template",
            template="Hello, ${name}! Your task is: ${task}",
        )

        assert template.name == "test_template"
        assert template.template == "Hello, ${name}! Your task is: ${task}"

    def test_prompt_template_render_simple(self):
        """Test simple template rendering"""
        # RED: This will fail since render doesn't exist yet
        template = PromptTemplate(name="greeting", template="Hello, {{name}}!")

        result = template.render({"name": "Alice"})
        assert result == "Hello, Alice!"

    def test_prompt_template_render_complex(self):
        """Test complex template rendering with multiple variables"""
        # RED: This will fail since complex rendering doesn't exist yet
        template_str = (
            "Task: {{task.title}}\n"
            "Priority: {{task.priority}}\n"
            "Due: {{task.due_date}}"
        )
        template = PromptTemplate(name="task_prompt", template=template_str)

        context = {
            "task": {
                "title": "Fix bug in login",
                "priority": "high",
                "due_date": "2023-10-15",
            }
        }

        result = template.render(context)
        expected = "Task: Fix bug in login\nPriority: high\nDue: 2023-10-15"
        assert result == expected

    def test_prompt_template_with_system_prompt(self):
        """Test template with system prompt section"""
        # RED: This will fail since system prompt support doesn't exist yet
        template = PromptTemplate(
            name="agent_prompt",
            system_template="You are a {{role}} assistant.",
            template="Please help with: {{request}}",
        )

        context = {"role": "development", "request": "code review"}

        system_prompt = template.render_system(context)
        user_prompt = template.render(context)

        assert system_prompt == "You are a development assistant."
        assert user_prompt == "Please help with: code review"

    def test_prompt_template_missing_variable_error(self):
        """Test error handling for missing template variables"""
        # RED: This will fail since error handling doesn't exist yet
        template = PromptTemplate(name="test", template="Hello, {{missing_var}}!")

        with pytest.raises(AIProviderError) as exc_info:
            template.render({})

        assert "missing_var" in str(exc_info.value)

    def test_prompt_template_load_from_file(self):
        """Test loading template from file"""
        # RED: This will fail since file loading doesn't exist yet
        import os
        import tempfile

        template_content = """
        name: file_template
        system_template: You are a helpful assistant.
        template: |
          Task: ${task}
          Instructions: ${instructions}
        """

        temp_file_args = {"mode": "w", "suffix": ".yaml", "delete": False}
        with tempfile.NamedTemporaryFile(**temp_file_args) as f:
            f.write(template_content)
            temp_file = f.name

        try:
            template = PromptTemplate.load_from_file(temp_file)

            assert template.name == "file_template"
            assert template.system_template == "You are a helpful assistant."
            assert "Task: ${task}" in template.template
        finally:
            os.unlink(temp_file)


class TestAIProviderResult:
    """Unit tests for AI Provider result objects"""

    def test_ai_provider_result_success(self):
        """Test successful AI provider result"""
        # RED: This will fail since AIProviderResult doesn't exist yet
        token_usage = TokenUsage(input_tokens=100, output_tokens=50)

        result = AIProviderResult(
            success=True,
            content="Generated content",
            token_usage=token_usage,
            cost=0.005,
            response_time=0.85,
        )

        assert result.success is True
        assert result.content == "Generated content"
        assert result.token_usage.input_tokens == 100
        assert result.cost == 0.005
        assert result.response_time == 0.85
        assert result.error_message is None

    def test_ai_provider_result_failure(self):
        """Test failed AI provider result"""
        # RED: This will fail since error result doesn't exist yet
        result = AIProviderResult(
            success=False,
            error_message="API rate limit exceeded",
            content=None,
            token_usage=None,
            cost=0,
            response_time=0.1,
        )

        assert result.success is False
        assert result.error_message == "API rate limit exceeded"
        assert result.content is None
        assert result.token_usage is None
        assert result.cost == 0


class TestAIProviderIntegration:
    """Integration tests for AI provider system"""

    def test_claude_provider_with_cost_tracker(self):
        """Test Claude provider integrated with cost tracker"""
        # RED: This will fail since integration doesn't exist yet
        config = {
            "api_key": "test-key",
            "model": "claude-3-sonnet-20240229",
            "cost_per_input_token": 0.000003,
            "cost_per_output_token": 0.000015,
        }

        provider = ClaudeProvider(config)
        cost_tracker = CostTracker()

        # Test that provider can integrate with cost tracker
        assert hasattr(provider, "set_cost_tracker")
        provider.set_cost_tracker(cost_tracker)

        assert provider.cost_tracker == cost_tracker

    @pytest.mark.asyncio
    async def test_end_to_end_generation_with_tracking(self):
        """Test end-to-end generation with cost tracking"""
        config = {
            "api_key": "test-key",
            "model": "claude-3-sonnet-20240229",
            "cost_per_input_token": 0.000003,
            "cost_per_output_token": 0.000015,
        }

        # Mock the anthropic client
        mock_client = AsyncMock()
        mock_messages = AsyncMock()
        mock_client.messages = mock_messages

        mock_response = Mock()
        mock_response.content = [Mock(text="Generated response")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_messages.create.return_value = mock_response

        provider = ClaudeProvider(config, client=mock_client)
        cost_tracker = CostTracker()
        provider.set_cost_tracker(cost_tracker)

        # Generate text
        result = await provider.generate_text("Test prompt")

        # Verify result
        assert result.success is True
        assert result.content == "Generated response"

        # Verify cost tracking was updated
        assert cost_tracker.total_tokens == 150
        assert cost_tracker.total_cost > 0
        assert len(cost_tracker.usage_history) == 1
