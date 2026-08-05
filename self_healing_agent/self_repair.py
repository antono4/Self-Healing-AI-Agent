"""Self-Repair Engine - Generate dan apply fixes untuk bug."""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from .code_analyzer import CodeAnalyzer, RootCauseAnalysis
from .config import Config
from .bug_detector import BugReport, BugType

logger = structlog.get_logger()


@dataclass
class FixCandidate:
    """Kandidat fix untuk bug."""

    fix_id: str
    description: str
    original_code: str
    fixed_code: str
    file_path: str
    line_start: int
    line_end: int
    confidence: float
    strategy: str
    diff: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerifiedFix:
    """Fix yang sudah diverifikasi dan siap di-apply."""

    fix: FixCandidate
    verified: bool
    verification_result: str
    tests_passed: bool
    regressions_found: list[str] = field(default_factory=list)


class SelfRepairEngine:
    """Engine untuk generate dan apply fixes."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.logger = logger.bind(component="SelfRepair")
        self.code_analyzer = CodeAnalyzer()
        self._fix_strategies = self._init_fix_strategies()

    def _init_fix_strategies(self) -> dict[BugType, callable]:
        """Initialize fix strategies for each bug type."""
        return {
            BugType.SYNTAX_ERROR: self._fix_syntax_error,
            BugType.IMPORT_ERROR: self._fix_import_error,
            BugType.TYPE_ERROR: self._fix_type_error,
            BugType.VALUE_ERROR: self._fix_value_error,
            BugType.LOGIC_ERROR: self._fix_logic_error,
            BugType.RUNTIME_ERROR: self._fix_runtime_error,
            BugType.ASSERTION_ERROR: self._fix_assertion_error,
            BugType.UNKNOWN: self._fix_unknown_error,
        }

    def generate_fix(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Generate fix candidate berdasarkan root cause analysis."""
        self.logger.info(
            "Generating fix",
            bug_id=analysis.bug_report.bug_id,
            bug_type=analysis.bug_report.bug_type.value,
        )

        strategy = self._fix_strategies.get(
            analysis.bug_report.bug_type, self._fix_unknown_error
        )

        try:
            return strategy(analysis)
        except Exception as e:
            self.logger.error("Fix generation failed", error=str(e))
            return self._create_failed_fix(analysis, str(e))

    def apply_fix(self, fix: FixCandidate) -> bool:
        """Apply fix ke file."""
        self.logger.info("Applying fix", fix_id=fix.fix_id, file=fix.file_path)

        if not self._validate_fix_safety(fix):
            self.logger.warning("Fix failed safety check", fix_id=fix.fix_id)
            return False

        try:
            file_path = Path(fix.file_path)
            if not file_path.exists():
                self.logger.error("File not found", file=fix.file_path)
                return False

            # Read original content
            content = file_path.read_text()
            lines = content.split("\n")

            # Apply the fix
            fixed_lines = lines[: fix.line_start - 1]
            fixed_lines.extend(fix.fixed_code.split("\n"))
            fixed_lines.extend(lines[fix.line_end :])

            # Write back
            file_path.write_text("\n".join(fixed_lines))

            self.logger.info("Fix applied successfully", fix_id=fix.fix_id)
            return True

        except Exception as e:
            self.logger.error("Failed to apply fix", error=str(e))
            return False

    def _fix_syntax_error(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Fix syntax errors."""
        bug = analysis.bug_report
        line_number = bug.line_number or 1

        # Common syntax fixes
        fixed_code = analysis.related_code

        # Check for missing colon
        if ":" not in fixed_code and "def " in fixed_code or "class " in fixed_code or "if " in fixed_code or "for " in fixed_code:
            fixed_code = re.sub(r"(def |class |if |for |while |except )([^\n:]+)$", r"\1\2:", fixed_code, flags=re.MULTILINE)

        # Check for unbalanced brackets
        open_parens = fixed_code.count("(") - fixed_code.count(")")
        open_brackets = fixed_code.count("[") - fixed_code.count("]")
        open_braces = fixed_code.count("{") - fixed_code.count("}")

        if open_parens > 0:
            fixed_code += ")" * open_parens
        if open_brackets > 0:
            fixed_code += "]" * open_brackets
        if open_braces > 0:
            fixed_code += "}" * open_braces

        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-SYNT",
            description="Fix syntax error",
            original_code=analysis.related_code,
            fixed_code=fixed_code,
            file_path=bug.file_path or "",
            line_start=line_number,
            line_end=line_number + analysis.related_code.count("\n"),
            confidence=0.9,
            strategy="syntax_fix",
            diff=self._generate_diff(analysis.related_code, fixed_code),
        )

    def _fix_import_error(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Fix import errors."""
        bug = analysis.bug_report

        # Extract module name
        import re

        module_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", bug.message)
        module_name = module_match.group(1) if module_match else "unknown"

        # Generate pip install command or fix import
        if module_name.startswith("'") or module_name.startswith('"'):
            module_name = module_name.strip("'\"")

        # Check if it's a relative import issue
        if "attempted relative import" in bug.message.lower():
            return FixCandidate(
                fix_id=f"FIX-{bug.bug_id}-IMPR",
                description="Fix relative import to absolute import",
                original_code=analysis.related_code,
                fixed_code="from package.module import component",
                file_path=bug.file_path or "",
                line_start=bug.line_number or 1,
                line_end=(bug.line_number or 1) + 1,
                confidence=0.85,
                strategy="import_fix",
                metadata={"suggested_install": f"pip install {module_name}"},
            )

        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-IMPR",
            description=f"Install missing module: {module_name}",
            original_code="",
            fixed_code=f"# Install with: pip install {module_name}",
            file_path=bug.file_path or "",
            line_start=bug.line_number or 1,
            line_end=bug.line_number or 1,
            confidence=0.95,
            strategy="import_fix",
            metadata={"suggested_install": f"pip install {module_name}"},
        )

    def _fix_type_error(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Fix type errors."""
        bug = analysis.bug_report
        message = bug.message.lower()

        original_code = analysis.related_code
        fixed_code = original_code

        # Handle NoneType errors
        if "nonetype" in message or "none" in message:
            if "NoneType" in message:
                # Add null check
                fixed_code = self._add_null_check(original_code)

        # Handle unsupported operand
        if "unsupported operand" in message:
            fixed_code = self._fix_type_conversion(original_code)

        # Handle cannot unpack
        if "unpack" in message:
            fixed_code = self._handle_unpack_issue(original_code)

        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-TYPE",
            description="Fix type error - add type conversion or null handling",
            original_code=original_code,
            fixed_code=fixed_code,
            file_path=bug.file_path or "",
            line_start=bug.line_number or 1,
            line_end=(bug.line_number or 1) + original_code.count("\n"),
            confidence=0.75,
            strategy="type_fix",
        )

    def _fix_value_error(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Fix value errors."""
        bug = analysis.bug_report
        original_code = analysis.related_code

        # Add validation wrapper
        fixed_code = self._add_validation(original_code, analysis)

        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-VAL",
            description="Fix value error - add input validation",
            original_code=original_code,
            fixed_code=fixed_code,
            file_path=bug.file_path or "",
            line_start=bug.line_number or 1,
            line_end=(bug.line_number or 1) + original_code.count("\n"),
            confidence=0.7,
            strategy="value_fix",
        )

    def _fix_logic_error(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Fix logic errors."""
        bug = analysis.bug_report

        # For logic errors, we need more context
        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-LOG",
            description="Fix logic error - requires code review",
            original_code=analysis.related_code,
            fixed_code=analysis.related_code,  # Placeholder
            file_path=bug.file_path or "",
            line_start=bug.line_number or 1,
            line_end=(bug.line_number or 1) + analysis.related_code.count("\n"),
            confidence=0.5,
            strategy="logic_fix",
            metadata={"suggestion": analysis.suggested_fix_strategy},
        )

    def _fix_runtime_error(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Fix runtime errors."""
        bug = analysis.bug_report
        original_code = analysis.related_code

        # Add try-except wrapper
        fixed_code = self._add_exception_handling(original_code)

        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-RTE",
            description="Fix runtime error - add exception handling",
            original_code=original_code,
            fixed_code=fixed_code,
            file_path=bug.file_path or "",
            line_start=bug.line_number or 1,
            line_end=(bug.line_number or 1) + original_code.count("\n"),
            confidence=0.7,
            strategy="runtime_fix",
        )

    def _fix_assertion_error(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Fix assertion errors."""
        bug = analysis.bug_report

        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-ASS",
            description="Fix assertion error - verify assumptions",
            original_code=analysis.related_code,
            fixed_code=analysis.related_code,
            file_path=bug.file_path or "",
            line_start=bug.line_number or 1,
            line_end=(bug.line_number or 1) + analysis.related_code.count("\n"),
            confidence=0.6,
            strategy="assertion_fix",
            metadata={"suggestion": "Review assertion logic and fix code or test"},
        )

    def _fix_unknown_error(self, analysis: RootCauseAnalysis) -> FixCandidate:
        """Handle unknown errors."""
        bug = analysis.bug_report

        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-UNK",
            description="Unknown error - requires manual investigation",
            original_code=analysis.related_code,
            fixed_code=analysis.related_code,
            file_path=bug.file_path or "",
            line_start=bug.line_number or 1,
            line_end=(bug.line_number or 1) + analysis.related_code.count("\n"),
            confidence=0.3,
            strategy="unknown_fix",
            metadata={"root_cause": analysis.root_cause},
        )

    def _create_failed_fix(self, analysis: RootCauseAnalysis, error: str) -> FixCandidate:
        """Create a placeholder fix when generation fails."""
        bug = analysis.bug_report

        return FixCandidate(
            fix_id=f"FIX-{bug.bug_id}-FAIL",
            description=f"Fix generation failed: {error}",
            original_code=analysis.related_code,
            fixed_code="",
            file_path=bug.file_path or "",
            line_start=bug.line_number or 1,
            line_end=bug.line_number or 1,
            confidence=0.0,
            strategy="failed",
        )

    def _validate_fix_safety(self, fix: FixCandidate) -> bool:
        """Validate fix passes safety checks."""
        # Check for blocked patterns
        for pattern in self.config.blocked_patterns:
            if pattern in fix.fixed_code:
                self.logger.warning(
                    "Fix contains blocked pattern", pattern=pattern, fix_id=fix.fix_id
                )
                return False

        # Check fix size
        fix_lines = len(fix.fixed_code.split("\n"))
        if fix_lines > self.config.get("security.max_fix_size", 500):
            self.logger.warning(
                "Fix exceeds maximum size", size=fix_lines, fix_id=fix.fix_id
            )
            return False

        # Check file extension
        if fix.file_path:
            ext = Path(fix.file_path).suffix
            if ext not in self.config.allowed_extensions:
                self.logger.warning(
                    "File type not allowed", extension=ext, fix_id=fix.fix_id
                )
                return False

        return True

    def _add_null_check(self, code: str) -> str:
        """Add null check to code."""
        # Simple null check wrapper
        if "=" in code and not code.strip().startswith("if"):
            lines = code.split("\n")
            for i, line in enumerate(lines):
                if "=" in line and "==" not in line:
                    var = line.split("=")[0].strip()
                    if var and var.isidentifier():
                        return f"if {var} is not None:\n    {code}"
        return code

    def _fix_type_conversion(self, code: str) -> str:
        """Fix type conversion issues."""
        # Add type conversion hints
        return code

    def _handle_unpack_issue(self, code: str) -> str:
        """Handle unpacking issues."""
        # Wrap in list() if needed
        return code

    def _add_validation(self, code: str, analysis: RootCauseAnalysis) -> str:
        """Add input validation."""
        return f"try:\n    {code}\nexcept ValueError:\n    # Handle validation error\n    pass"

    def _add_exception_handling(self, code: str) -> str:
        """Add try-except wrapper."""
        return f"try:\n    {code}\nexcept Exception as e:\n    # Handle exception\n    raise"

    def _generate_diff(self, original: str, fixed: str) -> str:
        """Generate diff between original and fixed code."""
        diff_lines = []
        original_lines = original.split("\n")
        fixed_lines = fixed.split("\n")

        max_lines = max(len(original_lines), len(fixed_lines))

        for i in range(max_lines):
            orig = original_lines[i] if i < len(original_lines) else ""
            fix = fixed_lines[i] if i < len(fixed_lines) else ""

            if orig != fix:
                if orig:
                    diff_lines.append(f"- {orig}")
                if fix:
                    diff_lines.append(f"+ {fix}")
            else:
                diff_lines.append(f"  {orig}")

        return "\n".join(diff_lines)
