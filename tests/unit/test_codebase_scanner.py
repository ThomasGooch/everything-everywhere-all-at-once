"""
Unit tests for CodebaseScanner - TDD implementation
Following the Red-Green-Refactor cycle
"""
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from core.codebase_scanner import (
    ArchitecturePattern,
    CodebaseAnalysis,
    CodebaseScanner,
    CodePattern,
    DependencyInfo,
    DocumentationStyle,
    TechStack,
    TestFrameworkInfo,
)
from core.exceptions import BaseSystemError


class TestCodebaseScanner:
    """Unit tests for CodebaseScanner"""

    @pytest.fixture
    def temp_repository(self):
        """Create a temporary repository structure for testing"""
        temp_dir = tempfile.mkdtemp(prefix="test_codebase_")

        # Create a sample repository structure
        repo_structure = {
            "package.json": '{"name": "test-app", "dependencies": {"react": "^18.0.0", "typescript": "^4.0.0"}}',
            "requirements.txt": "fastapi==0.68.0\npydantic==1.8.2\npytest==6.2.4",
            "pyproject.toml": '[tool.poetry]\nname = "test-project"\n[tool.poetry.dependencies]\npython = "^3.9"',
            "src/main.py": 'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/")\ndef read_root():\n    return {"Hello": "World"}',
            "src/components/Button.tsx": 'import React from "react";\nexport const Button = () => <button>Click me</button>;',
            "src/utils/helpers.py": "def format_name(name: str) -> str:\n    return name.title()",
            "tests/test_main.py": "import pytest\nfrom src.main import app\n\ndef test_read_root():\n    assert True",
            "tests/Button.test.tsx": 'import { render } from "@testing-library/react";\nimport { Button } from "../src/components/Button";',
            "docs/README.md": "# Test Project\nThis is a test project.",
            "docs/api.md": "# API Documentation\n## Endpoints",
            ".gitignore": "node_modules/\n__pycache__/\n.env",
            "Dockerfile": "FROM python:3.9\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt",
            "docker-compose.yml": 'version: "3.8"\nservices:\n  app:\n    build: .',
        }

        for file_path, content in repo_structure.items():
            full_path = Path(temp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def codebase_scanner(self):
        """Create CodebaseScanner instance for testing"""
        return CodebaseScanner()

    def test_codebase_scanner_initialization(self, codebase_scanner):
        """Test CodebaseScanner initialization"""
        assert codebase_scanner is not None
        assert hasattr(codebase_scanner, "analyze_repository")
        assert hasattr(codebase_scanner, "detect_tech_stack")
        assert hasattr(codebase_scanner, "identify_architecture")
        assert hasattr(codebase_scanner, "extract_patterns")

    @pytest.mark.asyncio
    async def test_analyze_repository_success(self, codebase_scanner, temp_repository):
        """Test successful repository analysis"""
        analysis = await codebase_scanner.analyze_repository(temp_repository)

        assert isinstance(analysis, CodebaseAnalysis)
        assert analysis.repository_path == temp_repository
        assert analysis.tech_stack is not None
        assert analysis.architecture_pattern is not None
        assert analysis.code_style is not None
        assert analysis.patterns is not None
        assert analysis.dependencies is not None
        assert analysis.test_framework is not None
        assert analysis.documentation_style is not None

    @pytest.mark.asyncio
    async def test_detect_tech_stack_python_fastapi(
        self, codebase_scanner, temp_repository
    ):
        """Test tech stack detection for Python FastAPI project"""
        tech_stack = await codebase_scanner.detect_tech_stack(temp_repository)

        assert isinstance(tech_stack, TechStack)
        assert "python" in tech_stack.languages
        assert "typescript" in tech_stack.languages  # Due to .tsx file
        assert "fastapi" in tech_stack.frameworks
        assert "react" in tech_stack.frameworks
        assert "typescript" in tech_stack.libraries
        assert "pydantic" in tech_stack.libraries

    @pytest.mark.asyncio
    async def test_detect_tech_stack_empty_directory(self, codebase_scanner):
        """Test tech stack detection on empty directory"""
        with tempfile.TemporaryDirectory() as empty_dir:
            tech_stack = await codebase_scanner.detect_tech_stack(empty_dir)

            assert isinstance(tech_stack, TechStack)
            assert len(tech_stack.languages) == 0
            assert len(tech_stack.frameworks) == 0
            assert len(tech_stack.libraries) == 0

    @pytest.mark.asyncio
    async def test_identify_architecture_pattern(
        self, codebase_scanner, temp_repository
    ):
        """Test architecture pattern identification"""
        pattern = await codebase_scanner.identify_architecture(temp_repository)

        assert isinstance(pattern, ArchitecturePattern)
        assert pattern.name in ["microservice", "monolith", "mvc", "layered", "unknown"]
        assert pattern.confidence >= 0.0
        assert pattern.confidence <= 1.0
        assert isinstance(pattern.characteristics, list)

    @pytest.mark.asyncio
    async def test_analyze_code_style_python(self, codebase_scanner, temp_repository):
        """Test Python code style analysis"""
        code_style = await codebase_scanner.analyze_code_style(temp_repository)

        assert code_style is not None
        assert "indentation" in code_style
        assert "naming_convention" in code_style
        assert "import_style" in code_style

    @pytest.mark.asyncio
    async def test_extract_code_patterns(self, codebase_scanner, temp_repository):
        """Test code pattern extraction"""
        patterns = await codebase_scanner.extract_patterns(temp_repository)

        assert isinstance(patterns, list)
        for pattern in patterns:
            assert isinstance(pattern, CodePattern)
            assert hasattr(pattern, "type")
            assert hasattr(pattern, "description")
            assert hasattr(pattern, "examples")

    @pytest.mark.asyncio
    async def test_list_dependencies_python(self, codebase_scanner, temp_repository):
        """Test Python dependency extraction"""
        dependencies = await codebase_scanner.list_dependencies(temp_repository)

        assert isinstance(dependencies, list)

        # Should find dependencies from requirements.txt and pyproject.toml
        dep_names = [
            dep.name for dep in dependencies if isinstance(dep, DependencyInfo)
        ]
        assert any("fastapi" in name for name in dep_names)
        assert any("pydantic" in name for name in dep_names)
        assert any("pytest" in name for name in dep_names)

    @pytest.mark.asyncio
    async def test_detect_test_framework(self, codebase_scanner, temp_repository):
        """Test test framework detection"""
        test_framework = await codebase_scanner.detect_test_framework(temp_repository)

        assert isinstance(test_framework, TestFrameworkInfo)
        assert "pytest" in test_framework.frameworks
        assert test_framework.test_file_patterns is not None
        assert any(
            pattern.endswith(".py") for pattern in test_framework.test_file_patterns
        )

    @pytest.mark.asyncio
    async def test_analyze_documentation_style(self, codebase_scanner, temp_repository):
        """Test documentation style analysis"""
        doc_style = await codebase_scanner.analyze_docs(temp_repository)

        assert isinstance(doc_style, DocumentationStyle)
        assert doc_style.format in ["markdown", "rst", "mixed", "none"]
        assert isinstance(doc_style.structure, dict)
        assert "readme_exists" in doc_style.structure

    @pytest.mark.asyncio
    async def test_scan_directory_structure(self, codebase_scanner, temp_repository):
        """Test directory structure scanning"""
        structure = await codebase_scanner.scan_directory_structure(temp_repository)

        assert isinstance(structure, dict)
        assert "total_files" in structure
        assert "directories" in structure
        assert "file_types" in structure
        assert structure["total_files"] > 0

    @pytest.mark.asyncio
    async def test_identify_configuration_files(
        self, codebase_scanner, temp_repository
    ):
        """Test configuration file identification"""
        config_files = await codebase_scanner.identify_configuration_files(
            temp_repository
        )

        assert isinstance(config_files, list)
        config_names = [cf["name"] for cf in config_files]
        assert any("package.json" in name for name in config_names)
        assert any("pyproject.toml" in name for name in config_names)
        assert any("Dockerfile" in name for name in config_names)

    @pytest.mark.asyncio
    async def test_analyze_imports_and_usage(self, codebase_scanner, temp_repository):
        """Test import and usage analysis"""
        usage_analysis = await codebase_scanner.analyze_imports_and_usage(
            temp_repository
        )

        assert isinstance(usage_analysis, dict)
        assert "python" in usage_analysis or "javascript" in usage_analysis

        if "python" in usage_analysis:
            python_analysis = usage_analysis["python"]
            assert "imports" in python_analysis
            assert "common_patterns" in python_analysis

    def test_file_type_detection(self, codebase_scanner):
        """Test file type detection logic"""
        assert codebase_scanner._get_file_type("test.py") == "python"
        assert codebase_scanner._get_file_type("test.js") == "javascript"
        assert codebase_scanner._get_file_type("test.ts") == "typescript"
        assert codebase_scanner._get_file_type("test.tsx") == "typescript"
        assert codebase_scanner._get_file_type("test.java") == "java"
        assert codebase_scanner._get_file_type("test.cpp") == "cpp"
        assert codebase_scanner._get_file_type("test.unknown") == "unknown"

    def test_is_configuration_file(self, codebase_scanner):
        """Test configuration file detection"""
        assert codebase_scanner._is_configuration_file("package.json") is True
        assert codebase_scanner._is_configuration_file("requirements.txt") is True
        assert codebase_scanner._is_configuration_file("pyproject.toml") is True
        assert codebase_scanner._is_configuration_file("Dockerfile") is True
        assert codebase_scanner._is_configuration_file("docker-compose.yml") is True
        assert codebase_scanner._is_configuration_file(".gitignore") is True
        assert codebase_scanner._is_configuration_file("regular_file.py") is False

    def test_should_ignore_file(self, codebase_scanner):
        """Test file ignore logic"""
        assert codebase_scanner._should_ignore_file(".git/config") is True
        assert codebase_scanner._should_ignore_file("node_modules/package.json") is True
        assert codebase_scanner._should_ignore_file("__pycache__/cache.pyc") is True
        assert codebase_scanner._should_ignore_file(".DS_Store") is True
        assert codebase_scanner._should_ignore_file("src/main.py") is False

    @pytest.mark.asyncio
    async def test_analyze_repository_invalid_path(self, codebase_scanner):
        """Test repository analysis with invalid path"""
        with pytest.raises(BaseSystemError, match="Repository path does not exist"):
            await codebase_scanner.analyze_repository("/invalid/path")

    @pytest.mark.asyncio
    async def test_performance_with_large_repository(self, codebase_scanner):
        """Test performance with a large repository structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a larger repository structure
            for i in range(100):
                file_path = Path(temp_dir) / f"src/module_{i}.py"
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(f"# Module {i}\nclass Class{i}:\n    pass\n")

            import time

            start_time = time.time()

            analysis = await codebase_scanner.analyze_repository(temp_dir)

            end_time = time.time()
            execution_time = end_time - start_time

            # Should complete within reasonable time (5 seconds for 100 files)
            assert execution_time < 5.0
            assert isinstance(analysis, CodebaseAnalysis)


class TestCodebaseAnalysisModels:
    """Unit tests for CodebaseAnalysis data models"""

    def test_tech_stack_creation(self):
        """Test TechStack model creation"""
        tech_stack = TechStack(
            languages=["python", "javascript"],
            frameworks=["fastapi", "react"],
            libraries=["pydantic", "axios"],
        )

        assert tech_stack.languages == ["python", "javascript"]
        assert tech_stack.frameworks == ["fastapi", "react"]
        assert tech_stack.libraries == ["pydantic", "axios"]

    def test_architecture_pattern_creation(self):
        """Test ArchitecturePattern model creation"""
        pattern = ArchitecturePattern(
            name="microservice",
            confidence=0.8,
            characteristics=["api_endpoints", "containerized", "database"],
        )

        assert pattern.name == "microservice"
        assert pattern.confidence == 0.8
        assert "api_endpoints" in pattern.characteristics

    def test_code_pattern_creation(self):
        """Test CodePattern model creation"""
        pattern = CodePattern(
            type="class_definition",
            description="Standard class definition pattern",
            examples=["class User:", "class Product:"],
            file_paths=["src/models.py", "src/entities.py"],
        )

        assert pattern.type == "class_definition"
        assert pattern.description == "Standard class definition pattern"
        assert len(pattern.examples) == 2
        assert len(pattern.file_paths) == 2

    def test_dependency_info_creation(self):
        """Test DependencyInfo model creation"""
        dependency = DependencyInfo(
            name="fastapi", version="0.68.0", type="runtime", source="requirements.txt"
        )

        assert dependency.name == "fastapi"
        assert dependency.version == "0.68.0"
        assert dependency.type == "runtime"
        assert dependency.source == "requirements.txt"

    def test_test_framework_creation(self):
        """Test TestFrameworkInfo model creation"""
        test_framework = TestFrameworkInfo(
            frameworks=["pytest", "jest"],
            test_file_patterns=["test_*.py", "*.test.js"],
            coverage_tools=["coverage.py", "jest-coverage"],
        )

        assert "pytest" in test_framework.frameworks
        assert "jest" in test_framework.frameworks
        assert any("test_" in pattern for pattern in test_framework.test_file_patterns)

    def test_documentation_style_creation(self):
        """Test DocumentationStyle model creation"""
        doc_style = DocumentationStyle(
            format="markdown",
            structure={"readme_exists": True, "api_docs": True},
            coverage_score=0.75,
        )

        assert doc_style.format == "markdown"
        assert doc_style.structure["readme_exists"] is True
        assert doc_style.coverage_score == 0.75
