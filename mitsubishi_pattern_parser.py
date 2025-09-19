#!/usr/bin/env python3
"""
Mitsubishi PLK-A0804F Sewing Pattern Parser

⚠️ EXPERIMENTAL PARSER - VALIDATION REQUIRED ⚠️

This script attempts to parse sewing pattern files from a Mitsubishi PLK-A0804F controller
based on reverse-engineering. The interpretation has NOT been validated against official
documentation and contains known issues.

VALIDATION FINDINGS:
✓ Coordinate extraction appears correct (envelope pattern validates as square)
✓ Function codes from manual found in pattern data
❌ Command type identification is QUESTIONABLE (0x03 = coordinates, not commands)
❌ Binary structure interpretation needs verification

The patterns are supposed to contain commands for Point, Linear, Circular, Arc, Curve,
Speed and FUNCTION calls with x,y coordinates, but the actual binary structure may be
different from this implementation.

USE AT YOUR OWN RISK - Always verify with test patterns on your machine!
"""

import struct
import os
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

class CommandType(Enum):
    POINT = 0x61
    LINEAR_MOVE = 0x03
    SPEED = 0x02
    FUNCTION = 0x1F
    SEPARATOR = 0x01
    CIRCULAR = 0xE1  # Observed in patterns
    ARC = 0x82       # Observed in patterns
    CURVE = 0x83     # Observed in patterns
    UNKNOWN = 0xFF

class FunctionCode(Enum):
    """Function codes from PLK-A0804F manual"""
    FEED = 0x0003
    THREAD_TRIMMING = 0x0002
    HALT = 0x0004
    REVERSE_ROTATION = 0x0005
    SECOND_HOME_POSITION = 0x0006
    BASTING = 0x0007
    END_DATA = 0x0031
    # Reserved codes 0x0008-0x0030

@dataclass
class PatternCommand:
    command_type: CommandType
    x: int = 0
    y: int = 0
    parameters: List[int] = None
    raw_data: bytes = None
    function_code: FunctionCode = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []

    def get_function_name(self) -> str:
        """Get human-readable function name if this is a function command."""
        if self.function_code:
            return self.function_code.name.replace('_', ' ').title()
        elif self.command_type == CommandType.FUNCTION and self.parameters:
            # Try to decode function from parameters
            if len(self.parameters) >= 2:
                func_code = (self.parameters[1] << 8) | self.parameters[0]  # Little-endian
                try:
                    return FunctionCode(func_code).name.replace('_', ' ').title()
                except ValueError:
                    return f"Unknown Function {func_code:04X}"
        return ""

