"""Self-Healing Task Generator for OpenHands.

This module generates task descriptions for OpenHands agents
based on workflow execution results.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SelfHealingTask:
    """Represents a self-healing task for OpenHands."""

    bug_id: str
    bug_type: str
    message: str
    file_path: str | None
    line_number: int | None
    root_cause: str
    suggested_fix: str
    priority: str = "medium"


class TaskGenerator:
    """Generate task descriptions for OpenHands agents."""

    @staticmethod
    def generate_analyze_task(bug: SelfHealingTask) -> str:
        """Generate task for analyzing a bug."""
        return f"""Analyze and fix the following bug:

## Bug Information
- Bug ID: {bug.bug_id}
- Type: {bug.bug_type}
- Message: {bug.message}
- File: {bug.file_path or "Unknown"}
- Line: {bug.line_number or "Unknown"}

## Root Cause
{bug.root_cause}

## Suggested Fix Strategy
{bug.suggested_fix}

## Tasks
1. Investigate the bug in the codebase
2. Identify the root cause
3. Implement a fix
4. Verify the fix with tests
5. Ensure no regressions

Please analyze this bug and implement an appropriate fix. Report back with:
- Root cause analysis
- Fix implementation
- Test results
"""

    @staticmethod
    def generate_review_task(bug: SelfHealingTask) -> str:
        """Generate task for reviewing code."""
        return f"""Review the following bug and suggest improvements:

## Bug Information
- Bug ID: {bug.bug_id}
- Type: {bug.bug_type}
- Message: {bug.message}

## Context
{bug.root_cause}

## Tasks
1. Review the buggy code
2. Identify patterns that caused the bug
3. Suggest preventive measures
4. Recommend code improvements to avoid similar issues
"""

    @staticmethod
    def generate_full_workflow_task(
        stats: dict[str, Any],
        recent_bugs: list[SelfHealingTask] | None = None,
    ) -> str:
        """Generate task for full self-healing workflow."""
        
        bugs_section = ""
        if recent_bugs:
            bugs_section = "\n## Recent Bugs Detected\n"
            for bug in recent_bugs:
                bugs_section += f"""
### {bug.bug_id}
- Type: {bug.bug_type}
- Message: {bug.message}
- Priority: {bug.priority}
"""

        return f"""# Self-Healing AI Agent Task

You are a self-healing AI agent. Your task is to:

## Current Statistics
- Bugs Detected: {stats.get('bugs_detected', 0)}
- Bugs Fixed: {stats.get('bugs_fixed', 0)}
- Success Rate: {stats.get('success_rate', 0)}%
- Total Runs: {stats.get('total_runs', 0)}
- Last Run: {stats.get('last_run', 'Never')}

{bugs_section}

## Workflow Steps
1. **Detect**: Scan for bugs in logs, test failures, exceptions
2. **Analyze**: Investigate root cause using code analysis
3. **Fix**: Generate and apply fixes with proper validation
4. **Verify**: Run tests to ensure fixes work
5. **Learn**: Update knowledge base with new patterns

## Instructions
1. Scan the codebase for potential bugs
2. Analyze any detected issues
3. Implement fixes for identified bugs
4. Run tests to verify fixes
5. Report findings and actions taken

Please execute the self-healing workflow and report results.
"""

    @staticmethod
    def generate_fix_only_task(bug: SelfHealingTask) -> str:
        """Generate focused fix task."""
        return f"""Fix this bug immediately:

## Bug Details
- ID: {bug.bug_id}
- Type: {bug.bug_type}
- Error: {bug.message}

## Location
- File: {bug.file_path or "Unknown"}
- Line: {bug.line_number or "Unknown"}

## Analysis
{bug.root_cause}

## Required Actions
1. Open the affected file
2. Implement the fix
3. Run tests
4. Commit the fix

Do not stop until the bug is fixed and verified.
"""

    @staticmethod
    def generate_improve_agent_task() -> str:
        """Generate task to improve the agent itself."""
        return """Improve the Self-Healing AI Agent:

## Current Capabilities
- Bug detection from logs, exceptions, test failures
- Root cause analysis using AST parsing
- Automatic fix generation
- Verification with tests
- Knowledge base for learning

## Enhancement Tasks

### 1. Improve Detection
- Add more error pattern detection
- Support for additional languages
- Better log parsing

### 2. Improve Analysis
- Better root cause identification
- More accurate fix suggestions
- Context-aware recommendations

### 3. Improve Fixes
- More fix strategies
- Better code generation
- Safety validation improvements

### 4. Improve Learning
- Better pattern recognition
- Improved knowledge base
- Faster retrieval

Please analyze the current implementation and suggest/implement improvements.
"""

    @staticmethod
    def generate_report_task(stats: dict[str, Any]) -> str:
        """Generate task for generating reports."""
        return f"""Generate a self-healing report:

## Statistics
- Bugs Detected: {stats.get('bugs_detected', 0)}
- Bugs Fixed: {stats.get('bugs_fixed', 0)}
- Success Rate: {stats.get('success_rate', 0)}%
- Total Runs: {stats.get('total_runs', 0)}

## Tasks
1. Compile the statistics
2. Generate release notes
3. Update CHANGELOG.md
4. Create a summary report

Please generate a comprehensive report with all findings and recommendations.
"""
