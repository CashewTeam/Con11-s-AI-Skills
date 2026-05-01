# Automatic Subtitle Generation & Optimization — AI Skill
本技能自动化 DaVinci Resolve 的完整字幕工作流程：
从音频生成 → 导出 → 使用 LLM 优化 → 重新导入 → 翻译。
This skill automates the full subtitle workflow in DaVinci Resolve:
generate from audio → export → optimize with LLM → import back → translate.

---

## Platform Compatibility

This skill is primarily developed on macOS. The helper script `subtitles_auto.py`
automatically detects the platform via environment variables.

### Python Virtual Environment Path

| Platform | Path |
|---|---|
| macOS / Linux | `{MCP_ROOT}/venv/bin/python` |
| Windows | `{MCP_ROOT}/venv\\Scripts\\python.exe` |

The SKILL.md uses `{MCP_ROOT}/venv/bin/python` as the default. On **Windows**,
replace it with `{MCP_ROOT}\venv\Scripts\python.exe` and use `\` as the path
separator throughout.

### Environment Variables

The script reads `RESOLVE_SCRIPT_API` from the environment first. If set, it
uses that value; otherwise it falls back to the macOS default path.

| Platform | `RESOLVE_SCRIPT_API` |
|---|---|
| macOS | `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting` |
| Windows | `%PROGRAMDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting` |
| Linux | `/opt/resolve/Developer/Scripting` |

Set the environment variable before running any command:

**macOS / Linux:**
```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules"
```

**Windows (PowerShell):**
```powershell
$env:RESOLVE_SCRIPT_API = "$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
$env:RESOLVE_SCRIPT_LIB = "C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
$env:PYTHONPATH = "$env:PYTHONPATH;$env:RESOLVE_SCRIPT_API\Modules"
```

### Path Separators

- **Python** (`subtitles_auto.py`): Uses `os.path.join()` throughout, which
  automatically uses the correct separator (`/` on macOS/Linux, `\` on Windows).
- **SKILL.md / CLI examples**: Written with `/` for readability. On Windows
  replace `/` with `\` when typing commands.

---

## Directory Structure

All paths in this skill are relative to the **Agent's current working directory (`{CWD}`)**.
`{MCP_ROOT}` refers to the `davinci-resolve-mcp-main` project directory.

```
{CWD}/
├── subtitle-skill/            # This skill folder
│   ├── SKILL.md               # This file
│   ├── subtitles_auto.py      # Python helper (standalone CLI)
├── davinci-resolve-mcp-main/  # MCP server (MCP_ROOT)
│   ├── venv/bin/python        # Virtual env Python
│   ├── src/server.py          # MCP server entry
│   └── docs/
├── {project_name}_subtitles_raw.srt  # Exported (auto-generated)
├── {project_name}_subtitles_zh_cn.srt        # Cleaned (optimized, Chinese)
```

---

## Required Tooling

| Tool | Path |
|---|---|
| MCP server | `{MCP_ROOT}/src/server.py` (compound, 27 tools) |
| Python helper | `subtitle-skill/subtitles_auto.py` |
| Venv Python | `{MCP_ROOT}/venv/bin/python` |
| Raw SRT (exported) | `./{project_name}_subtitles_raw.srt` |
| Optimized SRT | `./{project_name}_subtitles_{lang}.srt` |

---

## Running the Helper Script

All commands use the venv Python and are run from `{CWD}`:

```
{MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py <command> [args...]
```

Environment variables are required (set once per shell session):

```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
export PYTHONPATH="$RESOLVE_SCRIPT_API/Modules"
```

Or inline (macOS/Linux):

```bash
RESOLVE_SCRIPT_API="..." RESOLVE_SCRIPT_LIB="..." PYTHONPATH="$RESOLVE_SCRIPT_API/Modules" \
  {MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py version
```

Or inline (Windows PowerShell):

```powershell
$env:RESOLVE_SCRIPT_API="..."; $env:RESOLVE_SCRIPT_LIB="..."; $env:PYTHONPATH="$env:RESOLVE_SCRIPT_API\Modules"; \
  {MCP_ROOT}\venv\Scripts\python.exe subtitle-skill/subtitles_auto.py version
```

---

## Step-by-Step Workflow (6 Steps)

### Step 1: Initialize

Run the `init` command to verify Resolve is connected, get the current project
name, list all timelines, and check the start timecode — all in one call:

```
{MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py init
```

Expected response:
```json
{
  "version": {"product": "DaVinci Resolve Studio", "version_string": "20.1.0.20"},
  "project_name": "MyProject",
  "timelines": [
    {"index": 1, "name": "Timeline 1", "start_timecode": "00:00:00;00", ...}
  ],
  "current_timeline": "Timeline 1",
  "start_timecode": "00:00:00;00"
}
```

The `project_name` is used as `{project_name}` for file names throughout this skill.

If the response has a `warning` field (start timecode not `00`-prefixed), warn
the user: the SRT uses frame-relative timing from `00:00:00,000`, which may be
misaligned on other platforms. **Run `fix-timecode` to reset it:**

```
{MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py fix-timecode
```

Then re-run `init` to confirm the timecode is now `00:00:00:00` before
proceeding.

- Exactly **1 timeline**: proceed automatically.
- **Multiple timelines**: ask the user which one to use, then switch:

```
{MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py set-timeline <index>
```

### Step 2: Generate Subtitles from Audio

Deletes existing subtitle track, creates a fresh one, and runs Resolve's
speech-to-text with 24 characters per line:

```
{MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py generate 24
```

Expected:
```json
{"success": true, "count": 5, "items": [...]}
```

### Step 3: Export Subtitles to SRT

Export the generated subtitles to SRT:

```
{MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py export-srt
```

→ Writes `./{project_name}_subtitles_raw.srt` (project name used as prefix)

### Step 4: LLM Reads, Optimizes, and Writes SRT Directly

Read the exported raw SRT file to get the subtitle content:

```
{MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py read-srt ./{project_name}_subtitles_raw.srt
```

The response includes `items` (parsed subtitles) and `content` (full SRT text).
Use the `content` as your source.

**LLM — apply these optimization rules to each subtitle text and write the
result directly to `./subtitles.srt` using your file writing ability:**

1. **User reference**: If the user provided custom text (e.g. corrected
   transcript or specific wording per index), use that as the primary source
   for each matching subtitle index.
2. **Chinese punctuation**: Replace English `,` between Chinese characters
   with `，`. Replace English `.` between Chinese characters with `。`.
3. **CJK-English spacing**: Add a space between Chinese/Japanese/Korean
   characters and adjacent English letters or numbers.  
   Example: `达芬奇mcp` → `达芬奇 MCP`, `新的skill` → `新的 Skill`.
4. **Acronym capitalization**: Capitalize common technical acronyms:
   `mcp` → `MCP`, `api` → `API`, `srt` → `SRT`, `fps` → `FPS`,
   `hdr` → `HDR`, `sdr` → `SDR`, `lut` → `LUT`, `ai` → `AI`, `ml` → `ML`.
5. **Remove redundant punctuation**: Remove duplicate consecutive punctuation,
   strip leading/trailing punctuation marks and whitespace.
6. **Line splitting**: If a single subtitle text exceeds ~60 characters
   (roughly 30 CJK chars or 60 Latin chars), split it into two consecutive
   subtitle entries. Divide the original duration evenly between the two new
   entries and adjust their timecodes accordingly. Re-number all entries.

**Write the optimized SRT as `./{project_name}_subtitles_{lang}.srt`** — preserve the exact SRT
format (index, timecode line with `-->`, text line, blank line separator).
Do NOT call `clean-srt`; you are responsible for the full output. The `{lang}`
default is `zh_cn` for Chinese subtitles from Resolve's auto-caption.

Show the user a before/after summary of changes and ask for confirmation
before proceeding.

### Step 5: Import Optimized SRT Back

Once confirmed:

```
{MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py import-srt ./{project_name}_subtitles_{lang}.srt
```

This:
1. Cleans old SRT clips from Media Pool
2. Deletes current subtitle track
3. `ImportMedia` → imports SRT into Media Pool
4. `AddTrack("subtitle")` → creates fresh subtitle track
5. `AppendToTimeline([clip_object])` → appends using clip **object** (NOT clip ID string — critical!)

Expected:
```json
{"success": true, "count": 5, "items": [{"start": 18, "end": 69, "text": "你好你好，这是一个用于测试"}, ...]}
```

---

## Complete Workflow Example

```bash
# 1. Init — single command for connection, project name, timelines, start TC
→ {MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py init
→ Project "酷态科", 1 timeline, start TC 01:00:00;00 (warning)

# 1b. Fix timecode if needed (start TC not 00:00:00:00)
→ {MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py fix-timecode
→ Re-run init to confirm TC is now 00:00:00:00

# 2. Generate with 24 chars/line
→ {MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py generate 24

# 3. Export SRT
→ {MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py export-srt

# 4. Read raw SRT
→ {MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py read-srt ./{project_name}_subtitles_raw.srt
→ Ask user for corrections

# 5. LLM applies optimization rules and writes ./{project_name}_subtitles_{lang}.srt directly
→ Write file: ./{project_name}_subtitles_{lang}.srt

# 6. Show changes, confirm with user
→ Read ./{project_name}_subtitles_{lang}.srt, present before/after diff

# 7. Import back
→ {MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py import-srt ./{project_name}_subtitles_{lang}.srt

# 8. (Optional) Ask user → translate → write SRT files for other languages
→ Repeat Step 7 for each language requested
```

---

### Step 6: Generate Other Language SRTs via LLM Translation

After the optimized subtitles are imported, **ask the user** if they want to
generate subtitles in other languages.

If yes, for each requested language:

1. **Read the optimized SRT** to get the source text and timecodes:
   ```
   {MCP_ROOT}/venv/bin/python subtitle-skill/subtitles_auto.py read-srt ./{project_name}_subtitles_{lang}.srt
   ```
   (Use the existing `{lang}` optimized file, e.g. `zh_cn`.)

2. **LLM translates** each subtitle text to the target language while keeping
   the timecodes, index numbers, and SRT format exactly the same. Only the text
   line changes.

3. **Write the translated SRT** as `./{project_name}_subtitles_{target_lang}.srt`
   using your file writing ability. The translated file is saved to disk for the
   user to use later.

Repeat for each language the user requests.

---

## Error Handling

| Error | Likely cause | Fix |
|---|---|---|
| `"DaVinci Resolve is not running"` | Resolve closed or scripting disabled | `resolve_control(action="launch")` |
| `"No project is currently open"` | No project loaded | `project_manager(action="load", ...)` |
| `"No timeline is currently active"` | Timeline not set | `timeline(action="set_current", ...)` |
| `start_timecode` not `00`-prefixed | Timeline starts at e.g. `01:00:00:00` | Run `subtitles_auto.py fix-timecode` to reset |
| `"Failed to generate subtitles"` | No audio / speech not detected | Ensure timeline has audio with speech |
| `"Failed to import SRT"` | `ImportMedia` returned empty | Check SRT path exists, valid UTF-8 |
| `"Failed to append subtitles"` | Wrong arg type to `AppendToTimeline` | Pass clip **object**, not clip ID string |

## CLI Reference

```
python subtitles_auto.py <command> [args...]

Commands:
  init                           Verify connection, get project name, list timelines, check start TC
  version                        Check Resolve version
  fix-timecode                   Reset timeline start timecode to 00:00:00:00
  list-timelines                 List all timelines
  set-timeline <index>           Switch to timeline by index
  generate [chars_per_line=24]   Generate subtitles from audio
  export-srt [output_path]       Export subtitles to SRT (default: ./<project>_subtitles_raw.srt)
  read-srt <path>                Read and parse SRT file
  import-srt <srt_path>          Import SRT back to timeline as subtitle track
```
