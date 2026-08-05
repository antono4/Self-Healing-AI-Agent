"""Tests for BugDetector."""

import pytest

from self_healing_agent.bug_detector import BugDetector, BugReport, BugSeverity, BugType


class TestBugDetector:
    """Test cases for BugDetector."""

    @pytest.fixture
    def detector(self):
        """Create a BugDetector instance."""
        return BugDetector()

    def test_classify_syntax_error(self, detector):
        """Test classification of syntax errors."""
        exc = SyntaxError("invalid syntax")
        bug_type = detector._classify_exception(exc)
        assert bug_type == BugType.SYNTAX_ERROR

    def test_classify_import_error(self, detector):
        """Test classification of import errors."""
        exc = ModuleNotFoundError("No module named 'nonexistent'")
        bug_type = detector._classify_exception(exc)
        assert bug_type == BugType.IMPORT_ERROR

    def test_classify_type_error(self, detector):
        """Test classification of type errors."""
        exc = TypeError("unsupported operand type(s)")
        bug_type = detector._classify_exception(exc)
        assert bug_type == BugType.TYPE_ERROR

    def test_classify_value_error(self, detector):
        """Test classification of value errors."""
        exc = ValueError("invalid literal")
        bug_type = detector._classify_exception(exc)
        assert bug_type == BugType.VALUE_ERROR

    def test_detect_from_exception(self, detector):
        """Test bug detection from exception."""
        try:
            raise TypeError("Test error")
        except TypeError as e:
            bug = detector.detect_from_exception(e)

        assert bug.bug_type == BugType.TYPE_ERROR
        assert bug.message == "Test error"
        assert bug.source == "exception"
        assert bug.bug_id.startswith("BUG-")

    def test_estimate_severity(self, detector):
        """Test severity estimation."""
        assert detector._estimate_severity(BugType.SYNTAX_ERROR) == BugSeverity.HIGH
        assert detector._estimate_severity(BugType.IMPORT_ERROR) == BugSeverity.HIGH
        assert detector._estimate_severity(BugType.TYPE_ERROR) == BugSeverity.MEDIUM
        assert detector._estimate_severity(BugType.VALUE_ERROR) == BugSeverity.MEDIUM

    def test_generate_bug_id(self, detector):
        """Test bug ID generation."""
        bug_id = detector._generate_bug_id()
        assert bug_id.startswith("BUG-")
        assert len(bug_id.split("-")) == 3

    def test_extract_file_path(self, detector):
        """Test file path extraction from log line."""
        line = '  File "/path/to/file.py", line 10, in function'
        path = detector._extract_file_path(line)
        assert path == "/path/to/file.py"

    def test_detect_from_test_failure(self, detector):
        """Test bug detection from test output."""
        output = """
FAILED test_example.py::test_something
ERROR test_example.py::test_other
Traceback (most recent call last):
  File "test_example.py", line 5, in test_something
    assert x == y
AssertionError
ZeroDivisionError: division by zero
TypeError: unsupported operand
        """
        bugs = detector.detect_from_test_failure(output)
        # Should detect at least some errors
        assert len(bugs) >= 2
