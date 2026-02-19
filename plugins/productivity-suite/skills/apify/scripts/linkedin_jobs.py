#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["aiohttp>=3.9.0"]
# ///
"""
LinkedIn Jobs Search using Apify.

Uses the fantastic-jobs/advanced-linkedin-job-search-api actor to find
companies posting specific job titles.

Perfect for Tier 1 EDP verification - finding companies actively hiring
for specific roles.

Usage:
    uv run linkedin_jobs.py --query "operations manager" --location "United States"
    uv run linkedin_jobs.py --query "director of operations" --company-size "11-50,51-200"
    uv run linkedin_jobs.py --query "head of ops" --industries "marketing,advertising" --output jobs.json
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


# Actor details
ACTOR_ID = "vIGxjRrHqDTPuE6M4"
ACTOR_NAME = "fantastic-jobs/advanced-linkedin-job-search-api"
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


async def search_linkedin_jobs(
    query: str,
    location: str | None = None,
    company_sizes: list[str] | None = None,
    industries: list[str] | None = None,
    posted_within: str = "month",
    experience_levels: list[str] | None = None,
    job_types: list[str] | None = None,
    max_results: int = 100,
    api_key: str = None,
    verbose: bool = False
) -> list[dict]:
    """
    Search LinkedIn for job postings.

    Args:
        query: Job title to search for
        location: Geographic location filter
        company_sizes: List of company size ranges (e.g., ["11-50", "51-200"])
        industries: List of industries to filter
        posted_within: Time filter (day, week, month)
        experience_levels: Experience levels (entry, associate, mid_senior, director, executive)
        job_types: Job types (full_time, part_time, contract, temporary, internship)
        max_results: Maximum results to return
        api_key: Apify API key
        verbose: Print progress

    Returns:
        List of job postings with company information
    """
    import aiohttp

    if not api_key:
        api_key = get_api_key()

    # Build input parameters using correct API schema
    # See: fantastic-jobs/advanced-linkedin-job-search-api
    input_params = {
        "titleSearch": [query] if isinstance(query, str) else query,
        "limit": max_results,
        "includeAi": True,  # Get AI-enhanced fields
    }

    if location:
        # locationSearch expects an array
        input_params["locationSearch"] = [location] if isinstance(location, str) else location

    if company_sizes:
        # Parse company sizes into min/max employees
        # Format: "21-50,51-200" -> find min and max
        all_sizes = []
        for size in company_sizes:
            if "-" in size:
                parts = size.split("-")
                all_sizes.extend([int(p) for p in parts if p.isdigit()])
            elif size.endswith("+"):
                all_sizes.append(int(size.replace("+", "")))
        if all_sizes:
            input_params["organizationEmployeesGte"] = min(all_sizes)
            input_params["organizationEmployeesLte"] = max(all_sizes) if max(all_sizes) != min(all_sizes) else max(all_sizes) * 10

    if industries:
        input_params["industryFilter"] = industries if isinstance(industries, list) else [industries]

    # Map posted_within to timeRange format
    # Valid values: "1h", "24h", "7d", "6m"
    date_mapping = {
        "day": "24h",
        "week": "7d",
        "month": "6m",  # No 30d option, use 6m for broader results
    }
    if posted_within in date_mapping:
        input_params["timeRange"] = date_mapping[posted_within]

    if experience_levels:
        input_params["seniorityFilter"] = experience_levels

    if job_types:
        input_params["EmploymentTypeFilter"] = job_types

    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        # Start the actor run
        run_url = f"{APIFY_API_BASE}/acts/{ACTOR_ID}/runs?token={api_key}"

        if verbose:
            print(f"Searching LinkedIn Jobs for: {query}", file=sys.stderr)
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
        timeout_secs = 600

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

        # Fetch results
        dataset_id = status_data["data"]["defaultDatasetId"]
        dataset_url = f"{APIFY_API_BASE}/datasets/{dataset_id}/items?token={api_key}&format=json"

        async with session.get(dataset_url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch results: {resp.status}")

            results = await resp.json()

            if verbose:
                print(f"Found {len(results)} job postings", file=sys.stderr)

            return results


def extract_companies(job_results: list[dict]) -> list[dict]:
    """
    Extract unique companies from job results.

    Returns deduplicated list of companies that are actively hiring.
    Uses field names from fantastic-jobs/advanced-linkedin-job-search-api.
    """
    companies = {}

    for job in job_results:
        # Primary field is 'organization' in this API
        company_name = job.get("organization", "").strip()

        if not company_name:
            continue

        if company_name not in companies:
            companies[company_name] = {
                "company_name": company_name,
                "company_url": job.get("organization_url", ""),
                "company_linkedin": job.get("linkedin_org_url", ""),
                "industry": job.get("linkedin_org_industry", ""),
                "company_size": job.get("linkedin_org_size", ""),
                "employee_count": job.get("linkedin_org_employees", ""),
                "location": job.get("linkedin_org_headquarters", ""),
                "description": job.get("linkedin_org_description", "")[:200] if job.get("linkedin_org_description") else "",
                "job_titles_hiring": [],
                "job_descriptions": [],  # Store job descriptions for PVP personalization
                "job_count": 0,
            }

        job_title = job.get("title", "")
        job_description = job.get("description_text", "")[:500] if job.get("description_text") else ""

        if job_title:
            companies[company_name]["job_titles_hiring"].append(job_title)
        if job_description:
            companies[company_name]["job_descriptions"].append(job_description)
        companies[company_name]["job_count"] += 1

    # Convert to list and dedupe job titles
    result = []
    for company in companies.values():
        company["job_titles_hiring"] = list(set(company["job_titles_hiring"]))
        # Keep only first 3 job descriptions to avoid bloat
        company["job_descriptions"] = company["job_descriptions"][:3]
        result.append(company)

    return result


async def main():
    parser = argparse.ArgumentParser(
        description="Search LinkedIn Jobs for companies hiring specific roles"
    )
    parser.add_argument("--query", "-q", required=True, help="Job title to search")
    parser.add_argument("--location", "-l", help="Location filter")
    parser.add_argument(
        "--company-size", "-s",
        help="Company sizes (comma-separated: 1-10,11-50,51-200,201-500,501-1000,1001+)"
    )
    parser.add_argument(
        "--industries", "-i",
        help="Industries to filter (comma-separated)"
    )
    parser.add_argument(
        "--posted-within", "-p",
        choices=["day", "week", "month"],
        default="month",
        help="How recent (default: month)"
    )
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=100,
        help="Maximum results (default: 100)"
    )
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument(
        "--companies-only", "-c",
        action="store_true",
        help="Output unique companies only (deduplicated)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Parse comma-separated arguments
    company_sizes = args.company_size.split(",") if args.company_size else None
    industries = args.industries.split(",") if args.industries else None

    try:
        results = await search_linkedin_jobs(
            query=args.query,
            location=args.location,
            company_sizes=company_sizes,
            industries=industries,
            posted_within=args.posted_within,
            max_results=args.max_results,
            verbose=args.verbose
        )

        # Extract companies if requested
        if args.companies_only:
            output_data = extract_companies(results)
            if args.verbose:
                print(f"Extracted {len(output_data)} unique companies", file=sys.stderr)
                if output_data:
                    print(f"Sample companies:", file=sys.stderr)
                    for company in output_data[:3]:
                        print(f"  - {company['company_name']} ({company['job_count']} jobs)", file=sys.stderr)

            # Warning if no companies extracted
            if len(results) > 0 and len(output_data) == 0:
                print("⚠️ WARNING: Jobs found but no companies extracted!", file=sys.stderr)
                print("   This may indicate a field mapping issue.", file=sys.stderr)
                print("   Raw job sample fields:", file=sys.stderr)
                if results:
                    print(f"   {list(results[0].keys())}", file=sys.stderr)
        else:
            output_data = results

        output_json = json.dumps(output_data, indent=2)

        if args.output:
            Path(args.output).write_text(output_json)
            print(f"Results saved to {args.output}", file=sys.stderr)
            print(f"Total: {len(output_data)} {'companies' if args.companies_only else 'jobs'}")
        else:
            print(output_json)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
