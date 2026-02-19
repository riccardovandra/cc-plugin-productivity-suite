# Create Spreadsheet

Create new Google Spreadsheets with headers and folder placement.

## Prerequisites

- Google OAuth set up with `spreadsheets` and `drive` scopes
- Run `python oauth_setup.py --add-scope spreadsheets --add-scope drive` if needed

## Basic Usage

```bash
# Simple spreadsheet
uv run scripts/create.py --title "My Data"

# With headers
uv run scripts/create.py --title "Habit Tracker" --headers "Date,Training,Meditation,Reading"

# In specific folder
uv run scripts/create.py --title "Report" --folder "Work/Reports" --headers "Date,Task,Status"
```

## Arguments

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `--title` | `-t` | Yes | Spreadsheet title |
| `--headers` | `-H` | No | Comma-separated header names |
| `--folder` | `-f` | No | Google Drive folder path (supports nested: `A/B/C`) |
| `--sheet` | `-s` | No | First sheet name (default: "Sheet1") |
| `--json` | `-j` | No | JSON config with headers |

## Folder Paths

The `--folder` argument supports nested folder paths:

```bash
# Top-level folder
--folder "Reports"

# Nested path
--folder "Uplifted AI/1_Fundamentals/Tracking"

# Deep nesting
--folder "Work/2024/Q4/Reports"
```

**Note:** Folders must exist. The script will warn if a folder is not found.

## JSON Configuration

For complex setups, use JSON:

```bash
uv run scripts/create.py --title "Project" --json '{
  "headers": ["Task", "Owner", "Due Date", "Status", "Notes"]
}'
```

## Output

```
Using folder: Work/Reports
Created: Q4 Report
URL: https://docs.google.com/spreadsheets/d/1abc.../edit

Spreadsheet ID: 1abc...
```

## Header Formatting

Headers are automatically formatted:
- **Bold white text** on blue background
- Centered alignment
- Frozen row (stays visible when scrolling)
- Auto-resized column widths

## Programmatic Usage

```python
from sheets_client import GoogleSheetsClient

client = GoogleSheetsClient()

# Create with headers
result = client.create_spreadsheet(
    title="Habit Tracker",
    headers=["Date", "Training", "Meditation", "Reading"],
    folder_id=client.get_folder_id("Tracking")
)

print(result['url'])
```
