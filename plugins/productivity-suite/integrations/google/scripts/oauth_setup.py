#!/usr/bin/env python3
"""
Google OAuth Setup CLI

One-time setup for Google OAuth authentication.
Run this once to unlock Gmail, Google Drive, Google Sheets, and Google Docs.

Usage:
    uv run oauth_setup.py                   # Initial setup
    uv run oauth_setup.py --status          # Check current status
    uv run oauth_setup.py --refresh         # Re-authenticate
    uv run oauth_setup.py --add-scope drive # Add Drive access
"""

import argparse
import sys
from pathlib import Path

# Import from local module
from google_auth import (
    get_credentials,
    get_authorized_scopes,
    get_token_file,
    resolve_scopes,
    CLIENT_SECRETS_FILE,
    TOKEN_FILE,
    SCOPE_ALIASES
)


def show_status(profile: str = None):
    """Display current authentication status."""
    print("Google OAuth Status")
    print("=" * 50)

    # Check client secrets
    if CLIENT_SECRETS_FILE.exists():
        print(f"Client secrets: Found")
    else:
        print(f"Client secrets: NOT FOUND")
        print(f"  Expected at: {CLIENT_SECRETS_FILE}")
        print(f"  See modules/SETUP.md for instructions")
        return

    # Show specific profile or default
    profiles_to_show = [profile] if profile else ['default']

    for p in profiles_to_show:
        token_file = get_token_file(p)
        print(f"\nProfile '{p}':")
        if token_file.exists():
            print(f"  Token file: Found")
            scopes = get_authorized_scopes(p)
            if scopes:
                print(f"  Authorized scopes ({len(scopes)}):")
                for scope in sorted(scopes):
                    alias = next((k for k, v in SCOPE_ALIASES.items() if v == scope), None)
                    if alias:
                        print(f"    - {alias}")
                    else:
                        print(f"    - {scope}")
            else:
                print("  No scopes in token (may be corrupted)")
        else:
            print(f"  Token file: NOT FOUND")

    print()


def show_available_scopes():
    """Display available scope aliases."""
    print("\nAvailable scope aliases:")
    print("-" * 40)

    categories = {
        'Gmail': ['gmail.readonly', 'gmail.modify', 'gmail.send', 'gmail.compose'],
        'Calendar': ['calendar', 'calendar.readonly', 'calendar.events', 'calendar.events.readonly'],
        'Drive': ['drive', 'drive.readonly', 'drive.file'],
        'Sheets': ['spreadsheets', 'spreadsheets.readonly'],
        'Docs': ['documents', 'documents.readonly'],
    }

    for category, scopes in categories.items():
        print(f"\n{category}:")
        for scope in scopes:
            print(f"  {scope}")


def initial_setup(scopes: list[str] = None, profile: str = 'default'):
    """Run initial OAuth setup."""
    if not CLIENT_SECRETS_FILE.exists():
        print(f"Error: Client secrets not found at {CLIENT_SECRETS_FILE}")
        print()
        print("To set up:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a project and enable needed APIs")
        print("3. Create OAuth 2.0 credentials (Desktop app)")
        print("4. Download JSON and save as:")
        print(f"   {CLIENT_SECRETS_FILE}")
        print()
        print("See modules/SETUP.md for detailed instructions")
        sys.exit(1)

    # Default scopes for initial setup
    if scopes is None:
        scopes = ['gmail.readonly', 'gmail.modify', 'drive', 'spreadsheets', 'documents']
        print(f"Setting up Google OAuth with default scopes (Gmail, Drive, Sheets, Docs)")
        print("You can add more scopes later with --add-scope")

    print()
    print(f"Profile: {profile}")
    print(f"Requesting authorization for: {scopes}")
    print()
    print("*** Log in with the correct Google account for this profile ***")

    try:
        credentials = get_credentials(scopes, interactive=True, profile=profile)
        print()
        print("Setup complete!")
        print()
        show_status(profile)
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)


