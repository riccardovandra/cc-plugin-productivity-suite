#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["aiohttp>=3.9.0"]
# ///
"""
Search Apify Store for actors.

Finds actors matching a research need and filters by pricing model.

Usage:
    uv run search_store.py --query "linkedin job postings"
    uv run search_store.py --query "web scraper" --pricing pay_per_result
    uv run search_store.py --query "youtube" --limit 10
"""

import argparse
import asyncio
import json
import sys


APIFY_STORE_API = "https://api.apify.com/v2/store"


async def search_actors(
    query: str,
    limit: int = 20,
    pricing_filter: str | None = None,
    verbose: bool = False
) -> list[dict]:
    """
    Search Apify store for actors.

    Args:
        query: Search query
        limit: Maximum results to return
        pricing_filter: Filter by pricing type (pay_per_result, pay_per_event, etc.)
        verbose: Print verbose output

    Returns:
        List of matching actors with their details
    """
    import aiohttp

    params = {
        "search": query,
        "limit": limit,
        "offset": 0,
    }

    if verbose:
        print(f"Searching Apify store for: {query}", file=sys.stderr)

    async with aiohttp.ClientSession() as session:
        async with session.get(APIFY_STORE_API, params=params) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Store search failed: {resp.status} - {error}")

            data = await resp.json()
            actors = data.get("data", {}).get("items", [])

    # Process and filter results
    results = []
    for actor in actors:
        pricing_model = actor.get("pricingModel", "UNKNOWN")

        # Filter by pricing if specified
        if pricing_filter:
            pricing_lower = pricing_model.lower().replace("_", " ")
            filter_lower = pricing_filter.lower().replace("_", " ")
            if filter_lower not in pricing_lower and pricing_lower != filter_lower:
                continue

        result = {
            "name": actor.get("name", ""),
            "title": actor.get("title", ""),
            "username": actor.get("username", ""),
            "actor_id": actor.get("id", ""),
            "description": actor.get("description", "")[:200] + "..." if actor.get("description", "") and len(actor.get("description", "")) > 200 else actor.get("description", ""),
            "pricing_model": pricing_model,
            "stats": {
                "runs": actor.get("stats", {}).get("totalRuns", 0),
                "users": actor.get("stats", {}).get("totalUsers", 0),
            },
            "url": f"https://apify.com/{actor.get('username', '')}/{actor.get('name', '')}",
        }
        results.append(result)

    # Sort by usage (most popular first)
    results.sort(key=lambda x: x["stats"]["runs"], reverse=True)

    return results


def format_results(actors: list[dict], detailed: bool = False) -> str:
    """Format search results for display."""
    if not actors:
        return "No actors found matching your query."

    lines = []
    lines.append(f"Found {len(actors)} actors:\n")

    for i, actor in enumerate(actors, 1):
        full_name = f"{actor['username']}/{actor['name']}"
        pricing = actor['pricing_model']
        runs = actor['stats']['runs']

        lines.append(f"{i}. **{actor['title']}**")
        lines.append(f"   Actor: `{full_name}`")
        lines.append(f"   ID: `{actor['actor_id']}`")
        lines.append(f"   Pricing: {pricing}")
        lines.append(f"   Usage: {runs:,} runs")

        if detailed and actor['description']:
            lines.append(f"   Description: {actor['description']}")

        lines.append(f"   URL: {actor['url']}")
        lines.append("")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="Search Apify Store for actors")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Max results")
    parser.add_argument(
        "--pricing", "-p",
        choices=["pay_per_result", "pay_per_event", "flat_rate", "free"],
        help="Filter by pricing model"
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--detailed", "-d", action="store_true", help="Show descriptions")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        actors = await search_actors(
            query=args.query,
            limit=args.limit,
            pricing_filter=args.pricing,
            verbose=args.verbose
        )

        if args.json:
            print(json.dumps(actors, indent=2))
        else:
            print(format_results(actors, detailed=args.detailed))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
