"""Self-Healing Orchestrator - Main agent yang mengkoordinasikan workflow."""

import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from .bug_detector import BugDetector, BugReport
from .code_analyzer import CodeAnalyzer, RootCauseAnalysis
from .config import Config, get_config
from .memory import MemoryStore
from .self_repair import FixCandidate, SelfRepairEngine
from .verification import VerificationSuite, VerifiedFix

logger = structlog.get_logger()


class WorkflowStatus(Enum):
    """Status dari self-healing workflow."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


@dataclass
class SelfHealingTask:
    """Task untuk self-healing process."""

    task_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    bug_report: BugReport | None = None
    analysis: RootCauseAnalysis | None = None
    fix: FixCandidate | None = None
    verified_fix: VerifiedFix | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfHealingResult:
    """Result dari self-healing process."""

    success: bool
    task: SelfHealingTask
    message: str
    fix_applied: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class SelfHealingOrchestrator:
    """Orchestrator utama untuk self-healing workflow."""

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self.logger = logger.bind(component="Orchestrator")

        # Initialize components
        self.bug_detector = BugDetector(self.config)
        self.code_analyzer = CodeAnalyzer()
        self.self_repair = SelfRepairEngine(self.config)
        self.verification = VerificationSuite(self.config)
        self.memory = MemoryStore()

        # Task tracking
        self.tasks: dict[str, SelfHealingTask] = {}

    def process_bug(self, bug: BugReport) -> SelfHealingResult:
        """Process bug through self-healing workflow."""
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.logger.info("Processing bug", bug_id=bug.bug_id, task_id=task_id)

        task = SelfHealingTask(task_id=task_id, bug_report=bug)
        self.tasks[task_id] = task

        try:
            # Step 1: Store bug report
            task.status = WorkflowStatus.RUNNING
            self.memory.store_bug_report(bug)

            # Step 2: Analyze root cause
            self.logger.info("Analyzing root cause", task_id=task_id)
            analysis = self.code_analyzer.analyze(bug)
            task.analysis = analysis
            self.memory.store_analysis(task_id, analysis)

            if analysis.confidence < 0.3:
                # Low confidence - need manual review
                task.status = WorkflowStatus.MANUAL_REVIEW
                return SelfHealingResult(
                    success=False,
                    task=task,
                    message=f"Low confidence analysis ({analysis.confidence:.0%}). Manual review required.",
                )

            # Step 3: Generate fix
            self.logger.info("Generating fix", task_id=task_id)
            fix = self.self_repair.generate_fix(analysis)
            task.fix = fix
            self.memory.store_fix(fix)

            if fix.confidence < 0.3:
                # Low confidence fix - need manual review
                task.status = WorkflowStatus.MANUAL_REVIEW
                return SelfHealingResult(
                    success=False,
                    task=task,
                    message=f"Low confidence fix ({fix.confidence:.0%}). Manual review required.",
                )

            # Step 4: Verify fix
            self.logger.info("Verifying fix", task_id=task_id)
            verified = self.verification.verify_fix(fix)
            task.verified_fix = verified

            if not verified.verified:
                # Verification failed - retry or manual review
                if task.retry_count < self.config.max_retries:
                    task.retry_count += 1
                    self.logger.warning(
                        "Verification failed, retrying",
                        task_id=task_id,
                        retry=task.retry_count,
                    )
                    return self.process_bug(bug)  # Recursive retry

                task.status = WorkflowStatus.MANUAL_REVIEW
                return SelfHealingResult(
                    success=False,
                    task=task,
                    message=f"Fix verification failed after {task.retry_count} retries. Manual review required.",
                )

            # Step 5: Apply fix
            if self.config.is_auto_fix:
                self.logger.info("Applying fix", task_id=task_id)
                applied = self.self_repair.apply_fix(fix)

                if applied:
                    self.memory.store_successful_fix(fix, bug)
                    task.status = WorkflowStatus.COMPLETED
                    task.completed_at = datetime.now()
                    return SelfHealingResult(
                        success=True,
                        task=task,
                        message="Bug fixed successfully!",
                        fix_applied=True,
                    )

            # Fix not applied but verified
            task.status = WorkflowStatus.COMPLETED
            task.completed_at = datetime.now()
            return SelfHealingResult(
                success=True,
                task=task,
                message="Fix verified and ready to apply (auto-fix disabled).",
                fix_applied=False,
            )

        except Exception as e:
            error_msg = f"Workflow failed: {str(e)}\n{traceback.format_exc()}"
            self.logger.error("Workflow failed", task_id=task_id, error=error_msg)
            task.status = WorkflowStatus.FAILED
            task.error = error_msg

            return SelfHealingResult(
                success=False,
                task=task,
                message=error_msg,
            )

    def process_exception(self, exc: Exception) -> SelfHealingResult:
        """Process an exception through self-healing."""
        self.logger.info("Processing exception", type=type(exc).__name__)

        bug = self.bug_detector.detect_from_exception(exc)
        return self.process_bug(bug)

    def process_file(self, file_path: str | Path) -> list[SelfHealingResult]:
        """Process a file for potential bugs."""
        self.logger.info("Processing file", file=str(file_path))

        bugs = self.bug_detector.run_static_analysis(file_path)
        results = []

        for bug in bugs:
            result = self.process_bug(bug)
            results.append(result)

        return results

    def get_task_status(self, task_id: str) -> SelfHealingTask | None:
        """Get status of a task."""
        return self.tasks.get(task_id)

    def get_statistics(self) -> dict[str, Any]:
        """Get self-healing statistics."""
        stats = self.memory.get_fix_statistics()

        # Add task statistics
        task_stats = {
            "total_tasks": len(self.tasks),
            "pending_tasks": sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.PENDING),
            "running_tasks": sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.RUNNING),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.COMPLETED),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.FAILED),
            "manual_review_tasks": sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.MANUAL_REVIEW),
        }

        return {**stats, **task_stats}

    def list_tasks(
        self,
        status: WorkflowStatus | None = None,
        limit: int = 100,
    ) -> list[SelfHealingTask]:
        """List tasks, optionally filtered by status."""
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        return sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old completed tasks."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        old_tasks = [
            tid for tid, task in self.tasks.items()
            if task.completed_at and task.completed_at < cutoff
        ]

        for tid in old_tasks:
            del self.tasks[tid]

        self.logger.info("Cleaned up old tasks", count=len(old_tasks))
        return len(old_tasks)
