"""
Test suite for the PlanningAgent.

This test suite follows TDD methodology to implement the PlanningAgent
that analyzes tasks and creates comprehensive development plans.
"""

from unittest.mock import AsyncMock, Mock

import pytest

# Import the classes we're going to implement
from agents.planning_agent import (
    AnalysisResult,
    PlanningAgent,
    PlanningAgentError,
    PlanStep,
    TaskAnalysis,
    TaskPlan,
)


class TestPlanningAgent:
    """Unit tests for PlanningAgent core functionality"""

    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.mock_ai_provider = AsyncMock()
        self.agent = PlanningAgent(ai_provider=self.mock_ai_provider)

        # Sample task data for testing
        self.sample_task = {
            "id": "TEST-123",
            "title": "Implement user authentication system",
            "description": "Add JWT-based authentication with login/logout",
            "type": "feature",
            "priority": "high",
            "repository_url": "https://github.com/company/app.git",
            "labels": ["backend", "security"],
            "estimated_effort": "5 days",
        }

    def test_planning_agent_initialization(self):
        """Test that PlanningAgent can be initialized properly"""
        # RED: This will fail since PlanningAgent doesn't exist yet
        agent = PlanningAgent(ai_provider=self.mock_ai_provider)

        assert agent is not None
        assert agent.ai_provider is not None
        assert hasattr(agent, "analyze_task")
        assert hasattr(agent, "create_plan")

    def test_planning_agent_requires_ai_provider(self):
        """Test that PlanningAgent requires an AI provider"""
        # RED: This will fail since validation doesn't exist yet
        with pytest.raises(PlanningAgentError) as exc_info:
            PlanningAgent(ai_provider=None)

        assert "ai_provider is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_task_basic(self):
        """Test basic task analysis functionality"""
        # RED: This will fail since analyze_task doesn't exist yet
        # Mock AI provider response
        mock_analysis = {
            "complexity": "medium",
            "estimated_effort": "3-5 days",
            "technologies": ["Python", "FastAPI", "JWT"],
            "dependencies": ["user-management", "database-schema"],
            "risks": ["Security implementation complexity"],
            "acceptance_criteria": [
                "User can login with valid credentials",
                "JWT tokens are properly generated and validated",
                "Logout invalidates tokens",
            ],
        }

        self.mock_ai_provider.generate_text.return_value = Mock(
            success=True, content=str(mock_analysis)
        )

        result = await self.agent.analyze_task(self.sample_task)

        assert isinstance(result, TaskAnalysis)
        assert result.task_id == "TEST-123"
        assert result.complexity == "medium"
        assert "Python" in result.technologies
        assert len(result.acceptance_criteria) == 3

    @pytest.mark.asyncio
    async def test_analyze_task_with_context(self):
        """Test task analysis with additional context"""
        # RED: This will fail since context handling doesn't exist yet
        context = {
            "existing_auth": False,
            "database_type": "PostgreSQL",
            "framework": "FastAPI",
            "team_expertise": ["Python", "REST APIs"],
        }

        mock_analysis = {
            "complexity": "high",
            "estimated_effort": "7-10 days",
            "technologies": ["Python", "FastAPI", "JWT", "PostgreSQL"],
        }

        self.mock_ai_provider.generate_text.return_value = Mock(
            success=True, content=str(mock_analysis)
        )

        result = await self.agent.analyze_task(self.sample_task, context)

        assert result.complexity == "high"
        assert "PostgreSQL" in result.technologies
        # Verify that context was used in the analysis
        call_args = self.mock_ai_provider.generate_text.call_args
        # Check keyword arguments since that's how we're calling it
        if call_args[1].get("prompt"):
            prompt = call_args[1]["prompt"]  # Keyword argument
        else:
            prompt = call_args[0][0] if call_args[0] else ""  # Fallback to positional
        assert "PostgreSQL" in prompt
        assert "FastAPI" in prompt

    @pytest.mark.asyncio
    async def test_analyze_task_ai_error_handling(self):
        """Test error handling when AI provider fails"""
        # RED: This will fail since error handling doesn't exist yet
        self.mock_ai_provider.generate_text.return_value = Mock(
            success=False, error_message="API rate limit exceeded"
        )

        with pytest.raises(PlanningAgentError) as exc_info:
            await self.agent.analyze_task(self.sample_task)

        assert "Failed to analyze task" in str(exc_info.value)
        assert "API rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_plan_from_analysis(self):
        """Test creating a development plan from task analysis"""
        # RED: This will fail since create_plan doesn't exist yet
        analysis = TaskAnalysis(
            task_id="TEST-123",
            complexity="medium",
            estimated_effort="3-5 days",
            technologies=["Python", "FastAPI", "JWT"],
            dependencies=["user-management"],
            risks=["Security implementation"],
            acceptance_criteria=["User can login"],
        )

        mock_plan = {
            "phases": [
                {
                    "name": "Setup and Research",
                    "description": "Research JWT libraries and setup",
                    "estimated_duration": "4 hours",
                    "tasks": [
                        "Research JWT libraries for Python",
                        "Setup development environment",
                    ],
                    "deliverables": ["Environment setup", "Library selection"],
                },
                {
                    "name": "Implementation",
                    "description": "Implement authentication endpoints",
                    "estimated_duration": "2 days",
                    "tasks": [
                        "Create login endpoint",
                        "Create logout endpoint",
                        "Add JWT token generation",
                    ],
                    "deliverables": [
                        "Login/logout endpoints",
                        "JWT token system",
                    ],
                },
            ],
            "total_estimated_duration": "3 days",
            "success_criteria": ["All tests pass", "Security review complete"],
        }

        self.mock_ai_provider.generate_text.return_value = Mock(
            success=True, content=str(mock_plan)
        )

        plan = await self.agent.create_plan(analysis)

        assert isinstance(plan, TaskPlan)
        assert plan.task_id == "TEST-123"
        assert len(plan.steps) == 2
        assert plan.total_estimated_duration == "3 days"
        assert plan.steps[0].name == "Setup and Research"

    @pytest.mark.asyncio
    async def test_create_plan_with_constraints(self):
        """Test creating a plan with specific constraints"""
        # RED: This will fail since constraints handling doesn't exist yet
        analysis = TaskAnalysis(
            task_id="TEST-123",
            complexity="high",
            estimated_effort="1 week",
            technologies=["Python", "FastAPI"],
        )

        constraints = {
            "max_duration": "5 days",
            "team_size": 2,
            "must_include_testing": True,
            "deployment_deadline": "2023-12-01",
        }

        mock_plan = {
            "phases": [
                {"name": "Phase 1", "estimated_duration": "2 days"},
                {"name": "Testing", "estimated_duration": "1 day"},
                {"name": "Deployment", "estimated_duration": "2 days"},
            ],
            "total_estimated_duration": "5 days",
        }

        self.mock_ai_provider.generate_text.return_value = Mock(
            success=True, content=str(mock_plan)
        )

        plan = await self.agent.create_plan(analysis, constraints)

        assert plan.total_estimated_duration == "5 days"
        # Verify constraints were considered
        call_args = self.mock_ai_provider.generate_text.call_args
        # Check keyword arguments since that's how we're calling it
        if call_args[1].get("prompt"):
            prompt = call_args[1]["prompt"]  # Keyword argument
        else:
            prompt = call_args[0][0] if call_args[0] else ""  # Fallback to positional
        assert "5 days" in prompt
        assert "testing" in prompt.lower()

    @pytest.mark.asyncio
    async def test_end_to_end_planning_workflow(self):
        """Test complete planning workflow from task to plan"""
        # RED: This will fail since full workflow doesn't exist yet
        # Mock analysis response
        mock_analysis_response = {
            "complexity": "medium",
            "estimated_effort": "4 days",
            "technologies": ["Python", "FastAPI"],
        }

        # Mock planning response
        mock_plan_response = {
            "phases": [
                {
                    "name": "Implementation",
                    "estimated_duration": "3 days",
                    "tasks": ["Implement feature"],
                }
            ],
            "total_estimated_duration": "4 days",
        }

        # Setup mock responses in order
        self.mock_ai_provider.generate_text.side_effect = [
            Mock(success=True, content=str(mock_analysis_response)),
            Mock(success=True, content=str(mock_plan_response)),
        ]

        # Run complete workflow
        analysis = await self.agent.analyze_task(self.sample_task)
        plan = await self.agent.create_plan(analysis)

        assert isinstance(analysis, TaskAnalysis)
        assert isinstance(plan, TaskPlan)
        assert analysis.task_id == plan.task_id
        assert plan.total_estimated_duration == "4 days"

        # Verify both AI calls were made
        assert self.mock_ai_provider.generate_text.call_count == 2


