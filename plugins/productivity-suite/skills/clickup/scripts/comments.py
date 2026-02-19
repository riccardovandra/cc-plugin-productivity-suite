#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28.0", "python-dotenv>=1.0.0"]
# ///
"""
Read comments on a ClickUp task.

Usage:
    python comments.py abc123          # All comments
    python comments.py abc123 --limit 10
    python comments.py --search "homepage"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from clickup_client import ClickUpClient


def format_comment(comment: dict) -> str:
    """Format a comment for display."""
    return f"**{comment['user']}** ({comment['date']}):\n{comment['text']}"


def main():
    parser = argparse.ArgumentParser(description="Read ClickUp task comments")
    parser.add_argument("task_id", nargs="?", help="Task ID")
    parser.add_argument("--search", help="Search for task by name")
    parser.add_argument("--limit", type=int, default=20, help="Max comments (default: 20)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.task_id and not args.search:
        parser.error("Must provide task_id or --search")

    try:
        client = ClickUpClient()
        task_id = args.task_id

        if args.search and not task_id:
            tasks = client.search_tasks(args.search)

            if not tasks:
                print(f"No tasks found matching '{args.search}'")
                sys.exit(1)

            if len(tasks) > 1:
                print(f"Multiple tasks found. Use task ID directly.")
                for t in tasks[:5]:
                    summary = client.extract_task_summary(t)
                    print(f"  - {summary['name']} (ID: {summary['id']})")
                sys.exit(1)

            task_id = tasks[0]["id"]

        # Get task info for context
        task = client.get_task(task_id)
        if not task:
            print(f"Task '{task_id}' not found", file=sys.stderr)
            sys.exit(1)

        task_summary = client.extract_task_summary(task)

        # Get comments
        comments = client.get_task_comments(task_id)
        comments = comments[:args.limit]

        if not comments:
            print(f"No comments on task: {task_summary['name']}")
            return

        if args.json:
            formatted = [client.format_comment(c) for c in comments]
            print(json.dumps(formatted, indent=2))
        else:
            print(f"Comments on **{task_summary['name']}** ({len(comments)}):\n")
            for comment in comments:
                formatted = client.format_comment(comment)
                print(format_comment(formatted))
                print("-" * 40)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
