# DaVinci Resolve MCP Examples

This directory contains example scripts demonstrating how to use the DaVinci Resolve MCP server with different features of DaVinci Resolve.

## Directory Structure

- **markers/** - Examples related to timeline markers and marker operations
- **timeline/** - Examples for timeline management and operations
- **media/** - Examples for media pool operations and media management

## How to Run Examples

1. Make sure DaVinci Resolve is running
2. Ensure the MCP server is set up (run `./scripts/check-resolve-ready.sh` first)
3. Use a Python environment with the MCP SDK installed
4. Run an example script with:

```bash
# Activate the virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Run an example
python examples/markers/add_timecode_marker.py
```

## Example Categories

### Markers Examples

Examples in `markers/` demonstrate how to:
- Add markers at specific frames
- Add markers with timecode values
- Add markers at regular intervals
- Test marker frame placement
- Clear and replace markers

### Timeline Examples

Examples in `timeline/` demonstrate how to:
- Get information about timelines
- Check timeline properties
- Perform operations on timelines

### Media Examples

Examples in `media/` demonstrate how to:
- Import media into the media pool
- Organize media in bins
- Add media to timelines

## Creating Your Own Examples

When creating new examples, please follow these guidelines:

1. Place them in the appropriate category folder
2. Include clear comments explaining what the example does
3. Handle errors gracefully
4. Follow the code style of existing examples

If you create an example that doesn't fit in an existing category, feel free to create a new directory. 