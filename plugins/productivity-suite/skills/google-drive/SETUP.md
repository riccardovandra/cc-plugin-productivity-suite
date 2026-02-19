# Google Drive Skill Setup

## Prerequisites

-   UV Python runtime — install at [astral.sh/uv](https://astral.sh/uv)

-   Google OAuth set up (see plugin README — do this once for all 4 Google skills)


## Step 1: Complete Google OAuth Setup

The Google Drive skill uses the shared Google OAuth integration. If you haven't done this yet, follow the README.md in the plugin root.

Quick check — run this to verify your token exists:

```bash
uv run ~/.claude/plugins/cache/riccardovandra/cc-plugin-productivity-suite/integrations/google/scripts/google_auth.py
```

## Step 2: Verify Setup

Test the connection:

```bash
# Test search (read-only, safe to run)
uv run ~/.claude/plugins/cache/riccardovandra/cc-plugin-productivity-suite/skills/google-drive/scripts/search.py --query "name contains '.'" --limit 1
```



## Troubleshooting

### "Missing scopes" error

Run the OAuth setup and add Drive scopes:

```bash
cd .claude/integrations/google
uv run scripts/oauth_setup.py
```

### "Client secrets not found" error

The Google OAuth integration isn't set up. Follow the Google OAuth setup instructions in `.claude/integrations/google/`.

### "Token refresh failed" error

Your token may have expired. Re-run OAuth setup to refresh:

```bash
cd .claude/integrations/google
uv run scripts/oauth_setup.py --profile <profile_name>
```

### Upload fails with "403 Forbidden"

Check that:

1.  You requested `drive` scope (not just `drive.readonly`)
    
2.  You have write permission to the target folder
    
3.  The folder ID is correct (search for it first)
    

## Next Steps

-   See [SKILL.md](SKILL.md) for usage examples
    
-   Read [Drive API documentation](https://developers.google.com/drive/api/guides/search-files) for advanced search queries