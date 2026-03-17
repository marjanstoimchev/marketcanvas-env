"""Pillow-based PNG renderer for the canvas.

Renders the current canvas state to a PIL Image or saves it as a PNG file.
Supports text, shape (rectangle/ellipse/rounded_rect), and image elements.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .canvas_engine import CanvasEngine, CanvasElement, ElementType
from .color_utils import hex_to_rgb

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_BOLD_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a DejaVuSans font at the given size."""
    path = _BOLD_FONT_PATH if bold else _FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except (IOError, OSError):
            return ImageFont.load_default()


def render_canvas(
    engine: CanvasEngine, output_path: str | Path | None = None
) -> Image.Image:
    """Render the canvas to a Pillow Image.

    Args:
        engine: Canvas engine with current state.
        output_path: If provided, save PNG to this path.

    Returns:
        PIL.Image.Image of the rendered canvas.
    """
    bg_rgb = hex_to_rgb(engine.background_color)
    img = Image.new("RGB", (engine.width, engine.height), bg_rgb)
    draw = ImageDraw.Draw(img)

    for elem in engine.get_elements_sorted_by_z():
        if elem.type == ElementType.TEXT:
            _render_text_element(draw, elem)
        elif elem.type == ElementType.SHAPE:
            _render_shape_element(draw, elem)
        elif elem.type == ElementType.IMAGE:
            _render_image_element(draw, elem, img)

    if output_path is not None:
        img.save(str(output_path), "PNG")

    return img


def _render_text_element(draw: ImageDraw.ImageDraw, elem: CanvasElement) -> None:
    """Render a text element: background rectangle + centered text."""
    x1, y1 = int(elem.x), int(elem.y)
    x2, y2 = int(elem.x + elem.width), int(elem.y + elem.height)
    bg_color = hex_to_rgb(elem.color)
    text_color = hex_to_rgb(elem.text_color)

    # Draw background
    draw.rectangle([x1, y1, x2, y2], fill=bg_color)

    if not elem.content:
        return

    # Compute font size (start at ~60% of height, shrink to fit width)
    font_size = max(10, int(elem.height * 0.6))
    font = _get_font(font_size, bold=True)

    # Shrink font if text overflows width
    bbox = draw.textbbox((0, 0), elem.content, font=font)
    text_w = bbox[2] - bbox[0]
    while text_w > elem.width - 10 and font_size > 10:
        font_size -= 2
        font = _get_font(font_size, bold=True)
        bbox = draw.textbbox((0, 0), elem.content, font=font)
        text_w = bbox[2] - bbox[0]

    # Center text in bounding box
    bbox = draw.textbbox((0, 0), elem.content, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = x1 + (elem.width - text_w) / 2
    ty = y1 + (elem.height - text_h) / 2

    draw.text((tx, ty), elem.content, fill=text_color, font=font)


def _render_shape_element(draw: ImageDraw.ImageDraw, elem: CanvasElement) -> None:
    """Render a shape element: rectangle, ellipse, or rounded rectangle."""
    x1, y1 = int(elem.x), int(elem.y)
    x2, y2 = int(elem.x + elem.width), int(elem.y + elem.height)
    fill_color = hex_to_rgb(elem.color)

    shape_type = elem.content.lower() if elem.content else "rectangle"

    if shape_type == "ellipse":
        draw.ellipse([x1, y1, x2, y2], fill=fill_color)
    elif shape_type == "rounded_rect":
        radius = int(min(elem.width, elem.height) * 0.15)
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill_color)
    else:
        # Default: rectangle
        draw.rectangle([x1, y1, x2, y2], fill=fill_color)


def _render_image_element(
    draw: ImageDraw.ImageDraw, elem: CanvasElement, img: Image.Image
) -> None:
    """Render an image placeholder: gray box with 'IMAGE' label and X pattern."""
    x1, y1 = int(elem.x), int(elem.y)
    x2, y2 = int(elem.x + elem.width), int(elem.y + elem.height)

    # Gray placeholder box
    draw.rectangle([x1, y1, x2, y2], fill=(200, 200, 200))

    # X pattern to indicate placeholder
    line_color = (150, 150, 150)
    draw.line([x1, y1, x2, y2], fill=line_color, width=2)
    draw.line([x2, y1, x1, y2], fill=line_color, width=2)

    # Border
    draw.rectangle([x1, y1, x2, y2], outline=(100, 100, 100), width=2)

    # Label
    label = elem.content if elem.content else "IMAGE"
    font_size = max(10, int(min(elem.width, elem.height) * 0.2))
    font = _get_font(font_size)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = x1 + (elem.width - text_w) / 2
    ty = y1 + (elem.height - text_h) / 2
    draw.text((tx, ty), label, fill=(80, 80, 80), font=font)
