#!/usr/bin/env python3
"""
Test script for new stitch line and QR code functionality
"""

from mitsubishi_100_parser import Mitsubishi100Parser

def test_stitch_line():
    """Test the stitch line functionality."""
    print("Testing stitch line functionality...")

    parser = Mitsubishi100Parser()
    parser.create_new_pattern()

    # Test a simple horizontal line
    print("Creating horizontal stitch line from (0,0) to (60,0)...")
    parser.add_stitch_line(0, 0, 60, 0, stitch_spacing=20.0)

    print(f"Generated {len(parser.commands)} commands")
    for i, cmd in enumerate(parser.commands):
        print(f"  {i}: {cmd.command_type.value} at ({cmd.x}, {cmd.y})")

    # Test a diagonal line
    print("\nCreating diagonal stitch line from (0,0) to (40,40)...")
    parser.add_stitch_line(0, 0, 40, 40, stitch_spacing=20.0)

    print(f"Now has {len(parser.commands)} commands total")

    # Save and verify
    try:
        parser.save_to_file("test_stitch_line.001")
        print("Successfully saved stitch line pattern")
    except Exception as e:
        print(f"Error saving: {e}")

def test_qr_pattern():
    """Test the QR pattern functionality."""
    print("\nTesting QR pattern functionality...")

    parser = Mitsubishi100Parser()
    parser.create_new_pattern()

    # Generate a simple QR pattern
    test_text = "TEST"
    print(f"Generating QR pattern for text: '{test_text}'")
    parser.generate_simple_qr_pattern(test_text, center_x=0, center_y=0, module_size=8, stitch_spacing=10.0)

    print(f"Generated {len(parser.commands)} commands")

    # Show first few and last few commands
    print("First 10 commands:")
    for i, cmd in enumerate(parser.commands[:10]):
        print(f"  {i}: {cmd.command_type.value} at ({cmd.x}, {cmd.y})")

    if len(parser.commands) > 10:
        print(f"... ({len(parser.commands) - 10} more commands)")

    # Check bounds
    if parser.commands:
        x_coords = [cmd.x for cmd in parser.commands]
        y_coords = [cmd.y for cmd in parser.commands]
        print(f"Pattern bounds: X [{min(x_coords)}, {max(x_coords)}], Y [{min(y_coords)}, {max(y_coords)}]")

        # Check if within 20x20mm (200x200 units) bounds
        max_coord = max(abs(min(x_coords)), abs(max(x_coords)), abs(min(y_coords)), abs(max(y_coords)))
        if max_coord <= 100:
            print("Pattern fits within 20x20mm stitch area")
        else:
            print(f"Pattern extends beyond 20x20mm area (max coordinate: {max_coord})")

    # Save and verify
    try:
        parser.save_to_file("test_qr_pattern.002")
        print("Successfully saved QR pattern")
    except Exception as e:
        print(f"Error saving: {e}")

def test_combined_pattern():
    """Test combining both features in one pattern."""
    print("\nTesting combined pattern with both features...")

    parser = Mitsubishi100Parser()
    parser.create_new_pattern()

    # Add a border using stitch lines
    print("Creating border with stitch lines...")
    border_size = 80  # 8mm border
    spacing = 20      # 2mm stitch spacing

    # Top border
    parser.add_stitch_line(-border_size, border_size, border_size, border_size, spacing)
    # Right border
    parser.add_stitch_line(border_size, border_size, border_size, -border_size, spacing)
    # Bottom border
    parser.add_stitch_line(border_size, -border_size, -border_size, -border_size, spacing)
    # Left border
    parser.add_stitch_line(-border_size, -border_size, -border_size, border_size, spacing)

    print(f"Border created with {len(parser.commands)} commands")

    # Add QR pattern in center
    print("Adding QR pattern in center...")
    parser.generate_simple_qr_pattern("COMBINED", center_x=0, center_y=0, module_size=6, stitch_spacing=8.0)

    print(f"Combined pattern has {len(parser.commands)} total commands")

    # Add ending sequence
    parser.add_full_ending_sequence(8)
    print(f"With ending sequence: {len(parser.commands)} commands")

    # Save
    try:
        parser.save_to_file("test_combined.003")
        print("Successfully saved combined pattern")
    except Exception as e:
        print(f"Error saving: {e}")

if __name__ == "__main__":
    test_stitch_line()
    test_qr_pattern()
    test_combined_pattern()
    print("\nAll tests completed!")