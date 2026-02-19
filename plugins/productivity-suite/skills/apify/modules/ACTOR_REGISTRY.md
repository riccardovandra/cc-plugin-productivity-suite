# Apify Actor Registry

Validated actors for common research needs. All actors here have been tested and are known to work well.

---

## Registry Format

Each actor entry includes:
- **Use Case:** When to use this actor
- **Actor ID:** Apify actor identifier
- **Pricing:** Cost model and approximate costs
- **Input Schema:** Required and optional parameters
- **Output Schema:** What data you get back
- **Example:** Working example command

---

## Job Search Actors

### LinkedIn Jobs Search

**Use Case:** Find companies posting specific job titles
**Actor:** `fantastic-jobs/advanced-linkedin-job-search-api`
**Actor ID:** `vIGxjRrHqDTPuE6M4`
**Pricing:** Pay per result (~$0.002-0.005 per job posting)

**Best For:**
- Tier 1 EDP: Finding companies actively hiring for specific roles
- Competitive intelligence: Who's hiring in your space
- Market research: Job market trends

**Input Schema:**
```json
{
  "searchQuery": "operations manager",       // Required: Job title to search
  "location": "United States",               // Optional: Geographic filter
  "companySize": ["11-50", "51-200"],       // Optional: Company size filter
  "datePosted": "past_month",                // Optional: How recent
  "maxResults": 100,                         // Optional: Limit results
  "experienceLevel": ["mid_senior"],         // Optional: Experience level
  "jobType": ["full_time"]                   // Optional: Employment type
}
```

**Output Schema:**
```json
{
  "jobTitle": "Operations Manager",
  "companyName": "Acme Marketing Agency",
  "companyUrl": "https://linkedin.com/company/acme",
  "location": "New York, NY",
  "postedDate": "2026-01-15",
  "jobUrl": "https://linkedin.com/jobs/view/123456",
  "companySize": "51-200 employees",
  "industry": "Marketing and Advertising"
}
```

**Example:**
```bash
uv run .claude/skills/apify/scripts/linkedin_jobs.py \
  --query "operations manager" \
  --location "United States" \
  --industries "marketing,advertising" \
  --company-size "11-50,51-200" \
  --posted-within "month" \
  --max-results 100 \
  --output tier-1-companies.json
```

---

## People/Contact Actors

### People Database

**Use Case:** Find B2B contacts by job title, industry, company size
**Actor:** `apify/people-database`
**Actor ID:** `IoSHqwTR9YGhzccez`
**Pricing:** Pay per result

**Note:** Already integrated in `list-building` skill. Use when you need general people search outside the find-leads flow.

**Input Schema:**
```json
{
  "jobTitles": ["CEO", "Founder"],
  "industries": ["Marketing"],
  "locations": ["United States"],
  "companySizes": ["11-50"],
  "maxResults": 100
}
```

---

## Content Actors

### YouTube Transcripts

**Use Case:** Extract transcripts from YouTube videos
**Actor:** `karamelo/youtube-transcripts`
**Pricing:** Pay per result

**Note:** Already integrated in `youtube-transcript` skill.

---

## Social Media Actors

### LinkedIn Profile Scraper

**Use Case:** Extract detailed profile data from LinkedIn URLs
**Actor ID:** To be added when needed
**Status:** Not yet validated

### Twitter/X Search

**Use Case:** Search tweets by keyword, user, or hashtag
**Actor ID:** To be added when needed
**Status:** Not yet validated

---

## Adding New Actors

When you validate a new actor, add it to this registry:

```markdown
### [Actor Name]

**Use Case:** [When to use]
**Actor:** `[username/actor-name]`
**Actor ID:** `[actor_id]`
**Pricing:** [Pricing model and approximate costs]

**Input Schema:**
```json
{
  // Required and optional parameters
}
```

**Output Schema:**
```json
{
  // What data you get back
}
```

**Example:**
```bash
[Working command example]
```
```

---

## Pricing Guidelines

**Prefer (in order):**
1. Pay per result - Only pay for what you get
2. Pay per event - Pay for specific actions
3. Pay per usage - Based on compute time
4. Flat rate - Only if cost is very low

**Avoid:**
- High monthly minimums
- Actors without clear pricing
- Actors with no reviews or low usage

---

## Quality Checklist

Before adding an actor to the registry:

- [ ] Tested with real queries
- [ ] Output format documented
- [ ] Pricing verified and acceptable
- [ ] Error handling understood
- [ ] Rate limits documented (if any)
