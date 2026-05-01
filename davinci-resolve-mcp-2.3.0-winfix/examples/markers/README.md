# Marker Examples

This directory contains examples demonstrating how to work with markers in DaVinci Resolve timelines using the MCP server.

## Available Examples

### add_timecode_marker.py
Shows how to add markers with timecode values at specified positions.

### add_spaced_markers.py
Demonstrates adding markers at regular intervals throughout a timeline.

### alternating_markers.py
Shows how to add markers with alternating colors and notes.

### clear_add_markers.py
Demonstrates how to clear all markers and then add new ones.

### test_marker_frames.py
A test script to verify marker placement at specific frames.

## Running the Examples

Ensure DaVinci Resolve is running and that you have a project open with at least one timeline.

```bash
# From the root directory of the repository
python examples/markers/add_timecode_marker.py
```

## Marker Colors

DaVinci Resolve supports the following marker colors that can be used in scripts:
- Blue
- Cyan 
- Green
- Yellow
- Red
- Pink
- Purple
- Fuchsia
- Rose
- Lavender
- Sky
- Mint
- Lemon
- Sand
- Cocoa
- Cream

## Common Issues

- Make sure a timeline is open before trying to add markers
- Markers can only be placed on valid frames that contain media
- Some marker operations require specific permissions or project settings 