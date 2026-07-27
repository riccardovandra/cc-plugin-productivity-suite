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
    uv run run_actor.py --actor xquik~x-tweet-scraper --input-file input.json \
        --max-total-charge-usd 1
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


APIFY_API_BASE = "https://api.apify.com/v2"
XQUIK_ACTORS = {
    "xquik/x-tweet-scraper",
    "xquik~x-tweet-scraper",
    "wAusCMrm284Voaw86",
    "xquik/x-follower-scraper",
    "xquik~x-follower-scraper",
    "AaT0BcKU5GQh97wdt",
}


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
    key = os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_API_KEY")
    if not key:
        print("Error: APIFY_TOKEN not found in environment", file=sys.stderr)
        print("Set APIFY_TOKEN in your .env file or export it", file=sys.stderr)
        sys.exit(1)
    return key


def positive_float(value: str) -> float:
    """Parse a positive numeric command-line value."""
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def normalize_actor_id(actor_id: str) -> str:
    """Convert a Store slug to the Actor API's tilde-separated form."""
    return actor_id.replace("/", "~", 1)


async def run_actor(
    actor_id: str,
    input_params: dict,
    api_key: str,
    timeout_secs: int = 600,
    max_total_charge_usd: float | None = None,
    verbose: bool = False,
) -> list[dict]:
    """
    Run an Apify actor and wait for results.

    Args:
        actor_id: The Apify actor ID
        input_params: Input parameters for the actor
        api_key: Apify API key
        timeout_secs: Maximum time to wait for completion
        max_total_charge_usd: Approved hard charge cap for pay-per-event runs
        verbose: Print progress updates

    Returns:
        List of result items from the actor's dataset
    """
    import aiohttp

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    run_params = {}
    if max_total_charge_usd is not None:
        run_params["maxTotalChargeUsd"] = max_total_charge_usd

    async with aiohttp.ClientSession() as session:
        # Start the actor run
        api_actor_id = normalize_actor_id(actor_id)
        run_url = f"{APIFY_API_BASE}/actors/{api_actor_id}/runs"

        if verbose:
            print(f"Starting actor {actor_id}...", file=sys.stderr)
            print(f"Input: {json.dumps(input_params, indent=2)}", file=sys.stderr)

        async with session.post(
            run_url,
            headers=headers,
            params=run_params,
            json=input_params,
        ) as resp:
            if resp.status != 201:
                error_text = await resp.text()
                raise Exception(f"Failed to start actor: {resp.status} - {error_text}")

            run_data = await resp.json()
            run_id = run_data["data"]["id"]

            if verbose:
                print(f"Run started: {run_id}", file=sys.stderr)

        # Poll for completion
        status_url = f"{APIFY_API_BASE}/actor-runs/{run_id}"
        elapsed = 0
        poll_interval = 5

        while elapsed < timeout_secs:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            async with session.get(status_url, headers=headers) as resp:
                status_data = await resp.json()
                status = status_data["data"]["status"]

                if verbose:
                    print(f"Status: {status} ({elapsed}s elapsed)", file=sys.stderr)

                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    raise Exception(f"Actor run failed with status: {status}")
        else:
            raise Exception(f"Actor run timed out after {timeout_secs}s")

        # Fetch results from dataset
        dataset_id = status_data["data"]["defaultDatasetId"]
        dataset_url = f"{APIFY_API_BASE}/datasets/{dataset_id}/items"

        async with session.get(
            dataset_url,
            headers=headers,
            params={"format": "json"},
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch results: {resp.status}")

            results = await resp.json()

            if verbose:
                print(f"Fetched {len(results)} results", file=sys.stderr)

            return results


async def main():
    parser = argparse.ArgumentParser(description="Run an Apify actor")
    parser.add_argument("--actor", "-a", required=True, help="Actor ID to run")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", "-i", help="JSON input for the actor")
    input_group.add_argument("--input-file", type=Path, help="Path to an approved JSON input file")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--timeout", "-t", type=int, default=600, help="Timeout in seconds")
    parser.add_argument(
        "--max-total-charge-usd",
        type=positive_float,
        help="Approved hard charge cap for pay-per-event runs",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        if args.input_file:
            input_params = json.loads(args.input_file.read_text(encoding="utf-8"))
        else:
            input_params = json.loads(args.input)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error parsing input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(input_params, dict):
        print("Error: Actor input must be a JSON object", file=sys.stderr)
        sys.exit(1)

    if args.actor in XQUIK_ACTORS:
        if not args.input_file:
            print("Error: Xquik runs require --input-file", file=sys.stderr)
            sys.exit(1)
        if args.max_total_charge_usd is None:
            print(
                "Error: Xquik runs require --max-total-charge-usd",
                file=sys.stderr,
            )
            sys.exit(1)

    api_key = get_api_key()

    try:
        results = await run_actor(
            actor_id=args.actor,
            input_params=input_params,
            api_key=api_key,
            timeout_secs=args.timeout,
            max_total_charge_usd=args.max_total_charge_usd,
            verbose=args.verbose,
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