class MitsubishiPatternParser:
    def __init__(self):
        self.commands = []

    def parse_file(self, filepath: str) -> List[PatternCommand]:
        """Parse a Mitsubishi pattern file and return list of commands."""
        self.commands = []

        with open(filepath, 'rb') as f:
            data = f.read()

        self._parse_binary_data(data)
        return self.commands

    def _parse_binary_data(self, data: bytes) -> None:
        """Parse the binary data and extract commands.

        ⚠️ WARNING: This interpretation is based on reverse-engineering and may be incorrect!
        Validation shows that 0x03 bytes appear to be coordinate data, not command types.
        The actual command structure may be fundamentally different.
        """
        i = 0
        while i < len(data):
            if i >= len(data):
                break

            # Read command byte and parameters
            cmd_byte = data[i]

            if cmd_byte == 0x03:  # Linear movement command
                if i + 4 < len(data):
                    # Extract x,y coordinates (little-endian 16-bit values)
                    x = struct.unpack('<H', data[i+1:i+3])[0]
                    y = struct.unpack('<H', data[i+3:i+5])[0]

                    command = PatternCommand(
                        command_type=CommandType.LINEAR_MOVE,
                        x=x,
                        y=y,
                        raw_data=data[i:i+5]
                    )
                    self.commands.append(command)
                    i += 5
                else:
                    i += 1

            elif cmd_byte == 0x61:  # Point/stitch command
                if i + 3 < len(data):
                    # Extract x,y coordinates - first byte is x, next 2 bytes are y (little-endian)
                    x = data[i+1]
                    y = struct.unpack('<H', data[i+2:i+4])[0]

                    command = PatternCommand(
                        command_type=CommandType.POINT,
                        x=x,
                        y=y,
                        raw_data=data[i:i+4]
                    )
                    self.commands.append(command)
                    i += 4
                else:
                    i += 1

            elif cmd_byte == 0xE1:  # Circular command (observed in patterns)
                if i + 3 < len(data):
                    # Similar structure to point commands
                    x = data[i+1]
                    y = struct.unpack('<H', data[i+2:i+4])[0]

                    command = PatternCommand(
                        command_type=CommandType.CIRCULAR,
                        x=x,
                        y=y,
                        raw_data=data[i:i+4]
                    )
                    self.commands.append(command)
                    i += 4
                else:
                    i += 1

            elif cmd_byte == 0x82:  # Arc command
                if i + 3 < len(data):
                    command = PatternCommand(
                        command_type=CommandType.ARC,
                        parameters=[data[i+1], data[i+2], data[i+3]],
                        raw_data=data[i:i+4]
                    )
                    self.commands.append(command)
                    i += 4
                else:
                    i += 1

            elif cmd_byte == 0x83:  # Curve command
                if i + 3 < len(data):
                    command = PatternCommand(
                        command_type=CommandType.CURVE,
                        parameters=[data[i+1], data[i+2], data[i+3]],
                        raw_data=data[i:i+4]
                    )
                    self.commands.append(command)
                    i += 4
                else:
                    i += 1

            elif cmd_byte == 0x02:  # Speed command
                if i + 3 < len(data):
                    command = PatternCommand(
                        command_type=CommandType.SPEED,
                        parameters=[data[i+1], data[i+2], data[i+3]],
                        raw_data=data[i:i+4]
                    )
                    self.commands.append(command)
                    i += 4
                else:
                    i += 1

            elif cmd_byte == 0x1F:  # Function command
                if i + 3 < len(data):
                    params = [data[i+1], data[i+2], data[i+3]]
                    command = PatternCommand(
                        command_type=CommandType.FUNCTION,
                        parameters=params,
                        raw_data=data[i:i+4]
                    )

                    # Try to decode function code from parameters
                    if len(params) >= 2:
                        func_code = struct.unpack('<H', bytes(params[:2]))[0]
                        try:
                            command.function_code = FunctionCode(func_code)
                        except ValueError:
                            pass  # Unknown function code

                    self.commands.append(command)
                    i += 4
                else:
                    i += 1

            elif cmd_byte == 0x01:  # Separator/delimiter
                if i + 3 < len(data):
                    command = PatternCommand(
                        command_type=CommandType.SEPARATOR,
                        parameters=[data[i+1], data[i+2], data[i+3]],
                        raw_data=data[i:i+4]
                    )
                    self.commands.append(command)
                    i += 4
                else:
                    i += 1

            else:
                # Unknown command, try to handle gracefully
                command = PatternCommand(
                    command_type=CommandType.UNKNOWN,
                    parameters=[cmd_byte],
                    raw_data=data[i:i+1]
                )
                self.commands.append(command)
                i += 1

    def print_pattern_info(self, filepath: str) -> None:
        """Print detailed information about a pattern file."""
        commands = self.parse_file(filepath)

        print(f"\n=== Pattern File: {os.path.basename(filepath)} ===")
        print(f"File size: {os.path.getsize(filepath)} bytes")
        print(f"Total commands: {len(commands)}")

        # Count command types
        cmd_counts = {}
        for cmd in commands:
            cmd_type = cmd.command_type.name
            cmd_counts[cmd_type] = cmd_counts.get(cmd_type, 0) + 1

        print("\nCommand distribution:")
        for cmd_type, count in cmd_counts.items():
            print(f"  {cmd_type}: {count}")

        print("\nFirst 10 commands:")
        for i, cmd in enumerate(commands[:10]):
            if cmd.command_type == CommandType.POINT:
                print(f"  {i+1:2d}. POINT     x={cmd.x:3d}, y={cmd.y:4d}")
            elif cmd.command_type == CommandType.LINEAR_MOVE:
                print(f"  {i+1:2d}. LINEAR    x={cmd.x:4d}, y={cmd.y:4d}")
            elif cmd.command_type == CommandType.CIRCULAR:
                print(f"  {i+1:2d}. CIRCULAR  x={cmd.x:3d}, y={cmd.y:4d}")
            elif cmd.command_type == CommandType.ARC:
                print(f"  {i+1:2d}. ARC       params={cmd.parameters}")
            elif cmd.command_type == CommandType.CURVE:
                print(f"  {i+1:2d}. CURVE     params={cmd.parameters}")
            elif cmd.command_type == CommandType.SPEED:
                print(f"  {i+1:2d}. SPEED     params={cmd.parameters}")
            elif cmd.command_type == CommandType.FUNCTION:
                func_name = cmd.get_function_name()
                if func_name:
                    print(f"  {i+1:2d}. FUNCTION  {func_name} (params={cmd.parameters})")
                else:
                    print(f"  {i+1:2d}. FUNCTION  params={cmd.parameters}")
            elif cmd.command_type == CommandType.SEPARATOR:
                print(f"  {i+1:2d}. SEPARATOR params={cmd.parameters}")
            else:
                print(f"  {i+1:2d}. UNKNOWN   params={cmd.parameters}")

    def get_coordinates(self) -> List[Tuple[int, int]]:
        """Extract all x,y coordinates from the pattern."""
        coords = []
        for cmd in self.commands:
            if cmd.command_type in [CommandType.POINT, CommandType.LINEAR_MOVE, CommandType.CIRCULAR]:
                coords.append((cmd.x, cmd.y))
        return coords

    def get_bounding_box(self) -> Tuple[int, int, int, int]:
        """Get the bounding box of the pattern (min_x, min_y, max_x, max_y)."""
        coords = self.get_coordinates()
        if not coords:
            return (0, 0, 0, 0)

        x_coords = [x for x, y in coords]
        y_coords = [y for x, y in coords]

        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

    def export_to_csv(self, filepath: str, output_csv: str) -> None:
        """Export pattern commands to CSV format."""
        commands = self.parse_file(filepath)

        with open(output_csv, 'w') as f:
            f.write("Command,Type,X,Y,Parameters,Raw_Hex\n")

            for i, cmd in enumerate(commands):
                raw_hex = cmd.raw_data.hex() if cmd.raw_data else ""
                params_str = ",".join(map(str, cmd.parameters)) if cmd.parameters else ""

                f.write(f"{i+1},{cmd.command_type.name},{cmd.x},{cmd.y},\"{params_str}\",{raw_hex}\n")

    def analyze_pattern_motion(self, filepath: str) -> Dict[str, Any]:
        """Analyze the motion characteristics of a pattern."""
        commands = self.parse_file(filepath)

        analysis = {
            'total_commands': len(commands),
            'command_counts': {},
            'stitch_points': 0,
            'movement_commands': 0,
            'speed_changes': 0,
            'function_calls': 0,
            'coordinate_range': {'x': [0, 0], 'y': [0, 0]},
            'path_length': 0.0
        }

        coords = []
        prev_x, prev_y = 0, 0

        for cmd in commands:
            cmd_type = cmd.command_type.name
            analysis['command_counts'][cmd_type] = analysis['command_counts'].get(cmd_type, 0) + 1

            if cmd.command_type == CommandType.POINT:
                analysis['stitch_points'] += 1
                coords.append((cmd.x, cmd.y))
                # Calculate path distance
                if coords:
                    analysis['path_length'] += ((cmd.x - prev_x)**2 + (cmd.y - prev_y)**2)**0.5
                prev_x, prev_y = cmd.x, cmd.y

            elif cmd.command_type in [CommandType.LINEAR_MOVE, CommandType.CIRCULAR]:
                analysis['movement_commands'] += 1
                coords.append((cmd.x, cmd.y))
                if coords:
                    analysis['path_length'] += ((cmd.x - prev_x)**2 + (cmd.y - prev_y)**2)**0.5
                prev_x, prev_y = cmd.x, cmd.y

            elif cmd.command_type == CommandType.SPEED:
                analysis['speed_changes'] += 1

            elif cmd.command_type == CommandType.FUNCTION:
                analysis['function_calls'] += 1

        if coords:
            x_coords = [x for x, y in coords]
            y_coords = [y for x, y in coords]
            analysis['coordinate_range']['x'] = [min(x_coords), max(x_coords)]
            analysis['coordinate_range']['y'] = [min(y_coords), max(y_coords)]

        return analysis

