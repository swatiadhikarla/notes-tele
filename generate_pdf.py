#!/usr/bin/env python3
"""
Generate PDF from scraped Telegram messages.
- Embeds images directly in the PDF
- Shows filenames for audio/video files
- Orders by timestamp
"""

import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import subprocess

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Register Unicode fonts for IAST support
def register_fonts():
    """Register Unicode-compatible fonts for IAST diacritics"""
    # Try common macOS fonts that support Unicode/IAST
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf", 
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    
    # Also check for Noto fonts (excellent Unicode support)
    noto_paths = [
        "/Library/Fonts/NotoSans-Regular.ttf",
        "/Library/Fonts/NotoSerif-Regular.ttf",
    ]
    
    registered = False
    
    # Try Arial Unicode first (best IAST support)
    for font_path in font_paths:
        if Path(font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
                print(f"  Using font: {font_path}")
                registered = True
                return 'UnicodeFont'
            except:
                continue
    
    if not registered:
        print("  Warning: No Unicode font found, using default (IAST may not display)")
        return 'Helvetica'

# Image extensions to embed
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
# Audio/video extensions to show as filename
MEDIA_EXTENSIONS = {'.mp3', '.mp4', '.m4a', '.wav', '.ogg', '.mov', '.avi', '.mkv', '.pdf', '.doc', '.docx'}


def load_timeline():
    """Load the flattened timeline or group messages"""
    timeline_path = DATA_DIR / "timeline.json"
    if timeline_path.exists():
        with open(timeline_path, "r") as f:
            return json.load(f)
    
    # Fallback: load from first group found
    for group_dir in DATA_DIR.iterdir():
        if group_dir.is_dir():
            messages_path = group_dir / "messages.json"
            if messages_path.exists():
                with open(messages_path, "r") as f:
                    return json.load(f)
    return []


def format_date(date_str):
    """Format ISO date string to readable format"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except:
        return date_str


def get_media_type(media_path):
    """Determine if media is an image or other file"""
    if not media_path:
        return None, None
    
    path = Path(media_path)
    ext = path.suffix.lower()
    
    if ext in IMAGE_EXTENSIONS:
        return "image", path
    elif ext in MEDIA_EXTENSIONS:
        return "file", path
    else:
        return "file", path


def strip_emojis(text):
    """Remove or replace emojis and other non-printable Unicode"""
    import re
    
    # Common emoji replacements
    emoji_map = {
        '📱': '[Phone]',
        '🕐': '[Time]',
        '👤': '[User]',
        '📷': '[Photo]',
        '🎵': '[Audio]',
        '🎬': '[Video]',
        '📄': '[Doc]',
        '📎': '[File]',
        '✅': '[OK]',
        '❌': '[X]',
        '⭐': '*',
        '🙏': '',
        '👍': '[+1]',
        '❤️': '[heart]',
        '🔥': '[fire]',
        '💡': '[idea]',
        '📝': '[note]',
        '🎯': '[target]',
        '⚡': '[lightning]',
        '🌟': '*',
        '✨': '*',
        '💫': '*',
        '🙂': ':)',
        '😊': ':)',
        '😄': ':)',
        '🤔': '[thinking]',
        '👆': '[up]',
        '👇': '[down]',
        '👉': '->',
        '👈': '<-',
        '📌': '[pin]',
        '🔗': '[link]',
        '📊': '[chart]',
        '📈': '[chart]',
        '🎓': '[grad]',
        '🕉️': 'Om',
        '🕉': 'Om',
        '🙏🏻': '',
        '🙏🏼': '',
        '🙏🏽': '',
        '🙏🏾': '',
        '🙏🏿': '',
        # Zodiac signs
        '♈': 'Ar',  # Aries
        '♈︎': 'Ar',
        '♉': 'Ta',  # Taurus
        '♉︎': 'Ta',
        '♊': 'Ge',  # Gemini
        '♊︎': 'Ge',
        '♋': 'Cn',  # Cancer
        '♋︎': 'Cn',
        '♌': 'Le',  # Leo
        '♌︎': 'Le',
        '♍': 'Vi',  # Virgo
        '♍︎': 'Vi',
        '♎': 'Li',  # Libra
        '♎︎': 'Li',
        '♏': 'Sc',  # Scorpio
        '♏︎': 'Sc',
        '♐': 'Sg',  # Sagittarius
        '♐︎': 'Sg',
        '♑': 'Cp',  # Capricorn
        '♑︎': 'Cp',
        '♒': 'Aq',  # Aquarius
        '♒︎': 'Aq',
        '♓': 'Pi',  # Pisces
        '♓︎': 'Pi',
        # Planets
        '☉': 'Su',  # Sun
        '☽': 'Mo',  # Moon
        '☿': 'Me',  # Mercury
        '♀': 'Ve',  # Venus
        '♂': 'Ma',  # Mars
        '♃': 'Ju',  # Jupiter
        '♄': 'Sa',  # Saturn
        '⛢': 'Ra',  # Rahu (north node)
        '☊': 'Ra',  # North Node
        '☋': 'Ke',  # South Node / Ketu
        '♅': 'Ur',  # Uranus
        '♆': 'Ne',  # Neptune
        '♇': 'Pl',  # Pluto
        # Arrows and misc
        '↑': '^',
        '↓': 'v',
        '→': '->',
        '←': '<-',
        '↔': '<->',
        '⇒': '=>',
        '⇐': '<=',
        '»': '>>',
        '«': '<<',
        '—': '-',
        '–': '-',
        '…': '...',
        '•': '*',
        '·': '.',
        '°': ' deg',
        '′': "'",
        '″': '"',
        '※': '*',
    }
    
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
    
    # Remove variation selectors (these cause boxes)
    text = text.replace('\ufe0e', '')  # text variation selector
    text = text.replace('\ufe0f', '')  # emoji variation selector
    
    # Remove remaining emojis (Unicode emoji ranges)
    # This regex matches most emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # geometric shapes
        "\U0001F800-\U0001F8FF"  # supplemental arrows
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols & pictographs ext
        "\U00002702-\U000027B0"  # dingbats
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U000E0100-\U000E01EF"  # variation selectors supplement
        "]+", 
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Remove any remaining non-printable or problematic characters
    # Keep: basic Latin, Latin Extended (for IAST), common punctuation
    cleaned = []
    for char in text:
        code = ord(char)
        # Keep ASCII printable, Latin Extended, Devanagari, common symbols
        if (code < 0x2000 or  # Basic multilingual plane (includes IAST)
            (0x2010 <= code <= 0x2027) or  # General punctuation
            (0x2030 <= code <= 0x205E) or  # More punctuation
            (0x0900 <= code <= 0x097F) or  # Devanagari
            char in '→←↑↓↔⇒⇐«»—–…•·°′″'):
            cleaned.append(char)
    
    return ''.join(cleaned)


def create_pdf(messages, output_path):
    """Create PDF document from messages"""
    
    # Register Unicode font
    unicode_font = register_fonts()
    
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Styles with Unicode font
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        fontName=unicode_font,
        textColor=colors.HexColor('#1a1a2e')
    )
    
    date_style = ParagraphStyle(
        'Date',
        parent=styles['Normal'],
        fontSize=9,
        fontName=unicode_font,
        textColor=colors.HexColor('#666666'),
        spaceAfter=2
    )
    
    sender_style = ParagraphStyle(
        'Sender',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#0066cc'),
        fontName=unicode_font,
        spaceAfter=4
    )
    
    message_style = ParagraphStyle(
        'Message',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=6,
        fontName=unicode_font,
        textColor=colors.HexColor('#1a1a1a')
    )
    
    media_style = ParagraphStyle(
        'Media',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#888888'),
        fontName=unicode_font,
        spaceAfter=4,
        leftIndent=20
    )
    
    separator_style = ParagraphStyle(
        'Separator',
        parent=styles['Normal'],
        fontSize=6,
        spaceAfter=15,
        spaceBefore=10
    )
    
    # Build document content
    story = []
    
    # Title
    group_name = messages[0].get('group', 'Telegram Messages') if messages else 'Telegram Messages'
    story.append(Paragraph(strip_emojis(f"📱 {group_name}"), title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", date_style))
    story.append(Paragraph(f"Total messages: {len(messages)}", date_style))
    story.append(Spacer(1, 30))
    
    # Process messages
    for i, msg in enumerate(messages):
        # Date and Channel/Topic
        date_str = format_date(msg.get('date', ''))
        topic_name = msg.get('topic_name', '')
        group_name = msg.get('group', '')
        
        # Build location string (prefer topic, fallback to group)
        location = topic_name if topic_name else group_name
        if location:
            story.append(Paragraph(strip_emojis(f"[Time] {date_str}  |  #{location}"), date_style))
        else:
            story.append(Paragraph(strip_emojis(f"[Time] {date_str}"), date_style))
        
        # Sender
        sender = msg.get('sender') or 'Unknown'
        story.append(Paragraph(strip_emojis(f"[User] {sender}"), sender_style))
        
        # Linked/quoted message if exists
        linked_text = msg.get('linked_text', '')
        linked_sender = msg.get('linked_sender', '')
        if linked_text:
            # Show linked message in quotes
            linked_preview = linked_text[:200] + "..." if len(linked_text) > 200 else linked_text
            linked_preview = strip_emojis(linked_preview)
            linked_preview = linked_preview.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            linked_preview = linked_preview.replace('\n', ' ')
            quote_text = f"<i>[Linked from {linked_sender or 'Unknown'}]: \"{linked_preview}\"</i>"
            try:
                story.append(Paragraph(quote_text, media_style))
            except:
                pass
        
        # Message text
        text = msg.get('text', '').strip()
        if text:
            # Strip emojis first
            text = strip_emojis(text)
            # Escape HTML special characters and preserve newlines
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text = text.replace('\n', '<br/>')
            try:
                story.append(Paragraph(text, message_style))
            except:
                # If text has issues, just show plain
                story.append(Paragraph(text[:500] + "..." if len(text) > 500 else text, message_style))
        
        # Media
        media_path = msg.get('media_path')
        if media_path:
            media_type, path = get_media_type(media_path)
            full_path = BASE_DIR / media_path
            
            if media_type == "image" and full_path.exists():
                try:
                    # Verify image can be opened first
                    from PIL import Image as PILImage
                    with PILImage.open(str(full_path)) as pil_img:
                        pil_img.verify()
                    
                    # Embed image with small max size to avoid page overflow
                    img = Image(str(full_path), width=3*inch, height=3*inch, kind='proportional')
                    story.append(Spacer(1, 6))
                    story.append(img)
                    story.append(Spacer(1, 6))
                except Exception as e:
                    # If image fails, just show filename
                    story.append(Paragraph(f"[Photo] {path.name}", media_style))
            
            elif media_type == "file":
                # Show filename for audio/video/documents
                ext = path.suffix.lower()
                if ext in {'.mp3', '.m4a', '.wav', '.ogg'}:
                    icon = "[Audio]"
                elif ext in {'.mp4', '.mov', '.avi', '.mkv'}:
                    icon = "[Video]"
                elif ext == '.pdf':
                    icon = "[PDF]"
                else:
                    icon = "[File]"
                story.append(Paragraph(f"{icon} <b>Attachment:</b> {path.name}", media_style))
        
        # Separator between messages
        story.append(Paragraph("─" * 60, separator_style))
        
        # Progress
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(messages)} messages...")
    
    # Build PDF
    print(f"  Writing PDF...")
    doc.build(story)


def generate_group_pdf(group_name, messages, output_dir):
    """Generate PDF for a single group"""
    if not messages:
        return None
    
    messages.sort(key=lambda x: x.get('date', ''))
    first_date = messages[0].get('date', '')[:10]
    last_date = messages[-1].get('date', '')[:10]
    
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in group_name)
    output_path = output_dir / f"{safe_name}_{first_date}_to_{last_date}.pdf"
    
    print(f"\nCreating PDF for {group_name}: {len(messages)} messages")
    create_pdf(messages, output_path)
    print(f"  ✅ {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return output_path


def main():
    print("PDF Generator")
    print("=" * 50)

    # Load messages
    messages = load_timeline()
    if not messages:
        print("No messages found!")
        return

    print(f"Loaded {len(messages)} messages")

    # Sort by date (should already be sorted)
    messages.sort(key=lambda x: x.get('date', ''))

    # Get date range for filename
    first_date = messages[0].get('date', '')[:10]
    last_date = messages[-1].get('date', '')[:10]

    # Output path for combined PDF
    output_path = BASE_DIR / f"telegram_messages_{first_date}_to_{last_date}.pdf"

    print(f"Creating combined PDF: {output_path.name}")
    print(f"Date range: {first_date} to {last_date}")
    print()

    create_pdf(messages, output_path)

    print()
    print("=" * 50)
    print(f"✅ Combined PDF created: {output_path}")
    print(f"   Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Also create individual PDFs per group
    print("\n" + "=" * 50)
    print("Creating individual PDFs per group...")
    
    # Group messages by group name
    groups = {}
    for msg in messages:
        group = msg.get('group', 'Unknown')
        if group not in groups:
            groups[group] = []
        groups[group].append(msg)
    
    for group_name, group_messages in groups.items():
        generate_group_pdf(group_name, group_messages, BASE_DIR)


if __name__ == "__main__":
    main()
