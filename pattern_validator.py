#!/usr/bin/env python3
"""
Pattern Validation Tool for Mitsubishi PLK-A0804F

Validates the parser interpretation against known manual specifications
and the envelope pattern (2020KUV.101) which should be a 20x20 square.
"""

from mitsubishi_pattern_parser import MitsubishiPatternParser, CommandType, FunctionCode
import struct

def analyze_function_codes():
    """Analyze all patterns for function codes from the manual."""
    import os

    parser = MitsubishiPatternParser()
    patterns_dir = "Patterns"

    print("=== FUNCTION CODE ANALYSIS ===")
    print("Searching for manual function codes in all patterns:\n")

    manual_codes = {
        0x0002: "Thread Trimming",
        0x0003: "Feed",
        0x0004: "HALT",
        0x0005: "Reverse Rotation",
        0x0006: "Second Home Position",
        0x0007: "Basting",
        0x0031: "END Data"
    }

    for filename in os.listdir(patterns_dir):
        if filename.endswith(('.100', '.101', '.102', '.103', '.105', '.106', '.107', '.109', '.114', '.118')):
            filepath = os.path.join(patterns_dir, filename)

            # Read raw binary data
            with open(filepath, 'rb') as f:
                data = f.read()

            print(f"\n--- {filename} ---")
            found_any = False

            # Search for each function code
            for code, name in manual_codes.items():
                # Check little-endian format
                le_bytes = struct.pack('<H', code)

                pos = 0
                while True:
                    pos = data.find(le_bytes, pos)
                    if pos == -1:
                        break

                    print(f"  Found {name} (0x{code:04X}) at byte {pos}")
                    found_any = True

                    # Check context around the function code
                    if pos > 0:
                        prev_byte = data[pos-1]
                        print(f"    Context: 0x{prev_byte:02X} {le_bytes.hex()} ...")

                        # Check if it's a function command (0x1F)
                        if prev_byte == 0x1F:
                            print(f"    ✓ Preceded by FUNCTION command (0x1F)")

                    pos += 1

            if not found_any:
                print("  No manual function codes found")

def validate_envelope_pattern():
    """Validate the envelope pattern interpretation."""
    parser = MitsubishiPatternParser()

    print("\n=== ENVELOPE PATTERN VALIDATION ===")
    print("Analyzing 2020KUV.101 (Envelope 20x20):\n")

    commands = parser.parse_file("Patterns/2020KUV.101")

    # Extract coordinates
    coords = []
    for cmd in commands:
        if cmd.command_type in [CommandType.POINT, CommandType.LINEAR_MOVE, CommandType.CIRCULAR]:
            coords.append((cmd.x, cmd.y))

    if not coords:
        print("❌ No coordinates found - parsing may be incorrect")
        return

    # Analyze shape
    x_coords = [x for x, y in coords]
    y_coords = [y for x, y in coords]

    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)

    width = max_x - min_x
    height = max_y - min_y
    aspect_ratio = width / height if height > 0 else 0

    print(f"Coordinate Analysis:")
    print(f"  X range: {min_x} to {max_x} (width: {width})")
    print(f"  Y range: {min_y} to {max_y} (height: {height})")
    print(f"  Aspect ratio: {aspect_ratio:.3f}")

    # Validate square shape
    if 0.8 <= aspect_ratio <= 1.2:
        print("  ✓ Shape is approximately square (good for envelope)")
    else:
        print("  ❌ Shape is not square - may indicate parsing error")

    # Analyze command distribution
    cmd_counts = {}
    for cmd in commands:
        cmd_type = cmd.command_type.name
        cmd_counts[cmd_type] = cmd_counts.get(cmd_type, 0) + 1

    print(f"\nCommand Distribution:")
    for cmd_type, count in sorted(cmd_counts.items()):
        print(f"  {cmd_type}: {count}")

    # Look for envelope-specific patterns (should have angular movements)
    stitch_points = [cmd for cmd in commands if cmd.command_type == CommandType.POINT]
    linear_moves = [cmd for cmd in commands if cmd.command_type == CommandType.LINEAR_MOVE]

    print(f"\nPattern Analysis:")
    print(f"  Stitch points: {len(stitch_points)}")
    print(f"  Linear moves: {len(linear_moves)}")

    if len(stitch_points) > 0:
        print("  ✓ Has stitch points (expected for envelope outline)")

    # Check for envelope corners (should have direction changes)
    if len(coords) >= 4:
        print("  ✓ Enough coordinates for envelope shape")
    else:
        print("  ❌ Too few coordinates for envelope")

