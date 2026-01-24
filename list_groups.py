#!/usr/bin/env python3
"""
List all Telegram groups/channels you're a member of.
"""

import asyncio
import json
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


async def main():
    config = load_config()
    api_id = int(config["api_id"])  # Ensure int for TelegramClient
    api_hash = config["api_hash"]

    session_path = BASE_DIR / "telegram_session"
    client = TelegramClient(str(session_path), api_id, api_hash)

    # Check if session exists
    if not session_path.with_suffix('.session').exists():
        print("No session found. Please run scraper.py first to authenticate.")
        return
    
    print("Connecting using saved session...")
    await client.start()
    
    async with client:
        print("Connected to Telegram!\n")
        print("=" * 70)
        print(f"{'Type':<12} {'ID':<20} {'Name'}")
        print("=" * 70)

        async for dialog in client.iter_dialogs():
            entity = dialog.entity

            if isinstance(entity, Channel):
                if entity.megagroup:
                    dtype = "Group"
                else:
                    dtype = "Channel"
                print(f"{dtype:<12} {entity.id:<20} {dialog.name}")

            elif isinstance(entity, Chat):
                print(f"{'Group':<12} {entity.id:<20} {dialog.name}")

        print("=" * 70)
        print("\nTo scrape a group, add its ID to config.json 'groups' list.")
        print("For private groups, prefix the ID with -100, e.g., -1001234567890")


if __name__ == "__main__":
    asyncio.run(main())
