#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["aiohttp>=3.9.0"]
# ///
"""
Run any Apify actor by ID.

Generic actor runner that handles:
- Starting actor runs
- Polling for completion
- Fetching results

Usage:
    uv run run_actor.py --actor <actor_id> --input '{"key": "value"}' --output results.json
    uv run run_actor.py --actor vIGxjRrHqDTPuE6M4 --input '{"searchQuery": "ops manager"}'
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


APIFY_API_BASE = "https://api.apify.com/v2"


def load_env_file() -> None:
    """Load .env from multiple locations."""
    locations = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent.parent / ".env",
        Path.home() / "Coding" / "The Crucible" / ".env",
        Path.home() / "Coding" / "1. General Work" / "The Crucible" / ".env",
    ]

    for loc in locations:
        if loc.exists():
            with open(loc) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip().strip('"\''))
            break


def get_api_key() -> str:
    """Get Apify API key from environment."""
    load_env_file()
    key = os.environ.get("APIFY_API_KEY")
    if not key:
        print("Error: APIFY_API_KEY not found in environment", file=sys.stderr)
        print("Set it in your .env file or export it", file=sys.stderr)
        sys.exit(1)
    return key


async def run_actor(
    actor_id: str,
    input_params: dict,
    api_key: str,
    timeout_secs: int = 600,
    verbose: bool = False
) -> list[dict]:
    """
    Run an Apify actor and wait for results.

    Args:
        actor_id: The Apify actor ID
        input_params: Input parameters for the actor
        api_key: Apify API key
        timeout_secs: Maximum time to wait for completion
        verbose: Print progress updates

    Returns:
        List of result items from the actor's dataset
    """
    import aiohttp

    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        # Start the actor run
        run_url = f"{APIFY_API_BASE}/acts/{actor_id}/runs?token={api_key}"

        if verbose:
            print(f"Starting actor {actor_id}...", file=sys.stderr)
            print(f"Input: {json.dumps(input_params, indent=2)}", file=sys.stderr)

        async with session.post(run_url, headers=headers, json=input_params) as resp:
            if resp.status != 201:
                error_text = await resp.text()
                raise Exception(f"Failed to start actor: {resp.status} - {error_text}")

            run_data = await resp.json()
            run_id = run_data["data"]["id"]

            if verbose:
                print(f"Run started: {run_id}", file=sys.stderr)

        # Poll for completion
        status_url = f"{APIFY_API_BASE}/actor-runs/{run_id}?token={api_key}"
        elapsed = 0
        poll_interval = 5

        while elapsed < timeout_secs:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            async with session.get(status_url) as resp:
                status_data = await resp.json()
                status = status_data["data"]["status"]

                if verbose:
                    print(f"Status: {status} ({elapsed}s elapsed)", file=sys.stderr)

                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    raise Exception(f"Actor run failed with status: {status}")

        if elapsed >= timeout_secs:
            raise Exception(f"Actor run timed out after {timeout_secs}s")

        # Fetch results from dataset
        dataset_id = status_data["data"]["defaultDatasetId"]
        dataset_url = f"{APIFY_API_BASE}/datasets/{dataset_id}/items?token={api_key}&format=json"

        async with session.get(dataset_url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch results: {resp.status}")

            results = await resp.json()

            if verbose:
                print(f"Fetched {len(results)} results", file=sys.stderr)

            return results


async def main():
    parser = argparse.ArgumentParser(description="Run an Apify actor")
    parser.add_argument("--actor", "-a", required=True, help="Actor ID to run")
    parser.add_argument("--input", "-i", required=True, help="JSON input for the actor")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--timeout", "-t", type=int, default=600, help="Timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Parse input JSON
    try:
        input_params = json.loads(args.input)
    except json.JSONDecodeError as e:
        print(f"Error parsing input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key()

    try:
        results = await run_actor(
            actor_id=args.actor,
            input_params=input_params,
            api_key=api_key,
            timeout_secs=args.timeout,
            verbose=args.verbose
        )

        output_json = json.dumps(results, indent=2)

        if args.output:
            Path(args.output).write_text(output_json)
            print(f"Results saved to {args.output}", file=sys.stderr)
        else:
            print(output_json)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
