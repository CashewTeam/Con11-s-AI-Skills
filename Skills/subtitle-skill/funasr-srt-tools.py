#!/usr/bin/env python3
"""
FunASR SRT Tools — ASR (cloud/local) + forced alignment + SRT 校对

子命令:
  asr                 语音识别生成字幕（云端/本地），无需文稿
  align               强制对齐生成字幕（需提供参考文稿）
  read-srt            读取并解析 SRT 文件
  convert-srt         转换 SRT（ASR 修正 + 繁简转换 + CJK 间距）
  apply-corrections   应用纯文本替换（用于翻译）

用法:
  python funasr-srt-tools.py asr <audio> [选项]
  python funasr-srt-tools.py align <audio> <text> [选项]
  python funasr-srt-tools.py read-srt <srt> [选项]
  python funasr-srt-tools.py convert-srt <input> [output] [lang] [corrections.json]
  python funasr-srt-tools.py apply-corrections <input> <output> <corrections.json>

示例:
  python funasr-srt-tools.py asr audio.wav
  python funasr-srt-tools.py asr audio.mp3 --lang en
  python funasr-srt-tools.py asr audio.wav --local
  python funasr-srt-tools.py align audio.wav transcript.txt
  python funasr-srt-tools.py read-srt subtitles.srt
  python funasr-srt-tools.py convert-srt input.srt output.srt zh-cn corrections.json
  python funasr-srt-tools.py apply-corrections input.srt output.srt corrections.json
"""

import os
import sys
import json
import time
import re
import argparse

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "funasr_config.toml")

LANG_MODELS = {
    "zh": "fun-asr",
    "en": "fun-asr",
    "yue": "fun-asr-mtl-2025-08-25",
    "ja": "fun-asr-mtl-2025-08-25",
    "ko": "fun-asr-mtl-2025-08-25",
    "th": "fun-asr-mtl-2025-08-25",
    "vi": "fun-asr-mtl-2025-08-25",
    "id": "fun-asr-mtl-2025-08-25",
}

REGION_URLS = {
    "cn": "https://dashscope.aliyuncs.com/api/v1",
    "intl": "https://dashscope-intl.aliyuncs.com/api/v1",
}


def _load_config():
    config = {}
    if os.path.isfile(CONFIG_PATH):
        try:
            import tomllib
            with open(CONFIG_PATH, "rb") as f:
                config = tomllib.load(f)
        except ImportError:
            try:
                import tomli
                with open(CONFIG_PATH, "rb") as f:
                    config = tomli.load(f)
            except ImportError:
                try:
                    import toml
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        config = toml.load(f)
                except ImportError:
                    pass
        except Exception:
            pass
    return config


