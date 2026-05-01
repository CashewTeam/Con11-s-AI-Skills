# Timeline Examples

This directory contains examples demonstrating how to work with timelines in DaVinci Resolve using the MCP server.

## Available Examples

### timeline_info.py
Shows how to retrieve various information about timelines in a project.

### timeline_check.py
Demonstrates how to validate timeline properties and settings.

## Running the Examples

Ensure DaVinci Resolve is running and that you have a project open, preferably with multiple timelines.

```bash
# From the root directory of the repository
python examples/timeline/timeline_info.py
```

## Timeline Operations

Common operations demonstrated in these examples:
- Listing all timelines in a project
- Getting information about the current timeline
- Switching between timelines
- Creating new timelines
- Working with timeline settings

## Common Issues

- Some timeline operations require administrative access to the project
- Timeline operations may fail if the project is in read-only mode
- Creating timelines may be affected by project settings 