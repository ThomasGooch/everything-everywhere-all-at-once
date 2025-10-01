"""Claude AI Plugin for intelligent code generation and analysis"""

import logging
import os
from typing import Any, Dict, Optional

import anthropic
from anthropic import Anthropic

from core.plugin_interface import (
    AIProviderPlugin,
    PluginResult,
    PluginStatus,
    PluginType,
)

logger = logging.getLogger(__name__)


class ClaudePlugin(AIProviderPlugin):
    """Claude AI Plugin for code generation and analysis"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Claude plugin with configuration"""
        super().__init__(config)
        self.client: Optional[Anthropic] = None

        # Default model and pricing info (per million tokens)
        self.default_model = config.get("model", "claude-3-5-sonnet-20241022")
        self.input_cost_per_million = 3.00
        self.output_cost_per_million = 15.00

    def get_plugin_type(self) -> PluginType:
        """Return the plugin type"""
        return PluginType.AI_PROVIDER

    def get_plugin_name(self) -> str:
        """Return the plugin name"""
        return "claude"

    def get_version(self) -> str:
        """Return plugin version"""
        return "1.0.0"

    def get_required_config_keys(self) -> list[str]:
        """Return required configuration keys"""
        return ["api_key"]

    def get_optional_config_keys(self) -> list[str]:
        """Return optional configuration keys"""
        return ["model", "max_tokens", "temperature"]

    def validate_config(self) -> bool:
        """Validate plugin configuration"""
        required_keys = self.get_required_config_keys()

        for key in required_keys:
            if key not in self.config:
                logger.error(f"Missing required config key: {key}")
                return False

        # Validate API key format
        api_key = self.config.get("api_key", "")
        if not api_key.startswith("sk-ant-"):
            logger.error("Invalid Claude API key format")
            return False

        return True

    async def initialize(self) -> bool:
        """Initialize the Claude client"""
        try:
            if not self.validate_config():
                return False

            # Initialize Anthropic client
            api_key = self.config.get("api_key")
            self.client = Anthropic(api_key=api_key)

            # Test connection
            if await self.test_connection():
                self._is_initialized = True
                self._connection_established = True
                logger.info("Claude plugin initialized successfully")
                return True
            else:
                logger.error("Failed to establish connection to Claude API")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Claude plugin: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test connection to Claude API"""
        try:
            if not self.client:
                return False

            # Simple test message to verify connection
            response = self.client.messages.create(
                model=self.default_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}],
            )

            return bool(response.content)

        except Exception as e:
            logger.error(f"Claude connection test failed: {e}")
            return False

    async def cleanup(self) -> bool:
        """Clean up Claude plugin resources"""
        try:
            self.client = None
            self._is_initialized = False
            self._connection_established = False
            logger.info("Claude plugin cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up Claude plugin: {e}")
            return False

    async def health_check(self) -> PluginStatus:
        """Check Claude plugin health"""
        if not self._is_initialized or not self.client:
            return PluginStatus.UNHEALTHY

        try:
            if await self.test_connection():
                return PluginStatus.HEALTHY
            else:
                return PluginStatus.DEGRADED
        except Exception:
            return PluginStatus.UNHEALTHY

    async def generate_text(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> PluginResult:
        """Generate text using Claude API"""
        try:
            if not self.client:
                return PluginResult(
                    success=False, error="Claude client not initialized"
                )

            # Create message
            response = self.client.messages.create(
                model=self.default_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract generated text
            generated_text = ""
            if response.content and len(response.content) > 0:
                generated_text = response.content[0].text

            # Calculate actual cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens / 1_000_000) * self.input_cost_per_million + (
                output_tokens / 1_000_000
            ) * self.output_cost_per_million

            return PluginResult(
                success=True,
                data={
                    "generated_text": generated_text,
                    "model": self.default_model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": cost,
                },
                metadata={
                    "prompt_length": len(prompt),
                    "response_length": len(generated_text),
                    "model": self.default_model,
                    "temperature": temperature,
                },
            )

        except Exception as e:
            logger.error(f"Error generating text with Claude: {e}")
            return PluginResult(success=False, error=f"Text generation failed: {e}")

    async def estimate_cost(self, prompt: str, max_tokens: int = 1000) -> float:
        """Estimate cost for Claude API call"""
        try:
            # Rough estimation: 1 token ≈ 4 characters
            estimated_input_tokens = len(prompt) / 4
            estimated_output_tokens = max_tokens

            cost = (
                estimated_input_tokens / 1_000_000
            ) * self.input_cost_per_million + (
                estimated_output_tokens / 1_000_000
            ) * self.output_cost_per_million

            return cost

        except Exception as e:
            logger.error(f"Error estimating cost: {e}")
            return 0.0

    async def generate_code(
        self,
        task_description: str,
        programming_language: str = "python",
        framework: Optional[str] = None,
        additional_context: Optional[str] = None,
    ) -> PluginResult:
        """Generate code based on task description"""

        # Build comprehensive prompt for code generation
        prompt_parts = [
            f"Generate {programming_language} code for the following task:",
            f"Task: {task_description}",
        ]

        if framework:
            prompt_parts.append(f"Framework: {framework}")

        if additional_context:
            prompt_parts.append(f"Additional Context: {additional_context}")

        prompt_parts.extend(
            [
                "",
                "Requirements:",
                "- Write clean, production-ready code",
                "- Include proper error handling",
                "- Add docstrings and comments",
                "- Follow best practices and conventions",
                "- Include example usage if applicable",
                "",
                "Return only the code without additional explanation.",
            ]
        )

        prompt = "\n".join(prompt_parts)

        # Generate code with higher max tokens for complex tasks
        return await self.generate_text(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.2,  # Lower temperature for more consistent code
        )

    async def analyze_code(
        self, code: str, analysis_type: str = "review"
    ) -> PluginResult:
        """Analyze existing code and provide insights"""

        analysis_prompts = {
            "review": "Review this code for quality, bugs, and improvements:",
            "security": "Analyze this code for security vulnerabilities:",
            "performance": "Analyze this code for performance optimizations:",
            "documentation": "Generate documentation for this code:",
        }

        if analysis_type not in analysis_prompts:
            return PluginResult(
                success=False, error=f"Unknown analysis type: {analysis_type}"
            )

        prompt = f"{analysis_prompts[analysis_type]}\n\n```\n{code}\n```"

        return await self.generate_text(prompt=prompt, max_tokens=1500, temperature=0.3)

    async def generate_tests(
        self, code: str, test_framework: str = "pytest"
    ) -> PluginResult:
        """Generate unit tests for given code"""

        prompt = f"""
Generate comprehensive unit tests for the following code using {test_framework}:

```
{code}
```

Requirements:
- Test all public methods and functions
- Include edge cases and error scenarios
- Use appropriate assertions and mocking
- Follow {test_framework} conventions
- Include setup and teardown if needed

Return only the test code without additional explanation.
        """.strip()

        return await self.generate_text(prompt=prompt, max_tokens=2000, temperature=0.2)
