import sys
import os
import re

resolve_api = os.environ.get("RESOLVE_SCRIPT_API")
if resolve_api:
    sys.path.insert(0, os.path.join(resolve_api, "Modules"))
else:
    sys.path.insert(0, "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")


def _get_resolve():
    import DaVinciResolveScript as dvr
    return dvr.scriptapp("Resolve")


def _require_resolve():
    resolve = _get_resolve()
    if not resolve:
        raise RuntimeError("DaVinci Resolve is not running or scripting is disabled")
    return resolve


def _require_project(resolve=None):
    if resolve is None:
        resolve = _require_resolve()
    proj = resolve.GetProjectManager().GetCurrentProject()
    if not proj:
        raise RuntimeError("No project is currently open")
    return proj


def _require_timeline(proj=None):
    if proj is None:
        proj = _require_project()
    tl = proj.GetCurrentTimeline()
    if not tl:
        raise RuntimeError("No timeline is currently active")
    return tl


# ─── Default paths relative to CWD ─────────────────────────────────────────

def default_raw_srt():
    try:
        import DaVinciResolveScript as dvr
        resolve = dvr.scriptapp("Resolve")
        if resolve:
            proj = resolve.GetProjectManager().GetCurrentProject()
            if proj:
                name = proj.GetName()
                safe = re.sub(r'[^\w\-]', '_', name)
                return os.path.join(os.getcwd(), f"{safe}_subtitles_raw.srt")
    except Exception:
        pass
    return os.path.join(os.getcwd(), "subtitles_raw.srt")


# ─── Step 1: Init (check version + get project + list timelines + start tc) ──

def init():
    resolve = _require_resolve()
    proj = _require_project(resolve)
    tl = _require_timeline(proj)

    version = {
        "product": resolve.GetProductName(),
        "version_string": resolve.GetVersionString(),
        "version": resolve.GetVersion(),
    }
    project_name = proj.GetName()
    count = proj.GetTimelineCount()
    timelines = []
    for i in range(1, count + 1):
        t = proj.GetTimelineByIndex(i)
        if t:
            timelines.append({
                "index": i,
                "name": t.GetName(),
                "start_timecode": t.GetStartTimecode(),
                "start_frame": t.GetStartFrame(),
                "end_frame": t.GetEndFrame(),
            })

    current = tl.GetName()
    start_tc = tl.GetStartTimecode()

    result = {
        "version": version,
        "project_name": project_name,
        "timelines": timelines,
        "current_timeline": current,
        "start_timecode": start_tc,
    }

    if not start_tc.startswith("00"):
        result["warning"] = (
            f"Timeline '{current}' starts at {start_tc}, not 00:00:00:00. "
            "SRT timing is frame-relative from 00:00:00,000 and may be "
            "misaligned on other players. Consider setting start timecode "
            "to 00:00:00:00 first."
        )

    return result


# ─── Version Check ──────────────────────────────────────────────────────────

def check_version():
    resolve = _require_resolve()
    return {
        "product": resolve.GetProductName(),
        "version_string": resolve.GetVersionString(),
        "version": resolve.GetVersion(),
    }


# ─── Fix Timecode: Reset timeline start timecode to 00:00:00:00 ──────────────

def fix_timecode():
    tl = _require_timeline()
    old_tc = tl.GetStartTimecode()
    result = tl.SetStartTimecode("00:00:00:00")
    new_tc = tl.GetStartTimecode()
    if not result or new_tc != "00:00:00:00":
        raise RuntimeError(f"Failed to set start timecode (was: {old_tc})")
    return {
        "success": True,
        "old_timecode": old_tc,
        "new_timecode": new_tc,
    }


# ─── Step 2: Timeline Listing ───────────────────────────────────────────────

def list_timelines():
    proj = _require_project()
    count = proj.GetTimelineCount()
    timelines = []
    for i in range(1, count + 1):
        tl = proj.GetTimelineByIndex(i)
        if tl:
            timelines.append({
                "index": i,
                "name": tl.GetName(),
                "start_frame": tl.GetStartFrame(),
                "end_frame": tl.GetEndFrame(),
                "start_timecode": tl.GetStartTimecode(),
            })
    return timelines


def set_current_timeline(index):
    proj = _require_project()
    tl = proj.GetTimelineByIndex(index)
    if not tl:
        raise RuntimeError(f"Timeline index {index} not found")
    proj.SetCurrentTimeline(tl)
    return {"name": tl.GetName(), "index": index}


# ─── Step 3: Generate Subtitles from Audio ──────────────────────────────────

def generate_subtitles(chars_per_line=24):
    resolve = _require_resolve()
    proj = _require_project(resolve)
    tl = _require_timeline(proj)
    sc = tl.GetTrackCount("subtitle")
    while sc > 0:
        tl.DeleteTrack("subtitle", sc)
        sc = tl.GetTrackCount("subtitle")
    tl.AddTrack("subtitle")
    settings = {
        resolve.SUBTITLE_CHARS_PER_LINE: chars_per_line,
    }
    result = tl.CreateSubtitlesFromAudio(settings)
    if not result:
        raise RuntimeError("Failed to generate subtitles from audio")
    items = tl.GetItemListInTrack("subtitle", 1) or []
    return {
        "success": True,
        "count": len(items),
        "items": [{"start": it.GetStart(), "end": it.GetEnd(), "text": it.GetName()} for it in items],
    }


