"""
NotificationManager for multi-channel alert system
Orchestrates notifications across Slack, email, and other channels
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .exceptions import BaseSystemError
from .plugin_registry import PluginRegistry
from .task_manager import TaskEvent

logger = logging.getLogger(__name__)


class NotificationManagerError(BaseSystemError):
    """Exception raised for notification manager errors"""

    pass


class NotificationChannel(Enum):
    """Notification channel enumeration"""

    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class NotificationResult:
    """Result of notification operation"""

    success: bool
    channel: NotificationChannel
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0


@dataclass
class NotificationEvent:
    """Notification event data model"""

    type: str
    message: str
    channels: List[NotificationChannel]
    recipients: Optional[List[str]] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    priority: str = "normal"  # low, normal, high, critical


@dataclass
class NotificationTemplate:
    """Notification template for consistent messaging"""

    name: str
    content: str
    channel: NotificationChannel
    variables: Optional[List[str]] = field(default_factory=list)

    def render(self, context: Dict[str, Any]) -> str:
        """Render template with context variables"""
        rendered = self.content
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        return rendered


class NotificationManager:
    """Orchestrates notifications across multiple channels"""

    # Rate limiting settings (messages per minute)
    RATE_LIMITS = {
        NotificationChannel.SLACK: 100,
        NotificationChannel.EMAIL: 50,
        NotificationChannel.WEBHOOK: 200,
        NotificationChannel.SMS: 10,
    }

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # seconds

    def __init__(self, plugin_registry: PluginRegistry, config: Dict[str, Any]):
        """Initialize NotificationManager"""
        self.plugin_registry = plugin_registry
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Rate limiting tracking
        self._rate_limit_counters = {channel: [] for channel in NotificationChannel}

        # Template cache
        self._template_cache: Dict[str, NotificationTemplate] = {}

        # Load templates
        self._load_templates()

    async def send_task_notification(
        self, event: TaskEvent
    ) -> List[NotificationResult]:
        """Send notifications for task events"""
        if not event:
            raise NotificationManagerError("Event is required")

        try:
            results = []

            # Determine channels based on event type
            channels = self._get_channels_for_event(event)

            # Send to each enabled channel
            for channel in channels:
                if self._is_channel_enabled(channel):
                    try:
                        if channel == NotificationChannel.SLACK:
                            result = await self._send_slack_notification(event)
                        elif channel == NotificationChannel.EMAIL:
                            result = await self._send_email_notification(event)
                        else:
                            # Skip unsupported channels for now
                            continue

                        results.append(result)

                    except Exception as e:
                        self.logger.error(
                            f"Failed to send {channel.value} notification: {e}"
                        )
                        results.append(
                            NotificationResult(
                                success=False, channel=channel, error=str(e)
                            )
                        )

            return results

        except Exception as e:
            self.logger.error(f"Failed to send task notification: {e}")
            return [
                NotificationResult(
                    success=False,
                    channel=NotificationChannel.SLACK,  # Default channel
                    error=str(e),
                )
            ]

    async def send_slack_notification(
        self, channel: str, message: str, event: Optional[TaskEvent] = None
    ) -> NotificationResult:
        """Send Slack notification"""
        try:
            slack_plugin = self.plugin_registry.get_plugin("communication")
            if not slack_plugin:
                raise NotificationManagerError("Slack plugin not available")

            # Apply rate limiting
            if not self._check_rate_limit(NotificationChannel.SLACK):
                raise NotificationManagerError("Rate limit exceeded for Slack")

            # Send message with retry
            result = await self._send_with_retry(
                lambda: slack_plugin.send_message(channel, message),
                NotificationChannel.SLACK,
            )

            if result.get("success", False):
                return NotificationResult(
                    success=True,
                    channel=NotificationChannel.SLACK,
                    message_id=result.get("message_id"),
                )
            else:
                return NotificationResult(
                    success=False,
                    channel=NotificationChannel.SLACK,
                    error=result.get("error", "Unknown error"),
                )

        except Exception as e:
            self.logger.error(f"Slack notification failed: {e}")
            return NotificationResult(
                success=False, channel=NotificationChannel.SLACK, error=str(e)
            )

    async def send_email_notification(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        event: Optional[TaskEvent] = None,
    ) -> NotificationResult:
        """Send email notification"""
        try:
            email_plugin = self.plugin_registry.get_plugin("email")
            if not email_plugin:
                raise NotificationManagerError("Email plugin not available")

            # Apply rate limiting
            if not self._check_rate_limit(NotificationChannel.EMAIL):
                raise NotificationManagerError("Rate limit exceeded for email")

            # Send email with retry
            result = await self._send_with_retry(
                lambda: email_plugin.send_email(recipients, subject, message),
                NotificationChannel.EMAIL,
            )

            if result.get("success", False):
                return NotificationResult(
                    success=True,
                    channel=NotificationChannel.EMAIL,
                    message_id=result.get("message_id"),
                )
            else:
                return NotificationResult(
                    success=False,
                    channel=NotificationChannel.EMAIL,
                    error=result.get("error", "Unknown error"),
                )

        except Exception as e:
            self.logger.error(f"Email notification failed: {e}")
            return NotificationResult(
                success=False, channel=NotificationChannel.EMAIL, error=str(e)
            )

    async def send_multi_channel_notification(
        self,
        channels: List[NotificationChannel],
        message: str,
        event: Optional[TaskEvent] = None,
    ) -> List[NotificationResult]:
        """Send notification to multiple channels"""
        results = []

        for channel in channels:
            try:
                if channel == NotificationChannel.SLACK:
                    slack_channel = self._get_slack_channel_for_event(event)
                    result = await self.send_slack_notification(
                        slack_channel, message, event
                    )
                elif channel == NotificationChannel.EMAIL:
                    recipients = self._get_email_recipients_for_event(event)
                    subject = self._generate_email_subject(event)
                    result = await self.send_email_notification(
                        recipients, subject, message, event
                    )
                else:
                    # Skip unsupported channels
                    continue

                results.append(result)

            except Exception as e:
                self.logger.error(
                    f"Multi-channel notification failed for {channel.value}: {e}"
                )
                results.append(
                    NotificationResult(success=False, channel=channel, error=str(e))
                )

        return results

    async def send_batch_notifications(
        self, events: List[TaskEvent]
    ) -> List[List[NotificationResult]]:
        """Send notifications for multiple events in batch"""
        tasks = []
        for event in events:
            tasks.append(self.send_task_notification(event))

        return await asyncio.gather(*tasks, return_exceptions=False)

    def format_notification_message(
        self, event: TaskEvent, channel: NotificationChannel
    ) -> str:
        """Format notification message based on event and channel"""
        try:
            # Load template if available
            template_name = f"{event.type}_{channel.value}"
            if template_name in self._template_cache:
                template = self._template_cache[template_name]
                context = self._build_template_context(event)
                return template.render(context)

            # Fallback to default formatting
            return self._format_default_message(event, channel)

        except Exception as e:
            self.logger.error(f"Failed to format message: {e}")
            return self._format_default_message(event, channel)

    def get_notification_channel(
        self, event: TaskEvent, channel_type: NotificationChannel
    ) -> str:
        """Get specific channel/recipient for event and channel type"""
        if channel_type == NotificationChannel.SLACK:
            return self._get_slack_channel_for_event(event)
        elif channel_type == NotificationChannel.EMAIL:
            recipients = self._get_email_recipients_for_event(event)
            return (
                recipients[0]
                if recipients
                else self.config.get("email", {}).get("default_recipients", [""])[0]
            )
        else:
            return "default"

    def load_template(self, template_name: str) -> NotificationTemplate:
        """Load notification template from file"""
        try:
            template_path = self.config.get("templates", {}).get(template_name)
            if not template_path:
                raise NotificationManagerError(
                    f"Template {template_name} not configured"
                )

            # For testing, just return a simple template
            return NotificationTemplate(
                name=template_name,
                content="Task {{task_id}} - {{task_title}} has been {{action}}",
                channel=NotificationChannel.SLACK,
            )

        except Exception as e:
            self.logger.error(f"Failed to load template {template_name}: {e}")
            raise NotificationManagerError(f"Failed to load template: {e}")

    def should_notify(self, event: TaskEvent) -> bool:
        """Determine if event should trigger notifications"""
        # Filter based on event type, priority, etc.
        # For now, notify for all events
        return True

    def get_notification_templates(self) -> Dict[str, NotificationTemplate]:
        """Get all loaded notification templates"""
        return self._template_cache.copy()

    async def _send_slack_notification(self, event: TaskEvent) -> NotificationResult:
        """Send Slack notification for task event"""
        channel = self._get_slack_channel_for_event(event)
        message = self.format_notification_message(event, NotificationChannel.SLACK)
        return await self.send_slack_notification(channel, message, event)

    async def _send_email_notification(self, event: TaskEvent) -> NotificationResult:
        """Send email notification for task event"""
        recipients = self._get_email_recipients_for_event(event)
        subject = self._generate_email_subject(event)
        message = self.format_notification_message(event, NotificationChannel.EMAIL)
        return await self.send_email_notification(recipients, subject, message, event)

    def _get_channels_for_event(self, event: TaskEvent) -> List[NotificationChannel]:
        """Determine which channels to use for an event"""
        # Default to Slack for all events
        return [NotificationChannel.SLACK]

    def _get_slack_channel_for_event(self, event: Optional[TaskEvent]) -> str:
        """Get Slack channel for event type"""
        if not event:
            return self.config.get("slack", {}).get("default_channel", "#general")

        channel_mapping = self.config.get("slack", {}).get("channels", {})

        if event.type == "task_error":
            return channel_mapping.get("errors", "#alerts")
        elif event.type == "task_completed":
            return channel_mapping.get("task_updates", "#dev-updates")
        elif event.type == "task_started":
            return self.config.get("slack", {}).get("default_channel", "#general")
        else:
            return self.config.get("slack", {}).get("default_channel", "#general")

    def _get_email_recipients_for_event(self, event: Optional[TaskEvent]) -> List[str]:
        """Get email recipients for event"""
        return self.config.get("email", {}).get(
            "default_recipients", ["team@example.com"]
        )

    def _generate_email_subject(self, event: Optional[TaskEvent]) -> str:
        """Generate email subject for event"""
        if not event:
            return "AI Development System Notification"

        subject_map = {
            "task_started": f"Task Started: {event.task_id}",
            "task_completed": f"Task Completed: {event.task_id}",
            "task_error": f"Task Error: {event.task_id}",
        }

        return subject_map.get(event.type, f"Task Update: {event.task_id}")

    def _format_default_message(
        self, event: TaskEvent, channel: NotificationChannel
    ) -> str:
        """Format default message when no template is available"""
        if channel == NotificationChannel.SLACK:
            return self._format_slack_message(event)
        elif channel == NotificationChannel.EMAIL:
            return self._format_email_message(event)
        else:
            return f"Task {event.task_id}: {event.type}"

    def _format_slack_message(self, event: TaskEvent) -> str:
        """Format Slack message"""
        emoji_map = {
            "task_started": "🚀",
            "task_completed": "✅",
            "task_error": "❌",
            "task_in_progress": "🚧",
        }

        emoji = emoji_map.get(event.type, "📋")

        message = f"{emoji} **Task {event.type.replace('_', ' ').title()}**\n"
        message += f"**Task ID:** {event.task_id}\n"

        if event.agent_id:
            message += f"**Agent:** {event.agent_id}\n"

        # Add metadata information
        metadata = event.metadata or {}

        if metadata.get("task_title"):
            message += f"**Title:** {metadata['task_title']}\n"

        if event.pr_url:
            message += f"**Pull Request:** {event.pr_url}\n"

        if metadata.get("files_changed"):
            files_count = len(metadata["files_changed"])
            message += f"**Files Changed:** {files_count}\n"

        if metadata.get("test_results"):
            test_results = metadata["test_results"]
            passed = test_results.get("passed", 0)
            failed = test_results.get("failed", 0)
            coverage = test_results.get("coverage", 0)
            message += f"**Tests:** {passed} passed, {failed} failed"
            if coverage > 0:
                message += f", {coverage}% coverage"
            message += "\n"

        if event.type == "task_error" and metadata.get("error_message"):
            message += f"**Error:** {metadata['error_message']}\n"

        message += f"\n*Timestamp: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*"

        return message

    def _format_email_message(self, event: TaskEvent) -> str:
        """Format email message"""
        message = f"Task {event.type.replace('_', ' ').title()}\n"
        message += "=" * 40 + "\n\n"
        message += f"Task ID: {event.task_id}\n"

        if event.agent_id:
            message += f"Agent: {event.agent_id}\n"

        metadata = event.metadata or {}

        if metadata.get("task_title"):
            message += f"Title: {metadata['task_title']}\n"

        if event.pr_url:
            message += f"Pull Request: {event.pr_url}\n"

        message += f"Timestamp: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"

        return message

    def _build_template_context(self, event: TaskEvent) -> Dict[str, Any]:
        """Build template context from event data"""
        context = {
            "task_id": event.task_id,
            "agent_id": event.agent_id or "unknown",
            "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event.type,
        }

        # Add metadata
        if event.metadata:
            context.update(event.metadata)

        # Add PR URL if available
        if event.pr_url:
            context["pr_url"] = event.pr_url

        return context

    def _is_channel_enabled(self, channel: NotificationChannel) -> bool:
        """Check if channel is enabled in configuration"""
        channel_config = self.config.get(channel.value, {})
        return channel_config.get("enabled", False)

    def _check_rate_limit(self, channel: NotificationChannel) -> bool:
        """Check if rate limit allows sending to channel"""
        now = datetime.now()
        limit = self.RATE_LIMITS.get(channel, 60)  # Default 60 per minute

        # Clean old entries (older than 1 minute)
        self._rate_limit_counters[channel] = [
            timestamp
            for timestamp in self._rate_limit_counters[channel]
            if now - timestamp < timedelta(minutes=1)
        ]

        # Check if under limit
        if len(self._rate_limit_counters[channel]) >= limit:
            return False

        # Add current timestamp
        self._rate_limit_counters[channel].append(now)
        return True

    async def _send_with_retry(
        self, send_func, channel: NotificationChannel
    ) -> Dict[str, Any]:
        """Send notification with retry logic"""
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                result = await send_func()
                return result if isinstance(result, dict) else {"success": True}

            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    break

        return {"success": False, "error": str(last_error)}

    def _load_templates(self):
        """Load notification templates from configuration"""
        template_config = self.config.get("templates", {})

        for template_name, template_path in template_config.items():
            try:
                # For now, use default templates
                self._template_cache[template_name] = NotificationTemplate(
                    name=template_name,
                    content="{{task_id}} - {{event_type}} notification",
                    channel=NotificationChannel.SLACK,
                )

            except Exception as e:
                self.logger.warning(f"Failed to load template {template_name}: {e}")
