#!/usr/bin/env python3
"""
Transcribe all audio and video files using OpenAI Whisper.
Saves transcriptions as {filename}-transcription.txt in the same folder.
"""

import whisper
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Audio/video extensions to transcribe
MEDIA_EXTENSIONS = {'.mp3', '.mp4', '.m4a', '.wav', '.ogg', '.mov', '.avi', '.mkv', '.webm', '.flac'}


def get_media_files():
    """Find all audio/video files in data directories"""
    media_files = []
    
    for group_dir in DATA_DIR.iterdir():
        if not group_dir.is_dir():
            continue
        
        media_dir = group_dir / "media"
        if not media_dir.exists():
            continue
        
        for file in media_dir.iterdir():
            if file.suffix.lower() in MEDIA_EXTENSIONS:
                media_files.append(file)
    
    return sorted(media_files)


def transcribe_file(model, file_path):
    """Transcribe a single file and save the result"""
    output_path = file_path.with_name(file_path.stem + "-transcription.txt")
    
    # Skip if already transcribed
    if output_path.exists():
        return "skipped"
    
    try:
        print(f"  Transcribing: {file_path.name[:50]}...")
        # Auto-detect language (works for English, Hindi, Sanskrit, etc.)
        result = model.transcribe(str(file_path))
        
        # Save transcription
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"Transcription of: {file_path.name}\n")
            f.write("=" * 50 + "\n\n")
            f.write(result["text"])
        
        return "done"
    
    except Exception as e:
        print(f"    Error: {e}")
        return "error"


def main():
    print("=" * 60)
    print("Audio/Video Transcription using Whisper")
    print("=" * 60)
    
    # Find all media files
    media_files = get_media_files()
    
    if not media_files:
        print("No audio/video files found!")
        return
    
    print(f"\nFound {len(media_files)} media files to transcribe")
    
    # Check how many already have transcriptions
    already_done = sum(1 for f in media_files if f.with_name(f.stem + "-transcription.txt").exists())
    print(f"Already transcribed: {already_done}")
    print(f"To transcribe: {len(media_files) - already_done}")
    
    if already_done == len(media_files):
        print("\nAll files already transcribed!")
        return
    
    # Load Whisper model (using 'base' for balance of speed/accuracy)
    # Options: tiny, base, small, medium, large
    print("\nLoading Whisper model (base)...")
    print("(First run will download the model ~140MB)")
    model = whisper.load_model("base")
    print("Model loaded!")
    
    # Transcribe files
    print("\n" + "=" * 60)
    print("Starting transcription...")
    print("=" * 60)
    
    stats = {"done": 0, "skipped": 0, "error": 0}
    
    for i, file_path in enumerate(media_files, 1):
        print(f"\n[{i}/{len(media_files)}] {file_path.parent.parent.name}")
        result = transcribe_file(model, file_path)
        stats[result] += 1
        
        if result == "done":
            print(f"    ✅ Saved: {file_path.stem}-transcription.txt")
        elif result == "skipped":
            print(f"    ⏭️  Already exists")
    
    print("\n" + "=" * 60)
    print("Transcription complete!")
    print(f"  Done: {stats['done']}")
    print(f"  Skipped (already exists): {stats['skipped']}")
    print(f"  Errors: {stats['error']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
