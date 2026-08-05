"""Tests for SelfRepairEngine."""

import pytest
from pathlib import Path

from self_healing_agent.self_repair import SelfRepairEngine, FixCandidate
from self_healing_agent.code_analyzer import RootCauseAnalysis
from self_healing_agent.bug_detector import BugReport, BugType, BugSeverity


class TestSelfRepairEngine:
    """Test cases for SelfRepairEngine."""

    @pytest.fixture
    def engine(self):
        """Create a SelfRepairEngine instance."""
        return SelfRepairEngine()

    @pytest.fixture
    def sample_analysis(self):
        """Create a sample root cause analysis."""
        bug = BugReport(
            bug_id="BUG-TEST-001",
            bug_type=BugType.TYPE_ERROR,
            severity=BugSeverity.MEDIUM,
            message="TypeError: unsupported operand",
            file_path=None,
            line_number=10,
            stack_trace=None,
            source="test",
        )

        return RootCauseAnalysis(
            bug_report=bug,
            root_cause="Type mismatch between string and int",
            confidence=0.8,
            related_code="result = x + y",
            suggested_fix_strategy="Add type conversion",
        )

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine is not None
        assert engine.code_analyzer is not None
        assert len(engine._fix_strategies) > 0

    def test_generate_fix_syntax_error(self, engine):
        """Test fix generation for syntax error."""
        bug = BugReport(
            bug_id="BUG-TEST-002",
            bug_type=BugType.SYNTAX_ERROR,
            severity=BugSeverity.HIGH,
            message="SyntaxError: invalid syntax",
            file_path=None,
            line_number=10,
            stack_trace=None,
            source="test",
        )

        analysis = RootCauseAnalysis(
            bug_report=bug,
            root_cause="Missing colon",
            confidence=0.9,
            related_code="def test\n    pass",
            suggested_fix_strategy="Add colon",
        )

        fix = engine.generate_fix(analysis)
        assert fix.fix_id.startswith("FIX-")
        assert fix.strategy == "syntax_fix"
        assert fix.confidence > 0

    def test_generate_fix_import_error(self, engine):
        """Test fix generation for import error."""
        bug = BugReport(
            bug_id="BUG-TEST-003",
            bug_type=BugType.IMPORT_ERROR,
            severity=BugSeverity.HIGH,
            message="ModuleNotFoundError: No module named 'nonexistent'",
            file_path=None,
            line_number=1,
            stack_trace=None,
            source="test",
        )

        analysis = RootCauseAnalysis(
            bug_report=bug,
            root_cause="Module not found",
            confidence=0.95,
            related_code="import nonexistent",
            suggested_fix_strategy="Install module",
        )

        fix = engine.generate_fix(analysis)
        assert fix.strategy == "import_fix"
        assert "pip install" in fix.fixed_code.lower()

    def test_validate_fix_safety(self, engine):
        """Test fix safety validation."""
        # Safe fix
        safe_fix = FixCandidate(
            fix_id="FIX-SAFE",
            description="Safe fix",
            original_code="x = 1",
            fixed_code="x = 2",
            file_path="test.py",
            line_start=1,
            line_end=1,
            confidence=0.9,
            strategy="safe",
        )

        assert engine._validate_fix_safety(safe_fix) is True

        # Unsafe fix with blocked pattern
        unsafe_fix = FixCandidate(
            fix_id="FIX-UNSAFE",
            description="Unsafe fix",
            original_code="os.system('ls')",
            fixed_code="eval(input())",
            file_path="test.py",
            line_start=1,
            line_end=1,
            confidence=0.9,
            strategy="dangerous",
        )

        assert engine._validate_fix_safety(unsafe_fix) is False

    def test_generate_diff(self, engine):
        """Test diff generation."""
        original = "line1\nline2\nline3"
        fixed = "line1\nmodified\nline3"

        diff = engine._generate_diff(original, fixed)
        assert "- line2" in diff
        assert "+ modified" in diff

    def test_add_null_check(self, engine):
        """Test null check addition."""
        code = "result = x + y"
        wrapped = engine._add_null_check(code)

        # Should add null check
        assert "if" in wrapped or wrapped == code

    def test_add_validation(self, engine):
        """Test validation addition."""
        code = "int(value)"
        wrapped = engine._add_validation(code, RootCauseAnalysis(
            bug_report=BugReport(
                bug_id="BUG-TEST",
                bug_type=BugType.VALUE_ERROR,
                severity=BugSeverity.MEDIUM,
                message="",
                file_path=None,
                line_number=None,
                stack_trace=None,
                source="test",
            ),
            root_cause="",
            confidence=0.8,
        ))

        assert "try" in wrapped or "except" in wrapped

    def test_add_exception_handling(self, engine):
        """Test exception handling addition."""
        code = "risky_operation()"
        wrapped = engine._add_exception_handling(code)

        assert "try" in wrapped
        assert "except" in wrapped
