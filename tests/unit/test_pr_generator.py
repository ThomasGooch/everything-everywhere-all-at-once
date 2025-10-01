"""
Unit tests for PRGenerator - TDD implementation
Following the Red-Green-Refactor cycle
"""
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.code_modifier import FileChange, Implementation
from core.exceptions import BaseSystemError
from core.pr_generator import (
    ChangelogEntry,
    CommitMessageFormat,
    PRDescription,
    PRGenerationError,
    PRGenerator,
    ReviewChecklist,
)


class TestPRGenerator:
    """Unit tests for PRGenerator"""

    @pytest.fixture
    def pr_generator(self):
        """Create PRGenerator instance for testing"""
        return PRGenerator()

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return {
            "id": "TEST-123",
            "title": "Add user authentication system",
            "description": "Implement login/logout functionality with JWT tokens",
            "type": "feature",
            "priority": "high",
            "assignee": "developer@example.com",
        }

    @pytest.fixture
    def sample_implementation(self):
        """Create sample implementation for testing"""
        return Implementation(
            task_id="TEST-123",
            description="Add user authentication feature",
            files=[
                FileChange(
                    path="src/auth.py",
                    action="create",
                    content="def authenticate(username, password):\n    return True\n",
                ),
                FileChange(
                    path="src/models/user.py",
                    action="create",
                    content="class User:\n    def __init__(self, username):\n        self.username = username\n",
                ),
                FileChange(
                    path="README.md",
                    action="modify",
                    content="# Updated README with auth info",
                ),
            ],
            commit_message="feat: add user authentication system",
            pr_description="Implements basic user authentication",
        )

    @pytest.fixture
    def sample_test_results(self):
        """Create sample test results for testing"""
        return {
            "passed": 15,
            "failed": 0,
            "coverage": 85.5,
            "duration": 12.3,
            "test_files": ["test_auth.py", "test_user_model.py"],
        }

    def test_pr_generator_initialization(self, pr_generator):
        """Test PRGenerator initialization"""
        assert pr_generator is not None
        assert hasattr(pr_generator, "generate_pr_description")
        assert hasattr(pr_generator, "generate_commit_message")
        assert hasattr(pr_generator, "generate_review_checklist")

    @pytest.mark.asyncio
    async def test_generate_pr_description_success(
        self, pr_generator, sample_task, sample_implementation, sample_test_results
    ):
        """Test successful PR description generation"""
        pr_description = await pr_generator.generate_pr_description(
            task=sample_task,
            implementation=sample_implementation,
            test_results=sample_test_results,
        )

        assert isinstance(pr_description, PRDescription)
        assert pr_description.title == sample_task["title"]
        assert sample_task["id"] in pr_description.summary
        assert len(pr_description.files_changed) == 3
        assert pr_description.test_coverage == 85.5
        assert pr_description.breaking_changes is False
        assert isinstance(pr_description.review_checklist, list)
        assert len(pr_description.review_checklist) > 0

    @pytest.mark.asyncio
    async def test_generate_pr_description_with_breaking_changes(
        self, pr_generator, sample_task, sample_test_results
    ):
        """Test PR description generation with breaking changes"""
        implementation_with_breaking = Implementation(
            task_id="TEST-124",
            description="Update API endpoints",
            files=[
                FileChange(
                    path="src/api.py",
                    action="modify",
                    content="# Updated API with breaking changes",
                )
            ],
            commit_message="feat!: update API endpoints with breaking changes",
            breaking_changes="Removed deprecated /v1/users endpoint",
        )

        pr_description = await pr_generator.generate_pr_description(
            task=sample_task,
            implementation=implementation_with_breaking,
            test_results=sample_test_results,
        )

        assert pr_description.breaking_changes is True
        assert "breaking changes" in pr_description.summary.lower()
        assert "deprecated" in pr_description.changelog_entry.description

    @pytest.mark.asyncio
    async def test_generate_commit_message_feature(self, pr_generator, sample_task):
        """Test conventional commit message generation for feature"""
        commit_msg = await pr_generator.generate_commit_message(
            task=sample_task,
            implementation_summary="Implement JWT-based authentication",
            scope="auth",
        )

        assert isinstance(commit_msg, CommitMessageFormat)
        assert commit_msg.type == "feat"
        assert commit_msg.scope == "auth"
        assert "authentication" in commit_msg.description.lower()
        assert commit_msg.breaking_change is False
        assert len(commit_msg.body) > 0
        assert sample_task["id"] in commit_msg.footer

    @pytest.mark.asyncio
    async def test_generate_commit_message_bugfix(self, pr_generator):
        """Test conventional commit message generation for bug fix"""
        bug_task = {
            "id": "BUG-456",
            "title": "Fix login validation error",
            "description": "Resolve issue where empty passwords were accepted",
            "type": "bug",
        }

        commit_msg = await pr_generator.generate_commit_message(
            task=bug_task,
            implementation_summary="Add password validation check",
            scope="validation",
        )

        assert commit_msg.type == "fix"
        assert commit_msg.scope == "validation"
        assert "fix" in commit_msg.description.lower()

    @pytest.mark.asyncio
    async def test_generate_review_checklist_feature(
        self, pr_generator, sample_implementation
    ):
        """Test review checklist generation for feature"""
        checklist = await pr_generator.generate_review_checklist(
            task_type="feature",
            implementation=sample_implementation,
            files_changed=["src/auth.py", "src/models/user.py"],
        )

        assert isinstance(checklist, ReviewChecklist)
        assert len(checklist.code_review_items) > 0
        assert len(checklist.testing_items) > 0
        assert len(checklist.security_items) > 0
        assert len(checklist.documentation_items) > 0

        # Check for security-specific items since this involves auth
        security_items_text = " ".join(checklist.security_items)
        assert (
            "authentication" in security_items_text.lower()
            or "security" in security_items_text.lower()
        )

    @pytest.mark.asyncio
    async def test_generate_review_checklist_bugfix(
        self, pr_generator, sample_implementation
    ):
        """Test review checklist generation for bug fix"""
        checklist = await pr_generator.generate_review_checklist(
            task_type="bug",
            implementation=sample_implementation,
            files_changed=["src/validation.py"],
        )

        assert isinstance(checklist, ReviewChecklist)
        # Bug fixes should have regression testing items
        testing_text = " ".join(checklist.testing_items)
        assert (
            "regression" in testing_text.lower() or "edge case" in testing_text.lower()
        )

    @pytest.mark.asyncio
    async def test_summarize_changes_create_files(self, pr_generator):
        """Test change summarization for file creation"""
        files = [
            FileChange(path="new_file.py", action="create", content="new content"),
            FileChange(path="another.py", action="create", content="more content"),
        ]

        summary = await pr_generator._summarize_changes(files)

        assert "2 new files" in summary or "created 2 files" in summary
        assert "new_file.py" in summary
        assert "another.py" in summary

    @pytest.mark.asyncio
    async def test_summarize_changes_mixed_actions(self, pr_generator):
        """Test change summarization for mixed file actions"""
        files = [
            FileChange(path="created.py", action="create", content="new"),
            FileChange(path="modified.py", action="modify", content="updated"),
            FileChange(path="deleted.py", action="delete"),
        ]

        summary = await pr_generator._summarize_changes(files)

        assert "1 new" in summary or "created 1" in summary
        assert "1 modified" in summary or "updated 1" in summary
        assert "1 deleted" in summary or "removed 1" in summary

    @pytest.mark.asyncio
    async def test_format_pr_markdown(
        self, pr_generator, sample_task, sample_implementation, sample_test_results
    ):
        """Test PR description formatting in Markdown"""
        pr_description = await pr_generator.generate_pr_description(
            task=sample_task,
            implementation=sample_implementation,
            test_results=sample_test_results,
        )

        markdown = await pr_generator.format_pr_markdown(pr_description)

        assert isinstance(markdown, str)
        assert "## Summary" in markdown
        assert "## Changes Made" in markdown
        assert "## Test Results" in markdown
        assert "## Review Checklist" in markdown
        assert sample_task["id"] in markdown
        assert "85.5%" in markdown  # Coverage percentage

    @pytest.mark.asyncio
    async def test_detect_change_type(self, pr_generator):
        """Test automatic change type detection"""
        # Test feature detection
        feature_files = [
            FileChange(
                path="src/new_feature.py", action="create", content="def new_function()"
            ),
            FileChange(
                path="docs/feature.md", action="create", content="# New feature"
            ),
        ]
        change_type = await pr_generator._detect_change_type(
            feature_files, "Add new user management"
        )
        assert change_type == "feat"

        # Test bug fix detection
        bug_files = [
            FileChange(
                path="src/bugfix.py", action="modify", content="# Fixed the issue"
            )
        ]
        change_type = await pr_generator._detect_change_type(
            bug_files, "Fix validation bug"
        )
        assert change_type == "fix"

        # Test docs detection
        docs_files = [
            FileChange(path="README.md", action="modify", content="Updated docs")
        ]
        change_type = await pr_generator._detect_change_type(
            docs_files, "Update documentation"
        )
        assert change_type == "docs"

    @pytest.mark.asyncio
    async def test_analyze_impact_assessment(self, pr_generator, sample_implementation):
        """Test impact assessment of changes"""
        impact = await pr_generator._analyze_impact(sample_implementation)

        assert isinstance(impact, dict)
        assert "risk_level" in impact
        assert "affected_areas" in impact
        assert "deployment_notes" in impact

        assert impact["risk_level"] in ["low", "medium", "high"]
        assert len(impact["affected_areas"]) > 0

    @pytest.mark.asyncio
    async def test_generate_changelog_entry(
        self, pr_generator, sample_task, sample_implementation
    ):
        """Test changelog entry generation"""
        changelog = await pr_generator.generate_changelog_entry(
            task=sample_task, implementation=sample_implementation
        )

        assert isinstance(changelog, ChangelogEntry)
        assert changelog.version is not None
        assert changelog.type == "added"  # For new features
        assert sample_task["title"] in changelog.description
        assert changelog.breaking_change is False

    @pytest.mark.asyncio
    async def test_validate_pr_requirements(self, pr_generator, sample_implementation):
        """Test PR requirement validation"""
        validation = await pr_generator.validate_pr_requirements(sample_implementation)

        assert isinstance(validation, dict)
        assert "has_tests" in validation
        assert "has_documentation" in validation
        assert "follows_conventions" in validation
        assert "ready_for_review" in validation

    @pytest.mark.asyncio
    async def test_generate_pr_with_failed_tests(
        self, pr_generator, sample_task, sample_implementation
    ):
        """Test PR generation with failed tests"""
        failed_test_results = {
            "passed": 10,
            "failed": 3,
            "coverage": 75.0,
            "duration": 15.2,
            "failures": [
                {"test": "test_auth_invalid_user", "error": "AssertionError"},
                {"test": "test_user_creation", "error": "ValidationError"},
            ],
        }

        pr_description = await pr_generator.generate_pr_description(
            task=sample_task,
            implementation=sample_implementation,
            test_results=failed_test_results,
        )

        assert (
            "⚠️" in pr_description.test_summary
            or "failed" in pr_description.test_summary.lower()
        )
        assert pr_description.ready_for_review is False

    @pytest.mark.asyncio
    async def test_error_handling(self, pr_generator):
        """Test error handling in PR generation"""
        with pytest.raises(PRGenerationError, match="Task is required"):
            await pr_generator.generate_pr_description(None, None, None)

        invalid_task = {"invalid": "data"}
        with pytest.raises(PRGenerationError, match="Task must have"):
            await pr_generator.generate_pr_description(invalid_task, None, None)