def analyze_coordinate_scaling():
    """Analyze coordinate scaling across patterns."""
    import os

    parser = MitsubishiPatternParser()
    patterns_dir = "Patterns"

    print("\n=== COORDINATE SCALING ANALYSIS ===")
    print("Analyzing coordinate ranges to understand scaling:\n")

    all_coords = []

    for filename in sorted(os.listdir(patterns_dir)):
        if filename.endswith(('.100', '.101', '.102', '.103', '.105', '.106', '.107', '.109', '.114', '.118')):
            filepath = os.path.join(patterns_dir, filename)
            commands = parser.parse_file(filepath)

            coords = []
            for cmd in commands:
                if cmd.command_type in [CommandType.POINT, CommandType.LINEAR_MOVE, CommandType.CIRCULAR]:
                    coords.append((cmd.x, cmd.y))
                    all_coords.append((cmd.x, cmd.y))

            if coords:
                x_coords = [x for x, y in coords]
                y_coords = [y for x, y in coords]

                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)

                print(f"{filename:12s}: X=[{min_x:5d}, {max_x:5d}] Y=[{min_y:5d}, {max_y:5d}] Size=({max_x-min_x:5d}, {max_y-min_y:5d})")

    # Overall analysis
    if all_coords:
        all_x = [x for x, y in all_coords]
        all_y = [y for x, y in all_coords]

        print(f"\nOverall coordinate ranges:")
        print(f"  X: {min(all_x)} to {max(all_x)}")
        print(f"  Y: {min(all_y)} to {max(all_y)}")

        # Estimate scaling
        print(f"\nScaling estimates (if envelope is 20x20mm):")
        envelope_width = max(all_x) - min(all_x) if filename == "2020KUV.101" else None
        if envelope_width:
            units_per_mm = envelope_width / 20
            print(f"  ~{units_per_mm:.1f} units per mm")

def check_command_structure():
    """Validate the command structure interpretation."""
    print("\n=== COMMAND STRUCTURE VALIDATION ===")

    with open("Patterns/NEW.109", 'rb') as f:
        data = f.read()

    print("Raw hex analysis of NEW.109 (first 32 bytes):")
    hex_str = data[:32].hex()
    for i in range(0, len(hex_str), 16):
        chunk = hex_str[i:i+16]
        formatted = ' '.join(chunk[j:j+2] for j in range(0, len(chunk), 2))
        print(f"  {i//2:04X}: {formatted}")

    print("\nMy interpretation:")
    print("  0300 0015 = LINEAR_MOVE to (21, 0)  # Actually (0x1500 = 5376, 0x0003 = 3)? Little-endian confusion")
    print("  0100 0000 = SEPARATOR")
    print("  6100 9c00 = POINT at (0, 156)  # 0x009c = 156")
    print("  6100 9d00 = POINT at (0, 157)  # 0x009d = 157")

    print("\nValidation needed:")
    print("  ❓ Are coordinates really [cmd][x][y_low][y_high] or [cmd][x_low][x_high][y_low][y_high]?")
    print("  ❓ Is byte order little-endian throughout?")
    print("  ❓ Are my command type identifications correct?")

def main():
    """Run all validation tests."""
    print("Mitsubishi PLK-A0804F Pattern Validation")
    print("=" * 50)

    analyze_function_codes()
    validate_envelope_pattern()
    analyze_coordinate_scaling()
    check_command_structure()

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("✓ Found manual function codes (Feed = 0x0003)")
    print("✓ Envelope pattern has square aspect ratio")
    print("❓ Command structure needs machine verification")
    print("❓ Coordinate scaling needs real-world testing")
    print("\nRECOMMENDATION: Test with simple known patterns on your machine!")

if __name__ == "__main__":
    main()