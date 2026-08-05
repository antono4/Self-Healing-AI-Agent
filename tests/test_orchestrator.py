"""Tests for SelfHealingOrchestrator."""

import pytest
from unittest.mock import MagicMock, patch

from self_healing_agent.orchestrator import (
    SelfHealingOrchestrator,
    SelfHealingTask,
    WorkflowStatus,
)
from self_healing_agent.bug_detector import BugDetector, BugReport, BugType, BugSeverity


class TestSelfHealingOrchestrator:
    """Test cases for SelfHealingOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance."""
        return SelfHealingOrchestrator()

    @pytest.fixture
    def sample_bug(self):
        """Create a sample bug report."""
        return BugReport(
            bug_id="BUG-TEST-001",
            bug_type=BugType.TYPE_ERROR,
            severity=BugSeverity.MEDIUM,
            message="TypeError: unsupported operand",
            file_path=None,
            line_number=None,
            stack_trace=None,
            source="test",
        )

    def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.bug_detector is not None
        assert orchestrator.code_analyzer is not None
        assert orchestrator.self_repair is not None
        assert orchestrator.verification is not None
        assert orchestrator.memory is not None

    def test_process_bug_with_no_file(self, orchestrator, sample_bug):
        """Test processing bug with no file path."""
        result = orchestrator.process_bug(sample_bug)

        assert result.task.bug_report == sample_bug
        # Without file path, should require manual review
        assert result.task.status == WorkflowStatus.MANUAL_REVIEW or result.success is False

    def test_task_creation(self, orchestrator, sample_bug):
        """Test task is created when processing bug."""
        orchestrator.process_bug(sample_bug)

        assert len(orchestrator.tasks) > 0
        task = list(orchestrator.tasks.values())[0]
        assert task.bug_report == sample_bug

    def test_get_statistics(self, orchestrator):
        """Test statistics retrieval."""
        stats = orchestrator.get_statistics()

        assert "total_bugs" in stats
        assert "bugs_by_type" in stats
        assert "total_tasks" in stats

    def test_list_tasks(self, orchestrator, sample_bug):
        """Test listing tasks."""
        orchestrator.process_bug(sample_bug)

        tasks = orchestrator.list_tasks()
        assert len(tasks) > 0

        pending_tasks = orchestrator.list_tasks(status=WorkflowStatus.PENDING)
        assert isinstance(pending_tasks, list)

    def test_process_exception(self, orchestrator):
        """Test processing an exception."""
        result = orchestrator.process_exception(ValueError("Test value error"))

        assert result.task is not None
        assert result.task.bug_report is not None

    def test_cleanup_old_tasks(self, orchestrator):
        """Test cleanup of old tasks."""
        count = orchestrator.cleanup_old_tasks(days=7)
        assert count >= 0
