#!/usr/bin/env python3
"""
Test script to verify pattern saving works correctly
"""

from mitsubishi_100_parser import Mitsubishi100Parser, CommandType

def test_save():
    """Test saving a simple pattern."""
    parser = Mitsubishi100Parser()

    # Create a simple pattern
    parser.create_new_pattern()

    # Add some commands
    parser.add_stitch(0, 0)
    parser.add_stitch(10, 10)
    parser.add_move(20, 20)
    parser.add_stitch(30, 30)
    parser.add_color_change()
    parser.add_stitch(40, 40)

    print(f"Created pattern with {len(parser.commands)} commands")

    # Try to save it
    test_filename = "test_pattern.001"
    try:
        parser.save_to_file(test_filename)
        print(f"Successfully saved pattern to {test_filename}")

        # Try to read it back
        parser2 = Mitsubishi100Parser()
        commands = parser2.parse_file(test_filename)
        print(f"Successfully read back pattern with {len(commands)} commands")

        # Show the commands
        for i, cmd in enumerate(commands):
            if cmd.command_type in [CommandType.STITCH, CommandType.MOVE]:
                print(f"  {i}: {cmd.command_type.value} at ({cmd.x}, {cmd.y})")
            else:
                print(f"  {i}: {cmd.command_type.value}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_save()