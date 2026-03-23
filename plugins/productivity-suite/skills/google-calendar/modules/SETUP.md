# Google Calendar Setup

This skill uses the shared Google OAuth integration at `.claude/integrations/google/`.

## Prerequisites

1. **Google Cloud Project** with Calendar API enabled
2. **OAuth credentials** (Desktop app type)
3. **client_secrets.json** in `.claude/integrations/google/credentials/`

If you already have Gmail working, you just need to add the calendar scope.

## Quick Setup (If Gmail Already Works)

```bash
cd .claude/integrations/google/scripts
python oauth_setup.py --add-scope calendar.events
```

This adds the calendar permission to your existing OAuth token.

## Full Setup (First Time)

See the shared integration setup: `.claude/integrations/google/modules/SETUP.md`

In summary:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project (or use existing)
3. Enable "Google Calendar API"
4. Create OAuth 2.0 credentials (Desktop app)
5. Download as `client_secrets.json`
6. Place in `.claude/integrations/google/credentials/`
7. Run: `python oauth_setup.py --add-scope calendar.events`

## Verify Setup

```bash
cd .claude/skills/google-calendar/scripts
python today.py
```

Should show today's calendar events.

## Troubleshooting

**"Missing dependencies"**
```bash
pip install google-api-python-client google-auth-oauthlib python-dateutil
```

**"Client secrets not found"**
Download OAuth credentials from Google Cloud Console and save as `client_secrets.json`

**"Missing scopes"**
```bash
python oauth_setup.py --add-scope calendar.events
```

**Can't see calendar events**
- Ensure you're logged in with the correct Google account
- Check that Calendar API is enabled in Google Cloud Console
