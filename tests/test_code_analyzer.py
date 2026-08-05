"""Tests for CodeAnalyzer."""

import pytest
from pathlib import Path

from self_healing_agent.code_analyzer import CodeAnalyzer, RootCauseAnalysis
from self_healing_agent.bug_detector import BugReport, BugType, BugSeverity


class TestCodeAnalyzer:
    """Test cases for CodeAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create a CodeAnalyzer instance."""
        return CodeAnalyzer()

    @pytest.fixture
    def sample_bug(self):
        """Create a sample bug report."""
        return BugReport(
            bug_id="BUG-TEST-001",
            bug_type=BugType.TYPE_ERROR,
            severity=BugSeverity.MEDIUM,
            message="TypeError: unsupported operand",
            file_path=str(Path(__file__).parent.parent / "examples" / "sample_buggy_code.py"),
            line_number=10,
            stack_trace=None,
            source="test",
        )

    def test_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None
        assert analyzer.logger is not None

    def test_analyze_without_file_path(self, analyzer):
        """Test analysis without file path."""
        bug = BugReport(
            bug_id="BUG-TEST-002",
            bug_type=BugType.TYPE_ERROR,
            severity=BugSeverity.MEDIUM,
            message="Test error",
            file_path=None,
            line_number=None,
            stack_trace=None,
            source="test",
        )

        result = analyzer.analyze(bug)
        assert result.confidence == 0.0
        assert "no file path" in result.root_cause.lower()

    def test_analyze_nonexistent_file(self, analyzer):
        """Test analysis with nonexistent file."""
        bug = BugReport(
            bug_id="BUG-TEST-003",
            bug_type=BugType.TYPE_ERROR,
            severity=BugSeverity.MEDIUM,
            message="Test error",
            file_path="/nonexistent/file.py",
            line_number=10,
            stack_trace=None,
            source="test",
        )

        result = analyzer.analyze(bug)
        assert result.confidence == 0.0
        assert "not found" in result.root_cause.lower()

    def test_suggest_fix_strategy(self, analyzer):
        """Test fix strategy suggestions."""
        strategies = {
            BugType.SYNTAX_ERROR: "syntax",
            BugType.IMPORT_ERROR: "install",
            BugType.TYPE_ERROR: "type",
            BugType.VALUE_ERROR: "validation",
            BugType.LOGIC_ERROR: "review",
            BugType.RUNTIME_ERROR: "exception",
        }

        for bug_type, expected in strategies.items():
            suggestion = analyzer._suggest_fix_strategy(bug_type)
            assert expected in suggestion.lower()

    def test_build_dependency_graph(self, analyzer, tmp_path):
        """Test dependency graph building."""
        # Create a test file with imports
        test_file = tmp_path / "test_deps.py"
        test_file.write_text("""
import os
import sys
from pathlib import Path
import json
""")

        graph = analyzer.build_dependency_graph(test_file)

        assert str(test_file) in graph
        imports = graph[str(test_file)]
        assert "os" in imports
        assert "sys" in imports
        assert "pathlib" in imports
        assert "json" in imports
