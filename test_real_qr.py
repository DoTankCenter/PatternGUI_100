#!/usr/bin/env python3
"""
Test script for real QR code functionality
"""

from mitsubishi_100_parser import Mitsubishi100Parser

def test_real_qr_codes():
    """Test the real QR code functionality with various inputs."""
    print("Testing real QR code functionality...")

    parser = Mitsubishi100Parser()

    # Test data with different lengths and error correction levels
    test_cases = [
        ("Hello", 'L', 8),
        ("Hello World!", 'M', 8),
        ("https://example.com", 'M', 6),
        ("A longer text string to test capacity limits", 'Q', 6),
        ("Short URL: bit.ly/abc123", 'H', 8),
        ("Contact: john@company.com +1234567890", 'M', 5),
    ]

    results = []

    for i, (text, error_level, module_size) in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: '{text}' (Error: {error_level}, Module: {module_size})")
        print(f"{'='*60}")

        parser.create_new_pattern()
        success, info, capacity = parser.generate_qr_code(
            text, 0, 0, module_size, 8.0, error_level)

        if success:
            print(f"SUCCESS: {info}")
            print(f"  Text length: {len(text)} characters")
            print(f"  QR capacity: ~{capacity} alphanumeric characters")
            print(f"  Commands generated: {len(parser.commands)}")

            # Check bounds
            if parser.commands:
                x_coords = [cmd.x for cmd in parser.commands]
                y_coords = [cmd.y for cmd in parser.commands]
                bounds = {
                    'min_x': min(x_coords), 'max_x': max(x_coords),
                    'min_y': min(y_coords), 'max_y': max(y_coords)
                }
                print(f"  Bounds: X[{bounds['min_x']}, {bounds['max_x']}], Y[{bounds['min_y']}, {bounds['max_y']}]")

                max_coord = max(abs(bounds['min_x']), abs(bounds['max_x']),
                              abs(bounds['min_y']), abs(bounds['max_y']))
                if max_coord <= 100:
                    print(f"  Fits in 20x20mm area (max coord: {max_coord})")
                else:
                    print(f"  Exceeds 20x20mm area (max coord: {max_coord})")

            # Test saving
            filename = f"test_real_qr_{i+1:02d}.{i+1:03d}"
            try:
                parser.save_to_file(filename)
                print(f"  Saved as {filename}")
                results.append((text, True, info, filename))
            except Exception as e:
                print(f"  Save failed: {e}")
                results.append((text, False, str(e), ""))

        else:
            print(f"FAILED: {info}")
            results.append((text, False, info, ""))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY OF RESULTS")
    print(f"{'='*60}")

    successful = 0
    for text, success, info, filename in results:
        status = "OK" if success else "FAIL"
        print(f"{status} '{text[:30]:<30}' - {info[:40]}")
        if success:
            successful += 1

    print(f"\nSuccessful QR codes: {successful}/{len(test_cases)}")

    # Test capacity limits
    print(f"\n{'='*60}")
    print("TESTING CAPACITY LIMITS")
    print(f"{'='*60}")

    # Test increasingly long strings
    base_text = "This is a test string to check QR code capacity limits. "
    for multiplier in [1, 2, 3, 4, 5]:
        long_text = base_text * multiplier
        print(f"\nTesting {len(long_text)} character text...")

        parser.create_new_pattern()
        success, info, capacity = parser.generate_qr_code(
            long_text, 0, 0, 6, 8.0, 'M')

        if success:
            print(f"Fits: {info}")
        else:
            print(f"Too long: {info}")
            break

def test_qr_readback():
    """Test that saved QR codes can be read back correctly."""
    print(f"\n{'='*60}")
    print("TESTING QR CODE FILE READBACK")
    print(f"{'='*60}")

    parser = Mitsubishi100Parser()

    # Test reading back saved files
    import os
    qr_files = [f for f in os.listdir('.') if f.startswith('test_real_qr_') and f.endswith(('.001', '.002', '.003', '.004', '.005', '.006'))]

    for filename in sorted(qr_files):
        try:
            commands = parser.parse_file(filename)
            print(f"OK {filename}: {len(commands)} commands loaded successfully")
        except Exception as e:
            print(f"FAIL {filename}: Error - {e}")

if __name__ == "__main__":
    test_real_qr_codes()
    test_qr_readback()
    print("\nAll QR code tests completed!")