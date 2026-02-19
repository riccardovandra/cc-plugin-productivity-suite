# Create Google Doc

Create a new Google Doc from a markdown file with formatting preserved.

## Usage

```bash
uv run scripts/create.py <input.md> [options]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input` | Yes | Path to markdown file |

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--title` | `-t` | Document title (defaults to filename) |
| `--folder` | `-f` | Google Drive folder name (created if missing) |

## Examples

### Basic - Create from markdown
```bash
uv run scripts/create.py document.md
```
Creates a doc named "document" in Google Drive root.

### With custom title
```bash
uv run scripts/create.py report.md --title "Q4 2024 Report"
```

### In specific folder
```bash
uv run scripts/create.py proposal.md --title "Client Proposal" --folder "Proposals"
```
Creates folder "Proposals" if it doesn't exist.

### Nested folder path
```bash
uv run scripts/create.py notes.md --folder "Work/Meeting Notes"
```
Note: Only creates/finds the final folder name, not nested paths.

## Output

The script outputs:
1. Created document title
2. Folder used (if specified)
3. Google Doc URL
4. Document ID

```
Created document: Q4 2024 Report
Using folder: Reports
URL: https://docs.google.com/document/d/1abc.../edit

Document ID: 1abc123...
```

## Supported Markdown

| Element | Result |
|---------|--------|
| `# Heading 1` | Title / Heading 1 style |
| `## Heading 2` | Heading 2 style |
| `### Heading 3` | Heading 3 style |
| `**bold**` | Bold text |
| `*italic*` | Italic text |
| `` `code` `` | Monospace (Courier New) |
| `- item` | Bullet list |
| `1. item` | Numbered list |
| Code blocks | Monospace with gray background |
| Tables | Google Docs tables (structure only) |

## Notes

- First-time use requires OAuth authorization
- Tables insert structure but content population is limited in V1
- Very long documents may hit API rate limits
