#!/usr/bin/env python3
"""
Script to trigger OpenHands Cloud conversations for self-healing tasks.

Usage:
    python scripts/trigger_openhands.py --task analyze
    python scripts/trigger_openhands.py --task full-workflow
    python scripts/trigger_openhands.py --task improve
    python scripts/trigger_openhands.py --list
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openhands import OpenHandsClient, OpenHandsConfig, TaskGenerator, SelfHealingTask


def main():
    parser = argparse.ArgumentParser(description="Trigger OpenHands Cloud for Self-Healing")
    
    parser.add_argument(
        "--task",
        choices=["analyze", "fix", "review", "full-workflow", "improve", "report"],
        default="full-workflow",
        help="Type of task to run",
    )
    
    parser.add_argument(
        "--repo",
        default="antono4/Self-Healing-AI-Agent",
        help="GitHub repository (owner/repo)",
    )
    
    parser.add_argument(
        "--branch",
        default="master",
        help="Branch to work on",
    )
    
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for conversation to complete",
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List recent conversations",
    )
    
    parser.add_argument(
        "--bug-id",
        help="Bug ID for analyze/fix tasks",
    )
    
    parser.add_argument(
        "--bug-type",
        default="TYPE_ERROR",
        help="Type of bug",
    )
    
    parser.add_argument(
        "--bug-message",
        default="Sample bug message",
        help="Bug error message",
    )
    
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENHANDS_CLOUD_API_KEY"),
        help="OpenHands API key (or set OPENHANDS_CLOUD_API_KEY)",
    )
    
    args = parser.parse_args()

    # Configure client
    config = OpenHandsConfig(
        api_key=args.api_key or "",
        repository=args.repo,
        branch=args.branch,
        title_prefix="[Self-Healing]",
    )
    
    client = OpenHandsClient(config)

    # Check API key
    if not config.api_key:
        print("❌ Error: OPENHANDS_CLOUD_API_KEY not set")
        print("\nTo get an API key:")
        print("1. Go to https://app.all-hands.dev")
        print("2. Sign in / Sign up")
        print("3. Go to Settings > API Keys")
        print("4. Create a new API key")
        print("5. Set it as environment variable:")
        print("   export OPENHANDS_CLOUD_API_KEY='your-key'")
        return 1

    # List mode
    if args.list:
        print("📋 Recent Conversations:\n")
        conversations = client.list_recent_conversations(limit=10)
        
        if not conversations:
            print("No conversations found.")
        else:
            for conv in conversations:
                print(f"  • {conv.get('title', 'Untitled')}")
                print(f"    Status: {conv.get('execution_status')}")
                print(f"    ID: {conv.get('app_conversation_id')}")
                print(f"    URL: {config.base_url}/conversations/{conv.get('app_conversation_id')}")
                print()
        return 0

    # Generate task based on type
    if args.task == "analyze":
        bug = SelfHealingTask(
            bug_id=args.bug_id or "BUG-NEW",
            bug_type=args.bug_type,
            message=args.bug_message,
            file_path=None,
            line_number=None,
            root_cause="To be analyzed",
            suggested_fix="To be determined",
        )
        task_message = TaskGenerator.generate_analyze_task(bug)
        title = f"Analyze Bug {args.bug_id or 'NEW'}"

    elif args.task == "fix":
        bug = SelfHealingTask(
            bug_id=args.bug_id or "BUG-NEW",
            bug_type=args.bug_type,
            message=args.bug_message,
            file_path=None,
            line_number=None,
            root_cause="To be fixed",
            suggested_fix="To be implemented",
        )
        task_message = TaskGenerator.generate_fix_only_task(bug)
        title = f"Fix Bug {args.bug_id or 'NEW'}"

    elif args.task == "review":
        bug = SelfHealingTask(
            bug_id=args.bug_id or "BUG-NEW",
            bug_type=args.bug_type,
            message=args.bug_message,
            file_path=None,
            line_number=None,
            root_cause="To be reviewed",
            suggested_fix="Suggestions to be provided",
        )
        task_message = TaskGenerator.generate_review_task(bug)
        title = f"Review Bug {args.bug_id or 'NEW'}"

    elif args.task == "full-workflow":
        task_message = TaskGenerator.generate_full_workflow_task({
            "bugs_detected": 0,
            "bugs_fixed": 0,
            "success_rate": 0,
            "total_runs": 0,
            "last_run": "Now",
        })
        title = "Full Self-Healing Workflow"

    elif args.task == "improve":
        task_message = TaskGenerator.generate_improve_agent_task()
        title = "Improve Self-Healing Agent"

    elif args.task == "report":
        task_message = TaskGenerator.generate_report_task({
            "bugs_detected": 0,
            "bugs_fixed": 0,
            "success_rate": 0,
            "total_runs": 0,
        })
        title = "Generate Self-Healing Report"

    else:
        print(f"❌ Unknown task: {args.task}")
        return 1

    # Start conversation
    print(f"🚀 Starting OpenHands conversation: {title}\n")
    
    result = client.run_self_healing_task(
        task_description=task_message,
        wait_for_completion=args.wait,
    )

    if result.get("success"):
        print("✅ Conversation started successfully!")
        print(f"\n📎 Conversation URL:")
        print(f"   {result.get('conversation_url')}")
        
        if args.wait:
            print(f"\n📊 Status: {result.get('status')}")
    else:
        print(f"❌ Failed to start conversation: {result.get('error')}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
