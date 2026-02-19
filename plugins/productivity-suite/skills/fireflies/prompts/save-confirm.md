# Save Confirmation

After displaying the transcript, ask:

> "Would you like to save this transcript?
>
> - **Yes, sales call** → `context/calls/sales-calls/`
> - **Yes, client call** → `context/calls/client-calls/`
> - **No** → Keep in conversation only"

If user confirms, save with filename: `{date} - {title}.md`
