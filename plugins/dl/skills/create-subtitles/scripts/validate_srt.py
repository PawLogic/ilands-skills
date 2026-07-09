import re
import math
import textwrap

MIN_GAP_SECONDS = 0.001
TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)
max_chars_per_line = int(globals().get("max_chars_per_line", 0) or 0)
max_lines = int(globals().get("max_lines", 0) or 0)


def _seconds(value):
    hours, minutes, rest = value.replace(".", ",").split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def _fmt(seconds):
    total_ms = int(round(max(0.0, float(seconds)) * 1000))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    secs = total_ms // 1000
    ms = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _blocks(value):
    return [block.strip() for block in re.split(r"\n\s*\n", value.strip()) if block.strip()]


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


normalize_overlaps = bool(globals().get("normalize_overlaps", True))
input_srt = str(globals().get("srt_content", ""))

warnings = []
errors = []
parsed = []

for block_index, block in enumerate(_blocks(input_srt), start=1):
    lines = [line.rstrip() for line in block.splitlines() if line.strip()]
    if not lines:
        continue

    timing_line_index = 1 if len(lines) > 1 and lines[0].strip().isdigit() else 0
    if timing_line_index >= len(lines):
        errors.append(f"block {block_index} missing timing line")
        continue

    match = TIME_RE.search(lines[timing_line_index])
    if not match:
        errors.append(f"block {block_index} has invalid timing line")
        continue

    text_lines = lines[timing_line_index + 1 :]
    text = _wrap_text("\n".join(text_lines))
    if not text:
        warnings.append(f"skipped empty cue in block {block_index}")
        continue

    start = _seconds(match.group("start"))
    end = _seconds(match.group("end"))
    if end <= start:
        errors.append(f"block {block_index} has non-positive timing: {start:.3f} -> {end:.3f}")
        continue

    parsed.append({"index": block_index, "start": start, "end": end, "text": text})

sorted_cues = sorted(parsed, key=lambda cue: (cue["start"], cue["end"], cue["index"]))
if [cue["index"] for cue in sorted_cues] != [cue["index"] for cue in parsed]:
    warnings.append("SRT cues were sorted by start time before validation output")

rows = []
last_end = -1.0
overlap_count = 0
skipped_count = 0

for cue in sorted_cues:
    start = cue["start"]
    end = cue["end"]
    if start < last_end + MIN_GAP_SECONDS:
        overlap_count += 1
        if normalize_overlaps:
            original_start = start
            start = last_end + MIN_GAP_SECONDS
            warnings.append(f"normalized overlapping cue start: {original_start:.3f} -> {start:.3f}")
        else:
            errors.append(f"cue {cue['index']} overlaps previous cue: {start:.3f} < {last_end:.3f}")

    if end <= start:
        skipped_count += 1
        message = f"skipped cue after overlap normalization: {start:.3f} -> {end:.3f}"
        if normalize_overlaps:
            warnings.append(message)
        else:
            errors.append(message)
        continue

    rows.append(f"{len(rows) + 1}\n{_fmt(start)} --> {_fmt(end)}\n{cue['text']}")
    last_end = end

normalized_srt_content = "\n\n".join(rows)
if normalized_srt_content:
    normalized_srt_content += "\n"

srt_validation = {
    "valid": bool(rows) and not errors,
    "cue_count": len(rows),
    "overlap_count": overlap_count,
    "skipped_count": skipped_count,
    "warnings": warnings,
    "errors": errors,
    "strategy": "shift_start_to_previous_end_plus_1ms" if overlap_count and normalize_overlaps else "none",
}

result = {
    "srt_content": normalized_srt_content,
    "srt_validation": srt_validation,
}
