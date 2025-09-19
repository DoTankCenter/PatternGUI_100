#!/usr/bin/env python3
"""
Pattern File Analyzer - Examine raw binary data for special control codes
"""

import os
import struct
from typing import List, Tuple

def hex_dump(data: bytes, offset: int = 0, width: int = 16) -> str:
    """Create a hex dump of binary data."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        lines.append(f'{offset+i:08x}  {hex_part:<{width*3-1}}  {ascii_part}')
    return '\n'.join(lines)

def analyze_pattern_ending(filename: str, last_bytes: int = 100) -> None:
    """Analyze the last bytes of a pattern file."""
    try:
        with open(filename, 'rb') as f:
            # Get file size
            f.seek(0, 2)
            file_size = f.tell()

            # Read the last bytes
            read_size = min(last_bytes, file_size)
            f.seek(file_size - read_size)
            data = f.read(read_size)

            print(f"\n{'='*60}")
            print(f"File: {filename}")
            print(f"Size: {file_size} bytes")
            print(f"Last {read_size} bytes:")
            print(f"{'='*60}")

            # Show hex dump
            start_offset = file_size - read_size
            print(hex_dump(data, start_offset))

            # Parse as 4-byte commands
            print(f"\nParsed as 4-byte commands:")
            print(f"{'Offset':<8} {'Cmd':<4} {'B1':<4} {'X':<4} {'Y':<4} {'Notes'}")
            print(f"{'-'*40}")

            for i in range(0, len(data), 4):
                if i + 3 < len(data):
                    chunk = data[i:i+4]
                    cmd, b1, x, y = struct.unpack('<BBBB', chunk)
                    offset = start_offset + i

                    # Decode coordinates
                    x_val = x if x <= 0x80 else -(x - 0x80)
                    y_val = y if y <= 0x80 else -(y - 0x80)
                    y_val = -y_val  # Y is negated

                    notes = []
                    if cmd == 0x61:
                        notes.append("STITCH")
                    elif cmd & 0x01:
                        notes.append("MOVE")
                    elif cmd % 2 == 0:
                        notes.append("COLOR_CHANGE")

                    # Check for special patterns
                    if cmd == 0x00:
                        notes.append("NULL/END?")
                    if x == 0 and y == 0:
                        notes.append("ZERO_COORDS")
                    if chunk == b'\x00\x00\x00\x00':
                        notes.append("ALL_ZEROS")

                    print(f"{offset:08x} {cmd:02x}   {b1:02x}   {x:02x}   {y:02x}   {' '.join(notes)}")

            # Look for specific end patterns
            print(f"\nSpecial pattern analysis:")

            # Check last few 4-byte chunks for patterns
            last_16_bytes = data[-16:] if len(data) >= 16 else data
            print(f"Last 16 bytes: {last_16_bytes.hex()}")

            # Look for repeated patterns
            for pattern_len in [1, 2, 4]:
                if len(data) >= pattern_len * 2:
                    for start in range(len(data) - pattern_len * 2, -1, -pattern_len):
                        pattern = data[start:start+pattern_len]
                        next_pattern = data[start+pattern_len:start+pattern_len*2]
                        if pattern == next_pattern:
                            print(f"Repeated {pattern_len}-byte pattern at end: {pattern.hex()}")
                            break

    except Exception as e:
        print(f"Error analyzing {filename}: {e}")

def compare_pattern_endings(directory: str = "Patterns") -> None:
    """Compare endings of multiple pattern files."""
    if not os.path.exists(directory):
        directory = "."

    pattern_files = []
    for file in os.listdir(directory):
        if any(file.endswith(f'.{ext}') for ext in ['100'] + [f'{i:03d}' for i in range(1, 301)]):
            pattern_files.append(os.path.join(directory, file))

    if not pattern_files:
        print("No pattern files found")
        return

    print(f"Found {len(pattern_files)} pattern files to analyze:")
    for file in pattern_files:
        print(f"  - {file}")

    # Analyze each file
    for filename in pattern_files:
        analyze_pattern_ending(filename)

    # Summary comparison
    print(f"\n{'='*60}")
    print("SUMMARY COMPARISON OF FILE ENDINGS")
    print(f"{'='*60}")

    endings = {}
    for filename in pattern_files:
        try:
            with open(filename, 'rb') as f:
                f.seek(-16, 2)  # Last 16 bytes
                ending = f.read()
                endings[filename] = ending.hex()
        except:
            endings[filename] = "ERROR"

    # Group by ending pattern
    ending_groups = {}
    for filename, ending in endings.items():
        if ending not in ending_groups:
            ending_groups[ending] = []
        ending_groups[ending].append(filename)

    for ending, files in ending_groups.items():
        print(f"\nEnding pattern: {ending}")
        print(f"Files with this ending:")
        for file in files:
            print(f"  - {os.path.basename(file)}")

if __name__ == "__main__":
    compare_pattern_endings()