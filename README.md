# Mitsubishi PLK-A0804F Pattern Editor

⚠️ **EXPERIMENTAL SOFTWARE - VALIDATION REQUIRED** ⚠️

A reverse-engineered Python toolkit for interpreting, visualizing, and editing sewing patterns from Mitsubishi PLK-A0804F controllers.

All cread to https://github.com/EmbroidePy/pyembroidery for their code on .100 files.

## 🚨 IMPORTANT DISCLAIMER

**This parser is based on reverse-engineering and contains known issues:**
- ✅ Coordinate extraction appears correct (validated with envelope pattern)
- ✅ Function codes from manual found in pattern data
- ❌ **Command type identification is questionable** (0x03 = coordinates, not commands)
- ❌ Binary structure interpretation needs machine verification

**USE AT YOUR OWN RISK** - Always test with simple known patterns on your machine before trusting the interpretation!

## Features

### Pattern Parsing
- **Full Command Support**: Interprets Point, Linear, Circular, Arc, Curve, Speed, and Function calls
- **Binary Format Analysis**: Reads native Mitsubishi pattern files (.100, .101, .102, etc.)
- **Coordinate System**: Handles x,y coordinate patterns as used by the sewing machine

### GUI Pattern Editor
- **Visual Pattern Display**: Interactive canvas with zoom, pan, and grid
- **Pattern Editing**: Add, remove, and modify stitch points (⚠️ experimental)
- **Real-time Preview**: See changes immediately as you edit
- **Validation Tools**: Built-in validation reporting and confidence assessment
- **Multiple File Formats**: Support for all Mitsubishi pattern file extensions
- **Parser Status Warnings**: Clear indication of interpretation limitations

### Export Capabilities
- **CSV Export**: Detailed command-by-command analysis
- **G-code Export**: For use with CNC machines and CAD software
- **Pattern Statistics**: Comprehensive analysis of pattern properties

## Files

### Core Library
- `mitsubishi_pattern_parser.py` - Main parsing library
- `pattern_interpreter_example.py` - Command-line usage examples
- `pattern_gui.py` - GUI application

### Generated Output
- `*.csv` - Command analysis files
- `*_gcode.txt` - G-code exports
- Pattern files can be saved in native Mitsubishi format

## Installation

### Requirements
- Python 3.6 or higher
- tkinter (usually included with Python)
- No additional dependencies required

### Setup
1. Clone or download the files to your project directory
2. Ensure your pattern files are in a "Patterns" folder
3. Run the applications directly with Python

## Usage

### GUI Application

Launch the pattern editor GUI:
```bash
python pattern_gui.py
```

#### GUI Features

**File Operations:**
- **Open Pattern** (Ctrl+O): Load Mitsubishi pattern files
- **Save Pattern** (Ctrl+S): Save modifications to pattern
- **Save As**: Save with a new filename
- **Export to CSV**: Generate detailed command analysis
- **Export to G-code**: Create G-code for CNC use

**Viewing:**
- **Mouse Wheel**: Zoom in/out
- **Click and Drag**: Pan around the pattern
- **Fit to Window**: Auto-scale pattern to fit display
- **Grid Display**: Reference grid for measurements

**Editing:**
- **Click on Points**: Select individual stitch points or commands
- **Drag Points**: Move selected stitch points
- **Add Point**: Add new stitch points to the pattern
- **Delete**: Remove selected commands

**Information Panel:**
- Pattern statistics (stitch count, dimensions, etc.)
- Command list with real-time updates
- Coordinate ranges and pattern bounds

### Command Line Usage

#### Basic Pattern Analysis
```bash
python mitsubishi_pattern_parser.py
```
This will analyze all patterns in the "Patterns" folder and generate CSV files.

#### Pattern Interpretation Examples
```bash
python pattern_interpreter_example.py
```
Shows detailed interpretation of sample patterns and generates G-code exports.

### Library Usage

```python
from mitsubishi_pattern_parser import MitsubishiPatternParser

# Create parser instance
parser = MitsubishiPatternParser()

# Parse a pattern file
commands = parser.parse_file("Patterns/NEW.109")

# Get pattern statistics
analysis = parser.analyze_pattern_motion("Patterns/NEW.109")
print(f"Stitch points: {analysis['stitch_points']}")
print(f"Pattern size: {analysis['coordinate_range']}")

# Export to different formats
parser.export_to_csv("Patterns/NEW.109", "output.csv")
```

## Pattern File Formats

### Supported Extensions
- `.100` to `.118` - Standard Mitsubishi pattern files

### Command Types Recognized
- **POINT (0x61)**: Stitch points with x,y coordinates
- **LINEAR_MOVE (0x03)**: Linear positioning commands
- **CIRCULAR (0xE1)**: Circular motion patterns
- **ARC (0x82)**: Arc definitions with parameters
- **CURVE (0x83)**: Curve definitions with parameters
- **SPEED (0x02)**: Speed control commands
- **FUNCTION (0x1F)**: Special function calls
- **SEPARATOR (0x01)**: Pattern section delimiters

### Coordinate System
- Units appear to be in machine-specific increments
- X,Y coordinates represent needle position
- Patterns use absolute positioning
- Scale conversion to metric: divide by ~100 for millimeter approximation

## Example Workflows

### Analyzing an Existing Pattern
1. Launch `python pattern_gui.py`
2. File → Open Pattern
3. Select your pattern file
4. View statistics in the information panel
5. Export to CSV for detailed analysis

### Editing a Pattern
1. Open pattern in GUI
2. Click on stitch points to select them
3. Drag points to new positions
4. Use "Add Point" to insert new stitches
5. Save your modifications

### Converting to G-code
1. Open pattern in GUI
2. File → Export to G-code
3. Use the generated G-code in your CNC software

## Technical Details

### Binary Format
The parser handles the proprietary Mitsubishi binary format:
- Little-endian byte order
- Variable-length commands
- Command-specific parameter structures

### Coordinate Scaling
- Raw coordinates are in machine units
- GUI displays coordinates as-is
- G-code export applies 1:100 scale for metric conversion

### Error Handling
- Graceful handling of unknown command types
- Robust parsing of malformed files
- User-friendly error messages in GUI

## Troubleshooting

### Common Issues

**"Pattern file not found"**
- Ensure pattern files are in the "Patterns" directory
- Check file permissions

**"Failed to parse pattern"**
- File may be corrupted or in unsupported format
- Try opening with a different pattern file

**GUI doesn't display pattern**
- Try "Fit to Window" from View menu
- Check if pattern has valid coordinates

### Performance
- Large patterns (>10,000 commands) may load slowly
- Zoom operations are optimized for real-time interaction
- CSV export handles any pattern size

## Contributing

The codebase is modular and extensible:
- `CommandType` enum can be extended for new command types
- Pattern visualization can be customized via color schemes
- Export formats can be added by implementing new export methods

## License

This tool is provided for educational and personal use. The Mitsubishi pattern format is proprietary to Mitsubishi Electric.