def _ms_to_srt(ms):
    h = int(ms // 3600000)
    m = int((ms % 3600000) // 60000)
    s = int((ms % 60000) // 1000)
    ms_remain = int(ms % 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_remain:03d}"


# ─── 音频预处理 ──────────────────────────────────────────────────────


def _get_audio_info(path):
    import subprocess
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "a:0", path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        info = json.loads(result.stdout)
        stream = info.get("streams", [{}])[0]
        return {
            "sample_rate": int(stream.get("sample_rate", 0)),
            "channels": int(stream.get("channels", 0)),
            "format": stream.get("codec_name", ""),
            "duration": float(stream.get("duration", 0)),
        }
    except Exception as e:
        print(f"[警告] 无法读取音频信息: {e}")
        return None


def _normalize_audio(path, config=None):
    info = _get_audio_info(path)
    if info is None:
        return path, False

    sr = info["sample_rate"]
    ch = info["channels"]
    ext = os.path.splitext(path)[1].lower()

    target_sr = int((config or {}).get("audio_sample_rate", 16000))
    target_ch = int((config or {}).get("audio_channels", 1))
    ffmpeg_timeout = int((config or {}).get("ffmpeg_timeout", 300))

    needs_resample = sr > target_sr
    needs_mono = ch > target_ch
    needs_wav = ext not in (".wav",)

    if not needs_resample and not needs_mono and not needs_wav:
        return path, False

    print(f"[预处理] 源文件: {sr}Hz/{ch}ch/{ext}")
    if needs_resample:
        print(f"[预处理] 采样率 {sr}Hz 过高，压缩至 {target_sr}Hz")
    if needs_mono:
        print(f"[预处理] {ch} 声道转换为 {target_ch} 声道")
    if needs_wav:
        print(f"[预处理] 转换为 WAV 格式")

    out_path = os.path.splitext(path)[0] + "_16k.wav"
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-i", path,
        "-ar", str(target_sr),
        "-ac", str(target_ch),
        "-sample_fmt", "s16",
        "-map_metadata", "-1",
        out_path,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=ffmpeg_timeout, check=True)
        print(f"[预处理] 输出: {out_path}")
        return out_path, True
    except subprocess.CalledProcessError as e:
        print(f"[警告] 音频压缩失败，使用原始文件: {e.stderr[:200]}")
        return path, False


# ─── 云端 ASR ────────────────────────────────────────────────────────


def _init_dashscope(config):
    import dashscope
    api_key = (config.get("api_key") or "").strip()
    if not api_key:
        api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "未配置 API Key\n"
            "  方式1: 编辑 funasr_config.json\n"
            "  方式2: 设置环境变量 DASHSCOPE_API_KEY"
        )
    dashscope.api_key = api_key
    region = (config.get("region") or "cn").strip()
    dashscope.base_http_api_url = REGION_URLS.get(region, REGION_URLS["cn"])
    return dashscope


def _get_model(config, lang):
    model = (config.get("model") or "").strip()
    if model:
        return model
    return LANG_MODELS.get(lang, "fun-asr")


def upload_audio(audio_path):
    from dashscope import Files
    name = os.path.basename(audio_path)
    file_size = os.path.getsize(audio_path)
    print(f"[上传] 上传文件: {name} ({file_size/1024/1024:.1f}MB) ...")
    try:
        file_obj = Files.upload(file_path=audio_path, purpose="file_asr")
    except Exception as e:
        raise RuntimeError(f"文件上传失败: {e}")
    file_id = file_obj.get("output", {}).get("uploaded_files", [{}])[0].get("file_id", "")
    if not file_id:
        raise RuntimeError(f"上传成功但未获取到 file_id: {file_obj}")
    print(f"[上传] 上传完成，file_id: {file_id}")
    for attempt in range(5):
        time.sleep(1)
        file_info = Files.get(file_id)
        if file_info:
            break
        print(f"[上传] 文件尚未就绪，重试 {attempt+1}/5 ...")
    else:
        raise RuntimeError(f"查询文件信息失败: file_id={file_id}")
    file_url = file_info.get("output", {}).get("url", "")
    if not file_url:
        raise RuntimeError(f"获取文件 URL 失败: {file_info}")
    print(f"[上传] 文件 URL 已获取")
    return file_url


def transcribe(file_url, language="zh", config=None):
    from dashscope.audio.asr import Transcription
    if config is None:
        config = {}
    model = _get_model(config, language)
    max_retries = int(config.get("transcription_max_retries", 600))
    poll_interval = int(config.get("transcription_poll_interval", 2))
    print(f"[转录] 提交任务，模型: {model}，语言: {language} ...")
    task_response = Transcription.async_call(
        model=model,
        file_urls=[file_url],
        language_hints=[language],
    )
    task_id = getattr(task_response, "output", {}).get("task_id", None)
    if not task_id:
        raise RuntimeError(f"提交任务失败: {task_response}")
    print(f"[转录] 任务 ID: {task_id}，等待处理...")
    for i in range(max_retries):
        time.sleep(poll_interval)
        result = Transcription.wait(task=task_id)
        status = getattr(result, "output", {}).get("task_status", "UNKNOWN")
        if i % max(1, 15 // poll_interval) == 0 and i > 0:
            print(f"[转录] 等待中... ({i*poll_interval}s) 状态: {status}")
        if status == "SUCCEEDED":
            print(f"[转录] 完成! (耗时 {i*poll_interval}s)")
            return result
        elif status == "FAILED":
            msg = getattr(result, "output", {}).get("message", "未知错误")
            raise RuntimeError(f"转录失败: {msg}")
    raise RuntimeError("转录超时")


def result_to_srt(transcription_result, max_words=0):
    import requests as _requests
    output = transcription_result.get("output", {}) if isinstance(transcription_result, dict) else {}
    task_results = output.get("results", [])
    all_words = []
    for item in task_results:
        t_url = item.get("transcription_url", "")
        if not t_url:
            continue
        try:
            resp = _requests.get(t_url, timeout=30)
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"下载转录结果失败: {e}")
        transcripts = data.get("transcripts", [])
        for t in transcripts:
            sentences = t.get("sentences", [])
            for sent in sentences:
                words = sent.get("words", [])
                if not words:
                    all_words.append({
                        "begin_time": int(sent.get("begin_time", 0)),
                        "end_time": int(sent.get("end_time", 0)),
                        "text": sent.get("text", "").strip(),
                        "punct": "",
                    })
                    continue
                for w in words:
                    all_words.append({
                        "begin_time": int(w.get("begin_time", 0)),
                        "end_time": int(w.get("end_time", 0)),
                        "text": w.get("text", "").strip(),
                        "punct": w.get("punctuation", ""),
                    })
    if not all_words:
        print("[警告] 转录结果为空")
        return "\n", 0
    srt_lines = []
    PUNCT = set("。！？，；：")
    buf_text = ""
    buf_start = 0
    buf_end = 0
    buf_len = 0
    def _flush():
        nonlocal buf_text, buf_start, buf_len
        ftext = buf_text.strip().rstrip("，。！？；：、")
        if ftext:
            srt_lines.append(str(len(srt_lines) // 4 + 1))
            srt_lines.append(f"{_ms_to_srt(buf_start)} --> {_ms_to_srt(buf_end)}")
            srt_lines.append(ftext)
            srt_lines.append("")
        buf_text = ""
        buf_start = 0
        buf_len = 0
    for w in all_words:
        punct = w.get("punct", "")
        if buf_len == 0:
            buf_start = w["begin_time"]
        buf_text += w["text"] + punct
        buf_end = w["end_time"]
        buf_len += 1
        if punct and punct[-1] in PUNCT:
            _flush()
        elif max_words > 0 and buf_len >= max_words:
            _flush()
    _flush()
    return "\n".join(srt_lines), len(srt_lines) // 4


# ─── 本地 ASR ─────────────────────────────────────────────────────────


def _init_local_model(config, model_name=None, device="cpu", model_dir=None):
    try:
        from funasr import AutoModel
    except ImportError:
        raise RuntimeError(
            "未安装 funasr 本地包\n"
            "  安装方式: pip install funasr\n"
            "  如需 GPU 加速: pip install funasr[gpu]"
        )
    if not model_name:
        model_name = (config.get("local_model") or "paraformer-zh").strip()
    if not device:
        device = (config.get("local_device") or "cpu").strip()
    kwargs = {"model": model_name, "device": device}
    if model_dir:
        kwargs["model_dir"] = model_dir
    if "paraformer" in model_name:
        kwargs["vad_model"] = "fsmn-vad"
        kwargs["punc_model"] = "ct-punc"
        print(f"[本地模型] 附加 VAD 模型: fsmn-vad，标点模型: ct-punc")
    print(f"[本地模型] 加载模型: {model_name} (设备: {device})...")
    print(f"[本地模型] 首次加载会自动下载，请耐心等待...")
    model = AutoModel(**kwargs)
    print(f"[本地模型] 模型加载完成")
    return model


def transcribe_local(audio_path, model):
    print(f"[本地识别] 开始识别: {audio_path}")
    results = model.generate(input=audio_path)
    if not results or len(results) == 0:
        raise RuntimeError("识别结果为空")
    result = results[0] if isinstance(results, list) else results
    print(f"[本地识别] 识别文本长度: {len(result.get('text', ''))} 字符")
    return result


def _local_result_to_srt(local_result, max_words=0):
    timestamp_segs = local_result.get("timestamp", [])
    full_text = local_result.get("text", "").strip()
    if not timestamp_segs and not full_text:
        print("[警告] 转录结果为空")
        return "\n", 0
    if not timestamp_segs and full_text:
        print("[警告] 转录结果中无时间戳信息，使用完整文本作为单条字幕")
        return f"1\n00:00:00,000 --> 00:00:01,000\n{full_text}\n\n", 1
    srt_lines = []
    def _flush_seg(start_ms, end_ms, text):
        ftext = text.strip().rstrip("，。！？；：、")
        if not ftext:
            return
        srt_lines.append(str(len(srt_lines) // 4 + 1))
        srt_lines.append(f"{_ms_to_srt(int(start_ms))} --> {_ms_to_srt(int(end_ms))}")
        srt_lines.append(ftext)
        srt_lines.append("")
    has_text_in_ts = (
        len(timestamp_segs) > 0
        and len(timestamp_segs[0]) >= 3
        and isinstance(timestamp_segs[0][2], str)
        and timestamp_segs[0][2].strip() != ""
    )
    if has_text_in_ts:
        for seg in timestamp_segs:
            start_ms, end_ms = seg[0], seg[1]
            text = str(seg[2] or "").strip()
            if not text:
                continue
            _flush_seg(start_ms, end_ms, text)
    else:
        import re
        total_ts = len(timestamp_segs)
        total_chars = len(full_text)
        sentences = re.findall(r'[^。！？，；：、]+[。！？，；：、]?', full_text)
        char_cursor = 0
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            sent_len = len(sent)
            if total_chars == 0 or total_ts == 0:
                continue
            start_ts_i = int(char_cursor * total_ts / total_chars)
            end_ts_i = int((char_cursor + sent_len) * total_ts / total_chars)
            end_ts_i = min(end_ts_i, total_ts - 1)
            start_ms = timestamp_segs[start_ts_i][0]
            end_ms = timestamp_segs[end_ts_i][1]
            _flush_seg(start_ms, end_ms, sent)
            char_cursor += sent_len
    return "\n".join(srt_lines), len(srt_lines) // 4


# ─── 强制对齐 ──────────────────────────────────────────────────────────


PUNCT_WHITESPACE = set("，。！？；：\n\r \t\u201c\u201d\u2018\u2019")


def _build_char_timeline(ref_text, model_text, model_timestamps):
    model_tokens = model_text.split()
    min_len = min(len(model_tokens), len(model_timestamps))
    ref_clean_chars = []
    for i, c in enumerate(ref_text):
        if c not in PUNCT_WHITESPACE:
            ref_clean_chars.append(c)
    ref_cursor = 0
    clean_to_tok = {}
    for tok_idx in range(min_len):
        token = model_tokens[tok_idx]
        tok_lower = token.lower()
        tok_len = len(token)
        found = False
        search_end = len(ref_clean_chars) - tok_len + 1
        for start in range(ref_cursor, max(ref_cursor, search_end)):
            if start >= search_end:
                break
            if "".join(ref_clean_chars[start:start + tok_len]).lower() == tok_lower:
                for offset in range(tok_len):
                    clean_to_tok[start + offset] = tok_idx
                ref_cursor = start + tok_len
                found = True
                break
        if not found:
            clean_to_tok[ref_cursor] = tok_idx
            ref_cursor += 1
    char_timeline = []
    clean_pos = 0
    for ref_char in ref_text:
        if ref_char in PUNCT_WHITESPACE:
            if char_timeline:
                char_timeline.append((ref_char, char_timeline[-1][1], char_timeline[-1][2]))
            else:
                char_timeline.append((ref_char, 0, 0))
        else:
            tok_idx = clean_to_tok.get(clean_pos)
            if tok_idx is not None and tok_idx < len(model_timestamps):
                start_ms, end_ms = model_timestamps[tok_idx]
                char_timeline.append((ref_char, start_ms, end_ms))
            else:
                if char_timeline:
                    char_timeline.append((ref_char, char_timeline[-1][1], char_timeline[-1][2]))
                else:
                    char_timeline.append((ref_char, 0, 0))
            clean_pos += 1
    return char_timeline


def _build_srt_segments(ref_text, result, max_chars=0):
    if isinstance(result, list) and len(result) > 0:
        item = result[0]
    elif isinstance(result, dict):
        item = result
    else:
        raise RuntimeError(f"不支持的返回格式: {type(result)}")
    model_text = item.get("text", "")
    model_timestamps = item.get("timestamp", [])
    if not model_timestamps:
        return [(ref_text, 0, 0)]
    char_timeline = _build_char_timeline(ref_text, model_text, model_timestamps)
    segments = []
    buf_chars = []
    buf_start = 0
    for i, (char, start_ms, end_ms) in enumerate(char_timeline):
        if not buf_chars:
            buf_start = start_ms
        buf_chars.append(char)
        should_split = False
        if char in PUNCT_WHITESPACE:
            should_split = True
        elif max_chars > 0 and len(buf_chars) >= max_chars:
            should_split = True
        elif i == len(char_timeline) - 1:
            should_split = True
        if should_split:
            seg_text = "".join(buf_chars)
            seg_text = seg_text.strip().rstrip("，。！？；：、\n\r \t")
            if seg_text:
                segments.append((seg_text, buf_start, end_ms))
            buf_chars = []
    return segments


# ─── SRT 校对 ──────────────────────────────────────────────────────────

SRT_TIME_RE = re.compile(r'^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})')


def _read_srt(path):
    """读取 SRT 文件，解析为条目列表

    返回: [{'index': int, 'start': str, 'end': str, 'text': str}, ...]
    """
    import re as _re
    entries = []
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        index = None
        try:
            index = int(line)
        except ValueError:
            i += 1
            continue

        if i + 1 >= len(lines):
            break

        time_match = _re.match(SRT_TIME_RE, lines[i + 1].strip())
        if not time_match:
            i += 1
            continue

        start, end = time_match.groups()
        text_lines = []
        i += 2
        while i < len(lines):
            l = lines[i].strip()
            if not l:
                break
            text_lines.append(l)
            i += 1

        entries.append({
            "index": index,
            "start": start,
            "end": end,
            "text": "\n".join(text_lines),
        })
        i += 1

    return entries


def _write_srt(path, entries):
    """将条目列表写回 SRT 文件"""
    lines = []
    for e in entries:
        lines.append(str(e["index"]))
        lines.append(f'{e["start"]} --> {e["end"]}')
        lines.append(e["text"])
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _load_corrections(path):
    """加载修正 JSON，返回 {错误: 正确} dict"""
    if not os.path.isfile(path):
        print(f"[错误] 修正文件不存在: {path}")
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            corrections = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[错误] 修正文件解析失败: {e}")
        sys.exit(1)
    if not isinstance(corrections, dict):
        print("[错误] 修正文件必须是 JSON 对象 (key: 错误文本, value: 正确文本)")
        sys.exit(1)
    return corrections


def _apply_corrections_to_text(text, corrections):
    """按顺序对文本应用修正替换"""
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
    return text


_ZHCONV_WARNED = False


def _zhconv_convert(text, lang):
    global _ZHCONV_WARNED
    """繁简转换，依赖 zhconv 库"""
    try:
        from zhconv import convert as _zhconv_convert_fn
    except ImportError:
        if not _ZHCONV_WARNED:
            print("[警告] 未安装 zhconv，跳过繁简转换")
            print("  安装: pip install zhconv")
            _ZHCONV_WARNED = True
        return text
    lang_map = {
        "zh_cn": "zh-cn",
        "zh-cn": "zh-cn",
        "zh_tw": "zh-tw",
        "zh-tw": "zh-tw",
        "zh_hk": "zh-hk",
        "zh-hk": "zh-hk",
    }
    target = lang_map.get(lang.lower(), "zh-cn")
    return _zhconv_convert_fn(text, target)


def _fix_cjk_spacing(text):
    """修复 CJK 与 ASCII 之间的空格"""
    import re as _re
    text = _re.sub(r'([\u4e00-\u9fff\u3400-\u4dbf\uff00-\uffef])\s+([a-zA-Z0-9])', r'\1\2', text)
    text = _re.sub(r'([a-zA-Z0-9])\s+([\u4e00-\u9fff\u3400-\u4dbf\uff00-\uffef])', r'\1\2', text)
    return text


def _fix_punctuation(text):
    """修复全半角标点"""
    import re as _re
    text = _re.sub(r'，,', '，', text)
    text = _re.sub(r',，', '，', text)
    text = _re.sub(r'[.][.]+', '…', text)
    text = _re.sub(r'…\.', '…', text)
    text = _re.sub(r'。\.', '。', text)
    text = text.replace('"', '「').replace('"', '」')
    return text


def _run_read_srt(args):
    if not os.path.isfile(args.path):
        print(f"[错误] SRT 文件不存在: {args.path}")
        sys.exit(1)
    entries = _read_srt(args.path)
    output = json.dumps({
        "success": True,
        "count": len(entries),
        "items": entries,
    }, ensure_ascii=False, indent=2)
    print(output)
    if not args.no_verify and args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            f.write(output)


def _run_convert_srt(args):
    config = _load_config()
    if args.lang is None:
        args.lang = config.get("convert_srt_default_lang", "zh-cn")

    if not os.path.isfile(args.input):
        print(f"[错误] 输入 SRT 文件不存在: {args.input}")
        sys.exit(1)

    entries = _read_srt(args.input)
    original_count = len(entries)
    print(f"[输入] {args.input} ({original_count} 条)")

    corrections = {}
    if args.corrections:
        corrections = _load_corrections(args.corrections)
        print(f"[修正] 已加载 {len(corrections)} 条修正")

    corrected_count = 0
    for e in entries:
        text = e["text"]
        before = text

        if corrections:
            text = _apply_corrections_to_text(text, corrections)

        if args.lang:
            text = _zhconv_convert(text, args.lang)

        text = _fix_cjk_spacing(text)
        text = _fix_punctuation(text)

        if text != before:
            corrected_count += 1
        e["text"] = text

    if args.output is None:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_{args.lang.replace('-', '_')}.srt"

    _write_srt(args.output, entries)
    print(f"[完成] 输出: {args.output} ({len(entries)} 条, {corrected_count} 条有变动)")

    if not args.no_verify:
        print(f"\n[预览] 前 3 条:")
        for e in entries[:3]:
            print(f"  {e['start']} --> {e['end']}")
            print(f"  {e['text']}")
            print()

    if original_count != len(entries):
        print(f"[警告] 条目数不一致! 输入 {original_count}, 输出 {len(entries)}")


def _run_apply_corrections(args):
    if not os.path.isfile(args.input):
        print(f"[错误] 输入 SRT 文件不存在: {args.input}")
        sys.exit(1)

    corrections = _load_corrections(args.corrections)
    entries = _read_srt(args.input)
    print(f"[输入] {args.input} ({len(entries)} 条)")
    print(f"[修正] 已加载 {len(corrections)} 条修正")

    corrected_count = 0
    for e in entries:
        before = e["text"]
        e["text"] = _apply_corrections_to_text(e["text"], corrections)
        if e["text"] != before:
            corrected_count += 1

    _write_srt(args.output, entries)
    print(f"[完成] 输出: {args.output} ({corrected_count} 条有变动)")

    if not args.no_verify:
        print(f"\n[预览] 前 3 条:")
        for e in entries[:3]:
            print(f"  {e['start']} --> {e['end']}")
            print(f"  {e['text']}")
            print()


# ─── CLI ──────────────────────────────────────────────────────────────


def _add_asr_parser(subparsers):
    parser = subparsers.add_parser("asr", help="语音识别生成字幕",
        description="语音识别生成字幕（支持云端/本地模式）")
    parser.add_argument("audio", help="音频文件路径 (WAV/MP3/M4A/等)")
    parser.add_argument("-o", "--output", default=None, help="输出 SRT 路径 (默认: 同音频文件名)")
    parser.add_argument("-l", "--lang", default=None, help="语言: zh(中文), en(英文), yue(粤语), ja(日语), ko(韩语)  (默认: zh)")
    parser.add_argument("-w", "--max-words", type=int, default=-1, help="每句词数上限 (0=仅按标点, >0 加安全上限)")
    parser.add_argument("--local", action="store_true", help="使用本地 FunASR 模型（而非云端 API）")
    parser.add_argument("--model-name", default=None, help="本地模型名 (默认: config 中 local_model 或 paraformer-zh)")
    parser.add_argument("--device", default=None, help="推理设备 cpu/cuda (默认: config 中 local_device 或 cpu)")
    parser.add_argument("--model-dir", default=None, help="本地模型目录路径")
    parser.add_argument("--no-upload", action="store_true", help="跳过上传，直接使用 audio 参数作为文件 URL")
    parser.add_argument("--no-verify", action="store_true", help="不显示预览")
    return parser


def _add_align_parser(subparsers):
    parser = subparsers.add_parser("align", help="强制对齐生成字幕",
        description="音频 + 参考文稿 -> 字级精准对齐的 SRT")
    parser.add_argument("audio", help="音频文件路径 (WAV/MP3)")
    parser.add_argument("text", help="参考文本文件路径 (TXT)")
    parser.add_argument("-o", "--output", default=None, help="输出 SRT 路径 (默认: 同音频文件名)")
    parser.add_argument("--model", default=None, help="FunASR 模型名 (默认: config 中 align_model 或 fa-zh)")
    parser.add_argument("--device", default=None, help="推理设备 cpu/cuda (默认: config 中 align_device 或 cpu)")
    parser.add_argument("--max-chars", type=int, default=0, help="每句字数上限 (0=仅按标点拆分, >0 加字数安全上限)")
    parser.add_argument("--no-verify", action="store_true", help="不显示预览")
    return parser


def _add_read_srt_parser(subparsers):
    parser = subparsers.add_parser("read-srt", help="读取并解析 SRT 文件",
        description="读取 SRT 文件，解析为 JSON 输出")
    parser.add_argument("path", help="SRT 文件路径")
    parser.add_argument("--json-output", default=None, help="将解析结果保存为 JSON 文件")
    parser.add_argument("--no-verify", action="store_true", help="不保存 JSON 输出")
    return parser


def _add_convert_srt_parser(subparsers):
    parser = subparsers.add_parser("convert-srt", help="转换 SRT（ASR 修正 + 繁简转换 + CJK 间距）",
        description="对 SRT 进行 ASR 错误修正、繁简转换、CJK 间距和标点修复，保留所有时码")
    parser.add_argument("input", help="输入 SRT 文件路径")
    parser.add_argument("output", nargs="?", default=None, help="输出 SRT 路径 (默认: {input}_{lang}.srt)")
    parser.add_argument("lang", nargs="?", default=None, help="目标语言: zh-cn(简体), zh-tw(繁体), zh-hk(香港) (默认: zh-cn)")
    parser.add_argument("corrections", nargs="?", default=None, help="修正 JSON 文件路径 ({错误: 正确})")
    parser.add_argument("--no-verify", action="store_true", help="不显示预览")
    return parser


def _add_apply_corrections_parser(subparsers):
    parser = subparsers.add_parser("apply-corrections", help="应用纯文本替换（用于翻译）",
        description="保留所有时码，仅对文本进行替换。用于翻译场景：LLM 生成修正 JSON，此命令应用修正")
    parser.add_argument("input", help="输入 SRT 文件路径")
    parser.add_argument("output", help="输出 SRT 路径")
    parser.add_argument("corrections", help="修正 JSON 文件路径 ({原文: 译文})")
    parser.add_argument("--no-verify", action="store_true", help="不显示预览")
    return parser


def _run_asr(args):
    config = _load_config()
    max_words = args.max_words
    if max_words < 0:
        max_words = int(config.get("max_words", 0) or 0)

    if args.lang is None:
        args.lang = config.get("lang", "zh")
    if args.device is None:
        args.device = config.get("local_device", "cpu")

    if args.output is None:
        base, _ = os.path.splitext(args.audio)
        args.output = f"{base}_subtitle.srt"

    if args.local:
        local_model = _init_local_model(config, model_name=args.model_name, device=args.device, model_dir=args.model_dir)
        audio_path = args.audio
        temp_file = None
        normalized_path, is_temp = _normalize_audio(audio_path, config)
        if is_temp:
            temp_file = normalized_path
        audio_path = normalized_path
        local_result = transcribe_local(audio_path, local_model)
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        srt_text, count = _local_result_to_srt(local_result, max_words=max_words)
    else:
        _init_dashscope(config)
        audio_path = args.audio
        temp_file = None
        if not args.no_upload:
            normalized_path, is_temp = _normalize_audio(audio_path, config)
            if is_temp:
                temp_file = normalized_path
            audio_path = normalized_path
        if args.no_upload:
            file_url = args.audio
            print(f"[输入] 直接使用 URL: {file_url}")
        else:
            file_url = upload_audio(audio_path)
        result = transcribe(file_url, language=args.lang, config=config)
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        srt_text, count = result_to_srt(result, max_words=max_words)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(srt_text)
    print(f"\n[完成] 共 {count} 条字幕")
    print(f"[完成] 输出: {args.output}")
    if not args.no_verify:
        print(f"\n[预览] 前 5 条:")
        lines = srt_text.strip().split("\n")
        for line in lines[:15]:
            print(f"  {line}")


def _run_align(args):
    config = _load_config()
    if args.model is None:
        args.model = config.get("align_model", "fa-zh")
    if args.device is None:
        args.device = config.get("align_device", "cpu")

    if not os.path.isfile(args.audio):
        print(f"[错误] 音频文件不存在: {args.audio}")
        sys.exit(1)
    if not os.path.isfile(args.text):
        print(f"[错误] 文本文件不存在: {args.text}")
        sys.exit(1)

    if args.output is None:
        base, _ = os.path.splitext(args.audio)
        args.output = f"{base}_aligned.srt"

    with open(args.text, "r", encoding="utf-8") as f:
        ref_text = f.read().strip()
    if not ref_text:
        print("[错误] 参考文本为空")
        sys.exit(1)

    print(f"[文稿] {len(ref_text)} 字")
    print(f"[模型] 加载 {args.model} ...")
    t0 = time.time()
    try:
        from funasr import AutoModel
        model = AutoModel(model=args.model, device=args.device)
    except ImportError as e:
        print(f"[错误] 缺少依赖: {e}")
        print("  请执行: pip install funasr torch")
        sys.exit(1)
    except Exception as e:
        print(f"[错误] 模型加载失败: {e}")
        sys.exit(1)
    print(f"[模型] 加载完成 ({time.time()-t0:.1f}s)")

    print(f"[对齐] 开始对齐 ...")
    t0 = time.time()
    try:
        result = model.generate(
            input=(args.audio, args.text),
            data_type=("sound", "text"),
        )
    except Exception as e:
        print(f"[错误] 对齐失败: {e}")
        sys.exit(1)
    print(f"[对齐] 完成 ({time.time()-t0:.1f}s)")

    segments = _build_srt_segments(ref_text, result, max_chars=args.max_chars)
    if not segments:
        print("[警告] 对齐结果为空")
        return

    srt_lines = []
    for idx, (text, start_ms, end_ms) in enumerate(segments, 1):
        if end_ms == 0 and start_ms == 0 and len(segments) == 1:
            srt_lines.append(str(idx))
            srt_lines.append("00:00:00,000 --> 00:00:00,000")
            srt_lines.append(text)
            srt_lines.append("")
        elif end_ms > start_ms:
            srt_lines.append(str(idx))
            srt_lines.append(f"{_ms_to_srt(start_ms)} --> {_ms_to_srt(end_ms)}")
            srt_lines.append(text)
            srt_lines.append("")

    output = "\n".join(srt_lines)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n[完成] 共 {len(segments)} 条字幕")
    print(f"[完成] 输出: {args.output}")
    if not args.no_verify:
        print(f"\n[预览] 前 5 条:")
        lines = output.strip().split("\n")
        for line in lines[:20]:
            if line.strip():
                print(f"  {line}")


def main():
    parser = argparse.ArgumentParser(
        description="FunASR SRT Tools - ASR + 强制对齐 + SRT 校对",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""子命令:
  asr                 语音识别生成字幕（云端/本地），无需文稿
  align               强制对齐生成字幕（需提供参考文稿）
  read-srt            读取并解析 SRT 文件
  convert-srt         转换 SRT（ASR 修正 + 繁简转换 + CJK 间距）
  apply-corrections   应用纯文本替换（用于翻译）

示例:
  python funasr-srt-tools.py asr audio.wav
  python funasr-srt-tools.py asr audio.mp3 --lang en
  python funasr-srt-tools.py asr audio.wav --local
  python funasr-srt-tools.py align audio.wav transcript.txt
  python funasr-srt-tools.py read-srt subtitles.srt
  python funasr-srt-tools.py convert-srt input.srt output.srt zh-cn corrections.json
  python funasr-srt-tools.py apply-corrections input.srt output.srt corrections.json
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_asr_parser(subparsers)
    _add_align_parser(subparsers)
    _add_read_srt_parser(subparsers)
    _add_convert_srt_parser(subparsers)
    _add_apply_corrections_parser(subparsers)
    args = parser.parse_args()

    if args.command == "asr":
        _run_asr(args)
    elif args.command == "align":
        _run_align(args)
    elif args.command == "read-srt":
        _run_read_srt(args)
    elif args.command == "convert-srt":
        _run_convert_srt(args)
    elif args.command == "apply-corrections":
        _run_apply_corrections(args)


if __name__ == "__main__":
    main()
