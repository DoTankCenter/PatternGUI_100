#!/usr/bin/env python3
"""
Test script for the Mitsubishi .100 format parser
"""

import os
from mitsubishi_100_parser import Mitsubishi100Parser, CommandType


def test_parser():
    """Test the .100 format parser with available files."""
    parser = Mitsubishi100Parser()

    # Look for .100 files in current directory and Patterns folder
    test_files = []

    # Check current directory
    for file in os.listdir('.'):
        if any(file.endswith(f'.{i:03d}') for i in range(1, 301)) or file.endswith('.100'):
            test_files.append(file)

    # Check Patterns folder if it exists
    if os.path.exists('Patterns'):
        for file in os.listdir('Patterns'):
            if any(file.endswith(f'.{i:03d}') for i in range(1, 301)) or file.endswith('.100'):
                test_files.append(os.path.join('Patterns', file))

    if not test_files:
        print("No pattern files found to test (.001-.300 or .100)")
        return

    print(f"Found {len(test_files)} .100 files to test:")
    for file in test_files:
        print(f"  - {file}")

    print("\n" + "="*50)

    # Test each file
    for filename in test_files:
        print(f"\nTesting file: {filename}")
        print("-" * 40)

        try:
            commands = parser.parse_file(filename)
            stats = parser.get_pattern_stats()
            bounds = parser.get_pattern_bounds()

            print(f"Successfully parsed: {filename}")
            print(f"Total commands: {stats['total_commands']}")
            print(f"Stitches: {stats['stitch_count']}")
            print(f"Moves: {stats['move_count']}")
            print(f"Color changes: {stats['color_changes']}")
            print(f"Path length: {stats['path_length']:.1f}")
            print(f"Bounds: X({bounds[0]} to {bounds[2]}), Y({bounds[1]} to {bounds[3]})")
            print(f"Size: {bounds[2]-bounds[0]} x {bounds[3]-bounds[1]}")

            # Show first few commands
            print(f"\nFirst 10 commands:")
            for i, cmd in enumerate(commands[:10]):
                if cmd.command_type in [CommandType.STITCH, CommandType.MOVE]:
                    print(f"  {i:2d}: {cmd.command_type.value:12s} ({cmd.x:5d}, {cmd.y:5d})")
                else:
                    print(f"  {i:2d}: {cmd.command_type.value:12s}")

            if len(commands) > 10:
                print(f"  ... and {len(commands) - 10} more commands")

        except Exception as e:
            print(f"Error parsing {filename}: {e}")


if __name__ == "__main__":
    test_parser()