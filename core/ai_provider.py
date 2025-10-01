"""
AI Provider system for the development automation platform.

This module provides the core AI Provider interface and implementations,
including Claude API integration with cost tracking and error handling.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import anthropic
import yaml
from jinja2 import StrictUndefined, Template, TemplateError, UndefinedError


class AIProviderError(Exception):
    """Base exception for AI provider errors."""

    pass


@dataclass
class TokenUsage:
    """Token usage tracking for AI API calls."""

    input_tokens: int
    output_tokens: int
    total_tokens: Optional[int] = None

    def __post_init__(self):
        """Auto-calculate total tokens if not provided."""
        if self.total_tokens is None:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class AIProviderResult:
    """Result object for AI provider operations."""

    success: bool
    content: Optional[str] = None
    token_usage: Optional[TokenUsage] = None
    cost: float = 0.0
    response_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostTracker:
    """Cost and usage tracking for AI provider calls."""

    def __init__(self):
        self.total_cost: float = 0.0
        self.total_tokens: int = 0
        self.usage_history: List[Dict[str, Any]] = []

    def record_usage(self, usage: TokenUsage, cost: float) -> None:
        """Record a usage event with cost."""
        self.total_cost += cost
        self.total_tokens += usage.total_tokens

        self.usage_history.append(
            {"timestamp": datetime.now(), "usage": usage, "cost": cost}
        )

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary statistics for usage."""
        total_requests = len(self.usage_history)
        avg_cost = self.total_cost / total_requests if total_requests > 0 else 0.0

        return {
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "total_requests": total_requests,
            "average_cost_per_request": avg_cost,
        }

    def reset(self) -> None:
        """Reset all tracking data."""
        self.total_cost = 0.0
        self.total_tokens = 0
        self.usage_history.clear()


class PromptTemplate:
    """Template system for AI prompts with Jinja2 integration."""

    def __init__(self, name: str, template: str, system_template: Optional[str] = None):
        self.name = name
        self.template = template
        self.system_template = system_template
        self._jinja_template = Template(template, undefined=StrictUndefined)
        self._jinja_system_template = (
            Template(system_template, undefined=StrictUndefined)
            if system_template
            else None
        )

    def render(self, context: Dict[str, Any]) -> str:
        """Render the main template with context variables."""
        try:
            return self._jinja_template.render(**context)
        except UndefinedError as e:
            raise AIProviderError(f"Template variable not found: {e}")
        except TemplateError as e:
            raise AIProviderError(f"Template rendering failed: {e}")
        except Exception as e:
            # Handle other template errors
            if "is undefined" in str(e):
                raise AIProviderError(f"Template variable not found: {e}")
            raise AIProviderError(f"Template rendering failed: {e}")

    def render_system(self, context: Dict[str, Any]) -> Optional[str]:
        """Render the system template with context variables."""
        if not self._jinja_system_template:
            return None

        try:
            return self._jinja_system_template.render(**context)
        except UndefinedError as e:
            raise AIProviderError(f"System template variable not found: {e}")
        except TemplateError as e:
            raise AIProviderError(f"System template rendering failed: {e}")
        except Exception as e:
            # Handle other template errors
            if "is undefined" in str(e):
                error_msg = f"System template variable not found: {e}"
                raise AIProviderError(error_msg)
            raise AIProviderError(f"System template rendering failed: {e}")

    @classmethod
    def load_from_file(cls, file_path: str) -> "PromptTemplate":
        """Load template from YAML file."""
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        return cls(
            name=data["name"],
            template=data["template"],
            system_template=data.get("system_template"),
        )


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cost_tracker: Optional[CostTracker] = None
        self.validate_config()

    @abstractmethod
    def validate_config(self) -> None:
        """Validate provider configuration."""
        pass

    @abstractmethod
    async def generate_text(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> AIProviderResult:
        """Generate text using the AI provider."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        pass

    @abstractmethod
    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for given token usage."""
        pass

    def set_cost_tracker(self, cost_tracker: CostTracker) -> None:
        """Set cost tracker for usage monitoring."""
        self.cost_tracker = cost_tracker


class ClaudeProvider(AIProvider):
    """Claude API provider implementation."""

    SUPPORTED_MODELS = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(
        self,
        config: Dict[str, Any],
        client: Optional[anthropic.AsyncAnthropic] = None,
    ):
        super().__init__(config)
        self.api_key = config["api_key"]
        self.model = config.get("model", "claude-3-sonnet-20240229")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)
        input_cost_key = "cost_per_input_token"
        output_cost_key = "cost_per_output_token"
        self.cost_per_input_token = config.get(input_cost_key, 0.000003)
        self.cost_per_output_token = config.get(output_cost_key, 0.000015)

        self.client = client or anthropic.AsyncAnthropic(api_key=self.api_key)

    def validate_config(self) -> None:
        """Validate Claude provider configuration."""
        if not self.config.get("api_key"):
            raise AIProviderError("api_key is required for Claude provider")

        model = self.config.get("model", "claude-3-sonnet-20240229")
        if model not in self.SUPPORTED_MODELS:
            error_msg = (
                f"Invalid model: {model}. " f"Supported models: {self.SUPPORTED_MODELS}"
            )
            raise AIProviderError(error_msg)

    async def generate_text(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> AIProviderResult:
        """Generate text using Claude API."""
        start_time = time.time()

        try:
            messages = [{"role": "user", "content": prompt}]

            api_kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": messages,
            }

            if system_prompt:
                api_kwargs["system"] = system_prompt

            # Override with any additional kwargs
            api_kwargs.update(kwargs)

            response = await self.client.messages.create(**api_kwargs)

            # Extract response content
            content = response.content[0].text if response.content else ""

            # Create token usage object
            token_usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            # Calculate cost
            cost = self.get_cost_estimate(
                token_usage.input_tokens, token_usage.output_tokens
            )

            # Record usage if cost tracker is available
            if self.cost_tracker:
                self.cost_tracker.record_usage(token_usage, cost)

            response_time = time.time() - start_time

            return AIProviderResult(
                success=True,
                content=content,
                token_usage=token_usage,
                cost=cost,
                response_time=response_time,
            )

        except Exception as e:
            response_time = time.time() - start_time
            return AIProviderResult(
                success=False,
                error_message=str(e),
                response_time=response_time,
            )

    async def health_check(self) -> bool:
        """Check if Claude API is accessible."""
        try:
            # Simple test message to verify API connectivity
            await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Health check"}],
            )
            return True
        except Exception:
            return False

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost estimate for token usage."""
        input_cost = input_tokens * self.cost_per_input_token
        output_cost = output_tokens * self.cost_per_output_token
        return input_cost + output_cost