# ─── Step 4: Export Subtitles to SRT ────────────────────────────────────────

def export_subtitles_srt(output_path=None):
    tl = _require_timeline()
    items = tl.GetItemListInTrack("subtitle", 1)
    if not items:
        raise RuntimeError("No subtitle items found on the timeline")
    proj = _require_project()
    sr = proj.GetSetting("timelineFrameRate")
    fps = float(sr) if sr else 24

    def frames_to_srt_tc(frames, fps):
        total_secs = frames / fps
        h = int(total_secs // 3600)
        m = int((total_secs % 3600) // 60)
        s = int(total_secs % 60)
        ms = int(round((total_secs - int(total_secs)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    srt_lines = []
    for idx, item in enumerate(items, 1):
        start = item.GetStart()
        end = item.GetEnd()
        text = item.GetName()
        start_tc = frames_to_srt_tc(start, fps)
        end_tc = frames_to_srt_tc(end, fps)
        srt_lines.append(str(idx))
        srt_lines.append(f"{start_tc} --> {end_tc}")
        srt_lines.append(text)
        srt_lines.append("")

    if output_path is None:
        output_path = default_raw_srt()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    return {"path": output_path, "count": len(items)}


# ─── SRT Parsing ─────────────────────────────────────────────────────────────

def parse_srt(srt_content):
    blocks = re.split(r'\n\n+', srt_content.strip())
    subtitles = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            times = lines[1].split(' --> ')
            text = ' '.join(lines[2:])
            subtitles.append({
                "index": int(lines[0]),
                "start_tc": times[0].strip(),
                "end_tc": times[1].strip(),
                "text": text,
            })
    return subtitles


def read_srt(srt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    subtitles = parse_srt(content)
    return {"count": len(subtitles), "items": subtitles, "content": content}


# ─── Step 5: Import SRT Back to Timeline ────────────────────────────────────

def import_srt_to_timeline(srt_path):
    resolve = _require_resolve()
    proj = _require_project(resolve)
    mp = proj.GetMediaPool()
    tl = _require_timeline(proj)
    root = mp.GetRootFolder()
    for clip in list(root.GetClipList() or []):
        if clip.GetName().endswith(".srt"):
            mp.DeleteClips([clip])
    sc = tl.GetTrackCount("subtitle")
    while sc > 0:
        tl.DeleteTrack("subtitle", sc)
        sc = tl.GetTrackCount("subtitle")
    abs_path = os.path.abspath(srt_path)
    imported = mp.ImportMedia([abs_path])
    if not imported:
        raise RuntimeError("Failed to import SRT file into Media Pool")
    srt_clip = imported[0]
    tl.AddTrack("subtitle")
    result = mp.AppendToTimeline([srt_clip])
    if not result:
        raise RuntimeError("Failed to append subtitles to timeline")
    items = tl.GetItemListInTrack("subtitle", 1) or []
    return {
        "success": True,
        "count": len(items),
        "items": [{"start": it.GetStart(), "end": it.GetEnd(), "text": it.GetName()} for it in items],
    }


# ─── CLI entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: python subtitles_auto.py <command> [args...]")
        print()
        print("Commands:")
        print("  init                           Verify connection, get project name, list timelines, check start TC")
        print("  version                        Check Resolve version")
        print("  fix-timecode                   Reset timeline start timecode to 00:00:00:00")
        print("  list-timelines                 List all timelines")
        print("  set-timeline <index>           Switch to timeline by index")
        print("  generate [chars_per_line=24]   Generate subtitles from audio")
        print("  export-srt [output_path]       Export subtitles to SRT (default: ./<project>_subtitles_raw.srt)")
        print("  read-srt <path>                Read and parse SRT file")
        print("  import-srt <srt_path>          Import SRT back to timeline as subtitle track")
        print()
        print("Examples:")
        print("  python subtitles_auto.py init")
        print("  python subtitles_auto.py fix-timecode")
        print("  python subtitles_auto.py generate 24")
        print("  python subtitles_auto.py import-srt ./subtitles.srt")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        result = init()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "version":
        result = check_version()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "fix-timecode":
        result = fix_timecode()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "list-timelines":
        result = list_timelines()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "set-timeline":
        if len(sys.argv) < 3:
            print("Error: Please provide timeline index", file=sys.stderr)
            sys.exit(1)
        result = set_current_timeline(int(sys.argv[2]))
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "generate":
        chars_per_line = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        result = generate_subtitles(chars_per_line)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "export-srt":
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        result = export_subtitles_srt(output_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "read-srt":
        if len(sys.argv) < 3:
            print("Error: Please provide SRT file path", file=sys.stderr)
            sys.exit(1)
        result = read_srt(sys.argv[2])
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "import-srt":
        if len(sys.argv) < 3:
            print("Error: Please provide SRT file path", file=sys.stderr)
            sys.exit(1)
        result = import_srt_to_timeline(sys.argv[2])
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
