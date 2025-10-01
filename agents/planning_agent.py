"""
Planning Agent for the AI Development Automation System.

This module provides the PlanningAgent that analyzes development tasks
and creates comprehensive implementation plans using AI.
"""

import ast
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.ai_provider import AIProvider, PromptTemplate


class PlanningAgentError(Exception):
    """Base exception for planning agent errors."""

    pass


@dataclass
class TaskAnalysis:
    """Analysis result for a development task."""

    task_id: str
    complexity: str
    estimated_effort: Optional[str] = None
    technologies: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    analysis_cost: float = 0.0
    token_usage: Optional[Any] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskAnalysis":
        """Create TaskAnalysis from dictionary."""
        return cls(
            task_id=data.get("task_id", ""),
            complexity=data.get("complexity", "unknown"),
            estimated_effort=data.get("estimated_effort"),
            technologies=data.get("technologies", []),
            dependencies=data.get("dependencies", []),
            risks=data.get("risks", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert TaskAnalysis to dictionary."""
        return {
            "task_id": self.task_id,
            "complexity": self.complexity,
            "estimated_effort": self.estimated_effort,
            "technologies": self.technologies,
            "dependencies": self.dependencies,
            "risks": self.risks,
            "acceptance_criteria": self.acceptance_criteria,
        }


@dataclass
class PlanStep:
    """A single step in a development plan."""

    name: str
    description: str
    estimated_duration: str
    tasks: List[str]
    deliverables: List[str]
    dependencies: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStep":
        """Create PlanStep from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            estimated_duration=data.get("estimated_duration", ""),
            tasks=data.get("tasks", []),
            deliverables=data.get("deliverables", []),
            dependencies=data.get("dependencies", []),
            prerequisites=data.get("prerequisites", []),
        )


@dataclass
class TaskPlan:
    """Complete development plan for a task."""

    task_id: str
    steps: List[PlanStep]
    total_estimated_duration: str
    success_criteria: List[str]

    def __post_init__(self):
        """Validate the plan after initialization."""
        self._validate_dependencies()

    def _validate_dependencies(self):
        """Validate that all step dependencies exist."""
        step_names = {step.name for step in self.steps}

        for step in self.steps:
            for dep in step.dependencies:
                if dep not in step_names:
                    raise PlanningAgentError(
                        f"Dependency validation failed: Step '{step.name}' "
                        f"depends on '{dep}' which does not exist"
                    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskPlan":
        """Create TaskPlan from dictionary."""
        steps = [PlanStep.from_dict(step_data) for step_data in data.get("steps", [])]

        return cls(
            task_id=data.get("task_id", ""),
            steps=steps,
            total_estimated_duration=data.get("total_estimated_duration", ""),
            success_criteria=data.get("success_criteria", []),
        )


@dataclass
class AnalysisResult:
    """Complete analysis result containing both analysis and plan."""

    task_analysis: TaskAnalysis
    task_plan: TaskPlan
    confidence_score: float
    recommendations: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate the result after initialization."""
        if self.task_analysis.task_id != self.task_plan.task_id:
            raise PlanningAgentError("Task IDs must match between analysis and plan")


class PlanningAgent:
    """AI-powered planning agent for development tasks."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        if ai_provider is None:
            raise PlanningAgentError("ai_provider is required")

        self.ai_provider = ai_provider

        # Initialize prompt templates
        self.analysis_template = PromptTemplate(
            name="task_analysis",
            system_template=(
                "You are an expert software development analyst. "
                "Analyze development tasks and provide detailed technical "
                "assessments including complexity, effort, technologies, "
                "dependencies, risks, and acceptance criteria."
            ),
            template="""
            Analyze the following development task:

            Task ID: {{task.id | default('N/A')}}
            Title: {{task.title | default('N/A')}}
            Description: {{task.description | default('N/A')}}
            Type: {{task.type | default('N/A')}}
            Priority: {{task.priority | default('N/A')}}
            {% if context %}
            Additional Context:
            {% for key, value in context.items() %}
            - {{key}}: {{value}}
            {% endfor %}
            {% endif %}

            Please provide a detailed analysis in the following format:
            {
                "complexity": "low|medium|high",
                "estimated_effort": "time estimate",
                "technologies": ["list", "of", "technologies"],
                "dependencies": ["list", "of", "dependencies"],
                "risks": ["list", "of", "risks"],
                "acceptance_criteria": ["list", "of", "criteria"]
            }

            Focus on technical accuracy and completeness.
            """,
        )

        self.planning_template = PromptTemplate(
            name="task_planning",
            system_template=(
                "You are an expert software development project planner. "
                "Create detailed, realistic development plans based on "
                "task analysis. Break down work into logical phases with "
                "clear deliverables and dependencies."
            ),
            template="""
            Create a detailed development plan based on this analysis:

            Task ID: {{analysis.task_id | default('N/A')}}
            Complexity: {{analysis.complexity | default('N/A')}}
            Estimated Effort: {{analysis.estimated_effort | default('N/A')}}
            Technologies: {{(analysis.technologies | default([])) | join(', ')}}
            Dependencies: {{(analysis.dependencies | default([])) | join(', ')}}
            Risks: {{(analysis.risks | default([])) | join(', ')}}

            {% if constraints %}
            Planning Constraints:
            {% for key, value in constraints.items() %}
            - {{key}}: {{value}}
            {% endfor %}
            {% endif %}

            Please create a development plan in the following format:
            {
                "phases": [
                    {
                        "name": "phase name",
                        "description": "phase description",
                        "estimated_duration": "time estimate",
                        "tasks": ["list", "of", "tasks"],
                        "deliverables": ["list", "of", "deliverables"],
                        "dependencies": ["list", "of", "phase", "dependencies"]
                    }
                ],
                "total_estimated_duration": "total time",
                "success_criteria": ["list", "of", "success", "criteria"]
            }

            Ensure phases are logical, dependencies are correct, and
            estimates are realistic.
            """,
        )

    async def analyze_task(
        self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> TaskAnalysis:
        """Analyze a development task and return detailed analysis."""
        try:
            # Render the analysis prompt
            prompt_context = {"task": task, "context": context}

            system_prompt = self.analysis_template.render_system(prompt_context)
            user_prompt = self.analysis_template.render(prompt_context)

            # Generate analysis using AI
            result = await self.ai_provider.generate_text(
                prompt=user_prompt, system_prompt=system_prompt
            )

            if not result.success:
                raise PlanningAgentError(
                    f"Failed to analyze task: {result.error_message}"
                )

            # Parse the AI response
            analysis_data = self._parse_ai_response(result.content)
            analysis_data["task_id"] = task.get("id", "")

            # Create TaskAnalysis object with cost tracking
            analysis = TaskAnalysis.from_dict(analysis_data)
            analysis.analysis_cost = result.cost
            analysis.token_usage = result.token_usage

            return analysis

        except Exception as e:
            if isinstance(e, PlanningAgentError):
                raise
            raise PlanningAgentError(f"Task analysis failed: {str(e)}")

    async def create_plan(
        self,
        analysis: TaskAnalysis,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> TaskPlan:
        """Create a development plan from task analysis."""
        try:
            # Render the planning prompt
            prompt_context = {"analysis": analysis, "constraints": constraints}

            system_prompt = self.planning_template.render_system(prompt_context)
            user_prompt = self.planning_template.render(prompt_context)

            # Generate plan using AI
            result = await self.ai_provider.generate_text(
                prompt=user_prompt, system_prompt=system_prompt
            )

            if not result.success:
                raise PlanningAgentError(
                    f"Failed to create plan: {result.error_message}"
                )

            # Parse the AI response
            plan_data = self._parse_ai_response(result.content)
            plan_data["task_id"] = analysis.task_id

            return TaskPlan.from_dict(plan_data)

        except Exception as e:
            if isinstance(e, PlanningAgentError):
                raise
            raise PlanningAgentError(f"Plan creation failed: {str(e)}")

    async def analyze_and_plan(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """Complete workflow: analyze task and create plan."""
        analysis = await self.analyze_task(task, context)
        plan = await self.create_plan(analysis, constraints)

        # Calculate confidence score based on analysis completeness
        confidence = self._calculate_confidence(analysis, plan)

        # Generate recommendations
        recommendations = self._generate_recommendations(analysis, plan)

        return AnalysisResult(
            task_analysis=analysis,
            task_plan=plan,
            confidence_score=confidence,
            recommendations=recommendations,
        )

    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        """Parse AI response content into structured data."""
        try:
            # Try parsing as JSON first
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Try parsing as Python literal
                try:
                    data = ast.literal_eval(content)
                except (ValueError, SyntaxError):
                    # If all else fails, raise an error
                    raise PlanningAgentError(
                        f"Could not parse AI response as valid data structure: {content[:200]}..."
                    )

            # Convert "phases" to "steps" if needed for compatibility
            if "phases" in data and "steps" not in data:
                data["steps"] = data.pop("phases")

            return data

        except Exception as e:
            if isinstance(e, PlanningAgentError):
                raise
            raise PlanningAgentError(f"Failed to parse AI response: {str(e)}")

    def _calculate_confidence(self, analysis: TaskAnalysis, plan: TaskPlan) -> float:
        """Calculate confidence score based on analysis and plan quality."""
        score = 0.0

        # Analysis completeness factors
        if analysis.complexity:
            score += 0.2
        if analysis.estimated_effort:
            score += 0.15
        if analysis.technologies:
            score += 0.15
        if analysis.acceptance_criteria:
            score += 0.15

        # Plan completeness factors
        if plan.steps:
            score += 0.2
        if plan.total_estimated_duration:
            score += 0.1
        if plan.success_criteria:
            score += 0.05

        return min(score, 1.0)

    def _generate_recommendations(
        self, analysis: TaskAnalysis, plan: TaskPlan
    ) -> List[str]:
        """Generate recommendations based on analysis and plan."""
        recommendations = []

        # Risk-based recommendations
        if "security" in str(analysis.risks).lower():
            recommendations.append("Conduct security review")

        if "performance" in str(analysis.risks).lower():
            recommendations.append("Include performance testing")

        # Complexity-based recommendations
        if analysis.complexity == "high":
            recommendations.append("Consider breaking into smaller tasks")
            recommendations.append("Plan for additional code reviews")

        # Plan-based recommendations
        if len(plan.steps) > 5:
            recommendations.append("Consider parallel execution of independent phases")

        if not any("test" in step.name.lower() for step in plan.steps):
            recommendations.append("Add dedicated testing phase")

        return recommendations