class TestPRDescriptionModel:
    """Unit tests for PR description data models"""

    def test_pr_description_creation(self):
        """Test PRDescription model creation"""
        pr_desc = PRDescription(
            title="Add user authentication",
            summary="Implements JWT-based authentication system",
            files_changed=["src/auth.py", "src/models/user.py"],
            test_coverage=85.5,
            test_summary="All tests passing",
            breaking_changes=False,
            review_checklist=["Check authentication logic", "Verify security measures"],
            changelog_entry=ChangelogEntry(
                version="1.1.0", type="added", description="User authentication system"
            ),
        )

        assert pr_desc.title == "Add user authentication"
        assert pr_desc.test_coverage == 85.5
        assert pr_desc.breaking_changes is False
        assert len(pr_desc.review_checklist) == 2
        assert pr_desc.changelog_entry.type == "added"

    def test_commit_message_format_creation(self):
        """Test CommitMessageFormat model creation"""
        commit_msg = CommitMessageFormat(
            type="feat",
            scope="auth",
            description="add user authentication system",
            body="Implements JWT-based authentication with login/logout endpoints",
            footer="Closes TEST-123",
            breaking_change=False,
        )

        assert commit_msg.type == "feat"
        assert commit_msg.scope == "auth"
        assert "authentication" in commit_msg.description
        assert commit_msg.breaking_change is False
        assert "TEST-123" in commit_msg.footer

    def test_review_checklist_creation(self):
        """Test ReviewChecklist model creation"""
        checklist = ReviewChecklist(
            code_review_items=["Check code quality", "Verify error handling"],
            testing_items=["Run all tests", "Check test coverage"],
            security_items=["Review authentication logic", "Check for vulnerabilities"],
            documentation_items=["Update README", "Add API documentation"],
        )

        assert len(checklist.code_review_items) == 2
        assert len(checklist.testing_items) == 2
        assert len(checklist.security_items) == 2
        assert len(checklist.documentation_items) == 2

    def test_changelog_entry_creation(self):
        """Test ChangelogEntry model creation"""
        changelog = ChangelogEntry(
            version="1.2.0",
            type="added",
            description="User authentication system with JWT tokens",
            breaking_change=False,
            migration_notes="No migration required",
        )

        assert changelog.version == "1.2.0"
        assert changelog.type == "added"
        assert "JWT tokens" in changelog.description
        assert changelog.breaking_change is False
        assert changelog.migration_notes == "No migration required"
