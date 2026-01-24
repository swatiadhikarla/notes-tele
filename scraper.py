#!/usr/bin/env python3
"""
Telegram Group Scraper
Incrementally scrapes messages, files, and documents from Telegram groups.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Cutoff date - only scrape messages up to this date (set to None to scrape all)
CUTOFF_DATE = None  # No cutoff - scrape all messages

from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaDocument,
    MessageMediaPhoto,
    DocumentAttributeFilename,
)

# Paths
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
STATE_PATH = BASE_DIR / "state.json"
DATA_DIR = BASE_DIR / "data"


def load_config():
    """Load configuration from config.json"""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_state():
    """Load scraping state (last message IDs per group)"""
    if STATE_PATH.exists():
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    """Save scraping state"""
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def load_existing_messages(messages_path):
    """Load existing messages from JSON file"""
    if messages_path.exists():
        with open(messages_path, "r") as f:
            return json.load(f)
    return []


def save_messages(messages_path, messages):
    """Save messages to JSON file"""
    messages_path.parent.mkdir(parents=True, exist_ok=True)
    with open(messages_path, "w") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False, default=str)


def get_filename_from_document(document):
    """Extract filename from document attributes"""
    for attr in document.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            return attr.file_name
    return f"file_{document.id}"


async def download_media(client, message, media_dir):
    """Download media from a message, return the local path"""
    if not message.media:
        return None

    media_dir.mkdir(parents=True, exist_ok=True)

    try:
        if isinstance(message.media, MessageMediaDocument):
            document = message.media.document
            filename = get_filename_from_document(document)
            # Add message ID prefix to avoid collisions
            safe_filename = f"{message.id}_{filename}"
            file_path = media_dir / safe_filename
            
            if not file_path.exists():
                await client.download_media(message, file=str(file_path))
                print(f"  Downloaded: {safe_filename}")
            return str(file_path.relative_to(BASE_DIR))

        elif isinstance(message.media, MessageMediaPhoto):
            safe_filename = f"{message.id}_photo.jpg"
            file_path = media_dir / safe_filename
            
            if not file_path.exists():
                await client.download_media(message, file=str(file_path))
                print(f"  Downloaded: {safe_filename}")
            return str(file_path.relative_to(BASE_DIR))

    except Exception as e:
        print(f"  Failed to download media for message {message.id}: {e}")
        return None

    return None


def message_to_dict(message, media_path=None, topic_name=None, linked_message=None):
    """Convert a Telegram message to a dictionary"""
    sender_name = None
    if message.sender:
        if hasattr(message.sender, "username") and message.sender.username:
            sender_name = message.sender.username
        elif hasattr(message.sender, "first_name"):
            sender_name = message.sender.first_name
            if hasattr(message.sender, "last_name") and message.sender.last_name:
                sender_name += f" {message.sender.last_name}"

    # Determine message type
    msg_type = "text"
    if message.media:
        if isinstance(message.media, MessageMediaDocument):
            msg_type = "document"
        elif isinstance(message.media, MessageMediaPhoto):
            msg_type = "photo"
        else:
            msg_type = "media"

    # Get topic/forum ID if available
    topic_id = None
    if message.reply_to and hasattr(message.reply_to, 'forum_topic') and message.reply_to.forum_topic:
        topic_id = message.reply_to.reply_to_msg_id
    elif message.reply_to and hasattr(message.reply_to, 'reply_to_top_id'):
        topic_id = message.reply_to.reply_to_top_id

    return {
        "id": message.id,
        "date": message.date.isoformat(),
        "sender": sender_name,
        "sender_id": message.sender_id,
        "text": message.text or "",
        "media_path": media_path,
        "type": msg_type,
        "reply_to": message.reply_to.reply_to_msg_id if message.reply_to else None,
        "topic_id": topic_id,
        "topic_name": topic_name,
        "linked_text": linked_message.get("text") if linked_message else None,
        "linked_sender": linked_message.get("sender") if linked_message else None,
    }


async def scrape_group(client, group_id, state):
    """Scrape messages from a single group"""
    try:
        entity = await client.get_entity(group_id)
        group_name = getattr(entity, "title", str(group_id))
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in group_name)
        safe_name = safe_name.strip().replace(" ", "_")
        
        print(f"\n{'='*50}")
        print(f"Scraping: {group_name}")
        print(f"{'='*50}")

    except Exception as e:
        print(f"Failed to get entity for {group_id}: {e}")
        return

    # Setup paths
    group_dir = DATA_DIR / safe_name
    messages_path = group_dir / "messages.json"
    media_dir = group_dir / "media"

    # Load existing data
    existing_messages = load_existing_messages(messages_path)
    existing_ids = {m["id"] for m in existing_messages}

    # Get last message ID from state
    state_key = str(group_id)
    last_id = state.get(state_key, {}).get("last_message_id", 0)
    
    print(f"Last scraped message ID: {last_id}")
    print(f"Existing messages: {len(existing_messages)}")

    # Fetch forum topics if this is a forum group
    topics = {}
    try:
        from telethon.tl.functions.channels import GetForumTopicsRequest
        result = await client(GetForumTopicsRequest(
            channel=entity,
            offset_date=None,
            offset_id=0,
            offset_topic=0,
            limit=100
        ))
        for topic in result.topics:
            topics[topic.id] = topic.title
            print(f"  Found topic: {topic.id} -> {topic.title}")
    except Exception as e:
        print(f"  Not a forum group or couldn't fetch topics: {e}")

    # Fetch new messages
    new_messages = []
    max_id = last_id

    async for message in client.iter_messages(entity, min_id=last_id, reverse=True):
        if message.id in existing_ids:
            continue
        
        # Check cutoff date
        if CUTOFF_DATE and message.date > CUTOFF_DATE:
            print(f"  Reached cutoff date ({CUTOFF_DATE.date()}), stopping.")
            break

        # Get topic name if available
        topic_name = None
        topic_id = None
        if message.reply_to:
            if hasattr(message.reply_to, 'reply_to_top_id') and message.reply_to.reply_to_top_id:
                topic_id = message.reply_to.reply_to_top_id
            elif hasattr(message.reply_to, 'forum_topic') and message.reply_to.forum_topic:
                topic_id = message.reply_to.reply_to_msg_id
        if topic_id and topic_id in topics:
            topic_name = topics[topic_id]

        # Fetch linked/replied message if exists
        linked_message = None
        if message.reply_to and message.reply_to.reply_to_msg_id:
            reply_id = message.reply_to.reply_to_msg_id
            # Check if it's not just a topic reference
            if reply_id not in topics:
                try:
                    reply_msg = await client.get_messages(entity, ids=reply_id)
                    if reply_msg and reply_msg.text:
                        reply_sender = None
                        if reply_msg.sender:
                            if hasattr(reply_msg.sender, "username") and reply_msg.sender.username:
                                reply_sender = reply_msg.sender.username
                            elif hasattr(reply_msg.sender, "first_name"):
                                reply_sender = reply_msg.sender.first_name
                        linked_message = {
                            "text": reply_msg.text[:500] if reply_msg.text else "",  # Limit length
                            "sender": reply_sender
                        }
                except Exception as e:
                    pass  # Couldn't fetch linked message

        # Download media if present
        media_path = await download_media(client, message, media_dir)

        # Convert to dict
        msg_dict = message_to_dict(message, media_path, topic_name, linked_message)
        new_messages.append(msg_dict)

        if message.id > max_id:
            max_id = message.id

        # Progress indicator - show timestamp and write to log
        msg_date = message.date.strftime("%Y-%m-%d %H:%M")
        log_line = f"[{msg_date}] #{message.id}"
        if media_path:
            log_line += f" - {media_path.split('/')[-1][:40]}"
        
        # Write to progress log file (append mode)
        with open(BASE_DIR / "progress.log", "a") as f:
            f.write(f"{log_line} | Total: {len(new_messages)}\n")
        
        print(log_line, flush=True)

    print(f"New messages found: {len(new_messages)}")

    # Merge and save
    if new_messages:
        all_messages = existing_messages + new_messages
        # Sort by date
        all_messages.sort(key=lambda x: x["date"])
        save_messages(messages_path, all_messages)
        print(f"Total messages saved: {len(all_messages)}")

        # Update state
        state[state_key] = {
            "last_message_id": max_id,
            "last_run": datetime.now().isoformat(),
            "group_name": group_name,
            "total_messages": len(all_messages),
        }
    else:
        print("No new messages to save.")


async def main():
    """Main entry point"""
    print("Telegram Group Scraper")
    print("=" * 50)

    # Load config
    config = load_config()
    api_id = int(config["api_id"])  # Ensure int for TelegramClient
    api_hash = config["api_hash"]
    groups = config["groups"]

    if api_id == "YOUR_API_ID":
        print("\nError: Please update config.json with your Telegram API credentials.")
        print("Get them from: https://my.telegram.org/apps")
        return

    # Load state
    state = load_state()

    # Create data directory
    DATA_DIR.mkdir(exist_ok=True)

    # Connect to Telegram with retry logic
    session_path = BASE_DIR / "telegram_session"
    client = TelegramClient(str(session_path), api_id, api_hash)
    client.flood_sleep_threshold = 60  # Auto-sleep on flood wait

    async with client:
        print("\nConnected to Telegram!")
        me = await client.get_me()
        print(f"Logged in as: {me.first_name} (@{me.username})")

        # Scrape each group with retry
        for group in groups:
            retries = 3
            for attempt in range(retries):
                try:
                    await scrape_group(client, group, state)
                    break
                except Exception as e:
                    print(f"Error scraping {group}: {e}")
                    if attempt < retries - 1:
                        print(f"Retrying in 30 seconds... (attempt {attempt + 2}/{retries})")
                        await asyncio.sleep(30)
                    else:
                        print(f"Failed after {retries} attempts")

        # Save final state
        save_state(state)
        print(f"\n{'='*50}")
        print("Scraping complete! State saved.")
        print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
