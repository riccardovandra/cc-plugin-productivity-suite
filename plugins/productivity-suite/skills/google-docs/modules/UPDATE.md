# Update Google Doc

Update an existing Google Doc from a markdown file.

## Usage

```bash
uv run scripts/update.py <input.md> --doc-id <id>
uv run scripts/update.py <input.md> --doc-url <url>
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input` | Yes | Path to markdown file |

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--doc-id` | `-d` | Document ID |
| `--doc-url` | `-u` | Document URL (alternative to --doc-id) |
| `--append` | `-a` | Append to existing content instead of replacing |

Must provide either `--doc-id` or `--doc-url`.

## Examples

### Update by document ID
```bash
uv run scripts/update.py changes.md --doc-id "1abc123xyz..."
```

### Update by URL
```bash
uv run scripts/update.py report.md --doc-url "https://docs.google.com/document/d/1abc123.../edit"
```

### Append content
```bash
uv run scripts/update.py additions.md --doc-id "1abc123..." --append
```
Adds content to end of document instead of replacing.

## Finding Document ID

The document ID is in the URL:
```
https://docs.google.com/document/d/[DOCUMENT_ID]/edit
                                    ^^^^^^^^^^^^
```

You can use either the full URL or just the ID.

## Output

```
Updating document: My Document Title
Updated: https://docs.google.com/document/d/1abc.../edit

Update complete!
```

## Behavior

### Replace Mode (default)
- Clears all existing document content
- Inserts new content from markdown file
- Preserves document title and sharing settings

### Append Mode (--append)
- Keeps existing content
- Adds new content at the end
- Useful for adding sections to existing docs

## Notes

- Document must exist and you must have edit access
- Replace mode cannot be undone (use Google Docs version history)
- Large documents may take longer to process
- Sharing settings and comments are preserved
