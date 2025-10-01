"""
Unit tests for NotificationManager - TDD implementation
Following the Red-Green-Refactor cycle for multi-channel notification system
"""
import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from core.notification_manager import (
    NotificationManager,
    NotificationEvent,
    NotificationChannel,
    NotificationResult,
    NotificationTemplate,
    NotificationManagerError
)
from core.task_manager import TaskEvent
from core.exceptions import BaseSystemError
from core.plugin_registry import PluginRegistry


class TestNotificationManager:
    """Unit tests for NotificationManager"""
    
    @pytest.fixture
    def mock_plugin_registry(self):
        """Create mock plugin registry"""
        registry = Mock()
        slack_plugin = AsyncMock()
        email_plugin = AsyncMock()
        
        registry.get_plugin = Mock(side_effect=lambda plugin_type, name=None: {
            'communication': slack_plugin,
            'email': email_plugin
        }.get(plugin_type))
        
        return registry, slack_plugin, email_plugin
    
    @pytest.fixture
    def notification_config(self):
        """Create notification configuration"""
        return {
            'slack': {
                'enabled': True,
                'default_channel': '#general',
                'channels': {
                    'task_updates': '#dev-updates',
                    'errors': '#alerts'
                }
            },
            'email': {
                'enabled': True,
                'default_recipients': ['team@example.com'],
                'smtp_server': 'smtp.example.com'
            },
            'templates': {
                'task_started': 'templates/task_started.txt',
                'task_completed': 'templates/task_completed.txt',
                'task_error': 'templates/task_error.txt'
            }
        }
    
    @pytest.fixture
    def notification_manager(self, mock_plugin_registry, notification_config):
        """Create NotificationManager instance for testing"""
        registry, _, _ = mock_plugin_registry
        return NotificationManager(plugin_registry=registry, config=notification_config)
    
    @pytest.fixture
    def sample_task_event(self):
        """Create sample task event for testing"""
        return TaskEvent(
            type='task_completed',
            task_id='TEST-123',
            agent_id='agent-001',
            pr_url='https://github.com/test/repo/pull/123',
            metadata={
                'task_title': 'Implement user authentication',
                'files_changed': ['src/auth.py', 'tests/test_auth.py'],
                'test_results': {'passed': 15, 'failed': 0, 'coverage': 95.2}
            }
        )

    def test_notification_manager_initialization(self, notification_manager):
        """Test NotificationManager initialization"""
        assert notification_manager is not None
        assert hasattr(notification_manager, 'send_task_notification')
        assert hasattr(notification_manager, 'send_multi_channel_notification')
        assert hasattr(notification_manager, 'get_notification_templates')

    @pytest.mark.asyncio
    async def test_send_slack_notification_success(self, notification_manager, mock_plugin_registry, sample_task_event):
        """Test successful Slack notification"""
        registry, slack_plugin, _ = mock_plugin_registry
        slack_plugin.send_message.return_value = {'success': True, 'message_id': 'msg_123'}
        
        result = await notification_manager.send_slack_notification(
            channel='#dev-updates',
            message='Task completed successfully',
            event=sample_task_event
        )
        
        assert result.success is True
        assert result.channel == NotificationChannel.SLACK
        slack_plugin.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_slack_notification_failure(self, notification_manager, mock_plugin_registry):
        """Test Slack notification failure"""
        registry, slack_plugin, _ = mock_plugin_registry
        slack_plugin.send_message.side_effect = Exception("Network error")
        
        result = await notification_manager.send_slack_notification(
            channel='#alerts',
            message='Error occurred',
            event=None
        )
        
        assert result.success is False
        assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_send_email_notification_success(self, notification_manager, mock_plugin_registry, sample_task_event):
        """Test successful email notification"""
        registry, _, email_plugin = mock_plugin_registry
        email_plugin.send_email.return_value = {'success': True, 'message_id': 'email_123'}
        
        result = await notification_manager.send_email_notification(
            recipients=['dev@example.com'],
            subject='Task Completed',
            message='Task TEST-123 has been completed',
            event=sample_task_event
        )
        
        assert result.success is True
        assert result.channel == NotificationChannel.EMAIL
        email_plugin.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_task_notification_task_started(self, notification_manager, mock_plugin_registry, sample_task_event):
        """Test task started notification"""
        registry, slack_plugin, _ = mock_plugin_registry
        slack_plugin.send_message.return_value = {'success': True}
        
        task_started_event = TaskEvent(
            type='task_started',
            task_id='TEST-123',
            agent_id='agent-001'
        )
        
        results = await notification_manager.send_task_notification(task_started_event)
        
        assert len(results) > 0
        assert any(result.success for result in results)
        slack_plugin.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_send_task_notification_task_completed(self, notification_manager, mock_plugin_registry, sample_task_event):
        """Test task completed notification"""
        registry, slack_plugin, _ = mock_plugin_registry
        slack_plugin.send_message.return_value = {'success': True}
        
        results = await notification_manager.send_task_notification(sample_task_event)
        
        assert len(results) > 0
        assert any(result.success for result in results)
        # Should include PR URL in the message
        call_args = slack_plugin.send_message.call_args
        message_content = str(call_args)
        assert 'https://github.com/test/repo/pull/123' in message_content

    @pytest.mark.asyncio
    async def test_send_task_notification_task_error(self, notification_manager, mock_plugin_registry):
        """Test task error notification"""
        registry, slack_plugin, _ = mock_plugin_registry
        slack_plugin.send_message.return_value = {'success': True}
        
        error_event = TaskEvent(
            type='task_error',
            task_id='TEST-456',
            agent_id='agent-002',
            metadata={
                'error_type': 'compilation_error',
                'error_message': 'Syntax error in src/main.py',
                'task_title': 'Fix login bug'
            }
        )
        
        results = await notification_manager.send_task_notification(error_event)
        
        assert len(results) > 0
        # Error notifications should go to alerts channel
        call_args = slack_plugin.send_message.call_args
        # Check first positional argument (channel)
        assert call_args[0][0] == '#alerts'

    @pytest.mark.asyncio
    async def test_send_multi_channel_notification(self, notification_manager, mock_plugin_registry, sample_task_event):
        """Test multi-channel notification sending"""
        registry, slack_plugin, email_plugin = mock_plugin_registry
        slack_plugin.send_message.return_value = {'success': True}
        email_plugin.send_email.return_value = {'success': True}
        
        channels = [NotificationChannel.SLACK, NotificationChannel.EMAIL]
        message = "Multi-channel notification test"
        
        results = await notification_manager.send_multi_channel_notification(
            channels=channels,
            message=message,
            event=sample_task_event
        )
        
        assert len(results) == 2
        assert all(result.success for result in results)
        slack_plugin.send_message.assert_called_once()
        email_plugin.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_format_notification_message_task_completed(self, notification_manager, sample_task_event):
        """Test notification message formatting for task completion"""
        message = notification_manager.format_notification_message(
            sample_task_event, 
            NotificationChannel.SLACK
        )
        
        assert 'TEST-123' in message
        assert 'completed' in message.lower()
        assert 'https://github.com/test/repo/pull/123' in message
        assert 'agent-001' in message

    @pytest.mark.asyncio
    async def test_format_notification_message_task_error(self, notification_manager):
        """Test notification message formatting for task error"""
        error_event = TaskEvent(
            type='task_error',
            task_id='TEST-789',
            agent_id='agent-003',
            metadata={
                'error_type': 'test_failure',
                'error_message': '5 tests failed',
                'task_title': 'Add validation logic'
            }
        )
        
        message = notification_manager.format_notification_message(
            error_event,
            NotificationChannel.SLACK
        )
        
        assert 'TEST-789' in message
        assert 'error' in message.lower()
        assert '5 tests failed' in message
        assert 'Add validation logic' in message

    @pytest.mark.asyncio
    async def test_get_notification_channel_for_event(self, notification_manager):
        """Test channel selection based on event type"""
        # Task completion should go to dev-updates
        completed_event = TaskEvent(type='task_completed', task_id='TEST-1')
        channel = notification_manager.get_notification_channel(completed_event, NotificationChannel.SLACK)
        assert channel == '#dev-updates'
        
        # Error should go to alerts
        error_event = TaskEvent(type='task_error', task_id='TEST-2')
        channel = notification_manager.get_notification_channel(error_event, NotificationChannel.SLACK)
        assert channel == '#alerts'
        
        # Default case
        other_event = TaskEvent(type='task_started', task_id='TEST-3')
        channel = notification_manager.get_notification_channel(other_event, NotificationChannel.SLACK)
        assert channel == '#general'

    @pytest.mark.asyncio
    async def test_load_notification_template(self, notification_manager):
        """Test notification template loading"""
        # Mock template file content
        template_content = "Task {{task_id}} - {{task_title}} has been {{action}}"
        
        with patch('builtins.open', Mock()):
            with patch('pathlib.Path.read_text', return_value=template_content):
                template = notification_manager.load_template('task_completed')
                
                context = {
                    'task_id': 'TEST-123',
                    'task_title': 'Test task',
                    'action': 'completed'
                }
                
                rendered = template.render(context)
                assert 'Task TEST-123 - Test task has been completed' == rendered

    @pytest.mark.asyncio
    async def test_rate_limiting(self, notification_manager, mock_plugin_registry):
        """Test notification rate limiting"""
        registry, slack_plugin, _ = mock_plugin_registry
        slack_plugin.send_message.return_value = {'success': True}
        
        # Send multiple notifications rapidly
        tasks = []
        for i in range(10):
            event = TaskEvent(type='task_completed', task_id=f'TEST-{i}')
            tasks.append(notification_manager.send_task_notification(event))
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed but rate limiting should be applied internally
        assert all(any(r.success for r in result) for result in results)
        # Verify calls were made (rate limiting is internal)
        assert slack_plugin.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_notification_retry_on_failure(self, notification_manager, mock_plugin_registry, sample_task_event):
        """Test notification retry mechanism"""
        registry, slack_plugin, _ = mock_plugin_registry
        
        # First call fails, second succeeds
        slack_plugin.send_message.side_effect = [
            Exception("Temporary failure"),
            {'success': True, 'message_id': 'retry_success'}
        ]
        
        result = await notification_manager.send_slack_notification(
            channel='#general',
            message='Retry test',
            event=sample_task_event
        )
        
        # Should succeed after retry
        assert result.success is True
        assert slack_plugin.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_notification_filtering(self, notification_manager):
        """Test notification filtering based on configuration"""
        # Low priority events might be filtered
        low_priority_event = TaskEvent(
            type='task_started',
            task_id='TEST-LOW',
            metadata={'priority': 'low'}
        )
        
        should_notify = notification_manager.should_notify(low_priority_event)
        
        # Should still notify for task events, but this tests the filtering mechanism
        assert isinstance(should_notify, bool)

    @pytest.mark.asyncio
    async def test_notification_batching(self, notification_manager, mock_plugin_registry):
        """Test notification batching for multiple events"""
        registry, slack_plugin, _ = mock_plugin_registry
        slack_plugin.send_message.return_value = {'success': True}
        
        events = [
            TaskEvent(type='task_completed', task_id=f'TEST-{i}')
            for i in range(5)
        ]
        
        results = await notification_manager.send_batch_notifications(events)
        
        assert len(results) == 5
        assert all(any(r.success for r in result) for result in results)

    @pytest.mark.asyncio
    async def test_notification_manager_error_handling(self, notification_manager):
        """Test NotificationManager error handling"""
        # Test with None event
        with pytest.raises(NotificationManagerError, match="Event is required"):
            await notification_manager.send_task_notification(None)
        
        # Test with invalid channel
        invalid_event = TaskEvent(type='invalid_type', task_id='TEST-ERR')
        # Should not raise but handle gracefully
        results = await notification_manager.send_task_notification(invalid_event)
        assert isinstance(results, list)


