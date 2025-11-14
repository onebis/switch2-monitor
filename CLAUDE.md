# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Switch2 lottery monitoring system that scrapes the Nintendo Store Japan website (https://store-jp.nintendo.com/) for Switch2-related lottery/raffle announcements and sends LINE Messaging API alerts when new information is detected. The system is designed to run on Google Cloud Functions with scheduled triggers.

## Architecture

### Core Data Flow

```
Scheduler → main.py → scraper.py → state_manager.py → notifier.py
                          ↓              ↓
                    HTML parsing    JSON state file
                                   (change detection)
```

1. **main.py**: Entry point with Cloud Functions decorators (`@functions_framework.http` and `@functions_framework.cloud_event`)
2. **scraper.py**: Fetches HTML and extracts keyword-matching content (headings, banners, links, paragraphs)
3. **state_manager.py**: Compares current scan against previous state using SHA256 hashes
4. **notifier.py**: Formats and sends LINE Messaging API messages
5. **config.py**: Centralized configuration with environment variable loading

### State Management

The system uses a stateful change detection approach:
- First run: Detects all matching content but does NOT send notifications (baseline establishment)
- Subsequent runs: Only notifies when content hash changes or new items appear
- **Local development**: State persisted in `switch2_state.json` (gitignored)
- **Cloud Functions**: State persisted in Google Cloud Storage (GCS) - **REQUIRED** for proper operation
  - Cloud Functions filesystem is read-only except `/tmp`
  - State files in `/tmp` are ephemeral and lost between invocations
  - GCS provides persistent storage across function executions

### Keyword Matching Strategy

Keywords defined in `config.py:WATCH_KEYWORDS` are matched against:
- HTML element text content (h1-h6, banners, links, paragraphs)
- URL paths (e.g., "/switch2" in href attributes)
- Match mode: `any` (OR) or `all` (AND) via `KEYWORD_MATCH_MODE`

## Development Commands

### Local Testing

```bash
# Setup
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID or LINE_GROUP_ID

# Component-level testing
python config.py          # Validate configuration
python scraper.py         # Test HTML scraping + keyword detection
python notifier.py        # Test LINE notifications (sends 5 test messages)
python state_manager.py   # Test state persistence logic

# Full system test
python main.py            # Runs complete monitoring cycle
```

### Cloud Functions Testing

```bash
# Test notification (no scraping)
curl "https://YOUR-FUNCTION-URL?test=true"

# Force notification (resets state)
curl "https://YOUR-FUNCTION-URL?force=true"
```

### Deployment

**Prerequisites:**
1. Create a Google Cloud Storage bucket for state persistence:
```bash
# Create GCS bucket (replace YOUR_PROJECT_ID with your actual project ID)
gsutil mb -p YOUR_PROJECT_ID gs://switch2-monitor-state

# Or specify region
gsutil mb -p YOUR_PROJECT_ID -l asia-northeast1 gs://switch2-monitor-state
```

2. Deploy Cloud Function with GCS configuration:
```bash
gcloud functions deploy switch2_monitor \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point main \
  --set-env-vars LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here,LINE_USER_ID=your_user_id_here,LINE_GROUP_ID=your_group_id_here,USE_CLOUD_STORAGE=True,GCS_BUCKET_NAME=switch2-monitor-state,GCS_STATE_FILE=switch2_lottery_state.json
```

3. Schedule hourly checks:
```bash
gcloud scheduler jobs create http switch2_monitor_job \
  --schedule="0 * * * *" \
  --uri="https://REGION-PROJECT_ID.cloudfunctions.net/switch2_monitor" \
  --http-method=GET
```

**Important:**
- `USE_CLOUD_STORAGE=True` is **REQUIRED** for Cloud Functions deployment
- The Cloud Function service account needs `Storage Object Admin` permissions on the GCS bucket
- Grant permissions if needed:
```bash
# Get service account email
gcloud projects get-iam-policy YOUR_PROJECT_ID

# Grant storage permissions (replace SERVICE_ACCOUNT_EMAIL)
gsutil iam ch serviceAccount:SERVICE_ACCOUNT_EMAIL:objectAdmin gs://switch2-monitor-state
```