def add_scopes(new_scopes: list[str], profile: str = 'default'):
    """Add additional scopes to existing authorization."""
    existing = get_authorized_scopes(profile)

    if not existing:
        print(f"No existing authorization for profile '{profile}'. Running initial setup...")
        initial_setup(new_scopes, profile)
        return

    # Resolve new scopes
    resolved_new = resolve_scopes(new_scopes)

    # Check if already authorized
    already_authorized = set(resolved_new) & set(existing)
    if already_authorized:
        print(f"Already authorized: {already_authorized}")

    need_auth = set(resolved_new) - set(existing)
    if not need_auth:
        print("All requested scopes are already authorized!")
        return

    print(f"Adding scopes: {need_auth}")

    # Get credentials with combined scopes (triggers re-auth)
    all_scopes = list(set(existing) | set(resolved_new))

    # Convert back to aliases for cleaner output
    aliases = [next((k for k, v in SCOPE_ALIASES.items() if v == s), s) for s in all_scopes]

    try:
        credentials = get_credentials(aliases, interactive=True, profile=profile)
        print()
        print("Scopes added successfully!")
        show_status(profile)
    except Exception as e:
        print(f"Failed to add scopes: {e}")
        sys.exit(1)


def refresh_auth(profile: str = 'default'):
    """Force re-authentication."""
    token_file = get_token_file(profile)
    if token_file.exists():
        token_file.unlink()
        print(f"Removed existing token for profile '{profile}'.")

    existing_scopes = get_authorized_scopes(profile)
    scopes = existing_scopes if existing_scopes else ['gmail.readonly', 'gmail.modify', 'drive', 'spreadsheets', 'documents']

    # Convert to aliases
    aliases = [next((k for k, v in SCOPE_ALIASES.items() if v == s), s) for s in scopes]

    print("Re-authenticating...")
    initial_setup(aliases, profile)


def revoke_credentials(profile: str = 'default'):
    """Remove stored credentials."""
    token_file = get_token_file(profile)
    if token_file.exists():
        token_file.unlink()
        print(f"Removed stored credentials for profile '{profile}'.")
        print()
        print("Note: To fully revoke access, visit:")
        print("  https://myaccount.google.com/permissions")
    else:
        print(f"No stored credentials found for profile '{profile}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Google OAuth setup — unlocks Gmail, Drive, Sheets, and Docs in one go",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run oauth_setup.py                              # Initial setup (opens browser)
  uv run oauth_setup.py --status                     # Check current status
  uv run oauth_setup.py --refresh                    # Re-authenticate
  uv run oauth_setup.py --add-scope drive.file       # Add an extra scope
"""
    )

    parser.add_argument(
        '--profile', '-p',
        default='default',
        help='Account profile to use (default)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current authentication status'
    )
    parser.add_argument(
        '--add-scope',
        nargs='+',
        metavar='SCOPE',
        help='Add additional scope(s) to authorization'
    )
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='Force re-authentication'
    )
    parser.add_argument(
        '--revoke',
        action='store_true',
        help='Remove stored credentials'
    )
    parser.add_argument(
        '--scopes',
        action='store_true',
        help='List available scope aliases'
    )

    args = parser.parse_args()

    # Handle commands
    if args.status:
        show_status(args.profile if args.profile != 'default' else None)
    elif args.scopes:
        show_available_scopes()
    elif args.add_scope:
        add_scopes(args.add_scope, args.profile)
    elif args.refresh:
        refresh_auth(args.profile)
    elif args.revoke:
        revoke_credentials(args.profile)
    else:
        # Default: run initial setup or show status if already set up
        token_file = get_token_file(args.profile)
        if token_file.exists():
            show_status(args.profile)
            print(f"Profile '{args.profile}' already authenticated.")
            print("Use --refresh to re-authenticate.")
            print("Use --add-scope to add additional permissions.")
        else:
            initial_setup(profile=args.profile)


if __name__ == '__main__':
    main()