class TestTaskAnalysis:
    """Unit tests for TaskAnalysis data structure"""

    def test_task_analysis_creation(self):
        """Test TaskAnalysis object creation and properties"""
        # RED: This will fail since TaskAnalysis doesn't exist yet
        analysis = TaskAnalysis(
            task_id="TEST-123",
            complexity="high",
            estimated_effort="1 week",
            technologies=["Python", "React"],
            dependencies=["auth-service"],
            risks=["API changes", "Performance issues"],
            acceptance_criteria=[
                "Feature works correctly",
                "Performance tests pass",
            ],
        )

        assert analysis.task_id == "TEST-123"
        assert analysis.complexity == "high"
        assert analysis.estimated_effort == "1 week"
        assert len(analysis.technologies) == 2
        assert "Python" in analysis.technologies
        assert len(analysis.risks) == 2
        assert len(analysis.acceptance_criteria) == 2

    def test_task_analysis_from_dict(self):
        """Test creating TaskAnalysis from dictionary"""
        # RED: This will fail since from_dict doesn't exist yet
        data = {
            "task_id": "TEST-456",
            "complexity": "low",
            "estimated_effort": "2 days",
            "technologies": ["JavaScript"],
            "dependencies": [],
            "risks": ["Browser compatibility"],
            "acceptance_criteria": ["UI works in Chrome"],
        }

        analysis = TaskAnalysis.from_dict(data)

        assert analysis.task_id == "TEST-456"
        assert analysis.complexity == "low"
        assert len(analysis.technologies) == 1

    def test_task_analysis_to_dict(self):
        """Test converting TaskAnalysis to dictionary"""
        # RED: This will fail since to_dict doesn't exist yet
        analysis = TaskAnalysis(
            task_id="TEST-789",
            complexity="medium",
            estimated_effort="3 days",
            technologies=["Python"],
            dependencies=[],
            risks=[],
            acceptance_criteria=["Works correctly"],
        )

        data = analysis.to_dict()

        assert isinstance(data, dict)
        assert data["task_id"] == "TEST-789"
        assert data["complexity"] == "medium"
        assert "technologies" in data
        assert isinstance(data["technologies"], list)