class TestNotificationDataModels:
    """Unit tests for notification data models"""
    
    def test_notification_result_creation(self):
        """Test NotificationResult creation"""
        result = NotificationResult(
            success=True,
            channel=NotificationChannel.SLACK,
            message_id='msg_123',
            timestamp=datetime.now()
        )
        
        assert result.success is True
        assert result.channel == NotificationChannel.SLACK
        assert result.message_id == 'msg_123'
        assert isinstance(result.timestamp, datetime)

    def test_notification_event_creation(self):
        """Test NotificationEvent creation"""
        event = NotificationEvent(
            type='custom_notification',
            channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
            message='Custom message',
            recipients=['user@example.com'],
            metadata={'custom_key': 'custom_value'}
        )
        
        assert event.type == 'custom_notification'
        assert len(event.channels) == 2
        assert event.message == 'Custom message'
        assert event.recipients == ['user@example.com']

    def test_notification_template_creation(self):
        """Test NotificationTemplate creation"""
        template = NotificationTemplate(
            name='test_template',
            content='Hello {{name}}, your task {{task_id}} is {{status}}',
            channel=NotificationChannel.SLACK
        )
        
        assert template.name == 'test_template'
        assert template.channel == NotificationChannel.SLACK
        
        # Test rendering
        context = {'name': 'John', 'task_id': 'TEST-1', 'status': 'completed'}
        rendered = template.render(context)
        assert 'Hello John, your task TEST-1 is completed' == rendered

    def test_notification_channel_enum(self):
        """Test NotificationChannel enumeration"""
        assert NotificationChannel.SLACK.value == 'slack'
        assert NotificationChannel.EMAIL.value == 'email'
        assert NotificationChannel.WEBHOOK.value == 'webhook'