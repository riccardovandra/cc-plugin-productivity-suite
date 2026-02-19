# Gmail Draft Module

Create draft emails - does NOT send. You must manually send from Gmail.

## Quick Usage

```bash
# Create new draft
uv run scripts/draft.py create --to "person@example.com" --subject "Meeting" --body message.txt

# Reply to thread
uv run scripts/draft.py reply --thread-id 18xyz789ghi --body reply.txt

# List drafts
uv run scripts/draft.py list

# Delete draft
uv run scripts/draft.py delete <draft_id>
```

## Create New Draft

```bash
uv run scripts/draft.py create \
  --to "person@example.com" \
  --subject "Project Update" \
  --body message.txt \
  --cc "team@example.com"
```

### Parameters
- `--to` (required): Recipient email
- `--subject` (required): Email subject
- `--body` (required): Path to body text file, or `-` for stdin
- `--cc` (optional): CC recipients
- `--bcc` (optional): BCC recipients
- `--attach, -a` (optional): File to attach (can be used multiple times)

### With Attachments
```bash
uv run scripts/draft.py create \
  --to "person@example.com" \
  --subject "Report" \
  --body message.txt \
  --attach report.pdf \
  --attach data.xlsx
```

### Body from stdin
```bash
echo "Hello, this is my message." | uv run scripts/draft.py create \
  --to "person@example.com" \
  --subject "Quick note" \
  --body -
```

## Reply to Thread

Creates a reply draft in an existing conversation.

```bash
uv run scripts/draft.py reply --thread-id 18xyz789ghi --body reply.txt
```

This will:
1. Find the last message in the thread
2. Set "To" to the sender of that message
3. Set "Subject" with "Re:" prefix
4. Link the draft to the thread

### Typical Workflow

1. **Find the conversation**
   ```bash
   uv run scripts/search.py --query "from:client"
   ```

2. **Read the thread**
   ```bash
   uv run scripts/read.py --thread-id 18xyz789ghi
   ```

3. **Write your reply**
   ```bash
   cat > reply.txt << 'EOF'
   Hi,

   Thanks for your message. Here's my response...

   Best,
   Riccardo
   EOF
   ```

4. **Create draft**
   ```bash
   uv run scripts/draft.py reply --thread-id 18xyz789ghi --body reply.txt
   ```

5. **Send manually in Gmail**

## List Drafts

```bash
uv run scripts/draft.py list
```

Output:
```
Found 3 drafts:

  Draft ID: r123456789
  Message ID: 18abc123def

  Draft ID: r234567890
  Message ID: 18def456ghi
```

## Delete Draft

```bash
uv run scripts/draft.py delete r123456789
```

## Important Notes

### This Does NOT Send

The draft is created in your Gmail Drafts folder. You must:
1. Open Gmail
2. Go to Drafts
3. Review the message
4. Click Send

### Why Drafts Only?

Safety. This skill is designed to be safe:
- No accidental sends
- Review before sending
- Full control over what goes out

### To Send Emails

Use the separate `gmail-send` skill, which has additional safety measures:
- Two-phase confirmation
- Interactive "SEND" verification
- Cannot be bypassed

## Tips

### Template Files
Create reusable templates:
```
workspace/templates/
├── follow-up.txt
├── meeting-request.txt
└── thank-you.txt
```

### Quick Replies
```bash
# One-liner reply
echo "Thanks, I'll review and get back to you." | \
  uv run scripts/draft.py reply --thread-id 18xyz789ghi --body -
```

### Review All Drafts
```bash
uv run scripts/draft.py list
# Then open Gmail to review and send
```
