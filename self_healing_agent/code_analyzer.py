"""Code Analyzer Service - Menganalisis kode untuk menemukan root cause."""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from .bug_detector import BugReport, BugType

logger = structlog.get_logger()


@dataclass
class CodeLocation:
    """Represents a location in code."""

    file_path: str
    line_start: int
    line_end: int
    function_name: str | None = None
    class_name: str | None = None

    def __str__(self) -> str:
        location = f"{self.file_path}:{self.line_start}"
        if self.function_name:
            location += f" in {self.function_name}"
        return location


@dataclass
class RootCauseAnalysis:
    """Result dari root cause analysis."""

    bug_report: BugReport
    root_cause: str
    affected_locations: list[CodeLocation] = field(default_factory=list)
    suggested_fix_strategy: str = ""
    confidence: float = 0.0
    related_code: str = ""
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ASTAnalyzer(ast.NodeVisitor):
    """AST visitor untuk analisis kode."""

    def __init__(self):
        self.imports: list[str] = []
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.classes: dict[str, ast.ClassDef] = {}
        self.current_class: str | None = None
        self.current_function: str | None = None
        self.source_lines: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from ... import statements."""
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Visit function definitions."""
        name = node.name
        if self.current_class:
            name = f"{self.current_class}.{node.name}"
        self.functions[name] = node

        old_function = self.current_function
        self.current_function = name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        old_class = self.current_class
        self.current_class = node.name
        self.classes[node.name] = node
        self.generic_visit(node)
        self.current_class = old_class

    def get_source_context(self, node: ast.AST, lines: int = 5) -> str:
        """Get source code context around an AST node."""
        if not hasattr(node, "lineno"):
            return ""

        start_line = max(1, node.lineno - lines)
        end_line = min(len(self.source_lines), node.end_lineno + lines if hasattr(node, "end_lineno") else node.lineno + lines)

        return "\n".join(self.source_lines[start_line - 1 : end_line])


