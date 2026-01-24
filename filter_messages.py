#!/usr/bin/env python3
"""
Filter out low-content messages (thank yous, namastes, etc.)
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Patterns to filter out (case-insensitive)
FILTER_PATTERNS = [
    # Thank yous
    r'^thanks?$',
    r'^thank\s*you\s*!*$',
    r'^thank\s*u\s*!*$',
    r'^ty$',
    r'^thx$',
    r'^thanks?\s+(sir|guruji|guru|ji)!*$',
    r'^thank\s*you\s*(sir|guruji|guru|ji|so\s*much)!*$',
    r'^many\s+thanks!*$',
    r'^thanks\s+a\s+lot!*$',
    
    # Namastes / Greetings
    r'^namaste!*$',
    r'^namaskar!*$',
    r'^namaskaram!*$',
    r'^pranam!*$',
    r'^pranaam!*$',
    r'^praṇām!*$',
    r'^jai\s*(guru|gurudev)!*$',
    r'^har(e|i)\s*(om|krishna|rama)!*$',
    r'^om!*$',
    r'^aum!*$',
    r'^hari\s*om!*$',
    r'^radhe\s*(radhe|shyam|krishna)?!*$',
    
    # Acknowledgments
    r'^ok!*$',
    r'^okay!*$',
    r'^yes!*$',
    r'^ya!*$',
    r'^yeah!*$',
    r'^sure!*$',
    r'^got\s*it!*$',
    r'^noted!*$',
    r'^understood!*$',
    r'^nice!*$',
    r'^great!*$',
    r'^wonderful!*$',
    r'^amazing!*$',
    r'^awesome!*$',
    r'^beautiful!*$',
    r'^wow!*$',
    
    # Gratitude variations
    r'^grateful!*$',
    r'^gratitude!*$',
    r'^blessed!*$',
    r'^dhanyavad!*$',
    r'^dhanyavaad!*$',
    r'^shukriya!*$',
    
    # Emoji-only or very short
    r'^[\s\.\!\?\,\:\;]*$',  # Only punctuation/whitespace
    r'^\+1$',
    r'^:[\)\(]$',
    
    # Welcome responses
    r'^welcome!*$',
    r'^you\'?re\s+welcome!*$',
    r'^most\s+welcome!*$',
    
    # Simple agreements
    r'^true!*$',
    r'^correct!*$',
    r'^right!*$',
    r'^exactly!*$',
    r'^agreed!*$',
    r'^indeed!*$',
]

# Compile patterns
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FILTER_PATTERNS]


def should_filter(text):
    """Check if message should be filtered out"""
    if not text:
        return True  # Empty text should be filtered (media check is done separately)
    
    # Clean text
    text = text.strip()
    
    # Filter if empty after strip
    if not text:
        return True
    
    # Skip very short messages (less than 5 chars, unless has media)
    if len(text) < 3:
        return True
    
    # Check against patterns
    for pattern in COMPILED_PATTERNS:
        if pattern.match(text):
            return True
    
    return False


def filter_messages(messages):
    """Filter out low-content messages, keeping those with media"""
    filtered = []
    removed_count = 0
    
    for msg in messages:
        text = msg.get('text', '').strip()
        has_media = msg.get('media_path') is not None
        
        # Keep if has media (even if text is filtered)
        if has_media:
            filtered.append(msg)
        # Keep if text is substantial
        elif not should_filter(text):
            filtered.append(msg)
        else:
            removed_count += 1
    
    return filtered, removed_count


def main():
    print("Message Filter")
    print("=" * 50)
    print("Removing: thank yous, namastes, short acknowledgments, etc.")
    print()
    
    total_removed = 0
    total_original = 0
    
    # Process each group's messages.json
    for group_dir in DATA_DIR.iterdir():
        if not group_dir.is_dir():
            continue
        
        messages_path = group_dir / "messages.json"
        if not messages_path.exists():
            continue
        
        # Load messages
        with open(messages_path, "r") as f:
            messages = json.load(f)
        
        original_count = len(messages)
        total_original += original_count
        
        # Filter
        filtered_messages, removed = filter_messages(messages)
        total_removed += removed
        
        # Save filtered messages
        with open(messages_path, "w") as f:
            json.dump(filtered_messages, f, indent=2, ensure_ascii=False)
        
        print(f"{group_dir.name}:")
        print(f"  Original: {original_count}")
        print(f"  Removed:  {removed}")
        print(f"  Kept:     {len(filtered_messages)}")
        print()
    
    print("=" * 50)
    print(f"Total removed: {total_removed} / {total_original} messages")
    print(f"Total kept:    {total_original - total_removed}")
    print()
    print("Now run: python3 flatten.py && python3 generate_pdf.py")


if __name__ == "__main__":
    main()
