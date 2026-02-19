#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["aiohttp>=3.9.0"]
# ///
"""
Fireflies.ai Transcript Extraction
Fetches meeting transcripts via GraphQL API.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import aiohttp
except ImportError:
    print("Error: aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)


# Configuration
API_ENDPOINT = "https://api.fireflies.ai/graphql"


def load_env_file(filepath: str = ".env") -> None:
    """Load environment variables from .env file."""
    env_path = Path(filepath)
    if not env_path.exists():
        # Try from project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_path = project_root / ".env"

    if not env_path.exists():
        return

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value


def get_api_key() -> str:
    """Get Fireflies API key from environment."""
    load_env_file()
    api_key = os.getenv("FIREFLIES_API_KEY")
    if not api_key:
        print("Error: FIREFLIES_API_KEY not set in environment or .env file")
        sys.exit(1)
    return api_key


# GraphQL Queries
LIST_TRANSCRIPTS_QUERY = """
query Transcripts($title: String, $fromDate: DateTime, $toDate: DateTime, $limit: Int, $skip: Int, $participants: [String!]) {
    transcripts(
        title: $title
        fromDate: $fromDate
        toDate: $toDate
        limit: $limit
        skip: $skip
        participants: $participants
    ) {
        id
        title
        dateString
        duration
        participants
        organizer_email
    }
}
"""

GET_TRANSCRIPT_QUERY = """
query Transcript($transcriptId: String!) {
    transcript(id: $transcriptId) {
        id
        title
        dateString
        duration
        participants
        organizer_email
        transcript_url
        sentences {
            speaker_name
            text
            start_time
            end_time
        }
        summary {
            overview
            action_items
        }
    }
}
"""


async def graphql_request(query: str, variables: dict = None) -> dict:
    """Execute a GraphQL request against Fireflies API."""
    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    async with aiohttp.ClientSession() as session:
        async with session.post(API_ENDPOINT, headers=headers, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"API error {response.status}: {text}")

            result = await response.json()
            if "errors" in result:
                raise Exception(f"GraphQL error: {result['errors']}")

            return result.get("data", {})


async def list_transcripts(
    title: str = None,
    participant: str = None,
    from_date: str = None,
    to_date: str = None,
    limit: int = 20,
    skip: int = 0
) -> list[dict]:
    """Fetch list of transcripts with optional filters."""
    variables = {"limit": limit, "skip": skip}

    if title:
        variables["title"] = title
    if participant:
        variables["participants"] = [participant]
    if from_date:
        variables["fromDate"] = from_date
    if to_date:
        variables["toDate"] = to_date

    data = await graphql_request(LIST_TRANSCRIPTS_QUERY, variables)
    return data.get("transcripts", [])


async def get_transcript(transcript_id: str) -> dict:
    """Fetch a single transcript by ID."""
    variables = {"transcriptId": transcript_id}
    data = await graphql_request(GET_TRANSCRIPT_QUERY, variables)
    return data.get("transcript", {})


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string."""
    if not seconds:
        return "Unknown"
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining_mins = minutes % 60
    return f"{hours}h {remaining_mins}m"


def format_transcript_list(transcripts: list[dict]) -> str:
    """Format transcript list as a table."""
    if not transcripts:
        return "No transcripts found."

    lines = ["| # | Title | Date | Duration | Participants |"]
    lines.append("|---|-------|------|----------|--------------|")

    for i, t in enumerate(transcripts, 1):
        title = t.get("title", "Untitled")[:40]
        date = t.get("dateString", "Unknown")[:10]
        duration = format_duration(t.get("duration"))
        participants = ", ".join(t.get("participants", [])[:3])
        if len(t.get("participants", [])) > 3:
            participants += "..."
        lines.append(f"| {i} | {title} | {date} | {duration} | {participants} |")

    return "\n".join(lines)


def format_transcript_text(transcript: dict) -> str:
    """Format transcript data as readable text."""
    lines = []

    # Header
    lines.append(f"# {transcript.get('title', 'Untitled')}")
    lines.append("")
    lines.append(f"**Date:** {transcript.get('dateString', 'Unknown')}")
    lines.append(f"**Duration:** {format_duration(transcript.get('duration'))}")
    lines.append(f"**Participants:** {', '.join(transcript.get('participants', []))}")
    if transcript.get("transcript_url"):
        lines.append(f"**Fireflies URL:** {transcript.get('transcript_url')}")
    lines.append("")

    # Summary (if available)
    summary = transcript.get("summary", {})
    if summary.get("overview"):
        lines.append("---")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(summary["overview"])
        lines.append("")

    if summary.get("action_items"):
        lines.append("## Action Items")
        lines.append("")
        for item in summary["action_items"]:
            lines.append(f"- {item}")
        lines.append("")

    # Full transcript
    sentences = transcript.get("sentences", [])
    if sentences:
        lines.append("---")
        lines.append("")
        lines.append("## Full Transcript")
        lines.append("")

        current_speaker = None
        for sentence in sentences:
            speaker = sentence.get("speaker_name", "Unknown")
            text = sentence.get("text", "")

            if speaker != current_speaker:
                if current_speaker is not None:
                    lines.append("")
                lines.append(f"**{speaker}:** {text}")
                current_speaker = speaker
            else:
                lines[-1] += f" {text}"

    return "\n".join(lines)


def save_transcript(transcript: dict, output_path: str) -> None:
    """Save transcript to markdown file."""
    content = format_transcript_text(transcript)

    # Ensure directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Saved to: {output_path}")


async def cmd_list(args):
    """Handle list command."""
    transcripts = await list_transcripts(
        title=args.title,
        participant=args.participant,
        from_date=args.from_date,
        to_date=args.to_date,
        limit=args.limit
    )

    if args.json:
        print(json.dumps(transcripts, indent=2))
    else:
        print(format_transcript_list(transcripts))
        print(f"\nTotal: {len(transcripts)} transcript(s)")

        # Print IDs for easy reference
        if transcripts:
            print("\nTranscript IDs:")
            for i, t in enumerate(transcripts, 1):
                print(f"  {i}. {t.get('id')}")


async def cmd_get(args):
    """Handle get command."""
    transcript = await get_transcript(args.transcript_id)

    if not transcript:
        print(f"Transcript not found: {args.transcript_id}")
        return

    if args.json:
        print(json.dumps(transcript, indent=2))
    elif args.output:
        save_transcript(transcript, args.output)
    else:
        print(format_transcript_text(transcript))


def main():
    parser = argparse.ArgumentParser(description="Fireflies.ai Transcript Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    list_parser = subparsers.add_parser("list", help="List transcripts")
    list_parser.add_argument("--title", "-t", help="Search by title")
    list_parser.add_argument("--participant", "-p", help="Filter by participant name/email")
    list_parser.add_argument("--from-date", "-f", help="From date (ISO format: 2024-01-01)")
    list_parser.add_argument("--to-date", "-T", help="To date (ISO format: 2024-12-31)")
    list_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results (default: 20)")
    list_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get a specific transcript")
    get_parser.add_argument("transcript_id", help="Transcript ID")
    get_parser.add_argument("--output", "-o", help="Save to file path")
    get_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.command == "list":
        asyncio.run(cmd_list(args))
    elif args.command == "get":
        asyncio.run(cmd_get(args))


if __name__ == "__main__":
    main()
