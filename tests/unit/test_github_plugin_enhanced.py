"""Enhanced unit tests for GitHub Plugin advanced features"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.plugin_interface import PluginResult
from plugins.github_plugin import GitHubPlugin


@pytest.mark.integration
class TestGitHubPluginEnhanced:
    """Test advanced GitHub plugin features"""

    @pytest.fixture
    def enhanced_github_config(self):
        """Enhanced GitHub configuration for testing"""
        return {
            "connection": {
                "token": "ghp_test_token_123",
                "api_url": "https://api.github.com",
            },
            "options": {
                "timeout": 60,
                "default_branch": "main",
                "branch_strategies": {
                    "feature": "feature/{task_id}-{title_slug}",
                    "hotfix": "hotfix/{task_id}-{title_slug}",
                    "release": "release/{version}",
                },
                "pr_templates": {
                    "default": "standard_pr_template.md",
                    "ai_generated": "ai_pr_template.md",
                },
                "auto_reviewers": {
                    "rules": [
                        {"path_pattern": "*.py", "reviewers": ["python-team"]},
                        {"path_pattern": "*.js", "reviewers": ["frontend-team"]},
                        {"size_threshold": 500, "reviewers": ["senior-dev"]},
                    ]
                },
            },
        }

    @pytest.fixture
    def enhanced_github_plugin(self, enhanced_github_config):
        """Create enhanced GitHub plugin instance"""
        return GitHubPlugin(enhanced_github_config)

    # RED: Test for setup_workspace_with_analysis
    @pytest.mark.asyncio
    async def test_setup_workspace_with_analysis(self, enhanced_github_plugin):
        """Test advanced workspace setup with codebase analysis"""

        workspace_config = {
            "repository_url": "https://github.com/user/repo.git",
            "branch_strategy": "feature",
            "task_id": "TEST-123",
            "title_slug": "implement-feature",
            "base_branch": "main",
            "analyze_codebase": True,
        }

        with patch.object(
            enhanced_github_plugin, "clone_repository"
        ) as mock_clone, patch.object(
            enhanced_github_plugin, "create_branch"
        ) as mock_branch, patch.object(
            enhanced_github_plugin, "_analyze_codebase_structure"
        ) as mock_analyze:
            mock_clone.return_value = PluginResult(
                success=True, data={"path": "/tmp/repo"}
            )
            mock_branch.return_value = PluginResult(
                success=True, data={"branch": "feature/TEST-123-implement-feature"}
            )
            mock_analyze.return_value = {
                "languages": ["Python", "JavaScript"],
                "frameworks": ["FastAPI", "React"],
                "test_framework": "pytest",
                "ci_config": ".github/workflows/ci.yml",
            }

            result = await enhanced_github_plugin.setup_workspace_with_analysis(
                workspace_config
            )

            assert result.success
            assert result.data["workspace_path"] == "/tmp/repo"
            assert result.data["branch_name"] == "feature/TEST-123-implement-feature"
            assert "codebase_analysis" in result.data
            assert result.data["codebase_analysis"]["languages"] == [
                "Python",
                "JavaScript",
            ]

    # RED: Test for create_pr_with_metadata
    @pytest.mark.asyncio
    async def test_create_pr_with_metadata(self, enhanced_github_plugin):
        """Test creating PR with rich metadata and auto-assigned reviewers"""

        pr_data = {
            "repository": "user/repo",
            "source_branch": "feature/TEST-123-implement-feature",
            "target_branch": "main",
            "title": "Implement new feature",
            "task_data": {
                "id": "TEST-123",
                "title": "Implement new feature",
                "description": "Add new feature with tests",
            },
            "implementation_data": {
                "files_modified": ["src/main.py", "src/utils.js"],
                "files_created": ["tests/test_feature.py"],
                "test_results": {"passed": 15, "total": 15},
            },
            "template_type": "ai_generated",
        }

        with patch.object(enhanced_github_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(
                return_value={
                    "id": 42,
                    "number": 42,
                    "html_url": "https://github.com/user/repo/pull/42",
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await enhanced_github_plugin.create_pr_with_metadata(pr_data)

            assert result.success
            assert result.data["pr_number"] == 42
            assert result.data["pr_url"] == "https://github.com/user/repo/pull/42"

            # Verify PR body contains expected metadata
            call_args = mock_session.post.call_args
            pr_body = json.loads(call_args[1]["data"])["body"]

            assert "TEST-123" in pr_body
            assert "src/main.py" in pr_body
            assert "15/15 passed" in pr_body

    # RED: Test for auto reviewer assignment
    @pytest.mark.asyncio
    async def test_get_auto_reviewers(self, enhanced_github_plugin):
        """Test automatic reviewer assignment based on rules"""

        file_changes = {
            "modified": ["src/main.py", "src/api/handlers.py"],
            "created": ["tests/test_feature.py", "frontend/component.js"],
            "deleted": [],
        }

        reviewers = enhanced_github_plugin._get_auto_reviewers(file_changes)

        # Should include python-team for .py files and frontend-team for .js files
        assert "python-team" in reviewers
        assert "frontend-team" in reviewers

        # For large changes, should include senior-dev
        large_file_changes = {
            "modified": [
                f"src/file_{i}.py" for i in range(600)
            ],  # Exceeds size threshold of 500
            "created": [],
            "deleted": [],
        }

        large_reviewers = enhanced_github_plugin._get_auto_reviewers(large_file_changes)
        assert "senior-dev" in large_reviewers

    # RED: Test for branch strategy templates
    def test_generate_branch_name(self, enhanced_github_plugin):
        """Test branch name generation using strategies"""

        # Feature branch strategy
        branch_name = enhanced_github_plugin._generate_branch_name(
            strategy="feature", task_id="TEST-123", title_slug="implement-new-api"
        )

        assert branch_name == "feature/TEST-123-implement-new-api"

        # Hotfix branch strategy
        branch_name = enhanced_github_plugin._generate_branch_name(
            strategy="hotfix", task_id="HOTFIX-456", title_slug="fix-critical-bug"
        )

        assert branch_name == "hotfix/HOTFIX-456-fix-critical-bug"

        # Release branch strategy
        branch_name = enhanced_github_plugin._generate_branch_name(
            strategy="release", version="v1.2.0"
        )

        assert branch_name == "release/v1.2.0"

    # RED: Test for PR template rendering
    def test_render_pr_template(self, enhanced_github_plugin):
        """Test PR template rendering with task and implementation data"""

        template_data = {
            "task_data": {
                "id": "TEST-123",
                "title": "Implement feature",
                "description": "Add new feature with proper testing",
            },
            "implementation_data": {
                "files_modified": ["src/main.py", "src/utils.py"],
                "files_created": ["tests/test_feature.py"],
                "test_results": {"passed": 12, "total": 12},
                "ai_cost": 0.23,
            },
            "codebase_analysis": {
                "languages": ["Python"],
                "frameworks": ["FastAPI"],
                "test_framework": "pytest",
            },
        }

        pr_body = enhanced_github_plugin._render_pr_template(
            "ai_generated", template_data
        )

        assert "TEST-123" in pr_body
        assert "Implement feature" in pr_body
        assert "src/main.py" in pr_body
        assert "tests/test_feature.py" in pr_body
        assert "12/12 passed" in pr_body
        assert "$0.23" in pr_body
        assert "🤖" in pr_body  # AI-generated indicator

    # RED: Test for GitHub Actions integration
    @pytest.mark.asyncio
    async def test_trigger_github_actions(self, enhanced_github_plugin):
        """Test triggering GitHub Actions workflow"""

        with patch.object(enhanced_github_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 204  # Success for workflow dispatch
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await enhanced_github_plugin.trigger_github_actions(
                repository="user/repo",
                workflow_name="ci.yml",
                branch="feature/test-branch",
                inputs={"environment": "development", "test_suite": "full"},
            )

            assert result.success
            assert "workflow_triggered" in result.data

    # RED: Test for enhanced repository analysis
    @pytest.mark.asyncio
    async def test_analyze_repository_structure(self, enhanced_github_plugin):
        """Test repository structure analysis"""

        mock_repo_files = {
            "tree": [
                {"path": "src/main.py", "type": "blob"},
                {"path": "src/api/__init__.py", "type": "blob"},
                {"path": "tests/test_main.py", "type": "blob"},
                {"path": "package.json", "type": "blob"},
                {"path": "requirements.txt", "type": "blob"},
                {"path": ".github/workflows/ci.yml", "type": "blob"},
            ]
        }

        with patch.object(enhanced_github_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_repo_files)
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await enhanced_github_plugin.analyze_repository_structure(
                repository="user/repo", branch="main"
            )

            assert result.success
            analysis = result.data["analysis"]

            assert "Python" in analysis["languages"]
            assert "JavaScript" in analysis["languages"]  # From package.json
            assert analysis["has_ci"] is True
            assert analysis["has_tests"] is True

    # RED: Test for PR status checks
    @pytest.mark.asyncio
    async def test_get_pr_status(self, enhanced_github_plugin):
        """Test getting PR status with checks and reviews"""

        mock_pr_data = {
            "state": "open",
            "mergeable": True,
            "mergeable_state": "clean",
            "head": {"sha": "abc123def456"},
        }

        mock_status_data = {
            "statuses": [
                {"state": "success", "context": "ci/tests"},
                {"state": "success", "context": "ci/lint"},
            ]
        }

        mock_reviews_data = [
            {"state": "APPROVED", "user": {"login": "reviewer1"}},
            {"state": "CHANGES_REQUESTED", "user": {"login": "reviewer2"}},
        ]

        with patch.object(enhanced_github_plugin, "_session") as mock_session:
            # Mock PR data response
            mock_pr_response = MagicMock()
            mock_pr_response.status = 200
            mock_pr_response.json = AsyncMock(return_value=mock_pr_data)

            # Mock status checks response
            mock_status_response = MagicMock()
            mock_status_response.status = 200
            mock_status_response.json = AsyncMock(return_value=mock_status_data)

            # Mock reviews response
            mock_reviews_response = MagicMock()
            mock_reviews_response.status = 200
            mock_reviews_response.json = AsyncMock(return_value=mock_reviews_data)

            # Set up responses in order: PR, status checks, reviews
            mock_session.get.return_value.__aenter__.side_effect = [
                mock_pr_response,
                mock_status_response,
                mock_reviews_response,
            ]

            result = await enhanced_github_plugin.get_pr_status(
                repository="user/repo", pr_number=42
            )

            assert result.success
            status = result.data["status"]

            assert status["state"] == "open"
            assert status["mergeable"] is True
            assert status["checks"]["ci/tests"] == "success"
            assert status["reviews"]["approved"] == 1
            assert status["reviews"]["changes_requested"] == 1

    # RED: Test for merge PR functionality
    @pytest.mark.asyncio
    async def test_merge_pr_with_strategy(self, enhanced_github_plugin):
        """Test merging PR with different merge strategies"""

        with patch.object(enhanced_github_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={
                    "sha": "abc123def456",
                    "merged": True,
                    "message": "Pull request successfully merged",
                }
            )
            mock_session.put.return_value.__aenter__.return_value = mock_response

            result = await enhanced_github_plugin.merge_pr_with_strategy(
                repository="user/repo",
                pr_number=42,
                merge_method="squash",
                commit_title="feat: implement new feature",
                commit_message="Squashed commit from feature branch",
            )

            assert result.success
            assert result.data["merged"] is True
            assert result.data["commit_sha"] == "abc123def456"

    # RED: Test for label and milestone management
    @pytest.mark.asyncio
    async def test_manage_pr_labels_and_milestones(self, enhanced_github_plugin):
        """Test adding labels and milestones to PR"""

        with patch.object(enhanced_github_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={"labels": [{"name": "ai-generated"}, {"name": "feature"}]}
            )
            mock_session.patch.return_value.__aenter__.return_value = mock_response

            result = await enhanced_github_plugin.update_pr_labels_and_milestone(
                repository="user/repo",
                pr_number=42,
                labels=["ai-generated", "feature", "priority-medium"],
                milestone="v1.2.0",
            )

            assert result.success
            assert "ai-generated" in result.data["labels"]
            assert "feature" in result.data["labels"]

    # RED: Test for draft PR functionality
    @pytest.mark.asyncio
    async def test_create_draft_pr(self, enhanced_github_plugin):
        """Test creating draft PR for work-in-progress"""

        with patch.object(enhanced_github_plugin, "_session") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(
                return_value={
                    "id": 43,
                    "number": 43,
                    "html_url": "https://github.com/user/repo/pull/43",
                    "draft": True,
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await enhanced_github_plugin.create_draft_pr(
                repository="user/repo",
                source_branch="feature/wip-branch",
                target_branch="main",
                title="WIP: New feature implementation",
                body="Work in progress - not ready for review",
            )

            assert result.success
            assert result.data["pr_number"] == 43
            assert result.data["is_draft"] is True
