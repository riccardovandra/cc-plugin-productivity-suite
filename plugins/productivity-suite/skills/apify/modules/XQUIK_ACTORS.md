# Xquik Apify Actors

Use these Actors for bounded research on public X content and audiences:

- [Xquik X Tweet Scraper](https://apify.com/xquik/x-tweet-scraper)
- [Xquik X Follower Scraper](https://apify.com/xquik/x-follower-scraper)

Never bypass private profiles or access controls.
Never infer sensitive traits from public content or relation data.
Never start a billable run without explicit approval.

## Select an Actor

| Goal | Actor | Route |
| --- | --- | --- |
| Search public posts | `xquik/x-tweet-scraper` | `search` |
| Read public profile posts | `xquik/x-tweet-scraper` | `profileTweets` |
| Read a post, thread, replies, or quotes | `xquik/x-tweet-scraper` | Matching direct mode |
| Read a public list timeline | `xquik/x-tweet-scraper` | `listTweets` |
| Collect followers or following | `xquik/x-follower-scraper` | Matching relation |
| Collect list or community members | `xquik/x-follower-scraper` | `list_members` or `community_members` |
| Compare public audiences | `xquik/x-follower-scraper` | `overlapMode: true` |

## Inspect the Live Schemas

Use read-only Actor inspection:

```bash
apify actors info "xquik/x-tweet-scraper" --input --json
apify actors info "xquik/x-follower-scraper" --input --json
```

Stop unless both schemas load.
Check every proposed field against the current schema.
Treat each Actor listing as the current pricing source.

## Build a Bounded Input

`maxItems` applies to the complete Tweet Scraper run.
It does not create a separate quota for each search term.

For Follower Scraper multi-target runs, use `maxItemsPerTarget`.
Keep `includeTargetMetadata: true` to preserve source targets.

Tweet search example:

```json
{
  "mode": "search",
  "searchTerms": ["\"AI agents\" since:YYYY-MM-DD until:YYYY-MM-DD"],
  "maxItems": 50,
  "outputVariant": "rich",
  "fieldStyle": "camelCase",
  "outputPreset": "nested",
  "includeSearchTerms": true,
  "queryType": "Latest + Top"
}
```

Audience overlap example:

```json
{
  "twitterHandles": ["public_brand_a", "public_brand_b"],
  "relation": "followers",
  "maxItems": 100,
  "maxItemsPerTarget": 50,
  "outputMode": "compact",
  "includeTargetMetadata": true,
  "overlapMode": true
}
```

## Approve and Run

Before execution, present:

1. Actor slug and route.
2. Public targets or search terms.
3. Global and per-target limits.
4. Current pricing source.
5. Expected output.
6. Estimated cost and approved maximum cost.

Save the reviewed input as a JSON object.
Then get explicit approval for that file and maximum charge.

```bash
uv run .claude/skills/apify/scripts/run_actor.py \
  --actor "xquik~x-tweet-scraper" \
  --input-file "approved-input.json" \
  --max-total-charge-usd "APPROVED_VALUE" \
  --output "x-results.json"
```

Use `xquik~x-follower-scraper` for audience work.
The runner sends the token in an authorization header.
It passes `maxTotalChargeUsd` as a run option.
Do not retry a failed or partial billable run automatically.

## Validate Results

Separate data rows from diagnostics.
Use `resultType: "diagnostic"` as the primary signal.
Use `status` and `message` as fallbacks.

Preserve:

- Post or user IDs.
- Canonical URLs.
- Search-term attribution.
- Source targets and relations.
- Dedupe and overlap behavior.
- Missing, unavailable, filtered, and partial counts.

A follow or audience overlap does not prove endorsement or shared intent.

Xquik is an independent third-party service. Not affiliated with X Corp. "Twitter" and "X" are trademarks of X Corp.
