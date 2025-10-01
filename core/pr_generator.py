"""
PR Generator for automated pull request creation and description generation
Follows TDD methodology and project conventions from CLAUDE.md
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .code_modifier import FileChange, Implementation
from .exceptions import BaseSystemError

logger = logging.getLogger(__name__)


class PRGenerationError(BaseSystemError):
    """Exception raised for PR generation errors"""

    pass


@dataclass
class PRDescription:
    """Pull request description data model"""

    title: str
    summary: str
    files_changed: List[str]
    test_coverage: float
    test_summary: str
    breaking_changes: bool
    review_checklist: List[str]
    changelog_entry: "ChangelogEntry"
    ready_for_review: bool = True
    impact_assessment: Optional[Dict[str, Any]] = None


@dataclass
class CommitMessageFormat:
    """Conventional commit message format"""

    type: str  # feat, fix, docs, style, refactor, test, chore
    scope: str
    description: str
    body: str
    footer: str
    breaking_change: bool = False


@dataclass
class ReviewChecklist:
    """Code review checklist"""

    code_review_items: List[str] = field(default_factory=list)
    testing_items: List[str] = field(default_factory=list)
    security_items: List[str] = field(default_factory=list)
    documentation_items: List[str] = field(default_factory=list)


@dataclass
class ChangelogEntry:
    """Changelog entry for release notes"""

    version: str
    type: str  # added, changed, deprecated, removed, fixed, security
    description: str
    breaking_change: bool = False
    migration_notes: Optional[str] = None


class PRGenerator:
    """Automated pull request description and commit message generator"""

    # Constants
    DEFAULT_VERSION = "1.0.0"
    DEFAULT_SCOPE = "core"
    MAX_FILES_DISPLAYED = 5
    HIGH_RISK_FILE_THRESHOLD = 10
    MEDIUM_RISK_FILE_THRESHOLD = 5

    # Conventional commit types mapping
    COMMIT_TYPES = {
        "feature": "feat",
        "bug": "fix",
        "bugfix": "fix",
        "documentation": "docs",
        "style": "style",
        "refactor": "refactor",
        "test": "test",
        "chore": "chore",
    }

    # Keywords for different change types
    CHANGE_KEYWORDS = {
        "fix": ["fix", "bug", "error", "issue"],
        "refactor": ["refactor", "cleanup", "reorganize"],
        "test": ["test", "spec"],
        "docs": ["doc", "readme", "guide", "documentation"],
    }

    # File patterns for change type detection
    FILE_PATTERNS = {
        "docs": [r"\.md$", r"\.rst$", r"docs/", r"README"],
        "test": [r"test_.*\.py$", r".*_test\.py$", r"/tests/", r"spec\."],
        "config": [r"\.yaml$", r"\.yml$", r"\.json$", r"config/", r"\.env"],
        "style": [r"\.css$", r"\.scss$", r"\.less$"],
    }

    # Changelog type mapping
    CHANGELOG_TYPE_MAPPING = {
        "feature": "added",
        "bug": "fixed",
        "bugfix": "fixed",
        "documentation": "changed",
        "refactor": "changed",
        "style": "changed",
    }

    def __init__(self) -> None:
        """Initialize PR generator"""
        self.logger = logging.getLogger(__name__)

    async def generate_pr_description(
        self,
        task: Dict[str, Any],
        implementation: Implementation,
        test_results: Optional[Dict[str, Any]] = None,
    ) -> PRDescription:
        """Generate comprehensive PR description"""
        if not task:
            raise PRGenerationError("Task is required")

        if not all(key in task for key in ["id", "title"]):
            raise PRGenerationError("Task must have id and title")

        if not implementation:
            raise PRGenerationError("Implementation is required")

        self.logger.info(f"Generating PR description for task {task.get('id')}")

        # Generate summary
        summary = await self._generate_summary(task, implementation)

        # Add breaking change warning to summary if present
        if (
            implementation.breaking_changes
            or "breaking" in implementation.commit_message.lower()
        ):
            summary += f"\n\n⚠️ **Breaking Changes:** {implementation.breaking_changes or 'This change includes breaking changes'}"

        # Analyze changes
        files_changed = [file_change.path for file_change in implementation.files]
        change_summary = await self._summarize_changes(implementation.files)
        summary += f"\n\n{change_summary}"

        # Process test results
        test_coverage = 0.0
        test_summary = "No test results provided"
        ready_for_review = True

        if test_results:
            test_coverage = test_results.get("coverage", 0.0)
            passed = test_results.get("passed", 0)
            failed = test_results.get("failed", 0)

            if failed > 0:
                test_summary = f"⚠️ {failed} test(s) failed, {passed} passed"
                ready_for_review = False
            else:
                test_summary = f"✅ All {passed} tests passing"

        # Detect breaking changes
        breaking_changes = (
            bool(implementation.breaking_changes)
            or "breaking" in implementation.commit_message.lower()
        )

        # Generate review checklist
        checklist = await self.generate_review_checklist(
            task_type=task.get("type", "feature"),
            implementation=implementation,
            files_changed=files_changed,
        )

        # Generate changelog entry
        changelog = await self.generate_changelog_entry(task, implementation)

        # Analyze impact
        impact = await self._analyze_impact(implementation)

        return PRDescription(
            title=task["title"],
            summary=summary,
            files_changed=files_changed,
            test_coverage=test_coverage,
            test_summary=test_summary,
            breaking_changes=breaking_changes,
            review_checklist=checklist.code_review_items
            + checklist.testing_items
            + checklist.security_items
            + checklist.documentation_items,
            changelog_entry=changelog,
            ready_for_review=ready_for_review,
            impact_assessment=impact,
        )

    async def generate_commit_message(
        self,
        task: Dict[str, Any],
        implementation_summary: str,
        scope: Optional[str] = None,
    ) -> CommitMessageFormat:
        """Generate conventional commit message"""
        # Determine commit type
        task_type = task.get("type", "feature").lower()
        commit_type = self.COMMIT_TYPES.get(task_type, "feat")

        # Detect breaking changes
        breaking = "breaking" in implementation_summary.lower()

        # Format description (lowercase, imperative)
        description = implementation_summary.lower()
        if not description.startswith(("add", "fix", "update", "remove", "implement")):
            if commit_type == "feat":
                description = f"add {description}"
            elif commit_type == "fix":
                description = f"fix {description}"
            else:
                description = f"update {description}"
        elif commit_type == "fix" and not description.startswith("fix"):
            # Ensure fix commits start with 'fix'
            description = f"fix {description}"

        # Generate body
        body = f"Implements {task.get('title', 'requested changes')}"
        if task.get("description"):
            body += f"\n\n{task['description']}"

        # Generate footer
        footer = f"Closes {task['id']}"

        return CommitMessageFormat(
            type=commit_type,
            scope=scope or self.DEFAULT_SCOPE,
            description=description,
            body=body,
            footer=footer,
            breaking_change=breaking,
        )

    async def generate_review_checklist(
        self, task_type: str, implementation: Implementation, files_changed: List[str]
    ) -> ReviewChecklist:
        """Generate code review checklist based on change type"""
        checklist = ReviewChecklist()

        # Base code review items
        checklist.code_review_items = [
            "Code follows project style guidelines",
            "Functions are well-named and focused",
            "Error handling is appropriate",
            "No hardcoded values or magic numbers",
        ]

        # Base testing items
        checklist.testing_items = [
            "Tests are included for new functionality",
            "All tests pass successfully",
            "Test coverage meets project standards",
        ]

        # Type-specific items
        if task_type == "bug":
            checklist.testing_items.extend(
                [
                    "Regression tests added to prevent future occurrences",
                    "Edge cases are properly handled",
                ]
            )
        elif task_type == "feature":
            checklist.testing_items.extend(
                [
                    "Integration tests verify feature works end-to-end",
                    "Performance impact has been considered",
                ]
            )

        # Security items
        checklist.security_items = [
            "No sensitive data is exposed in logs",
            "Input validation is implemented where needed",
            "Authentication and authorization are properly handled",
        ]

        # File-specific security checks
        auth_files = [
            f for f in files_changed if "auth" in f.lower() or "login" in f.lower()
        ]
        if auth_files:
            checklist.security_items.extend(
                [
                    "Authentication logic has been thoroughly reviewed",
                    "Password handling follows security best practices",
                    "Session management is secure",
                ]
            )

        # Documentation items
        checklist.documentation_items = [
            "Code is self-documenting with clear variable names",
            "Complex logic includes explanatory comments",
        ]

        # Check if docs need updating
        if any("api" in f.lower() or "endpoint" in f.lower() for f in files_changed):
            checklist.documentation_items.append("API documentation has been updated")

        return checklist

    async def generate_changelog_entry(
        self, task: Dict[str, Any], implementation: Implementation
    ) -> ChangelogEntry:
        """Generate changelog entry for the change"""
        # Determine entry type
        task_type = task.get("type", "feature").lower()
        entry_type = self.CHANGELOG_TYPE_MAPPING.get(task_type, "added")

        # Version would normally come from version control
        version = self.DEFAULT_VERSION

        # Check for breaking changes
        breaking = bool(implementation.breaking_changes)

        # Use implementation description for breaking changes, otherwise task title
        description = implementation.breaking_changes or task["title"]

        return ChangelogEntry(
            version=version,
            type=entry_type,
            description=description,
            breaking_change=breaking,
            migration_notes=implementation.breaking_changes if breaking else None,
        )

    async def format_pr_markdown(self, pr_description: PRDescription) -> str:
        """Format PR description as Markdown"""
        markdown = f"# {pr_description.title}\n\n"

        # Summary section
        markdown += "## Summary\n\n"
        markdown += f"{pr_description.summary}\n\n"

        # Changes section
        markdown += "## Changes Made\n\n"
        markdown += f"- **Files changed:** {len(pr_description.files_changed)}\n"

        for file_path in pr_description.files_changed:
            markdown += f"  - `{file_path}`\n"

        markdown += "\n"

        # Test results section
        markdown += "## Test Results\n\n"
        markdown += f"{pr_description.test_summary}\n"
        if pr_description.test_coverage > 0:
            markdown += f"- **Test coverage:** {pr_description.test_coverage}%\n"
        markdown += "\n"

        # Breaking changes
        if pr_description.breaking_changes:
            markdown += "## ⚠️ Breaking Changes\n\n"
            if pr_description.changelog_entry.migration_notes:
                markdown += f"{pr_description.changelog_entry.migration_notes}\n\n"
            else:
                markdown += "This change includes breaking changes. Please review carefully.\n\n"

        # Review checklist
        markdown += "## Review Checklist\n\n"
        for item in pr_description.review_checklist:
            markdown += f"- [ ] {item}\n"

        return markdown

    async def validate_pr_requirements(
        self, implementation: Implementation
    ) -> Dict[str, bool]:
        """Validate PR meets requirements"""
        validation = {
            "has_tests": False,
            "has_documentation": False,
            "follows_conventions": True,
            "ready_for_review": True,
        }

        # Check for test files
        test_files = [f for f in implementation.files if self._is_test_file(f.path)]
        validation["has_tests"] = len(test_files) > 0

        # Check for documentation
        doc_files = [f for f in implementation.files if self._is_doc_file(f.path)]
        validation["has_documentation"] = (
            len(doc_files) > 0 or len(implementation.files) <= 2
        )

        # Overall readiness
        validation["ready_for_review"] = (
            validation["has_tests"]
            and validation["has_documentation"]
            and validation["follows_conventions"]
        )

        return validation

    async def _generate_summary(
        self, task: Dict[str, Any], implementation: Implementation
    ) -> str:
        """Generate PR summary from task and implementation"""
        summary = f"**Task:** {task['id']} - {task['title']}\n\n"

        if task.get("description"):
            summary += f"**Description:** {task['description']}\n\n"

        if implementation.description:
            summary += f"**Implementation:** {implementation.description}"

        return summary

    async def _summarize_changes(self, files: List[FileChange]) -> str:
        """Summarize file changes"""
        if not files:
            return "No files changed"

        created = [f for f in files if f.action == "create"]
        modified = [f for f in files if f.action == "modify"]
        deleted = [f for f in files if f.action == "delete"]

        summary_parts = []

        if created:
            if len(created) == 1:
                summary_parts.append("created 1 new file")
            else:
                summary_parts.append(f"created {len(created)} new files")
        if modified:
            if len(modified) == 1:
                summary_parts.append("updated 1 file")
            else:
                summary_parts.append(f"updated {len(modified)} files")
        if deleted:
            if len(deleted) == 1:
                summary_parts.append("removed 1 file")
            else:
                summary_parts.append(f"removed {len(deleted)} files")

        summary = "**Changes:** " + ", ".join(summary_parts)

        # Add notable files
        notable_files = []
        for file_change in files[: self.MAX_FILES_DISPLAYED]:
            notable_files.append(f"  - `{file_change.path}` ({file_change.action})")

        if notable_files:
            summary += "\n\n" + "\n".join(notable_files)

        if len(files) > self.MAX_FILES_DISPLAYED:
            summary += (
                f"\n  - ... and {len(files) - self.MAX_FILES_DISPLAYED} more files"
            )

        return summary

    async def _detect_change_type(
        self, files: List[FileChange], description: str
    ) -> str:
        """Detect the type of change based on files and description"""
        file_paths = [f.path for f in files]

        # Check description keywords first (higher priority)
        description_lower = description.lower()

        for change_type, keywords in self.CHANGE_KEYWORDS.items():
            if any(word in description_lower for word in keywords):
                return change_type

        # Count different file types
        code_files = []
        doc_files = []
        other_files = []

        for path in file_paths:
            if any(
                re.search(pattern, path, re.IGNORECASE)
                for pattern in self.FILE_PATTERNS["docs"]
            ):
                doc_files.append(path)
            elif any(
                re.search(pattern, path, re.IGNORECASE)
                for patterns in [
                    self.FILE_PATTERNS[k] for k in ["test", "config", "style"]
                ]
                for pattern in patterns
            ):
                other_files.append(path)
            else:
                code_files.append(path)

        # If there are code files, prioritize based on code content
        if code_files:
            return "feat"

        # Check for other specific file types
        non_doc_patterns = {k: v for k, v in self.FILE_PATTERNS.items() if k != "docs"}
        for change_type, patterns in non_doc_patterns.items():
            for pattern in patterns:
                if any(re.search(pattern, path, re.IGNORECASE) for path in file_paths):
                    return change_type

        # Check for docs only if only doc files present
        if doc_files and not code_files and not other_files:
            return "docs"

        return "feat"  # Default to feature

    async def _analyze_impact(self, implementation: Implementation) -> Dict[str, Any]:
        """Analyze the impact of the changes"""
        impact: Dict[str, Any] = {
            "risk_level": "low",
            "affected_areas": [],
            "deployment_notes": [],
        }

        # Analyze file changes
        file_count = len(implementation.files)
        new_files = len([f for f in implementation.files if f.action == "create"])

        # Determine risk level
        if file_count > self.HIGH_RISK_FILE_THRESHOLD:
            impact["risk_level"] = "high"
        elif file_count > self.MEDIUM_RISK_FILE_THRESHOLD:
            impact["risk_level"] = "medium"
        elif any("auth" in f.path.lower() for f in implementation.files):
            impact["risk_level"] = "medium"  # Auth changes are always medium risk

        # Identify affected areas
        areas = set()
        for file_change in implementation.files:
            path_parts = file_change.path.split("/")
            if len(path_parts) > 1:
                areas.add(path_parts[0])  # Top-level directory

        impact["affected_areas"] = list(areas)

        # Generate deployment notes
        if implementation.breaking_changes:
            impact["deployment_notes"].append(
                "Breaking changes require careful deployment planning"
            )

        if new_files > 0:
            impact["deployment_notes"].append(f"{new_files} new files will be added")

        return impact

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file"""
        path_lower = file_path.lower()
        return (
            path_lower.startswith("test_")
            or path_lower.endswith("_test.py")
            or "/tests/" in path_lower
            or "spec." in path_lower
        )

    def _is_doc_file(self, file_path: str) -> bool:
        """Check if file is a documentation file"""
        path_lower = file_path.lower()
        return (
            path_lower.endswith(".md")
            or path_lower.endswith(".rst")
            or "readme" in path_lower
            or "docs/" in path_lower
        )
