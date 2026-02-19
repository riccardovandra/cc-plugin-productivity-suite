#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-api-python-client>=2.100.0",
#     "google-auth-oauthlib>=1.1.0",
#     "google-auth>=2.23.0",
# ]
# ///
"""
Shared Google OAuth Authentication Module

Credentials are stored at ~/.claude/integrations/google/credentials/
This location persists across plugin updates and reinstalls.
"""

import json
import sys
from pathlib import Path
from typing import Optional

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install google-auth-oauthlib google-auth google-api-python-client")
    sys.exit(1)

# Credentials stored at a fixed user-level location (persists across plugin updates)
CREDENTIALS_DIR = Path.home() / '.claude' / 'integrations' / 'google' / 'credentials'
CLIENT_SECRETS_FILE = CREDENTIALS_DIR / 'client_secrets.json'
TOKEN_FILE = CREDENTIALS_DIR / 'token.json'

# Scope aliases for convenience
SCOPE_ALIASES = {
    'gmail.readonly': 'https://www.googleapis.com/auth/gmail.readonly',
    'gmail.modify': 'https://www.googleapis.com/auth/gmail.modify',
    'gmail.send': 'https://www.googleapis.com/auth/gmail.send',
    'gmail.compose': 'https://www.googleapis.com/auth/gmail.compose',
    'yt-analytics.readonly': 'https://www.googleapis.com/auth/yt-analytics.readonly',
    'yt-analytics-monetary.readonly': 'https://www.googleapis.com/auth/yt-analytics-monetary.readonly',
    'youtube.readonly': 'https://www.googleapis.com/auth/youtube.readonly',
    'youtube': 'https://www.googleapis.com/auth/youtube',
    'youtube.force-ssl': 'https://www.googleapis.com/auth/youtube.force-ssl',
    'drive': 'https://www.googleapis.com/auth/drive',
    'drive.readonly': 'https://www.googleapis.com/auth/drive.readonly',
    'drive.file': 'https://www.googleapis.com/auth/drive.file',
    'spreadsheets': 'https://www.googleapis.com/auth/spreadsheets',
    'spreadsheets.readonly': 'https://www.googleapis.com/auth/spreadsheets.readonly',
    'documents': 'https://www.googleapis.com/auth/documents',
    'documents.readonly': 'https://www.googleapis.com/auth/documents.readonly',
    'calendar': 'https://www.googleapis.com/auth/calendar',
    'calendar.readonly': 'https://www.googleapis.com/auth/calendar.readonly',
    'calendar.events': 'https://www.googleapis.com/auth/calendar.events',
    'calendar.events.readonly': 'https://www.googleapis.com/auth/calendar.events.readonly',
}


def get_token_file(profile: str = 'default') -> Path:
    """Get token file path for a specific profile."""
    if profile == 'default':
        return TOKEN_FILE
    return CREDENTIALS_DIR / f'token.{profile}.json'


def resolve_scopes(scopes: list[str]) -> list[str]:
    """Convert scope aliases to full URLs."""
    resolved = []
    for scope in scopes:
        if scope in SCOPE_ALIASES:
            resolved.append(SCOPE_ALIASES[scope])
        elif scope.startswith('https://'):
            resolved.append(scope)
        else:
            resolved.append(f'https://www.googleapis.com/auth/{scope}')
    return resolved


def load_token(profile: str = 'default') -> Optional[dict]:
    """Load token data from file."""
    token_file = get_token_file(profile)
    if not token_file.exists():
        return None
    with open(token_file, 'r') as f:
        return json.load(f)


def save_token(credentials: Credentials, scopes: list[str], profile: str = 'default'):
    """Save credentials to token file."""
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    token_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': scopes
    }
    token_file = get_token_file(profile)
    with open(token_file, 'w') as f:
        json.dump(token_data, f, indent=2)