class TestTaskPlan:
    """Unit tests for TaskPlan data structure"""

    def test_task_plan_creation(self):
        """Test TaskPlan object creation"""
        # RED: This will fail since TaskPlan doesn't exist yet
        steps = [
            PlanStep(
                name="Design Phase",
                description="Create system design",
                estimated_duration="1 day",
                tasks=["Create architecture diagram", "Design API"],
                deliverables=["Architecture document"],
                dependencies=[],
            ),
            PlanStep(
                name="Implementation",
                description="Implement the feature",
                estimated_duration="3 days",
                tasks=["Code backend", "Code frontend"],
                deliverables=["Working feature"],
                dependencies=["Design Phase"],
            ),
        ]

        plan = TaskPlan(
            task_id="TEST-123",
            steps=steps,
            total_estimated_duration="4 days",
            success_criteria=["All tests pass"],
        )

        assert plan.task_id == "TEST-123"
        assert len(plan.steps) == 2
        assert plan.total_estimated_duration == "4 days"
        assert plan.steps[0].name == "Design Phase"
        assert plan.steps[1].dependencies == ["Design Phase"]

    def test_plan_step_creation(self):
        """Test PlanStep object creation"""
        # RED: This will fail since PlanStep doesn't exist yet
        step = PlanStep(
            name="Testing Phase",
            description="Comprehensive testing",
            estimated_duration="2 days",
            tasks=["Unit tests", "Integration tests", "E2E tests"],
            deliverables=["Test suite", "Test reports"],
            dependencies=["Implementation"],
            prerequisites=["Code complete"],
        )

        assert step.name == "Testing Phase"
        assert step.description == "Comprehensive testing"
        assert step.estimated_duration == "2 days"
        assert len(step.tasks) == 3
        assert len(step.deliverables) == 2
        assert step.dependencies == ["Implementation"]
        assert step.prerequisites == ["Code complete"]

    def test_task_plan_from_dict(self):
        """Test creating TaskPlan from dictionary"""
        # RED: This will fail since from_dict doesn't exist yet
        data = {
            "task_id": "TEST-456",
            "steps": [
                {
                    "name": "Phase 1",
                    "description": "First phase",
                    "estimated_duration": "1 day",
                    "tasks": ["Task 1"],
                    "deliverables": ["Deliverable 1"],
                    "dependencies": [],
                }
            ],
            "total_estimated_duration": "1 day",
            "success_criteria": ["Criteria 1"],
        }

        plan = TaskPlan.from_dict(data)

        assert plan.task_id == "TEST-456"
        assert len(plan.steps) == 1
        assert plan.steps[0].name == "Phase 1"

    def test_task_plan_validate_dependencies(self):
        """Test validation of step dependencies"""
        # RED: This will fail since validation doesn't exist yet
        steps = [
            PlanStep(
                name="Step 2",
                description="Second step",
                estimated_duration="1 day",
                tasks=["Task 2"],
                deliverables=["Deliverable 2"],
                dependencies=["Step 1"],  # References Step 1 which doesn't exist
            )
        ]

        with pytest.raises(PlanningAgentError) as exc_info:
            TaskPlan(
                task_id="TEST-123",
                steps=steps,
                total_estimated_duration="1 day",
                success_criteria=["Success"],
            )

        assert "dependency validation failed" in str(exc_info.value).lower()


