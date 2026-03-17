"""Color manipulation and WCAG accessibility utilities.

Provides hex/RGB conversion and WCAG 2.1 contrast ratio calculations
for evaluating text readability on the canvas.
"""
from __future__ import annotations


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#RRGGBB' or '#RGB' to (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (R, G, B) tuple to '#RRGGBB' string."""
    return f"#{r:02X}{g:02X}{b:02X}"


def _srgb_to_linear(channel_8bit: int) -> float:
    """Convert a single sRGB channel [0,255] to linear [0,1]."""
    c = channel_8bit / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(r: int, g: int, b: int) -> float:
    """Compute WCAG relative luminance from sRGB (0-255) values.

    L = 0.2126*R_lin + 0.7152*G_lin + 0.0722*B_lin
    Returns float in [0.0, 1.0].
    """
    return (
        0.2126 * _srgb_to_linear(r)
        + 0.7152 * _srgb_to_linear(g)
        + 0.0722 * _srgb_to_linear(b)
    )


def contrast_ratio(
    color1: tuple[int, int, int], color2: tuple[int, int, int]
) -> float:
    """Compute WCAG contrast ratio between two RGB colors.

    Returns float in [1.0, 21.0].
    WCAG AA requires >= 4.5 for normal text, >= 3.0 for large text.
    """
    l1 = relative_luminance(*color1)
    l2 = relative_luminance(*color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# Predefined color palette
NAMED_COLORS: dict[str, str] = {
    "white": "#FFFFFF",
    "black": "#000000",
    "red": "#FF0000",
    "green": "#00AA00",
    "blue": "#0066CC",
    "yellow": "#FFDD00",
    "orange": "#FF8800",
    "purple": "#8800CC",
    "gray": "#888888",
    "light_gray": "#CCCCCC",
    "dark_gray": "#333333",
}