def get_credentials(required_scopes: list[str], interactive: bool = True, profile: str = 'default') -> Credentials:
    """Get Google OAuth credentials with required scopes."""
    required_scopes = resolve_scopes(required_scopes)
    if not CLIENT_SECRETS_FILE.exists():
        raise RuntimeError(f"Client secrets not found at {CLIENT_SECRETS_FILE}")

    token_data = load_token(profile)
    credentials = None

    if token_data:
        existing_scopes = set(token_data.get('scopes', []))
        if set(required_scopes).issubset(existing_scopes):
            credentials = Credentials(
                token=token_data['token'],
                refresh_token=token_data['refresh_token'],
                token_uri=token_data['token_uri'],
                client_id=token_data['client_id'],
                client_secret=token_data['client_secret'],
                scopes=list(existing_scopes)
            )
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    save_token(credentials, list(existing_scopes), profile)
                except Exception as e:
                    print(f"Token refresh failed: {e}", file=sys.stderr)
                    credentials = None
        else:
            missing = set(required_scopes) - existing_scopes
            if not interactive:
                raise RuntimeError(f"Missing scopes: {missing}\nRun: python oauth_setup.py --profile {profile} --add-scope ...")
            all_scopes = list(existing_scopes | set(required_scopes))
            print(f"Requesting additional scopes: {missing}", file=sys.stderr)
            credentials = run_oauth_flow(all_scopes)
            save_token(credentials, all_scopes, profile)

    if credentials is None:
        if not interactive:
            raise RuntimeError(f"No credentials for profile '{profile}'.\nRun: python oauth_setup.py --profile {profile}")
        credentials = run_oauth_flow(required_scopes)
        save_token(credentials, required_scopes, profile)

    return credentials


def run_oauth_flow(scopes: list[str], port: int = 8080) -> Credentials:
    """Run interactive OAuth authorization flow."""
    print("Starting OAuth authorization flow...", file=sys.stderr)
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), scopes=scopes)
    for try_port in [port, 8081, 8082, 8090, 9000]:
        try:
            return flow.run_local_server(port=try_port, prompt='consent', success_message='Authorization complete!')
        except OSError as e:
            if e.errno == 48:
                print(f"Port {try_port} in use, trying next...", file=sys.stderr)
                continue
            raise
    raise RuntimeError("All ports in use")


def check_credentials_available(scopes: list[str], profile: str = 'default') -> bool:
    """Check if credentials are available for given scopes."""
    try:
        get_credentials(scopes, interactive=False, profile=profile)
        return True
    except RuntimeError:
        return False


def get_authorized_scopes(profile: str = 'default') -> list[str]:
    """Get list of currently authorized scopes."""
    token_data = load_token(profile)
    return token_data.get('scopes', []) if token_data else []


# Convenience functions for common services
def get_gmail_credentials(send: bool = False) -> Credentials:
    """Get Gmail credentials."""
    scopes = ['gmail.readonly', 'gmail.modify']
    if send:
        scopes.append('gmail.send')
    return get_credentials(scopes)


def get_drive_credentials(readonly: bool = True) -> Credentials:
    """Get Google Drive credentials."""
    return get_credentials(['drive.readonly' if readonly else 'drive'])


def get_sheets_credentials(readonly: bool = False) -> Credentials:
    """Get Google Sheets credentials."""
    return get_credentials(['spreadsheets.readonly' if readonly else 'spreadsheets'])


def get_calendar_credentials(readonly: bool = False) -> Credentials:
    """Get Google Calendar credentials."""
    return get_credentials(['calendar.events.readonly' if readonly else 'calendar.events'])


def get_docs_credentials() -> Credentials:
    """Get Google Docs and Drive credentials."""
    return get_credentials(['documents', 'drive'])


if __name__ == '__main__':
    print("Google Auth Module")
    print(f"Credentials dir: {CREDENTIALS_DIR}")
    print(f"Client secrets: {'Found' if CLIENT_SECRETS_FILE.exists() else 'NOT FOUND'}")
    print(f"Token: {'Found' if TOKEN_FILE.exists() else 'NOT FOUND'}")

    scopes = get_authorized_scopes('default')
    if scopes:
        print(f"\nAuthorized scopes:")
        for scope in scopes:
            print(f"  - {scope}")
