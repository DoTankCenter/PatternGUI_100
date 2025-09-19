#!/usr/bin/env python3
"""
Test script for backtack functionality
"""

from mitsubishi_100_parser import Mitsubishi100Parser, CommandType

def test_backtack():
    """Test the backtack and pattern end functionality."""
    parser = Mitsubishi100Parser()

    # Create a simple pattern with stitches
    parser.create_new_pattern()

    print("Creating test pattern...")

    # Add some stitches to create a seam
    parser.add_stitch(0, 0)
    parser.add_stitch(10, 0)
    parser.add_stitch(20, 0)
    parser.add_stitch(30, 0)
    parser.add_stitch(40, 0)

    print(f"Pattern has {len(parser.commands)} commands")

    # Test individual backtack
    print("\nTesting individual backtack...")
    parser.add_backtack(5, 3)
    print(f"After backtack: {len(parser.commands)} commands")

    # Test pattern end
    print("\nTesting pattern end...")
    parser.add_pattern_end()
    print(f"After pattern end: {len(parser.commands)} commands")

    # Show all commands
    print("\nAll commands:")
    for i, cmd in enumerate(parser.commands):
        if cmd.command_type in [CommandType.STITCH, CommandType.MOVE, CommandType.BACKTACK]:
            print(f"  {i:2d}: {cmd.command_type.value:12s} at ({cmd.x:3d}, {cmd.y:3d})")
        else:
            print(f"  {i:2d}: {cmd.command_type.value:12s}")

    # Test saving
    print("\nTesting save...")
    try:
        parser.save_to_file("test_backtack.001")
        print("Successfully saved pattern with backtack")

        # Test loading back
        parser2 = Mitsubishi100Parser()
        commands = parser2.parse_file("test_backtack.001")
        print(f"Successfully loaded back: {len(commands)} commands")

        print("\nLoaded commands:")
        for i, cmd in enumerate(commands):
            if cmd.command_type in [CommandType.STITCH, CommandType.MOVE, CommandType.BACKTACK]:
                print(f"  {i:2d}: {cmd.command_type.value:12s} at ({cmd.x:3d}, {cmd.y:3d})")
            else:
                print(f"  {i:2d}: {cmd.command_type.value:12s}")

    except Exception as e:
        print(f"Error: {e}")

    # Test full ending sequence
    print("\n" + "="*50)
    print("Testing full ending sequence...")

    parser3 = Mitsubishi100Parser()
    parser3.create_new_pattern()

    # Add a simple line of stitches
    for x in range(0, 50, 10):
        parser3.add_stitch(x, 0)

    print(f"Pattern before ending: {len(parser3.commands)} commands")

    # Add full ending sequence
    parser3.add_full_ending_sequence(8)

    print(f"Pattern after ending: {len(parser3.commands)} commands")

    print("\nFull ending sequence commands:")
    for i, cmd in enumerate(parser3.commands[-15:], len(parser3.commands)-15):  # Show last 15 commands
        if cmd.command_type in [CommandType.STITCH, CommandType.MOVE, CommandType.BACKTACK]:
            print(f"  {i:2d}: {cmd.command_type.value:12s} at ({cmd.x:3d}, {cmd.y:3d})")
        else:
            print(f"  {i:2d}: {cmd.command_type.value:12s}")

    # Test saving full ending
    try:
        parser3.save_to_file("test_full_ending.002")
        print("\nSuccessfully saved pattern with full ending sequence")
    except Exception as e:
        print(f"Error saving: {e}")

if __name__ == "__main__":
    test_backtack()