# Telegram Group Scraper

Incrementally scrapes messages, files, and documents from Telegram groups you're a member of.

## Setup

### 1. Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org/apps)
2. Log in with your phone number
3. Create a new application (name doesn't matter)
4. Copy your `api_id` and `api_hash`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Groups

Edit `config.json`:

```json
{
  "api_id": "12345678",
  "api_hash": "your_api_hash_here",
  "groups": [
    "public_group_username",
    -1001234567890,
    "https://t.me/+AbCdEfGhIjK"
  ]
}
```

**Group formats supported:**
- Public groups: use username (e.g., `"python_tips"`)
- Private groups: use numeric ID (e.g., `-1001234567890`) or invite link

**Finding private group IDs:**
- Forward a message from the group to [@userinfobot](https://t.me/userinfobot)
- Or use Telegram Desktop: right-click group → Copy Link → the number in the URL is the ID

## Usage

### First Run

```bash
python scraper.py
```

On first run, you'll be prompted to:
1. Enter your phone number
2. Enter the verification code sent to Telegram

This creates a session file so you won't need to authenticate again.

### Subsequent Runs

```bash
python scraper.py
```

The scraper automatically:
- Only fetches NEW messages (after last scraped)
- Preserves all old data
- Downloads new files/documents

### Generate Timeline

After scraping, create a merged chronological view:

```bash
python flatten.py
```

This creates `data/timeline.json` with all messages from all groups sorted by timestamp.

## Output Structure

```
data/
├── Group_Name_1/
│   ├── messages.json    # All messages
│   └── media/           # Downloaded files
│       ├── 123_document.pdf
│       └── 456_photo.jpg
├── Group_Name_2/
│   ├── messages.json
│   └── media/
└── timeline.json        # Merged chronological view
```

### Message Format

```json
{
  "id": 12345,
  "date": "2026-01-20T10:30:00+00:00",
  "sender": "username",
  "sender_id": 987654321,
  "text": "message content",
  "media_path": "data/Group_Name/media/12345_file.pdf",
  "type": "text|document|photo|media",
  "reply_to": null,
  "group": "Group_Name"
}
```

## State Tracking

`state.json` tracks scraping progress:

```json
{
  "group_id": {
    "last_message_id": 12345,
    "last_run": "2026-01-20T10:00:00",
    "group_name": "Group Name",
    "total_messages": 5000
  }
}
```

Delete a group's entry from `state.json` to re-scrape from the beginning.

## Tips

- **Rate limits**: Telegram may rate-limit heavy scraping. The scraper handles this gracefully.
- **Large groups**: First scrape of large groups can take a while. Subsequent runs are fast.
- **Storage**: Documents/files are downloaded. Monitor disk space for media-heavy groups.
