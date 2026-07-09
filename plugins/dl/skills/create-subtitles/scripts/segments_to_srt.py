import math
import re
import textwrap

MIN_GAP_SECONDS = 0.001
max_chars_per_line = int(globals().get("max_chars_per_line", 0) or 0)
max_lines = int(globals().get("max_lines", 0) or 0)
segments = globals().get("segments", []) or []
words = globals().get("words", []) or []
requested_subtitle_mode = str(
    globals().get("subtitle_mode", globals().get("mode", "standard")) or "standard"
).strip().lower().replace("-", "_")
subtitle_mode = requested_subtitle_mode if requested_subtitle_mode in ("standard", "word_by_word") else "standard"


def _normalize_text(value):
    return re.sub(r"\s+", " ", str(value).strip())


def _wrap_text(value):
    text = _normalize_text(value)
    if not text or max_chars_per_line <= 0:
        return text

    lines = textwrap.wrap(
        text,
        width=max_chars_per_line,
        break_long_words=True,
        break_on_hyphens=False,
    )
    if max_lines <= 0 or len(lines) <= max_lines:
        return "\n".join(lines)

    target_width = max(max_chars_per_line, math.ceil(len(text) / max_lines))
    lines = textwrap.wrap(
        text,
        width=target_width,
        break_long_words=True,
        break_on_hyphens=False,
    )
    while len(lines) > max_lines:
        tail = f"{lines[-2]} {lines[-1]}".strip()
        lines = [*lines[:-2], tail]
    return "\n".join(lines)


def _seconds(value):
    return max(0.0, float(value))


def _fmt(seconds):
    total_ms = int(round(_seconds(seconds) * 1000))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    secs = total_ms // 1000
    ms = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


raw_cues = []
warnings = []

if requested_subtitle_mode not in ("standard", "word_by_word"):
    warnings.append(f"unknown subtitle_mode '{requested_subtitle_mode}', using standard")


def _collect_words():
    collected = []
    for word in words:
        collected.append(word)
    for segment in segments:
        for word in segment.get("words", []) or []:
            collected.append(word)
    return collected


if subtitle_mode == "word_by_word":
    for index, word in enumerate(_collect_words()):
        text = _normalize_text(word.get("word", word.get("text", "")))
        if not text:
            continue

        start_raw = word.get("start", word.get("start_time"))
        end_raw = word.get("end", word.get("end_time"))
        if start_raw is None or end_raw is None:
            warnings.append(f"skipped word without start/end: {text[:40]}")
            continue

        start = _seconds(start_raw)
        end = _seconds(end_raw)
        if end <= start:
            warnings.append(f"skipped non-positive word cue: {start} -> {end}")
            continue

        raw_cues.append({"index": index, "start": start, "end": end, "text": text})

    if not raw_cues:
        warnings.append("word_by_word requested but no usable word timings were found; fell back to standard")
        subtitle_mode = "standard"

if subtitle_mode == "standard":
    for index, segment in enumerate(segments):
        text = _wrap_text(segment.get("text", ""))
        if not text:
            continue

        start_raw = segment.get("start", segment.get("start_time"))
        end_raw = segment.get("end", segment.get("end_time"))
        if start_raw is None or end_raw is None:
            warnings.append(f"skipped segment without start/end: {text[:40]}")
            continue

        start = _seconds(start_raw)
        end = _seconds(end_raw)
        if end <= start:
            warnings.append(f"skipped non-positive cue: {start} -> {end}")
            continue

        raw_cues.append({"index": index, "start": start, "end": end, "text": text})

sorted_cues = sorted(raw_cues, key=lambda cue: (cue["start"], cue["end"], cue["index"]))
if [cue["index"] for cue in sorted_cues] != [cue["index"] for cue in raw_cues]:
    warnings.append("segments were sorted by start time before SRT generation")

rows = []
last_end = -1.0
overlap_count = 0
skipped_count = 0

for cue in sorted_cues:
    start = cue["start"]
    end = cue["end"]
    if start < last_end + MIN_GAP_SECONDS:
        original_start = start
        start = last_end + MIN_GAP_SECONDS
        if original_start < last_end:
            overlap_count += 1
            warnings.append(f"normalized overlapping cue start: {original_start:.3f} -> {start:.3f}")

    if end <= start:
        skipped_count += 1
        warnings.append(f"skipped cue after overlap normalization: {start:.3f} -> {end:.3f}")
        continue

    rows.append(f"{len(rows) + 1}\n{_fmt(start)} --> {_fmt(end)}\n{cue['text']}")
    last_end = end

srt_content = "\n\n".join(rows)
if srt_content:
    srt_content += "\n"

srt_validation = {
    "valid": bool(rows),
    "cue_count": len(rows),
    "overlap_count": overlap_count,
    "skipped_count": skipped_count,
    "warnings": warnings,
    "strategy": "shift_start_to_previous_end_plus_1ms" if overlap_count else "none",
}

result = {
    "srt_content": srt_content,
    "cue_count": len(rows),
    "subtitle_mode": subtitle_mode,
    "warnings": warnings,
    "srt_validation": srt_validation,
}
