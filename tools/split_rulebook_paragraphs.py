"""
Split multi-paragraph rulebook entries into individual paragraph entries
so that the plugin's lookup works when the game sends each paragraph as a
separate TMP_Text component.

Reads overlay.tsv, finds E-type entries with multi-line text, splits them
into paragraphs, and writes back with individual paragraph entries prepended.
"""

import csv
import re
import sys
import os

OVERLAY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "AscensionGame_Data", "StreamingAssets", "zh-cn", "overlay.tsv"
)

def unescape(s):
    return s.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")

def escape(s):
    return s.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")

def split_paragraphs(text):
    """Split a multi-paragraph text into individual paragraphs.
    Separators: blank lines (\\r\\r or \\n\\n), or single \\r or \\n when
    they separate distinct blocks."""
    # First normalize: replace \r\n\n, \n\n, \r\r patterns with a unique sep
    # We split on blank-line patterns (two consecutive newlines with optional \r)
    paragraphs = re.split(r'\r?\n\r?\n|\r\r+', text)
    result = []
    for p in paragraphs:
        p = p.strip()
        if len(p) >= 80:  # Only keep paragraphs that are long enough to be meaningful
            result.append(p)
    return result

def main():
    if not os.path.exists(OVERLAY):
        print(f"overlay.tsv not found at {OVERLAY}")
        sys.exit(1)

    with open(OVERLAY, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    # Parse existing entries
    entries = []
    for line in lines:
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            entries.append(('comment', line))
            continue
        parts = line.split('\t')
        if len(parts) < 3:
            entries.append(('other', line))
            continue
        kind = parts[0]
        src = unescape(parts[1])
        zh = unescape(parts[2])
        entries.append((kind, src, zh, line))

    # Find multi-paragraph E entries
    split_count = 0
    new_entries = []
    existing_texts = set()

    # First pass: collect all existing source texts (normalized)
    for e in entries:
        if e[0] == 'E':
            kind, src, zh, line = e
            existing_texts.add(src.strip())

    # Process entries
    for e in entries:
        if e[0] != 'E':
            new_entries.append(e[-1] if len(e) > 3 else '')
            continue

        kind, src, zh, line = e
        # Check if this is a multi-paragraph entry
        if len(src) > 200 and ('\n' in src or '\r' in src):
            paragraphs = split_paragraphs(src)
            if len(paragraphs) >= 2:
                split_count += 1
                # For each paragraph, check if it already exists
                for i, para in enumerate(paragraphs):
                    if para.strip() not in existing_texts:
                        # Add as new E entry with same Chinese translation
                        # (will need translation work, but at least the
                        # matching will work)
                        para_escaped = escape(para)
                        # We use the full zh as placeholder — user will need
                        # to translate individual paragraphs. But we also
                        # store the paragraph index so we can correlate.
                        new_entries.append(f"E\t{para_escaped}\t{escape(zh)}")
                        existing_texts.add(para.strip())
                    split_count += 1
        new_entries.append(line)

    # Write back
    with open(OVERLAY, 'w', encoding='utf-8-sig') as f:
        for entry in new_entries:
            f.write(entry + '\n')

    print(f"Split {split_count} paragraphs from multi-paragraph rulebook entries.")
    print(f"Total entries in overlay: {len(new_entries)}")

if __name__ == '__main__':
    main()
