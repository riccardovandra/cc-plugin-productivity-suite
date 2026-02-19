#!/usr/bin/env python3
"""
Web Fallback Fetch Script

Fetches web content using Jina Reader API as an alternative to WebFetch.
Returns clean markdown content suitable for LLM consumption.

Usage:
    python fetch.py "https://example.com/page"
    python fetch.py "https://example.com/page" --timeout 60
"""

import argparse
import sys
import urllib.request
import urllib.error


def fetch_url(url: str, timeout: int = 30) -> str:
    """
    Fetch URL content via Jina Reader API.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Clean markdown content from the page
    """
    jina_url = f"https://r.jina.ai/{url}"

    req = urllib.request.Request(
        jina_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; WebFallback/1.0)",
            "Accept": "text/plain, text/markdown"
        }
    )

    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch web content using Jina Reader API"
    )
    parser.add_argument(
        "url",
        help="URL to fetch"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )

    args = parser.parse_args()

    try:
        content = fetch_url(args.url, args.timeout)
        print(content)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print(f"Request timed out after {args.timeout} seconds", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
