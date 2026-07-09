def _number(value, fallback):
    try:
        parsed = float(value)
        return parsed if parsed > 0 else fallback
    except Exception:
        return fallback


def _clamp(value, low, high):
    return max(low, min(high, value))


# Three font-size tiers based on 1920x1080: small/medium/large -> 20/28/36; default medium.
SIZE_BASE = {"small": 20, "medium": 28, "large": 36}
SIZE_LABEL = {"small": "sm", "medium": "md", "large": "lg"}
SIZE_ALIAS = {
    "s": "small", "sm": "small", "small": "small",
    "m": "medium", "md": "medium", "medium": "medium", "default": "medium", "": "medium",
    "l": "large", "lg": "large", "large": "large",
}

width = int(round(_number(globals().get("width"), 1080)))
height = int(round(_number(globals().get("height"), 1920)))
position = str(globals().get("position", "bottom")).strip().lower()
if position not in ("top", "bottom"):
    position = "bottom"

size = SIZE_ALIAS.get(str(globals().get("size", "medium")).strip().lower(), "medium")

is_vertical = height >= width * 1.2

# Scale font size by max(width, height)/1920 so landscape and portrait 16:9 feel consistent.
# Explicit font_size_px overrides the tier mapping as an escape hatch. Clamp to schema's 12-72 range.
scale = max(width, height) / 1920.0
explicit_px = _number(globals().get("font_size_px"), 0)
if explicit_px > 0:
    font_size_px = int(round(_clamp(explicit_px, 12, 72)))
else:
    font_size_px = int(round(_clamp(SIZE_BASE[size] * scale, 12, 72)))

position_value = 0.13 if is_vertical else 0.1
if bool(globals().get("avoid_lower_third", False)) and position == "bottom":
    position_value = 0.18

# Subtitle text occupies 70% of screen width, leaving 15% safe margin on each side.
# margin_lr_px is for ffmpeg MarginL / MarginR; max_chars also wraps against the 70% text area.
margin_lr_px = int(round(width * 0.15))
max_chars_per_line = int(
    round(_clamp((width * 0.70) / max(font_size_px * 0.58, 1), 22, 46))
)

caption = {
    "fill_color": str(globals().get("fill_color", "#FFFFFF")),
    "border_color": str(globals().get("border_color", "#000000")),
    "font_id": str(globals().get("font_id", "noto_sans")),
    "font_weight": str(globals().get("font_weight", "bold")),
    "position": position,
    "position_value": position_value,
    "font_size": SIZE_LABEL[size],
    "font_size_px": font_size_px,
}

result = {
    "caption": caption,
    "layout": {
        "width": width,
        "height": height,
        "orientation": "vertical" if is_vertical else "landscape_or_square",
        "max_chars_per_line": max_chars_per_line,
        "max_lines": 2,
        "margin_lr_px": margin_lr_px,
    },
}