class CodeAnalyzer:
    """Service untuk menganalisis kode dan menemukan root cause."""

    def __init__(self):
        self.logger = logger.bind(component="CodeAnalyzer")

    def analyze(self, bug_report: BugReport) -> RootCauseAnalysis:
        """Analyze bug report dan find root cause."""
        self.logger.info("Analyzing bug", bug_id=bug_report.bug_id)

        if not bug_report.file_path:
            return RootCauseAnalysis(
                bug_report=bug_report,
                root_cause="Cannot analyze: no file path provided",
                confidence=0.0,
            )

        try:
            return self._perform_analysis(bug_report)
        except Exception as e:
            self.logger.error("Analysis failed", error=str(e))
            return RootCauseAnalysis(
                bug_report=bug_report,
                root_cause=f"Analysis failed: {str(e)}",
                confidence=0.0,
            )

    def _perform_analysis(self, bug_report: BugReport) -> RootCauseAnalysis:
        """Perform the actual analysis."""
        file_path = Path(bug_report.file_path)

        if not file_path.exists():
            return RootCauseAnalysis(
                bug_report=bug_report,
                root_cause=f"File not found: {file_path}",
                confidence=0.0,
            )

        # Parse file
        try:
            source = file_path.read_text()
            tree = ast.parse(source)
            source_lines = source.split("\n")
        except SyntaxError as e:
            return RootCauseAnalysis(
                bug_report=bug_report,
                root_cause=f"Syntax error in file: {e}",
                confidence=1.0,
                related_code=f"Line {e.lineno}: {e.text}",
            )

        # Analyze AST
        analyzer = ASTAnalyzer()
        analyzer.source_lines = source_lines
        analyzer.visit(tree)

        # Find affected locations
        affected_locations = self._find_affected_locations(
            analyzer, bug_report.line_number, bug_report.bug_type
        )

        # Determine root cause based on bug type
        root_cause = self._determine_root_cause(
            bug_report, analyzer, source, source_lines
        )

        # Get related code
        related_code = self._get_related_code(analyzer, bug_report.line_number)

        return RootCauseAnalysis(
            bug_report=bug_report,
            root_cause=root_cause,
            affected_locations=affected_locations,
            suggested_fix_strategy=self._suggest_fix_strategy(bug_report.bug_type),
            confidence=0.8,
            related_code=related_code,
            dependencies=analyzer.imports,
        )

    def _find_affected_locations(
        self, analyzer: ASTAnalyzer, line_number: int | None, bug_type: BugType
    ) -> list[CodeLocation]:
        """Find code locations affected by the bug."""
        locations = []

        if line_number is None:
            return locations

        # Find function/class containing the line
        for func_name, func_node in analyzer.functions.items():
            if func_node.lineno <= line_number <= (func_node.end_lineno or func_node.lineno):
                locations.append(
                    CodeLocation(
                        file_path="",
                        line_start=func_node.lineno,
                        line_end=func_node.end_lineno or func_node.lineno,
                        function_name=func_name,
                    )
                )

        for class_name, class_node in analyzer.classes.items():
            if class_node.lineno <= line_number <= (class_node.end_lineno or class_node.lineno):
                locations.append(
                    CodeLocation(
                        file_path="",
                        line_start=class_node.lineno,
                        line_end=class_node.end_lineno or class_node.lineno,
                        class_name=class_name,
                    )
                )

        return locations

    def _determine_root_cause(
        self, bug_report: BugReport, analyzer: ASTAnalyzer, source: str, source_lines: list[str]
    ) -> str:
        """Determine root cause based on bug type and context."""
        bug_type = bug_report.bug_type

        if bug_type == BugType.SYNTAX_ERROR:
            return "Syntax error in code - likely missing or misplaced punctuation"

        if bug_type == BugType.IMPORT_ERROR:
            missing_module = self._extract_missing_module(bug_report.message)
            if missing_module:
                return f"Module '{missing_module}' is not installed or import path is incorrect"
            return "Import statement failed - module not found or circular import"

        if bug_type == BugType.TYPE_ERROR:
            return self._analyze_type_error(analyzer, bug_report)

        if bug_type == BugType.VALUE_ERROR:
            return self._analyze_value_error(analyzer, bug_report)

        if bug_type == BugType.LOGIC_ERROR:
            return "Logic error detected - algorithm or business logic needs review"

        if bug_type == BugType.RUNTIME_ERROR:
            return "Runtime error occurred - likely edge case not handled"

        return f"Unknown error: {bug_report.message}"

    def _analyze_type_error(self, analyzer: ASTAnalyzer, bug_report: BugReport) -> str:
        """Analyze type-related errors."""
        message = bug_report.message.lower()

        if "none" in message and "noneType" in message:
            return "TypeError: Variable is None when operation requires non-None value"
        if "unsupported operand" in message:
            return "TypeError: Operation between incompatible types"
        if "cannot unpack" in message:
            return "TypeError: Incorrect number of values to unpack"

        return "TypeError: Type mismatch between expected and actual value"

    def _analyze_value_error(self, analyzer: ASTAnalyzer, bug_report: BugReport) -> str:
        """Analyze value-related errors."""
        message = bug_report.message.lower()

        if "invalid literal" in message:
            return "ValueError: Invalid literal value for type conversion"
        if "too many values" in message:
            return "ValueError: Too many values to unpack"
        if "not enough values" in message:
            return "ValueError: Not enough values to unpack"

        return "ValueError: Invalid value provided"

    def _extract_missing_module(self, message: str) -> str | None:
        """Extract missing module name from error message."""
        import re

        patterns = [
            r"No module named ['\"]([^'\"]+)['\"]",
            r"ModuleNotFoundError: ([^'\"]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1)
        return None

    def _get_related_code(self, analyzer: ASTAnalyzer, line_number: int | None) -> str:
        """Get related code context around the error."""
        if line_number is None:
            return ""

        # Find the function containing the line
        for func_name, func_node in analyzer.functions.items():
            if func_node.lineno <= line_number <= (func_node.end_lineno or func_node.lineno):
                return analyzer.get_source_context(func_node)

        # Find the class containing the line
        for class_name, class_node in analyzer.classes.items():
            if class_node.lineno <= line_number <= (class_node.end_lineno or class_node.lineno):
                return analyzer.get_source_context(class_node)

        return ""

    def _suggest_fix_strategy(self, bug_type: BugType) -> str:
        """Suggest fix strategy based on bug type."""
        strategies = {
            BugType.SYNTAX_ERROR: "Check syntax - verify all brackets, colons, and indentation are correct",
            BugType.IMPORT_ERROR: "Install missing module or fix import path",
            BugType.TYPE_ERROR: "Add type checking, type conversion, or null/None handling",
            BugType.VALUE_ERROR: "Add input validation and error handling",
            BugType.LOGIC_ERROR: "Review algorithm logic and fix conditional statements",
            BugType.RUNTIME_ERROR: "Add exception handling and edge case checks",
            BugType.ASSERTION_ERROR: "Verify assumptions and fix test or code",
            BugType.UNKNOWN: "Further investigation required",
        }
        return strategies.get(bug_type, "Investigation required")

    def build_dependency_graph(self, file_path: str | Path) -> dict[str, list[str]]:
        """Build dependency graph for a file."""
        graph: dict[str, list[str]] = {}

        try:
            source = Path(file_path).read_text()
            tree = ast.parse(source)
            analyzer = ASTAnalyzer()
            analyzer.visit(tree)

            graph[str(file_path)] = analyzer.imports

        except Exception as e:
            self.logger.error("Failed to build dependency graph", error=str(e))

        return graph