## Key Implementation Details

### Scraper HTML Parsing (scraper.py)

The `Switch2Scraper` class uses BeautifulSoup with `lxml` parser to extract:
- **Headings**: All h1-h6 tags with keyword matches
- **Banners**: Elements with class names matching `banner|notification|alert|announcement|notice` (regex)
- **Links**: `<a>` tags where either text or href contains keywords
- **Paragraphs**: `<p>` and `<div>` with text length 10-500 chars

Each detected item includes:
- `type`: Element category (heading/banner/link/paragraph)
- `title`: Primary text (truncated to 100 chars for paragraphs)
- `content`: Context including up to 3 sibling elements
- `url`: Absolute URL (resolved via `urljoin`)

### State Comparison Logic (state_manager.py)

```python
# Signature for deduplication
signature = f"{item['title']}:{item['content']}"

# Change detection
has_changes = current_hash != previous_hash
new_items = items not in previous signatures
```

### Notification Formatting (notifier.py)

The `send_lottery_notification_v2` method:
- Groups items by type with priority: heading > banner > link > paragraph
- Limits to 3 items per type (configurable via `max_items_per_type`)
- Uses type-specific emojis: 💡📌🔔➡️📄
- Displays context info if content contains "|" separator
- Shortens URLs: `https://store-jp.nintendo.com/foo` → `...nintendo.com/foo`
- Enforces 5000-char LINE Messaging API limit

## Configuration

### Environment Variables (.env)

**Required for all environments:**
- `LINE_CHANNEL_ACCESS_TOKEN` (required): LINE Messaging API channel access token
- `LINE_USER_ID` (required if not using group): User ID for individual notifications
- `LINE_GROUP_ID` (required if not using user): Group ID for group notifications (takes priority over USER_ID)

**Storage configuration:**
- `USE_CLOUD_STORAGE`: `False` (local dev) or `True` (Cloud Functions - **REQUIRED**)
- `GCS_BUCKET_NAME` (required if USE_CLOUD_STORAGE=True): GCS bucket name for state storage
- `GCS_STATE_FILE` (optional): GCS state file name (default: `switch2_lottery_state.json`)
- `STATE_FILE` (optional): Local state file path (default: `switch2_state.json`)

**Optional settings:**
- `TARGET_URL`: Override default Nintendo Store URL
- `KEYWORD_MATCH_MODE`: `any` (default) or `all`
- `LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR (default: INFO)
- `DEBUG_MODE`: True/False (default: False)

### Monitored Keywords (config.py)

Default keywords: `Switch2`, `Switch 2`, `Nintendo Switch 2`, `多言語`, `多言語対応`, `抽選`, `抽選販売`, `招待販売`, `申込み`, `申し込み`

To add keywords, edit `config.py:WATCH_KEYWORDS` list.

## Error Handling

- **HTTP failures**: Retry up to 3 times with exponential backoff (in `scraper.fetch_page`)
- **Parse errors**: Logged but don't crash; return empty results
- **State file corruption**: Treated as first run (baseline re-established)
- **LINE API failures**: Logged; system continues (notifications may be missed)

All errors trigger `notifier.send_error_notification()` with formatted details.

## Important Notes

- **Initial run behavior**: First execution detects content but does NOT notify (prevents spam)
- **State reset**:
  - Local: Delete `switch2_state.json`
  - Cloud Functions: Use `?force=true` query parameter or delete GCS state file
  - `curl "https://YOUR-FUNCTION-URL?force=true"` to trigger re-notification
- **Rate limiting**: No built-in delay between Cloud Function invocations (rely on scheduler frequency)
- **Content hashing**: Uses SHA256 of entire item list (any change triggers re-scan)
- **Cloud Functions state persistence**:
  - **CRITICAL**: Must use GCS (`USE_CLOUD_STORAGE=True`) in production
  - Without GCS, every invocation is treated as "first run" (no notifications sent)
  - Local filesystem writes are lost between function executions
