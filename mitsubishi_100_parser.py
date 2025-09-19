#!/usr/bin/env python3
"""
Simplified Mitsubishi .100 Pattern File Parser

Based on the correct format interpretation from external software.
Uses the actual .100 format structure: 4-byte commands with simple coordinate encoding.
"""

from typing import BinaryIO, List, Tuple
from enum import Enum
from dataclasses import dataclass


class CommandType(Enum):
    """Command types for .100 format patterns."""
    STITCH = "STITCH"
    MOVE = "MOVE"
    COLOR_CHANGE = "COLOR_CHANGE"
    BACKTACK = "BACKTACK"
    END = "END"
    PATTERN_END = "PATTERN_END"  # 0x1F terminator


@dataclass
class PatternCommand:
    """Represents a single pattern command."""
    command_type: CommandType
    x: int = 0
    y: int = 0
    raw_bytes: bytes = None


class Mitsubishi100Parser:
    """Parser for Mitsubishi .100 format pattern files."""

    def __init__(self):
        self.commands = []
        self.current_x = 0
        self.current_y = 0

    def parse_file(self, filename: str) -> List[PatternCommand]:
        """Parse a .100 format file and return list of commands."""
        self.commands = []
        self.current_x = 0
        self.current_y = 0

        with open(filename, 'rb') as f:
            self._read_100_stitches(f)

        return self.commands

    def _read_100_stitches(self, f: BinaryIO):
        """Read stitches from .100 format file."""
        count = 0

        while True:
            count += 1
            b = bytearray(f.read(4))
            if len(b) != 4:
                break

            # Extract coordinates (bytes 2 and 3)
            x = b[2]
            y = b[3]

            # Handle sign encoding (0x80 bit indicates negative)
            if x > 0x80:
                x -= 0x80
                x = -x
            if y > 0x80:
                y -= 0x80
                y = -y

            # Y coordinate is negated in the format
            y = -y

            # Update absolute position
            self.current_x += x
            self.current_y += y

            # Determine command type based on first byte
            if b[0] == 0x61:
                # Stitch command
                cmd = PatternCommand(
                    command_type=CommandType.STITCH,
                    x=self.current_x,
                    y=self.current_y,
                    raw_bytes=bytes(b)
                )
                self.commands.append(cmd)

            elif b[0] == 0x1F:
                # Pattern end command (terminator)
                cmd = PatternCommand(
                    command_type=CommandType.PATTERN_END,
                    x=self.current_x,
                    y=self.current_y,
                    raw_bytes=bytes(b)
                )
                self.commands.append(cmd)
                break  # End of pattern

            elif b[0] == 0x03:
                # Backtack moves (rapid moves for thread securing)
                cmd = PatternCommand(
                    command_type=CommandType.BACKTACK,
                    x=self.current_x,
                    y=self.current_y,
                    raw_bytes=bytes(b)
                )
                self.commands.append(cmd)

            elif (b[0] & 0x01) != 0:
                # Move command (any odd-numbered command except 0x61 and 0x03)
                cmd = PatternCommand(
                    command_type=CommandType.MOVE,
                    x=self.current_x,
                    y=self.current_y,
                    raw_bytes=bytes(b)
                )
                self.commands.append(cmd)

            else:
                # Color change (even-numbered commands except 0x61)
                cmd = PatternCommand(
                    command_type=CommandType.COLOR_CHANGE,
                    x=self.current_x,
                    y=self.current_y,
                    raw_bytes=bytes(b)
                )
                self.commands.append(cmd)

        # Add end command
        end_cmd = PatternCommand(command_type=CommandType.END)
        self.commands.append(end_cmd)

    def get_pattern_bounds(self) -> Tuple[int, int, int, int]:
        """Get the bounding box of the pattern (min_x, min_y, max_x, max_y)."""
        if not self.commands:
            return (0, 0, 0, 0)

        coords = [(cmd.x, cmd.y) for cmd in self.commands
                 if cmd.command_type in [CommandType.STITCH, CommandType.MOVE]]

        if not coords:
            return (0, 0, 0, 0)

        x_coords = [x for x, y in coords]
        y_coords = [y for x, y in coords]

        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

    def get_pattern_stats(self) -> dict:
        """Get statistics about the pattern."""
        stats = {
            'total_commands': len(self.commands),
            'stitch_count': 0,
            'move_count': 0,
            'color_changes': 0,
            'path_length': 0.0
        }

        last_x, last_y = 0, 0

        for cmd in self.commands:
            if cmd.command_type == CommandType.STITCH:
                stats['stitch_count'] += 1
                if last_x != 0 or last_y != 0:
                    dx = cmd.x - last_x
                    dy = cmd.y - last_y
                    stats['path_length'] += (dx*dx + dy*dy) ** 0.5
                last_x, last_y = cmd.x, cmd.y

            elif cmd.command_type == CommandType.MOVE:
                stats['move_count'] += 1
                if last_x != 0 or last_y != 0:
                    dx = cmd.x - last_x
                    dy = cmd.y - last_y
                    stats['path_length'] += (dx*dx + dy*dy) ** 0.5
                last_x, last_y = cmd.x, cmd.y

            elif cmd.command_type == CommandType.COLOR_CHANGE:
                stats['color_changes'] += 1

        return stats

    def save_to_file(self, filename: str):
        """Save pattern to .100 format file."""
        with open(filename, 'wb') as f:
            for cmd in self.commands:
                if cmd.raw_bytes:
                    f.write(cmd.raw_bytes)
                else:
                    # Generate raw bytes for commands that don't have them
                    raw_bytes = self._generate_raw_bytes(cmd)
                    if raw_bytes:
                        f.write(raw_bytes)

    def _generate_raw_bytes(self, cmd: PatternCommand) -> bytes:
        """Generate raw bytes for a command."""
        if cmd.command_type == CommandType.END:
            return b''  # End commands don't write bytes

        # Calculate delta from previous position
        prev_x = getattr(self, '_last_save_x', 0)
        prev_y = getattr(self, '_last_save_y', 0)

        delta_x = cmd.x - prev_x
        delta_y = cmd.y - prev_y

        # Update last position for next command
        self._last_save_x = cmd.x
        self._last_save_y = cmd.y

        # Handle coordinate encoding to match the reading logic exactly
        # Reading logic:
        # if x > 0x80: x -= 0x80; x = -x
        # if y > 0x80: y -= 0x80; y = -y
        # y = -y  (Y is negated in format)

        # Limit delta movements to prevent overflow
        delta_x = max(-127, min(127, delta_x))
        delta_y = max(-127, min(127, delta_y))

        # Encode X coordinate
        if delta_x >= 0:
            x_byte = delta_x
        else:
            x_byte = abs(delta_x) + 0x80

        # Encode Y coordinate (reverse the reading logic)
        # Since reading does: if y > 0x80: y -= 0x80; y = -y; then y = -y
        # We need to reverse this: negate first, then apply sign encoding
        neg_delta_y = -delta_y  # Negate for format
        if neg_delta_y >= 0:
            y_byte = neg_delta_y
        else:
            y_byte = abs(neg_delta_y) + 0x80

        # Determine command byte
        if cmd.command_type == CommandType.STITCH:
            cmd_byte = 0x61
        elif cmd.command_type == CommandType.MOVE:
            cmd_byte = 0x01  # Use odd number for move
        elif cmd.command_type == CommandType.COLOR_CHANGE:
            cmd_byte = 0x02  # Use even number for color change
        elif cmd.command_type == CommandType.BACKTACK:
            cmd_byte = 0x03  # Backtack moves
        elif cmd.command_type == CommandType.PATTERN_END:
            cmd_byte = 0x1F  # Pattern terminator
        else:
            cmd_byte = 0x01  # Default to move

        return bytes([cmd_byte, 0x00, x_byte, y_byte])

    def create_new_pattern(self):
        """Create a new empty pattern."""
        self.commands = []
        self.current_x = 0
        self.current_y = 0

    def add_stitch(self, x: int, y: int):
        """Add a stitch command at the specified coordinates."""
        cmd = PatternCommand(
            command_type=CommandType.STITCH,
            x=x,
            y=y
        )
        self.commands.append(cmd)

    def add_move(self, x: int, y: int):
        """Add a move command to the specified coordinates."""
        cmd = PatternCommand(
            command_type=CommandType.MOVE,
            x=x,
            y=y
        )
        self.commands.append(cmd)

    def add_color_change(self):
        """Add a color change command at the current position."""
        # Use the last position if available
        last_x, last_y = 0, 0
        if self.commands:
            for cmd in reversed(self.commands):
                if cmd.command_type in [CommandType.STITCH, CommandType.MOVE]:
                    last_x, last_y = cmd.x, cmd.y
                    break

        cmd = PatternCommand(
            command_type=CommandType.COLOR_CHANGE,
            x=last_x,
            y=last_y
        )
        self.commands.append(cmd)

    def add_backtack(self, length: int = 5, steps: int = 3):
        """Add a backtack sequence at the current position."""
        # Get the last few stitches to determine backtack direction
        recent_stitches = []
        for cmd in reversed(self.commands):
            if cmd.command_type == CommandType.STITCH and len(recent_stitches) < steps:
                recent_stitches.insert(0, (cmd.x, cmd.y))
            if len(recent_stitches) >= steps:
                break

        if len(recent_stitches) < 2:
            # Not enough stitches for backtack, add simple pattern
            current_x = self.commands[-1].x if self.commands else 0
            current_y = self.commands[-1].y if self.commands else 0

            for i in range(length):
                cmd = PatternCommand(
                    command_type=CommandType.BACKTACK,
                    x=current_x + (i % 2),  # Simple back-and-forth
                    y=current_y
                )
                self.commands.append(cmd)
        else:
            # Calculate backtack direction from recent stitches
            start_x, start_y = recent_stitches[-1]
            prev_x, prev_y = recent_stitches[-2] if len(recent_stitches) > 1 else recent_stitches[-1]

            # Calculate average step size
            dx = start_x - prev_x
            dy = start_y - prev_y
            step_size = max(1, int((dx*dx + dy*dy)**0.5))
            step_size = min(step_size, 10)  # Limit step size

            # Generate backtack moves
            for i in range(length):
                if i % 2 == 0:
                    # Move back along the seam
                    back_x = start_x - dx * (i // 2 + 1) // step_size
                    back_y = start_y - dy * (i // 2 + 1) // step_size
                else:
                    # Move forward
                    back_x = start_x + dx * (i // 2) // step_size
                    back_y = start_y + dy * (i // 2) // step_size

                cmd = PatternCommand(
                    command_type=CommandType.BACKTACK,
                    x=back_x,
                    y=back_y
                )
                self.commands.append(cmd)

    def add_pattern_end(self):
        """Add the final pattern terminator (0x1F)."""
        # Use the last position if available
        last_x, last_y = 0, 0
        if self.commands:
            for cmd in reversed(self.commands):
                if cmd.command_type in [CommandType.STITCH, CommandType.MOVE, CommandType.BACKTACK]:
                    last_x, last_y = cmd.x, cmd.y
                    break

        cmd = PatternCommand(
            command_type=CommandType.PATTERN_END,
            x=last_x,
            y=last_y
        )
        self.commands.append(cmd)

    def add_full_ending_sequence(self, backtack_length: int = 6):
        """Add a complete ending sequence: color change, backtack, and pattern end."""
        # Add color change to stop for thread cutting
        self.add_color_change()

        # Add backtack sequence to secure thread
        self.add_backtack(backtack_length)

        # Add final terminator
        self.add_pattern_end()

    def add_stitch_line(self, start_x: int, start_y: int, end_x: int, end_y: int,
                       stitch_spacing: float = 20.0):
        """Add a line of evenly distributed stitches between two points."""
        import math

        # Calculate line length
        dx = end_x - start_x
        dy = end_y - start_y
        line_length = math.sqrt(dx * dx + dy * dy)

        if line_length == 0:
            # Single point
            self.add_stitch(start_x, start_y)
            return

        # Calculate number of stitches needed
        num_stitches = max(2, int(line_length / stitch_spacing) + 1)

        # Generate stitches along the line
        for i in range(num_stitches):
            t = i / (num_stitches - 1) if num_stitches > 1 else 0
            x = int(start_x + t * dx)
            y = int(start_y + t * dy)
            self.add_stitch(x, y)

    def add_rectangle_stitches(self, center_x: int, center_y: int, width: int, height: int,
                              stitch_spacing: float = 20.0):
        """Add a rectangular pattern of stitches."""
        half_w = width // 2
        half_h = height // 2

        # Calculate corner positions
        corners = [
            (center_x - half_w, center_y - half_h),  # Top-left
            (center_x + half_w, center_y - half_h),  # Top-right
            (center_x + half_w, center_y + half_h),  # Bottom-right
            (center_x - half_w, center_y + half_h),  # Bottom-left
        ]

        # Add move to start position
        self.add_move(corners[0][0], corners[0][1])

        # Create stitched outline
        for i in range(len(corners)):
            start_corner = corners[i]
            end_corner = corners[(i + 1) % len(corners)]

            # Don't add the first point again (except for the very first)
            if i == 0:
                self.add_stitch_line(start_corner[0], start_corner[1],
                                    end_corner[0], end_corner[1], stitch_spacing)
            else:
                # Skip the first point to avoid duplicates
                self.add_stitch_line_segment(start_corner[0], start_corner[1],
                                           end_corner[0], end_corner[1], stitch_spacing, skip_first=True)

    def add_stitch_line_segment(self, start_x: int, start_y: int, end_x: int, end_y: int,
                               stitch_spacing: float = 20.0, skip_first: bool = False):
        """Add a line segment of stitches, optionally skipping the first stitch."""
        import math

        dx = end_x - start_x
        dy = end_y - start_y
        line_length = math.sqrt(dx * dx + dy * dy)

        if line_length == 0:
            if not skip_first:
                self.add_stitch(start_x, start_y)
            return

        num_stitches = max(2, int(line_length / stitch_spacing) + 1)
        start_index = 1 if skip_first else 0

        for i in range(start_index, num_stitches):
            t = i / (num_stitches - 1) if num_stitches > 1 else 0
            x = int(start_x + t * dx)
            y = int(start_y + t * dy)
            self.add_stitch(x, y)

    def generate_qr_code(self, text: str, center_x: int = 0, center_y: int = 0,
                         module_size: int = 8, stitch_spacing: float = 10.0,
                         error_correction: str = 'M'):
        """Generate a real QR code pattern using the qrcode library.

        Args:
            text: Text to encode
            center_x, center_y: Center position for the QR code
            module_size: Size of each module in stitching units
            stitch_spacing: Spacing between stitches within modules
            error_correction: Error correction level ('L', 'M', 'Q', 'H')

        Returns:
            Tuple of (success: bool, info: str, data_capacity: int)
        """
        try:
            import qrcode
            from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

            # Map error correction levels
            error_levels = {
                'L': ERROR_CORRECT_L,  # ~7% correction
                'M': ERROR_CORRECT_M,  # ~15% correction
                'Q': ERROR_CORRECT_Q,  # ~25% correction
                'H': ERROR_CORRECT_H   # ~30% correction
            }

            error_level = error_levels.get(error_correction.upper(), ERROR_CORRECT_M)

            # Calculate maximum size that fits in stitch area (20x20mm = 200x200 units)
            max_total_size = 180  # Leave some margin
            max_modules = max_total_size // module_size

            # Try different QR versions to find the best fit
            qr = None
            version_used = None

            for version in range(1, 11):  # QR versions 1-10
                test_qr = qrcode.QRCode(
                    version=version,
                    error_correction=error_level,
                    box_size=1,
                    border=4
                )
                test_qr.add_data(text)

                try:
                    test_qr.make(fit=False)  # Don't auto-fit, use specified version
                    qr_size = test_qr.modules_count

                    if qr_size <= max_modules:
                        qr = test_qr
                        version_used = version
                    else:
                        break  # This version is too big, previous one was the largest that fits

                except qrcode.exceptions.DataOverflowError:
                    break  # Text too long for this version

            if qr is None:
                # Text too long, try with auto-fit on smallest possible version
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=error_level,
                    box_size=1,
                    border=4
                )
                qr.add_data(text)
                qr.make(fit=True)
                version_used = qr.version

                if qr.modules_count > max_modules:
                    return (False, f"QR code too large: {qr.modules_count}x{qr.modules_count} modules, max {max_modules}x{max_modules}", 0)

            # Get the QR code matrix
            matrix = qr.get_matrix()
            qr_size = len(matrix)

            # Calculate positioning
            total_size = qr_size * module_size
            start_x = center_x - total_size // 2
            start_y = center_y - total_size // 2

            # Check if it fits in stitch area
            half_size = total_size // 2
            if abs(center_x + half_size) > 100 or abs(center_x - half_size) > 100 or \
               abs(center_y + half_size) > 100 or abs(center_y - half_size) > 100:
                return (False, f"QR code extends beyond 20x20mm stitch area", 0)

            # Generate stitches for black modules
            modules_stitched = 0
            for i, row in enumerate(matrix):
                for j, is_black in enumerate(row):
                    if is_black:
                        module_center_x = start_x + j * module_size + module_size // 2
                        module_center_y = start_y + i * module_size + module_size // 2

                        # Add a small rectangle of stitches for each black module
                        self.add_rectangle_stitches(module_center_x, module_center_y,
                                                   max(4, module_size - 2), max(4, module_size - 2),
                                                   stitch_spacing)
                        modules_stitched += 1

            # Calculate data capacity for this QR version and error correction level
            capacity_map = {
                # Version: {L: numeric, M: numeric, Q: numeric, H: numeric} (approximate alphanumeric capacity is ~60% of numeric)
                1: {'L': 41, 'M': 34, 'Q': 27, 'H': 17},
                2: {'L': 77, 'M': 63, 'Q': 48, 'H': 34},
                3: {'L': 127, 'M': 101, 'Q': 77, 'H': 58},
                4: {'L': 187, 'M': 149, 'Q': 111, 'H': 82},
                5: {'L': 255, 'M': 202, 'Q': 144, 'H': 106},
                6: {'L': 322, 'M': 255, 'Q': 178, 'H': 139},
                7: {'L': 370, 'M': 293, 'Q': 207, 'H': 154},
                8: {'L': 461, 'M': 365, 'Q': 259, 'H': 202},
                9: {'L': 552, 'M': 432, 'Q': 312, 'H': 235},
                10: {'L': 652, 'M': 513, 'Q': 364, 'H': 288}
            }

            # Estimate alphanumeric capacity (roughly 60% of numeric)
            numeric_capacity = capacity_map.get(version_used, {}).get(error_correction.upper(), 0)
            alphanumeric_capacity = int(numeric_capacity * 0.6)

            info = f"QR Code v{version_used} ({qr_size}x{qr_size}), {modules_stitched} modules, ~{alphanumeric_capacity} chars capacity"
            return (True, info, alphanumeric_capacity)

        except ImportError:
            return (False, "qrcode library not available", 0)
        except Exception as e:
            return (False, f"Error generating QR code: {e}", 0)

    def generate_simple_qr_pattern(self, text: str, center_x: int = 0, center_y: int = 0,
                                  module_size: int = 8, stitch_spacing: float = 10.0):
        """Generate a simple QR-like pattern using text hash."""
        import hashlib

        # Create a simple hash-based pattern (not a real QR code)
        text_hash = hashlib.md5(text.encode()).hexdigest()

        # Create a simple 8x8 grid pattern based on hash
        grid_size = 8
        pattern = []

        # Convert hash characters to binary pattern
        for i in range(grid_size):
            row = []
            for j in range(grid_size):
                hash_index = (i * grid_size + j) % len(text_hash)
                # Use hash character value to determine if module is filled
                filled = int(text_hash[hash_index], 16) > 7
                row.append(filled)
            pattern.append(row)

        # Add border (QR codes have quiet zones)
        bordered_pattern = []
        border_size = grid_size + 2  # Add 1 border on each side

        for i in range(border_size):
            row = []
            for j in range(border_size):
                if i == 0 or i == border_size - 1 or j == 0 or j == border_size - 1:
                    row.append(False)  # Border is empty
                else:
                    row.append(pattern[i-1][j-1])
            bordered_pattern.append(row)

        # Calculate total size
        total_modules = len(bordered_pattern)
        total_size = total_modules * module_size
        start_x = center_x - total_size // 2
        start_y = center_y - total_size // 2

        # Generate stitches for filled modules
        for i, row in enumerate(bordered_pattern):
            for j, filled in enumerate(row):
                if filled:
                    module_center_x = start_x + j * module_size + module_size // 2
                    module_center_y = start_y + i * module_size + module_size // 2

                    # Add a small rectangle of stitches for each filled module
                    self.add_rectangle_stitches(module_center_x, module_center_y,
                                              module_size - 2, module_size - 2, stitch_spacing)

        return total_size  # Return the total size for reference

    def export_to_csv(self, output_filename: str):
        """Export pattern to CSV format."""
        with open(output_filename, 'w') as f:
            f.write("Index,Command,X,Y,RawBytes\n")
            for i, cmd in enumerate(self.commands):
                raw_hex = cmd.raw_bytes.hex() if cmd.raw_bytes else ""
                f.write(f"{i},{cmd.command_type.value},{cmd.x},{cmd.y},{raw_hex}\n")