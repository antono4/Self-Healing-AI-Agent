"""Bug Detection Service - Mendeteksi bug dari berbagai sumber."""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from .config import Config

logger = structlog.get_logger()


class BugSeverity(Enum):
    """Severity levels for bugs."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BugType(Enum):
    """Types of bugs."""

    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    TYPE_ERROR = "type_error"
    VALUE_ERROR = "value_error"
    LOGIC_ERROR = "logic_error"
    RUNTIME_ERROR = "runtime_error"
    ASSERTION_ERROR = "assertion_error"
    UNKNOWN = "unknown"


@dataclass
class BugReport:
    """Report containing bug information."""

    bug_id: str
    bug_type: BugType
    severity: BugSeverity
    message: str
    file_path: str | None
    line_number: int | None
    stack_trace: str | None
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bug_id": self.bug_id,
            "bug_type": self.bug_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "stack_trace": self.stack_trace,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class BugDetector:
    """Service untuk mendeteksi bug dari berbagai sumber."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.logger = logger.bind(component="BugDetector")
        self._error_patterns = self._compile_error_patterns()

    def _compile_error_patterns(self) -> dict[str, re.Pattern]:
        """Compile regex patterns for error detection."""
        patterns = {
            "python_syntax": r"SyntaxError: (.+)",
            "python_import": r"ImportError: (.+)",
            "python_type": r"TypeError: (.+)",
            "python_value": r"ValueError: (.+)",
            "python_attribute": r"AttributeError: (.+)",
            "python_runtime": r"RuntimeError: (.+)",
            "python_assertion": r"AssertionError: (.+)",
            "python_zero_division": r"ZeroDivisionError: (.+)",
            "python_key_error": r"KeyError: (.+)",
            "python_index_error": r"IndexError: (.+)",
        }
        return {k: re.compile(v) for k, v in patterns.items()}

    def detect_from_logs(self, log_path: str | Path) -> list[BugReport]:
        """Deteksi bug dari file log."""
        self.logger.info("Detecting bugs from logs", path=str(log_path))
        bugs: list[BugReport] = []

        try:
            content = Path(log_path).read_text()
            bugs = self._parse_log_content(content, "log_file")
        except Exception as e:
            self.logger.error("Failed to read log file", error=str(e))

        return bugs

    def detect_from_test_failure(self, test_output: str) -> list[BugReport]:
        """Deteksi bug dari output test failure."""
        self.logger.info("Detecting bugs from test output")
        return self._parse_log_content(test_output, "test_failure")

    def detect_from_exception(self, exception: Exception) -> BugReport:
        """Deteksi bug dari exception."""
        self.logger.info("Detecting bug from exception", type=type(exception).__name__)

        bug_type = self._classify_exception(exception)
        severity = self._estimate_severity(bug_type)

        # Extract file and line from traceback
        file_path = None
        line_number = None
        stack_trace = None

        if exception.__traceback__:
            tb = exception.__traceback__
            stack_trace = self._format_traceback(tb)
            while tb.tb_next:
                tb = tb.tb_next
            file_path = str(tb.tb_frame.f_code.co_filename)
            line_number = tb.tb_lineno

        return BugReport(
            bug_id=self._generate_bug_id(),
            bug_type=bug_type,
            severity=severity,
            message=str(exception),
            file_path=file_path,
            line_number=line_number,
            stack_trace=stack_trace,
            source="exception",
        )

    def _parse_log_content(self, content: str, source: str) -> list[BugReport]:
        """Parse log content untuk mencari error patterns."""
        bugs: list[BugReport] = []

        for line_num, line in enumerate(content.split("\n"), 1):
            for pattern_name, pattern in self._error_patterns.items():
                match = pattern.search(line)
                if match:
                    bug_type = self._pattern_to_bug_type(pattern_name)
                    severity = self._estimate_severity(bug_type)

                    bugs.append(
                        BugReport(
                            bug_id=self._generate_bug_id(),
                            bug_type=bug_type,
                            severity=severity,
                            message=match.group(0),
                            file_path=self._extract_file_path(line),
                            line_number=line_num,
                            stack_trace=self._extract_stack_trace(content, line_num),
                            source=source,
                            metadata={"pattern": pattern_name},
                        )
                    )

        return bugs

    def _classify_exception(self, exc: Exception) -> BugType:
        """Classify exception type to BugType."""
        exc_type = type(exc).__name__

        mapping = {
            "SyntaxError": BugType.SYNTAX_ERROR,
            "IndentationError": BugType.SYNTAX_ERROR,
            "TabError": BugType.SYNTAX_ERROR,
            "ImportError": BugType.IMPORT_ERROR,
            "ModuleNotFoundError": BugType.IMPORT_ERROR,
            "TypeError": BugType.TYPE_ERROR,
            "ValueError": BugType.VALUE_ERROR,
            "RuntimeError": BugType.RUNTIME_ERROR,
            "AssertionError": BugType.ASSERTION_ERROR,
            "ZeroDivisionError": BugType.VALUE_ERROR,
            "AttributeError": BugType.TYPE_ERROR,
            "KeyError": BugType.VALUE_ERROR,
            "IndexError": BugType.VALUE_ERROR,
        }

        return mapping.get(exc_type, BugType.UNKNOWN)

    def _pattern_to_bug_type(self, pattern_name: str) -> BugType:
        """Map pattern name to BugType."""
        mapping = {
            "python_syntax": BugType.SYNTAX_ERROR,
            "python_import": BugType.IMPORT_ERROR,
            "python_type": BugType.TYPE_ERROR,
            "python_value": BugType.VALUE_ERROR,
            "python_attribute": BugType.TYPE_ERROR,
            "python_runtime": BugType.RUNTIME_ERROR,
            "python_assertion": BugType.ASSERTION_ERROR,
            "python_zero_division": BugType.VALUE_ERROR,
            "python_key_error": BugType.VALUE_ERROR,
            "python_index_error": BugType.VALUE_ERROR,
        }
        return mapping.get(pattern_name, BugType.UNKNOWN)

    def _estimate_severity(self, bug_type: BugType) -> BugSeverity:
        """Estimate severity based on bug type."""
        severity_map = {
            BugType.SYNTAX_ERROR: BugSeverity.HIGH,
            BugType.IMPORT_ERROR: BugSeverity.HIGH,
            BugType.TYPE_ERROR: BugSeverity.MEDIUM,
            BugType.VALUE_ERROR: BugSeverity.MEDIUM,
            BugType.LOGIC_ERROR: BugSeverity.HIGH,
            BugType.RUNTIME_ERROR: BugSeverity.HIGH,
            BugType.ASSERTION_ERROR: BugSeverity.MEDIUM,
            BugType.UNKNOWN: BugSeverity.MEDIUM,
        }
        return severity_map.get(bug_type, BugSeverity.MEDIUM)

    def _generate_bug_id(self) -> str:
        """Generate unique bug ID."""
        import uuid

        return f"BUG-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    def _extract_file_path(self, line: str) -> str | None:
        """Extract file path from log line."""
        patterns = [r'File "([^"]+)"', r"File '([^']+)'", r'([/\w]+\.py)']
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return None

    def _extract_stack_trace(self, content: str, error_line: int) -> str | None:
        """Extract stack trace around error line."""
        lines = content.split("\n")
        start = max(0, error_line - 10)
        end = min(len(lines), error_line + 5)
        return "\n".join(lines[start:end])

    def _format_traceback(self, tb: Any) -> str:
        """Format traceback object to string."""
        import traceback
        import io

        s = io.StringIO()
        traceback.print_tb(tb, file=s)
        return s.getvalue()

    def run_static_analysis(self, file_path: str | Path) -> list[BugReport]:
        """Run static analysis pada file."""
        self.logger.info("Running static analysis", file=str(file_path))
        bugs: list[BugReport] = []

        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", str(file_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                bug = BugReport(
                    bug_id=self._generate_bug_id(),
                    bug_type=BugType.SYNTAX_ERROR,
                    severity=BugSeverity.HIGH,
                    message=result.stderr or "Compilation failed",
                    file_path=str(file_path),
                    line_number=self._extract_line_from_error(result.stderr),
                    stack_trace=result.stderr,
                    source="static_analysis",
                )
                bugs.append(bug)

        except Exception as e:
            self.logger.error("Static analysis failed", error=str(e))

        return bugs

    def _extract_line_from_error(self, error: str) -> int | None:
        """Extract line number from error message."""
        match = re.search(r"line (\d+)", error)
        return int(match.group(1)) if match else None