class TestAnalysisResult:
    """Unit tests for AnalysisResult data structure"""

    def test_analysis_result_creation(self):
        """Test AnalysisResult object creation"""
        # RED: This will fail since AnalysisResult doesn't exist yet
        analysis = TaskAnalysis(
            task_id="TEST-123",
            complexity="medium",
            estimated_effort="3 days",
            technologies=["Python"],
        )

        plan = TaskPlan(
            task_id="TEST-123",
            steps=[],
            total_estimated_duration="3 days",
            success_criteria=["Success"],
        )

        result = AnalysisResult(
            task_analysis=analysis,
            task_plan=plan,
            confidence_score=0.85,
            recommendations=["Use automated testing", "Code review"],
        )

        assert result.task_analysis == analysis
        assert result.task_plan == plan
        assert result.confidence_score == 0.85
        assert len(result.recommendations) == 2

    def test_analysis_result_validation(self):
        """Test AnalysisResult validation"""
        # RED: This will fail since validation doesn't exist yet
        analysis = TaskAnalysis(task_id="TEST-123", complexity="medium")
        plan = TaskPlan(
            task_id="TEST-456",
            steps=[],
            total_estimated_duration="1 day",
            success_criteria=[],
        )

        # Should fail because task IDs don't match
        with pytest.raises(PlanningAgentError) as exc_info:
            AnalysisResult(
                task_analysis=analysis,
                task_plan=plan,
                confidence_score=0.9,
            )

        assert "task ids must match" in str(exc_info.value).lower()


