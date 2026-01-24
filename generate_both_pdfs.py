#!/usr/bin/env python3
"""
Generate two versions of PDFs:
1. Full version - all messages
2. Filtered version - low-content removed
"""

import json
import re
from pathlib import Path
from datetime import datetime

# Import from generate_pdf
from generate_pdf import create_pdf, register_fonts, load_timeline

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Filter patterns (same as filter_messages.py)
FILTER_PATTERNS = [
    r'^thanks?$', r'^thank\s*you\s*!*$', r'^thank\s*u\s*!*$', r'^ty$', r'^thx$',
    r'^thanks?\s+(sir|guruji|guru|ji)!*$', r'^thank\s*you\s*(sir|guruji|guru|ji|so\s*much)!*$',
    r'^many\s+thanks!*$', r'^thanks\s+a\s+lot!*$',
    r'^namaste!*$', r'^namaskar!*$', r'^namaskaram!*$', r'^pranam!*$', r'^pranaam!*$',
    r'^praṇām!*$', r'^jai\s*(guru|gurudev)!*$', r'^har(e|i)\s*(om|krishna|rama)!*$',
    r'^om!*$', r'^aum!*$', r'^hari\s*om!*$', r'^radhe\s*(radhe|shyam|krishna)?!*$',
    r'^ok!*$', r'^okay!*$', r'^yes!*$', r'^ya!*$', r'^yeah!*$', r'^sure!*$',
    r'^got\s*it!*$', r'^noted!*$', r'^understood!*$', r'^nice!*$', r'^great!*$',
    r'^wonderful!*$', r'^amazing!*$', r'^awesome!*$', r'^beautiful!*$', r'^wow!*$',
    r'^grateful!*$', r'^gratitude!*$', r'^blessed!*$', r'^dhanyavad!*$', r'^shukriya!*$',
    r'^[\s\.\!\?\,\:\;]*$', r'^\+1$', r'^:[\)\(]$',
    r'^welcome!*$', r'^you\'?re\s+welcome!*$', r'^most\s+welcome!*$',
    r'^true!*$', r'^correct!*$', r'^right!*$', r'^exactly!*$', r'^agreed!*$', r'^indeed!*$',
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FILTER_PATTERNS]


def should_filter(text):
    if not text:
        return True  # Empty text should be filtered
    text = text.strip()
    if not text or len(text) < 3:
        return True
    for pattern in COMPILED_PATTERNS:
        if pattern.match(text):
            return True
    return False


def filter_messages(messages):
    filtered = []
    for msg in messages:
        text = msg.get('text', '').strip()
        has_media = msg.get('media_path') is not None
        
        # Keep if has media (regardless of text)
        if has_media:
            filtered.append(msg)
        # Keep if has substantial text content
        elif text and not should_filter(text):
            filtered.append(msg)
        # Otherwise skip (empty or low-content message without media)
    return filtered


def main():
    print("=" * 60)
    print("Generating SEPARATE PDFs per group (FULL + FILTERED)")
    print("=" * 60)
    
    # Load all messages
    messages = load_timeline()
    if not messages:
        print("No messages found!")
        return
    
    # Group messages by group name
    groups = {}
    for msg in messages:
        group = msg.get('group', 'Unknown')
        if group not in groups:
            groups[group] = []
        groups[group].append(msg)
    
    print(f"\nFound {len(groups)} groups:")
    for g in groups:
        print(f"  - {g}: {len(groups[g])} messages")
    
    # Create PDFs for each group separately
    for group_name, group_messages in groups.items():
        print("\n" + "=" * 60)
        print(f"Processing: {group_name}")
        print("=" * 60)
        
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in group_name)
        group_messages.sort(key=lambda x: x.get('date', ''))
        g_first = group_messages[0].get('date', '')[:10]
        g_last = group_messages[-1].get('date', '')[:10]
        
        # Full version
        full_group_path = BASE_DIR / f"FULL_{safe_name}_{g_first}_to_{g_last}.pdf"
        print(f"\nFULL version ({len(group_messages)} messages)...")
        create_pdf(group_messages, full_group_path)
        print(f"  ✅ {full_group_path.name} ({full_group_path.stat().st_size / 1024 / 1024:.1f} MB)")
        
        # Filtered version
        filtered_group = filter_messages(group_messages)
        removed = len(group_messages) - len(filtered_group)
        filtered_group_path = BASE_DIR / f"FILTERED_{safe_name}_{g_first}_to_{g_last}.pdf"
        print(f"FILTERED version ({len(filtered_group)} messages, removed {removed})...")
        create_pdf(filtered_group, filtered_group_path)
        print(f"  ✅ {filtered_group_path.name} ({filtered_group_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
    print("\n" + "=" * 60)
    print("All PDFs created! (Separate PDF for each group)")
    print("=" * 60)


if __name__ == "__main__":
    main()