def main():
    """Main function to demonstrate the parser."""
    parser = MitsubishiPatternParser()
    patterns_dir = "Patterns"

    if not os.path.exists(patterns_dir):
        print(f"Error: {patterns_dir} directory not found!")
        return

    # Get all pattern files
    pattern_files = [f for f in os.listdir(patterns_dir) if f.endswith(('.100', '.101', '.102', '.103', '.105', '.106', '.107', '.109', '.114', '.118'))]

    if not pattern_files:
        print(f"No pattern files found in {patterns_dir}!")
        return

    print("Available pattern files:")
    for i, filename in enumerate(pattern_files, 1):
        filepath = os.path.join(patterns_dir, filename)
        print(f"{i:2d}. {filename} ({os.path.getsize(filepath)} bytes)")

    # Analyze each pattern file
    for filename in pattern_files:
        filepath = os.path.join(patterns_dir, filename)
        parser.print_pattern_info(filepath)

        # Get bounding box
        bbox = parser.get_bounding_box()
        print(f"Bounding box: ({bbox[0]}, {bbox[1]}) to ({bbox[2]}, {bbox[3]})")

        # Export to CSV for detailed analysis
        csv_filename = f"{filename}.csv"
        parser.export_to_csv(filepath, csv_filename)
        print(f"Exported to: {csv_filename}")

if __name__ == "__main__":
    main()