class TestPlanningAgentIntegration:
    """Integration tests for PlanningAgent"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_ai_provider = AsyncMock()
        self.agent = PlanningAgent(ai_provider=self.mock_ai_provider)

    @pytest.mark.asyncio
    async def test_complete_planning_workflow(self):
        """Test complete planning workflow with realistic data"""
        # RED: This will fail since complete workflow doesn't exist yet
        task = {
            "id": "PROJ-456",
            "title": "Add user profile management",
            "description": "Allow users to edit their profiles",
            "type": "feature",
            "priority": "medium",
        }

        # Mock realistic AI responses
        analysis_response = {
            "complexity": "medium",
            "estimated_effort": "5 days",
            "technologies": ["Python", "FastAPI", "PostgreSQL", "React"],
            "dependencies": ["user-authentication", "database-migrations"],
            "risks": [
                "Data validation complexity",
                "File upload security",
            ],
            "acceptance_criteria": [
                "Users can update their profile information",
                "Profile images can be uploaded and displayed",
                "Changes are validated and saved to database",
                "Users receive confirmation of successful updates",
            ],
        }

        plan_response = {
            "phases": [
                {
                    "name": "Backend API Development",
                    "description": "Create profile management endpoints",
                    "estimated_duration": "2 days",
                    "tasks": [
                        "Create profile update endpoint",
                        "Add file upload endpoint",
                        "Implement validation logic",
                        "Add database migrations",
                    ],
                    "deliverables": [
                        "Profile API endpoints",
                        "File upload system",
                        "Database schema updates",
                    ],
                    "dependencies": [],
                },
                {
                    "name": "Frontend Implementation",
                    "description": "Create user interface for profile editing",
                    "estimated_duration": "2 days",
                    "tasks": [
                        "Create profile edit form",
                        "Add image upload component",
                        "Implement form validation",
                        "Connect to backend API",
                    ],
                    "deliverables": [
                        "Profile edit UI",
                        "Image upload interface",
                        "Client-side validation",
                    ],
                    "dependencies": ["Backend API Development"],
                },
                {
                    "name": "Testing and Integration",
                    "description": "Test the complete feature",
                    "estimated_duration": "1 day",
                    "tasks": [
                        "Write unit tests",
                        "Create integration tests",
                        "Manual testing",
                        "Security testing",
                    ],
                    "deliverables": [
                        "Test suite",
                        "Security audit results",
                        "QA sign-off",
                    ],
                    "dependencies": ["Frontend Implementation"],
                },
            ],
            "total_estimated_duration": "5 days",
            "success_criteria": [
                "All automated tests pass",
                "Security review completed",
                "Feature works in all supported browsers",
                "Performance meets requirements",
            ],
        }

        self.mock_ai_provider.generate_text.side_effect = [
            Mock(success=True, content=str(analysis_response)),
            Mock(success=True, content=str(plan_response)),
        ]

        # Execute complete workflow
        result = await self.agent.analyze_and_plan(task)

        assert isinstance(result, AnalysisResult)
        assert result.task_analysis.task_id == "PROJ-456"
        assert result.task_plan.task_id == "PROJ-456"
        assert result.task_analysis.complexity == "medium"
        assert len(result.task_plan.steps) == 3
        assert result.confidence_score > 0.0

        # Verify all steps have proper dependencies
        step_names = [step.name for step in result.task_plan.steps]
        assert "Backend API Development" in step_names
        assert "Frontend Implementation" in step_names
        assert "Testing and Integration" in step_names

    @pytest.mark.asyncio
    async def test_planning_with_cost_tracking(self):
        """Test that planning tracks AI usage costs"""
        # RED: This will fail since cost tracking doesn't exist yet
        task = {"id": "TEST-123", "title": "Simple task"}

        # Mock AI responses with token usage
        self.mock_ai_provider.generate_text.return_value = Mock(
            success=True,
            content="{'complexity': 'low'}",
            cost=0.05,
            token_usage=Mock(total_tokens=1000),
        )

        result = await self.agent.analyze_task(task)

        # Verify cost tracking
        assert hasattr(result, "analysis_cost")
        assert result.analysis_cost == 0.05
        assert hasattr(result, "token_usage")
        assert result.token_usage.total_tokens == 1000
