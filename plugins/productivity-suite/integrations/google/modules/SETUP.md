# Google OAuth Setup Instructions

One-time setup to enable Google API access for Gmail, YouTube Analytics, Drive, etc.

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Name it (e.g., "Claude Code Integration")
4. Click **Create**

## Step 2: Enable APIs

Enable the APIs you need:

1. Go to **APIs & Services** → **Library**
2. Search and enable:
   - **Gmail API** (for email)
   - **YouTube Analytics API** (for retention data)
   - **Google Drive API** (for file access)
   - **Google Sheets API** (for spreadsheets)
   - **Google Docs API** (for documents)

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** (unless you have Google Workspace)
3. Fill in:
   - App name: "Claude Code Integration"
   - User support email: Your email
   - Developer contact: Your email
4. Click **Save and Continue**
5. **Scopes**: Skip for now (we'll request at runtime)
6. **Test users**: Add your Gmail address
7. Click **Save and Continue**

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: "Claude Code"
5. Click **Create**
6. Click **Download JSON**
7. Save as:
   ```
   .claude/integrations/google/credentials/client_secrets.json
   ```

## Step 5: Run Setup Script

```bash
cd .claude/integrations/google/scripts
python oauth_setup.py
```

A browser window will open. Sign in and authorize the requested permissions.

## Adding More Scopes Later

When you need additional permissions (e.g., adding Gmail send after using read-only):

```bash
python oauth_setup.py --add-scope gmail.send
```

This will prompt for additional authorization without losing existing permissions.

## Troubleshooting

### "Access blocked: This app's request is invalid"
- Make sure you added yourself as a test user in OAuth consent screen

### "Error 403: access_denied"
- The app is in testing mode and your email isn't a test user
- Add your email to test users in Google Cloud Console

### "Token has been expired or revoked"
- Run `python oauth_setup.py --refresh` to re-authenticate

### "Quota exceeded"
- Google APIs have rate limits
- Wait a few minutes and try again

## Security Notes

- Never share `client_secrets.json` or `token.json`
- Both files are gitignored by default
- Tokens auto-refresh; manual re-auth rarely needed
- To revoke access: [Google Account Permissions](https://myaccount.google.com/permissions)
