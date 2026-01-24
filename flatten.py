#!/usr/bin/env python3
"""
Timeline Flattener
Merges all group messages into a single chronological timeline.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TIMELINE_PATH = DATA_DIR / "timeline.json"


def load_all_messages():
    """Load messages from all group directories"""
    all_messages = []

    if not DATA_DIR.exists():
        print("No data directory found. Run scraper.py first.")
        return []

    for group_dir in DATA_DIR.iterdir():
        if not group_dir.is_dir():
            continue

        messages_path = group_dir / "messages.json"
        if not messages_path.exists():
            continue

        group_name = group_dir.name

        with open(messages_path, "r") as f:
            messages = json.load(f)

        # Add group info to each message
        for msg in messages:
            msg["group"] = group_name
            all_messages.append(msg)

        print(f"Loaded {len(messages)} messages from {group_name}")

    return all_messages


def flatten_timeline():
    """Create a flattened chronological timeline"""
    print("Timeline Flattener")
    print("=" * 50)

    # Load all messages
    all_messages = load_all_messages()

    if not all_messages:
        print("No messages found.")
        return

    # Sort by date
    all_messages.sort(key=lambda x: x["date"])

    # Save timeline
    with open(TIMELINE_PATH, "w") as f:
        json.dump(all_messages, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"Timeline created: {TIMELINE_PATH}")
    print(f"Total messages: {len(all_messages)}")

    # Print date range
    if all_messages:
        first_date = all_messages[0]["date"][:10]
        last_date = all_messages[-1]["date"][:10]
        print(f"Date range: {first_date} to {last_date}")

    # Group breakdown
    print(f"\n{'='*50}")
    print("Messages per group:")
    group_counts = {}
    for msg in all_messages:
        group = msg["group"]
        group_counts[group] = group_counts.get(group, 0) + 1

    for group, count in sorted(group_counts.items(), key=lambda x: -x[1]):
        print(f"  {group}: {count}")

    print(f"{'='*50}")


if __name__ == "__main__":
    flatten_timeline()
