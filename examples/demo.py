#!/usr/bin/env python3
"""
Demo script untuk Self-Healing AI Agent.

Script ini mendemonstrasikan kemampuan self-healing agent dalam
mendeteksi dan memperbaiki bug secara otomatis.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from self_healing_agent import (
    SelfHealingOrchestrator,
    BugDetector,
    BugReport,
    BugType,
    BugSeverity,
)
from self_healing_agent.config import Config

console = Console()


def demo_exception_handling():
    """Demo: Process exception through self-healing."""
    console.print("\n[bold cyan]Demo 1: Exception Handling[/bold cyan]")

    orchestrator = SelfHealingOrchestrator()

    # Simulate various exceptions
    exceptions = [
        ("TypeError", TypeError("unsupported operand type(s) for +: 'str' and 'int'")),
        ("ValueError", ValueError("invalid literal for int() with base 10: 'abc'")),
        ("KeyError", KeyError("missing_key")),
    ]

    for name, exc in exceptions:
        console.print(f"\n[yellow]Testing {name}...[/yellow]")

        try:
try:
    Line 49: try:

except ValueError:
    # Handle validation error
    pass

except ValueError:
    # Handle validation error
    pass
console = Console()


def demo_exception_handling():
    """Demo: Process exception through self-healing."""
    console.print("\n[bold cyan]Demo 1: Exception Handling[/bold cyan]")

    orchestrator = SelfHealingOrchestrator()

    # Simulate various exceptions
    exceptions = [
        ("TypeError", TypeError("unsupported operand type(s) for +: 'str' and 'int'")),
        ("ValueError", ValueError("invalid literal for int() with base 10: 'abc'")),
        ("KeyError", KeyError("missing_key")),
    ]

    for name, exc in exceptions:
        console.print(f"\n[yellow]Testing {name}...[/yellow]")

        try:
            raise exc
        except Exception as e:
            result = orchestrator.process_exception(e)

            console.print(f"  Status: [{'green' if result.success else 'red'}]{result.task.status.value}[/]")
            console.print(f"  Bug ID: {result.task.bug_report.bug_id}")
            console.print(f"  Bug Type: {result.task.bug_report.bug_type.value}")
            console.print(f"  Message: {result.message}")


def demo_bug_detection():
    """Demo: Bug detection from various sources."""
    console.print("\n[bold cyan]Demo 2: Bug Detection[/bold cyan]")
    """Demo: Static analysis on buggy file."""
    console.print("\n[bold cyan]Demo 3: Static Analysis[/bold cyan]")

    detector = BugDetector()

    # Create a temporary buggy file
    buggy_file = Path(__file__).parent / "temp_buggy.py"
    buggy_file.write_text("""
def buggy_function():
    if True
        print("Missing colon")
    return

def another_bug():
    x = 1 +
    return x
""")

    bugs = detector.run_static_analysis(buggy_file)

    console.print(f"\n[yellow]Found {len(bugs)} syntax errors:[/yellow]")
    for bug in bugs:
        console.print(f"  - {bug.bug_type.value}: Line {bug.line_number}")

    # Cleanup
    buggy_file.unlink()


def demo_full_workflow():
    """Demo: Full self-healing workflow."""
    console.print("\n[bold cyan]Demo 4: Full Self-Healing Workflow[/bold cyan]")

    orchestrator = SelfHealingOrchestrator()

    # Create a test file with a bug
    test_file = Path(__file__).parent / "test_fix.py"
    test_file.write_text("""
def add_numbers(a, b):
    return a + b

result = add_numbers("hello", 123)
print(result)
""")

    console.print(f"\n[yellow]Testing file: {test_file}[/yellow]")

    # Run the file to get exception
    import subprocess
    result = subprocess.run(
        ["python", str(test_file)],
        capture_output=True,
        text=True,
    )

    console.print(f"  Original error: {result.stderr.strip()}")

    # Try to fix
    bugs = orchestrator.bug_detector.run_static_analysis(test_file)

    for bug in bugs:
        console.print(f"\n[yellow]Processing bug: {bug.bug_id}[/yellow]")
        fix_result = orchestrator.process_bug(bug)

        table = Table(title="Self-Healing Result")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", fix_result.task.status.value)
        table.add_row("Success", str(fix_result.success))
        table.add_row("Message", fix_result.message)

        if fix_result.task.analysis:
            table.add_row("Root Cause", fix_result.task.analysis.root_cause)
            table.add_row("Confidence", f"{fix_result.task.analysis.confidence:.0%}")

        if fix_result.task.fix:
            table.add_row("Fix Strategy", fix_result.task.fix.strategy)
            table.add_row("Fix Confidence", f"{fix_result.task.fix.confidence:.0%}")

        console.print(table)

    # Cleanup
    test_file.unlink()


def demo_statistics():
    """Demo: Show statistics."""
    console.print("\n[bold cyan]Demo 5: Statistics[/bold cyan]")

    orchestrator = SelfHealingOrchestrator()

    # Process some sample bugs
    sample_bugs = [
        BugReport(
            bug_id="BUG-DEMO-001",
            bug_type=BugType.TYPE_ERROR,
            severity=BugSeverity.MEDIUM,
            message="TypeError sample",
            file_path=None,
            line_number=None,
            stack_trace=None,
            source="demo",
        ),
        BugReport(
            bug_id="BUG-DEMO-002",
            bug_type=BugType.VALUE_ERROR,
            severity=BugSeverity.HIGH,
            message="ValueError sample",
            file_path=None,
            line_number=None,
            stack_trace=None,
            source="demo",
        ),
    ]

    for bug in sample_bugs:
        orchestrator.process_bug(bug)

    stats = orchestrator.get_statistics()

    table = Table(title="Self-Healing Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    for key, value in stats.items():
        if isinstance(value, dict):
            continue
        table.add_row(str(key), str(value))

    console.print(table)


def main():
    """Main demo function."""
    console.print(
        Panel.fit(
            "[bold cyan]Self-Healing AI Agent Demo[/bold cyan]\n\n"
            "Mendemonstrasikan kemampuan agent dalam:\n"
            "• Mendeteksi bug dari berbagai sumber\n"
            "• Menganalisis root cause\n"
            "• Generate dan verify fixes\n"
            "• Apply fixes secara otomatis",
            border_style="cyan",
        )
    )

    try:
        demo_exception_handling()
        demo_bug_detection()
        demo_static_analysis()
        demo_full_workflow()
        demo_statistics()

        console.print("\n[bold green]Demo completed successfully![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]Error during demo:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
