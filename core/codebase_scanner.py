"""
Codebase Scanner for repository analysis
Analyzes existing codebase to understand patterns, structure, and technologies
"""
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
import logging

from .exceptions import BaseSystemError

logger = logging.getLogger(__name__)


@dataclass
class TechStack:
    """Technology stack information"""

    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    libraries: List[str] = field(default_factory=list)


@dataclass
class ArchitecturePattern:
    """Architecture pattern information"""

    name: str
    confidence: float
    characteristics: List[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class CodePattern:
    """Code pattern information"""

    type: str
    description: str
    examples: List[str] = field(default_factory=list)
    file_paths: List[str] = field(default_factory=list)


@dataclass
class DependencyInfo:
    """Dependency information"""

    name: str
    version: Optional[str] = None
    type: str = "runtime"  # runtime, dev, peer
    source: Optional[str] = None  # requirements.txt, package.json, etc.


@dataclass
class TestFrameworkInfo:
    """Test framework information"""

    frameworks: List[str] = field(default_factory=list)
    test_file_patterns: List[str] = field(default_factory=list)
    coverage_tools: List[str] = field(default_factory=list)


@dataclass
class DocumentationStyle:
    """Documentation style information"""

    format: str = "none"  # markdown, rst, mixed, none
    structure: Dict[str, Any] = field(default_factory=dict)
    coverage_score: float = 0.0


@dataclass
class CodebaseAnalysis:
    """Complete codebase analysis result"""

    repository_path: str
    tech_stack: TechStack
    architecture_pattern: ArchitecturePattern
    code_style: Dict[str, Any]
    patterns: List[CodePattern]
    dependencies: List[DependencyInfo]
    test_framework: TestFrameworkInfo
    documentation_style: DocumentationStyle
    directory_structure: Optional[Dict[str, Any]] = None
    configuration_files: Optional[List[Dict[str, Any]]] = None


class CodebaseScanner:
    """Analyzes existing codebase to understand patterns and structure"""

    # File type mappings
    FILE_TYPE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".kt": "kotlin",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".dart": "dart",
        ".scala": "scala",
    }

    # Configuration files
    CONFIG_FILES = {
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "requirements.txt",
        "requirements-dev.txt",
        "Pipfile",
        "poetry.lock",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".gitignore",
        ".dockerignore",
        "Makefile",
        "CMakeLists.txt",
        "pom.xml",
        "build.gradle",
        "gradle.properties",
        "Cargo.toml",
        "go.mod",
        "composer.json",
        "Gemfile",
        "tsconfig.json",
        "webpack.config.js",
        "jest.config.js",
        ".eslintrc",
        ".prettierrc",
        ".babelrc",
    }

    # Directories to ignore
    IGNORE_DIRS = {
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "venv",
        "env",
        ".venv",
        ".env",
        "build",
        "dist",
        "target",
        "out",
        ".DS_Store",
        ".idea",
        ".vscode",
        "coverage",
        ".coverage",
        ".nyc_output",
    }

    def __init__(self):
        """Initialize CodebaseScanner"""
        pass

    async def analyze_repository(self, repository_path: str) -> CodebaseAnalysis:
        """Analyze complete repository and return comprehensive analysis"""
        repo_path = Path(repository_path)

        if not repo_path.exists():
            raise BaseSystemError(f"Repository path does not exist: {repository_path}")

        if not repo_path.is_dir():
            raise BaseSystemError(
                f"Repository path is not a directory: {repository_path}"
            )

        # Run all analysis tasks concurrently
        tech_stack_task = self.detect_tech_stack(repository_path)
        architecture_task = self.identify_architecture(repository_path)
        code_style_task = self.analyze_code_style(repository_path)
        patterns_task = self.extract_patterns(repository_path)
        dependencies_task = self.list_dependencies(repository_path)
        test_framework_task = self.detect_test_framework(repository_path)
        docs_task = self.analyze_docs(repository_path)
        structure_task = self.scan_directory_structure(repository_path)
        config_task = self.identify_configuration_files(repository_path)

        # Wait for all tasks to complete
        results = await asyncio.gather(
            tech_stack_task,
            architecture_task,
            code_style_task,
            patterns_task,
            dependencies_task,
            test_framework_task,
            docs_task,
            structure_task,
            config_task,
            return_exceptions=True,
        )

        # Extract results or provide defaults for failed tasks
        tech_stack = (
            results[0] if not isinstance(results[0], Exception) else TechStack()
        )
        architecture = (
            results[1]
            if not isinstance(results[1], Exception)
            else ArchitecturePattern("unknown", 0.0)
        )
        code_style = results[2] if not isinstance(results[2], Exception) else {}
        patterns = results[3] if not isinstance(results[3], Exception) else []
        dependencies = results[4] if not isinstance(results[4], Exception) else []
        test_framework = (
            results[5] if not isinstance(results[5], Exception) else TestFrameworkInfo()
        )
        docs = (
            results[6]
            if not isinstance(results[6], Exception)
            else DocumentationStyle()
        )
        structure = results[7] if not isinstance(results[7], Exception) else {}
        config_files = results[8] if not isinstance(results[8], Exception) else []

        return CodebaseAnalysis(
            repository_path=repository_path,
            tech_stack=tech_stack,
            architecture_pattern=architecture,
            code_style=code_style,
            patterns=patterns,
            dependencies=dependencies,
            test_framework=test_framework,
            documentation_style=docs,
            directory_structure=structure,
            configuration_files=config_files,
        )

    async def detect_tech_stack(self, repository_path: str) -> TechStack:
        """Detect technologies used in the repository"""
        languages = set()
        frameworks = set()
        libraries = set()

        repo_path = Path(repository_path)

        # Analyze files to detect languages
        for file_path in repo_path.rglob("*"):
            if self._should_ignore_file(str(file_path.relative_to(repo_path))):
                continue

            if file_path.is_file():
                file_type = self._get_file_type(file_path.name)
                if file_type != "unknown":
                    languages.add(file_type)

        # Analyze configuration files for frameworks and libraries
        await self._analyze_package_json(repo_path, frameworks, libraries)
        await self._analyze_requirements_txt(repo_path, frameworks, libraries)
        await self._analyze_pyproject_toml(repo_path, frameworks, libraries)

        return TechStack(
            languages=sorted(list(languages)),
            frameworks=sorted(list(frameworks)),
            libraries=sorted(list(libraries)),
        )

    async def identify_architecture(self, repository_path: str) -> ArchitecturePattern:
        """Identify the architecture pattern used"""
        repo_path = Path(repository_path)
        characteristics = []
        confidence = 0.0
        pattern_name = "unknown"

        # Check for common architectural indicators
        has_docker = (repo_path / "Dockerfile").exists()
        has_compose = any(
            (repo_path / name).exists()
            for name in ["docker-compose.yml", "docker-compose.yaml"]
        )
        has_api = await self._has_api_endpoints(repo_path)
        has_database = await self._has_database_config(repo_path)
        has_microservice_structure = await self._has_microservice_structure(repo_path)

        if has_docker:
            characteristics.append("containerized")
        if has_compose:
            characteristics.append("multi_service")
        if has_api:
            characteristics.append("api_endpoints")
        if has_database:
            characteristics.append("database")

        # Determine architecture pattern
        if has_microservice_structure and has_docker:
            pattern_name = "microservice"
            confidence = 0.8
        elif has_api and has_database:
            pattern_name = "monolith"
            confidence = 0.7
        elif has_api:
            pattern_name = "mvc"
            confidence = 0.6
        else:
            pattern_name = "layered"
            confidence = 0.4

        return ArchitecturePattern(
            name=pattern_name, confidence=confidence, characteristics=characteristics
        )

    async def analyze_code_style(self, repository_path: str) -> Dict[str, Any]:
        """Analyze code style and conventions"""
        style_analysis = {
            "indentation": "spaces",  # Default assumption
            "naming_convention": "snake_case",  # Default for Python
            "import_style": "standard",
        }

        repo_path = Path(repository_path)

        # Analyze Python files for style
        python_files = list(repo_path.rglob("*.py"))
        if python_files:
            await self._analyze_python_style(python_files, style_analysis)

        # Analyze JavaScript/TypeScript files for style
        js_files = list(repo_path.rglob("*.js")) + list(repo_path.rglob("*.ts"))
        if js_files:
            await self._analyze_javascript_style(js_files, style_analysis)

        return style_analysis

    async def extract_patterns(self, repository_path: str) -> List[CodePattern]:
        """Extract common code patterns from the repository"""
        patterns = []
        repo_path = Path(repository_path)

        # Extract Python patterns
        python_files = list(repo_path.rglob("*.py"))
        if python_files:
            python_patterns = await self._extract_python_patterns(python_files)
            patterns.extend(python_patterns)

        # Extract JavaScript/TypeScript patterns
        js_files = list(repo_path.rglob("*.js")) + list(repo_path.rglob("*.ts"))
        if js_files:
            js_patterns = await self._extract_javascript_patterns(js_files)
            patterns.extend(js_patterns)

        return patterns

    async def list_dependencies(self, repository_path: str) -> List[DependencyInfo]:
        """Extract dependency information from configuration files"""
        dependencies = []
        repo_path = Path(repository_path)

        # Parse package.json
        package_json = repo_path / "package.json"
        if package_json.exists():
            deps = await self._parse_package_json_deps(package_json)
            dependencies.extend(deps)

        # Parse requirements.txt
        requirements_txt = repo_path / "requirements.txt"
        if requirements_txt.exists():
            deps = await self._parse_requirements_txt(requirements_txt)
            dependencies.extend(deps)

        # Parse pyproject.toml
        pyproject_toml = repo_path / "pyproject.toml"
        if pyproject_toml.exists():
            deps = await self._parse_pyproject_toml_deps(pyproject_toml)
            dependencies.extend(deps)

        return dependencies

    async def detect_test_framework(self, repository_path: str) -> TestFrameworkInfo:
        """Detect testing frameworks and patterns"""
        frameworks = set()
        test_patterns = set()
        coverage_tools = set()

        repo_path = Path(repository_path)

        # Check for test files and patterns
        test_files = []
        for pattern in [
            "test_*.py",
            "*_test.py",
            "*.test.js",
            "*.test.ts",
            "*.spec.js",
            "*.spec.ts",
        ]:
            test_files.extend(repo_path.rglob(pattern))

        if test_files:
            # Analyze test files for frameworks
            for test_file in test_files:
                try:
                    content = test_file.read_text(encoding="utf-8", errors="ignore")

                    # Detect Python test frameworks
                    if "pytest" in content or "import pytest" in content:
                        frameworks.add("pytest")
                        test_patterns.add("test_*.py")
                    if "unittest" in content or "import unittest" in content:
                        frameworks.add("unittest")
                        test_patterns.add("test_*.py")

                    # Detect JavaScript test frameworks
                    if "jest" in content or "from 'jest'" in content:
                        frameworks.add("jest")
                        test_patterns.add("*.test.js")
                    if "mocha" in content or "describe(" in content:
                        frameworks.add("mocha")
                        test_patterns.add("*.spec.js")

                except Exception:
                    continue

        # Check for coverage tools
        if (repo_path / ".coverage").exists():
            coverage_tools.add("coverage.py")
        if (repo_path / "coverage").exists():
            coverage_tools.add("jest-coverage")

        return TestFrameworkInfo(
            frameworks=sorted(list(frameworks)),
            test_file_patterns=sorted(list(test_patterns)),
            coverage_tools=sorted(list(coverage_tools)),
        )

    async def analyze_docs(self, repository_path: str) -> DocumentationStyle:
        """Analyze documentation style and coverage"""
        repo_path = Path(repository_path)
        doc_format = "none"
        structure = {
            "readme_exists": False,
            "api_docs": False,
            "changelog": False,
            "license": False,
        }

        # Check for README files
        readme_files = list(repo_path.glob("README*"))
        if readme_files:
            structure["readme_exists"] = True
            readme_file = readme_files[0]
            if readme_file.suffix.lower() in [".md", ".markdown"]:
                doc_format = "markdown"
            elif readme_file.suffix.lower() in [".rst", ".txt"]:
                doc_format = "rst" if readme_file.suffix.lower() == ".rst" else "text"

        # Check for documentation directories
        docs_dirs = ["docs", "doc", "documentation"]
        for docs_dir in docs_dirs:
            docs_path = repo_path / docs_dir
            if docs_path.exists() and docs_path.is_dir():
                structure["api_docs"] = True
                # Check format of docs
                md_files = list(docs_path.rglob("*.md"))
                rst_files = list(docs_path.rglob("*.rst"))
                if md_files and rst_files:
                    doc_format = "mixed"
                elif md_files:
                    doc_format = "markdown" if doc_format == "none" else doc_format
                elif rst_files:
                    doc_format = "rst" if doc_format == "none" else doc_format
                break

        # Check for other documentation files
        if any(
            (repo_path / name).exists()
            for name in ["CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG.txt"]
        ):
            structure["changelog"] = True
        if any(
            (repo_path / name).exists()
            for name in ["LICENSE", "LICENSE.md", "LICENSE.txt"]
        ):
            structure["license"] = True

        # Calculate coverage score
        coverage_score = sum(structure.values()) / len(structure)

        return DocumentationStyle(
            format=doc_format, structure=structure, coverage_score=coverage_score
        )

    async def scan_directory_structure(self, repository_path: str) -> Dict[str, Any]:
        """Scan and analyze directory structure"""
        repo_path = Path(repository_path)

        total_files = 0
        directories = []
        file_types = {}

        for item in repo_path.rglob("*"):
            if self._should_ignore_file(str(item.relative_to(repo_path))):
                continue

            if item.is_file():
                total_files += 1
                file_type = self._get_file_type(item.name)
                file_types[file_type] = file_types.get(file_type, 0) + 1
            elif item.is_dir():
                directories.append(str(item.relative_to(repo_path)))

        return {
            "total_files": total_files,
            "directories": sorted(directories),
            "file_types": file_types,
        }

    async def identify_configuration_files(
        self, repository_path: str
    ) -> List[Dict[str, Any]]:
        """Identify configuration files in the repository"""
        repo_path = Path(repository_path)
        config_files = []

        for file_path in repo_path.rglob("*"):
            if file_path.is_file() and self._is_configuration_file(file_path.name):
                config_files.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path.relative_to(repo_path)),
                        "type": self._get_config_file_type(file_path.name),
                    }
                )

        return sorted(config_files, key=lambda x: x["name"])

    async def analyze_imports_and_usage(self, repository_path: str) -> Dict[str, Any]:
        """Analyze import patterns and library usage"""
        analysis = {}
        repo_path = Path(repository_path)

        # Analyze Python imports
        python_files = list(repo_path.rglob("*.py"))
        if python_files:
            analysis["python"] = await self._analyze_python_imports(python_files)

        # Analyze JavaScript imports
        js_files = list(repo_path.rglob("*.js")) + list(repo_path.rglob("*.ts"))
        if js_files:
            analysis["javascript"] = await self._analyze_javascript_imports(js_files)

        return analysis

    def _get_file_type(self, filename: str) -> str:
        """Get file type based on extension"""
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        return self.FILE_TYPE_EXTENSIONS.get(extension, "unknown")

    def _is_configuration_file(self, filename: str) -> bool:
        """Check if file is a configuration file"""
        return (
            filename in self.CONFIG_FILES
            or filename.startswith(".")
            and len(filename) > 1
        )

    def _should_ignore_file(self, file_path: str) -> bool:
        """Check if file/directory should be ignored"""
        path_parts = Path(file_path).parts
        return any(part in self.IGNORE_DIRS for part in path_parts)

    def _get_config_file_type(self, filename: str) -> str:
        """Get configuration file type"""
        if filename in ["package.json", "package-lock.json", "yarn.lock"]:
            return "node"
        elif filename in ["requirements.txt", "pyproject.toml", "setup.py"]:
            return "python"
        elif filename.startswith("Dockerfile") or "docker-compose" in filename:
            return "docker"
        elif filename in [".gitignore", ".dockerignore"]:
            return "ignore"
        else:
            return "other"

    # Helper methods for specific analysis tasks

    async def _analyze_package_json(
        self, repo_path: Path, frameworks: set, libraries: set
    ):
        """Analyze package.json for Node.js dependencies"""
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                content = json.loads(package_json.read_text())

                # Analyze dependencies
                all_deps = {}
                all_deps.update(content.get("dependencies", {}))
                all_deps.update(content.get("devDependencies", {}))

                for dep_name in all_deps.keys():
                    if dep_name in ["react", "vue", "angular", "svelte"]:
                        frameworks.add(dep_name)
                    elif dep_name in ["express", "fastify", "koa", "next", "nuxt"]:
                        frameworks.add(dep_name)
                    else:
                        libraries.add(dep_name)

            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")

    async def _analyze_requirements_txt(
        self, repo_path: Path, frameworks: set, libraries: set
    ):
        """Analyze requirements.txt for Python dependencies"""
        req_files = ["requirements.txt", "requirements-dev.txt"]

        for req_file in req_files:
            req_path = repo_path / req_file
            if req_path.exists():
                try:
                    content = req_path.read_text()
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Extract package name
                            pkg_name = re.split(r"[>=<!\s]", line)[0]
                            if pkg_name in ["django", "flask", "fastapi", "tornado"]:
                                frameworks.add(pkg_name)
                            elif pkg_name in ["pytest", "unittest2"]:
                                frameworks.add(pkg_name)
                            else:
                                libraries.add(pkg_name)
                except Exception as e:
                    logger.warning(f"Failed to parse {req_file}: {e}")

    async def _analyze_pyproject_toml(
        self, repo_path: Path, frameworks: set, libraries: set
    ):
        """Analyze pyproject.toml for Python dependencies"""
        pyproject_path = repo_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                # Simple regex-based parsing (could use toml library for more robust parsing)
                content = pyproject_path.read_text()

                # Find dependencies section
                deps_match = re.search(
                    r"\[tool\.poetry\.dependencies\](.*?)(?=\[|$)", content, re.DOTALL
                )
                if deps_match:
                    deps_section = deps_match.group(1)
                    for line in deps_section.split("\n"):
                        line = line.strip()
                        if "=" in line:
                            pkg_name = line.split("=")[0].strip().strip('"')
                            if pkg_name in ["django", "flask", "fastapi"]:
                                frameworks.add(pkg_name)
                            else:
                                libraries.add(pkg_name)

            except Exception as e:
                logger.warning(f"Failed to parse pyproject.toml: {e}")

    async def _has_api_endpoints(self, repo_path: Path) -> bool:
        """Check if repository has API endpoints"""
        # Look for common API patterns in Python and JavaScript files
        api_patterns = [
            r"@app\.(get|post|put|delete)",  # Flask/FastAPI
            r"\.route\(",  # Flask
            r"app\.(get|post|put|delete)\(",  # Express.js
            r"@RestController",  # Spring Boot
            r"@RequestMapping",  # Spring Boot
        ]

        files_to_check = list(repo_path.rglob("*.py")) + list(repo_path.rglob("*.js"))

        for file_path in files_to_check[:50]:  # Limit to first 50 files for performance
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for pattern in api_patterns:
                    if re.search(pattern, content):
                        return True
            except Exception:
                continue

        return False

    async def _has_database_config(self, repo_path: Path) -> bool:
        """Check if repository has database configuration"""
        db_indicators = [
            "DATABASE_URL",
            "DB_HOST",
            "MONGO_URI",
            "REDIS_URL",
            "database.yml",
            "db.properties",
            "hibernate.cfg.xml",
        ]

        # Check configuration files
        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    for indicator in db_indicators:
                        if indicator in content:
                            return True
                except Exception:
                    continue

        return False

    async def _has_microservice_structure(self, repo_path: Path) -> bool:
        """Check for microservice architecture indicators"""
        microservice_indicators = [
            (repo_path / "services").is_dir(),
            (repo_path / "microservices").is_dir(),
            len(list(repo_path.glob("*/Dockerfile"))) > 1,
            (repo_path / "kubernetes").is_dir(),
            (repo_path / "k8s").is_dir(),
        ]

        return any(microservice_indicators)

    async def _analyze_python_style(
        self, python_files: List[Path], style_analysis: Dict[str, Any]
    ):
        """Analyze Python code style"""
        # Sample a few files to determine style
        sample_files = python_files[: min(5, len(python_files))]

        for file_path in sample_files:
            try:
                content = file_path.read_text(encoding="utf-8")

                # Check indentation
                lines = content.split("\n")
                indented_lines = [
                    line for line in lines if line.startswith((" ", "\t"))
                ]
                if indented_lines:
                    first_indent = indented_lines[0]
                    if first_indent.startswith("\t"):
                        style_analysis["indentation"] = "tabs"
                    elif first_indent.startswith("    "):
                        style_analysis["indentation"] = "4_spaces"
                    elif first_indent.startswith("  "):
                        style_analysis["indentation"] = "2_spaces"

                # Check naming convention
                if re.search(r"def [a-z_]+\(", content):
                    style_analysis["naming_convention"] = "snake_case"
                elif re.search(r"def [a-zA-Z][a-zA-Z0-9]*\(", content):
                    style_analysis["naming_convention"] = "camelCase"

            except Exception:
                continue

    async def _analyze_javascript_style(
        self, js_files: List[Path], style_analysis: Dict[str, Any]
    ):
        """Analyze JavaScript/TypeScript code style"""
        # Sample a few files to determine style
        sample_files = js_files[: min(5, len(js_files))]

        for file_path in sample_files:
            try:
                content = file_path.read_text(encoding="utf-8")

                # Check naming convention
                if re.search(r"function [a-z][a-zA-Z0-9]*\(", content):
                    style_analysis["naming_convention"] = "camelCase"
                elif re.search(r"function [a-z_]+\(", content):
                    style_analysis["naming_convention"] = "snake_case"

            except Exception:
                continue

    async def _extract_python_patterns(
        self, python_files: List[Path]
    ) -> List[CodePattern]:
        """Extract Python code patterns"""
        patterns = []

        # Class definition pattern
        class_examples = []
        class_files = []

        for file_path in python_files[:10]:  # Sample first 10 files
            try:
                content = file_path.read_text(encoding="utf-8")
                class_matches = re.findall(r"class\s+(\w+).*?:", content)
                if class_matches:
                    class_examples.extend(class_matches[:2])  # Max 2 per file
                    class_files.append(str(file_path))
            except Exception:
                continue

        if class_examples:
            patterns.append(
                CodePattern(
                    type="class_definition",
                    description="Python class definitions",
                    examples=[f"class {name}:" for name in class_examples[:5]],
                    file_paths=class_files,
                )
            )

        return patterns

    async def _extract_javascript_patterns(
        self, js_files: List[Path]
    ) -> List[CodePattern]:
        """Extract JavaScript/TypeScript code patterns"""
        patterns = []

        # Function definition pattern
        function_examples = []
        function_files = []

        for file_path in js_files[:10]:  # Sample first 10 files
            try:
                content = file_path.read_text(encoding="utf-8")
                func_matches = re.findall(r"function\s+(\w+)\s*\(", content)
                if func_matches:
                    function_examples.extend(func_matches[:2])
                    function_files.append(str(file_path))
            except Exception:
                continue

        if function_examples:
            patterns.append(
                CodePattern(
                    type="function_definition",
                    description="JavaScript function definitions",
                    examples=[f"function {name}()" for name in function_examples[:5]],
                    file_paths=function_files,
                )
            )

        return patterns

    async def _parse_package_json_deps(
        self, package_json_path: Path
    ) -> List[DependencyInfo]:
        """Parse dependencies from package.json"""
        dependencies = []

        try:
            content = json.loads(package_json_path.read_text())

            # Regular dependencies
            for name, version in content.get("dependencies", {}).items():
                dependencies.append(
                    DependencyInfo(
                        name=name,
                        version=version,
                        type="runtime",
                        source="package.json",
                    )
                )

            # Dev dependencies
            for name, version in content.get("devDependencies", {}).items():
                dependencies.append(
                    DependencyInfo(
                        name=name, version=version, type="dev", source="package.json"
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")

        return dependencies

    async def _parse_requirements_txt(
        self, requirements_path: Path
    ) -> List[DependencyInfo]:
        """Parse dependencies from requirements.txt"""
        dependencies = []

        try:
            content = requirements_path.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Parse package==version or package>=version
                    match = re.match(r"([a-zA-Z0-9_-]+)([>=<!=]+)?(.*)", line)
                    if match:
                        name = match.group(1)
                        version = match.group(3) if match.group(2) else None
                        dependencies.append(
                            DependencyInfo(
                                name=name,
                                version=version,
                                type="runtime",
                                source="requirements.txt",
                            )
                        )
        except Exception as e:
            logger.warning(f"Failed to parse requirements.txt: {e}")

        return dependencies

    async def _parse_pyproject_toml_deps(
        self, pyproject_path: Path
    ) -> List[DependencyInfo]:
        """Parse dependencies from pyproject.toml"""
        dependencies = []

        try:
            content = pyproject_path.read_text()

            # Simple regex-based parsing for dependencies
            deps_match = re.search(
                r"\[tool\.poetry\.dependencies\](.*?)(?=\[|$)", content, re.DOTALL
            )
            if deps_match:
                deps_section = deps_match.group(1)
                for line in deps_section.split("\n"):
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        name = parts[0].strip().strip('"')
                        version = parts[1].strip().strip('"')
                        if name and name != "python":  # Skip python version requirement
                            dependencies.append(
                                DependencyInfo(
                                    name=name,
                                    version=version,
                                    type="runtime",
                                    source="pyproject.toml",
                                )
                            )
        except Exception as e:
            logger.warning(f"Failed to parse pyproject.toml: {e}")

        return dependencies

    async def _analyze_python_imports(self, python_files: List[Path]) -> Dict[str, Any]:
        """Analyze Python import patterns"""
        imports = {}
        common_patterns = []

        for file_path in python_files[:20]:  # Sample first 20 files
            try:
                content = file_path.read_text(encoding="utf-8")

                # Find import statements
                import_matches = re.findall(
                    r"^(import|from)\s+([a-zA-Z0-9_\.]+)", content, re.MULTILINE
                )
                for import_type, module in import_matches:
                    base_module = module.split(".")[0]
                    imports[base_module] = imports.get(base_module, 0) + 1
            except Exception:
                continue

        # Find most common imports
        if imports:
            sorted_imports = sorted(imports.items(), key=lambda x: x[1], reverse=True)
            common_patterns = [
                f"{module} (used {count} times)"
                for module, count in sorted_imports[:10]
            ]

        return {"imports": imports, "common_patterns": common_patterns}

    async def _analyze_javascript_imports(self, js_files: List[Path]) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript import patterns"""
        imports = {}
        common_patterns = []

        for file_path in js_files[:20]:  # Sample first 20 files
            try:
                content = file_path.read_text(encoding="utf-8")

                # Find import statements
                import_matches = re.findall(
                    r'import.*?from\s+[\'"]([^\'\"]+)[\'"]', content
                )
                for module in import_matches:
                    # Extract base module name
                    if module.startswith("./") or module.startswith("../"):
                        continue  # Skip relative imports
                    base_module = module.split("/")[0]
                    imports[base_module] = imports.get(base_module, 0) + 1
            except Exception:
                continue

        # Find most common imports
        if imports:
            sorted_imports = sorted(imports.items(), key=lambda x: x[1], reverse=True)
            common_patterns = [
                f"{module} (used {count} times)"
                for module, count in sorted_imports[:10]
            ]

        return {"imports": imports, "common_patterns": common_patterns}
