# Media Examples

This directory contains examples demonstrating how to work with media files and the Media Pool in DaVinci Resolve using the MCP server.

## Available Examples

### import_folder.py
Shows how to import a folder of media files into the Media Pool.

## Running the Examples

Ensure DaVinci Resolve is running and that you have a project open.

```bash
# From the root directory of the repository
python examples/media/import_folder.py
```

## Media Operations

Common media operations demonstrated in these examples:
- Importing media files into the Media Pool
- Creating and organizing bins (folders)
- Working with clips in the Media Pool
- Adding clips to timelines

## Common Issues

- File paths must be valid and accessible to DaVinci Resolve
- Some media formats may not be supported for import
- Large media files may take time to import and process
- DaVinci Resolve may have limitations on certain media operations depending on the version 