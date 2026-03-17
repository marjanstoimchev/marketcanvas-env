"""Core 2D canvas data model and manipulation engine.

Stores elements on an 800x600 canvas and provides CRUD operations.
This is the pure data layer with no RL or MCP awareness.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .color_utils import hex_to_rgb


class ElementType(Enum):
    """Types of elements that can be placed on the canvas."""

    TEXT = "text"
    SHAPE = "shape"
    IMAGE = "image"


@dataclass
class CanvasElement:
    """A single element on the canvas.

    Attributes:
        id: Unique identifier.
        type: Element type (text, shape, image).
        x: Left edge x-coordinate in pixels.
        y: Top edge y-coordinate in pixels.
        width: Width in pixels.
        height: Height in pixels.
        z_index: Stacking order (higher = on top).
        color: Fill/background color as '#RRGGBB'.
        text_color: Text foreground color (TEXT elements only).
        content: Text string, shape descriptor ('rectangle', 'ellipse',
                 'rounded_rect'), or image label.
    """

    id: str
    type: ElementType
    x: float
    y: float
    width: float
    height: float
    z_index: int = 0
    color: str = "#FFFFFF"
    text_color: str = "#000000"
    content: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        d = asdict(self)
        d["type"] = self.type.value
        return d

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return (x1, y1, x2, y2) bounding box."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def center(self) -> tuple[float, float]:
        """Return (cx, cy) center point."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    def area(self) -> float:
        """Return element area in pixels^2."""
        return self.width * self.height


@dataclass
class CanvasEngine:
    """Core canvas that manages a collection of elements.

    Attributes:
        width: Canvas width in pixels (default 800).
        height: Canvas height in pixels (default 600).
        background_color: Canvas background as hex string.
        elements: Dict of element_id -> CanvasElement.
    """

    width: int = 800
    height: int = 600
    background_color: str = "#FFFFFF"
    elements: dict[str, CanvasElement] = field(default_factory=dict)
    _next_z: int = field(default=0, repr=False)

    def clear(self) -> None:
        """Remove all elements and reset z-index counter."""
        self.elements.clear()
        self._next_z = 0

    def add_element(
        self,
        element_type: ElementType,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str = "#FFFFFF",
        text_color: str = "#000000",
        content: str = "",
        element_id: str | None = None,
    ) -> CanvasElement:
        """Add a new element to the canvas.

        Positions are clamped to canvas bounds. Dimensions are clamped
        to [10, canvas_size].
        """
        eid = element_id or uuid.uuid4().hex[:8]
        if eid in self.elements:
            raise ValueError(f"Element ID '{eid}' already exists")

        # Validate color
        hex_to_rgb(color)
        hex_to_rgb(text_color)

        # Clamp dimensions
        width = max(10, min(width, self.width))
        height = max(10, min(height, self.height))

        # Clamp position
        x = max(0, min(x, self.width - width))
        y = max(0, min(y, self.height - height))

        elem = CanvasElement(
            id=eid,
            type=element_type,
            x=x,
            y=y,
            width=width,
            height=height,
            z_index=self._next_z,
            color=color,
            text_color=text_color,
            content=content,
        )
        self._next_z += 1
        self.elements[eid] = elem
        return elem

    def remove_element(self, element_id: str) -> CanvasElement:
        """Remove and return an element by ID."""
        if element_id not in self.elements:
            raise KeyError(f"Element '{element_id}' not found")
        return self.elements.pop(element_id)

    def move_element(self, element_id: str, x: float, y: float) -> CanvasElement:
        """Move an element to new (x, y) position, clamped to canvas bounds."""
        if element_id not in self.elements:
            raise KeyError(f"Element '{element_id}' not found")
        elem = self.elements[element_id]
        elem.x = max(0, min(x, self.width - elem.width))
        elem.y = max(0, min(y, self.height - elem.height))
        return elem

    def resize_element(
        self, element_id: str, width: float, height: float
    ) -> CanvasElement:
        """Resize an element. Minimum 10x10, maximum canvas dimensions."""
        if element_id not in self.elements:
            raise KeyError(f"Element '{element_id}' not found")
        elem = self.elements[element_id]
        elem.width = max(10, min(width, self.width))
        elem.height = max(10, min(height, self.height))
        # Re-clamp position if element now extends beyond canvas
        elem.x = max(0, min(elem.x, self.width - elem.width))
        elem.y = max(0, min(elem.y, self.height - elem.height))
        return elem

    def change_color(self, element_id: str, color: str) -> CanvasElement:
        """Change the fill/background color of an element."""
        if element_id not in self.elements:
            raise KeyError(f"Element '{element_id}' not found")
        hex_to_rgb(color)  # validate
        self.elements[element_id].color = color
        return self.elements[element_id]

    def change_text_color(self, element_id: str, text_color: str) -> CanvasElement:
        """Change the text foreground color of a TEXT element."""
        if element_id not in self.elements:
            raise KeyError(f"Element '{element_id}' not found")
        hex_to_rgb(text_color)  # validate
        self.elements[element_id].text_color = text_color
        return self.elements[element_id]

    def change_text(self, element_id: str, content: str) -> CanvasElement:
        """Change the text content of a TEXT element."""
        if element_id not in self.elements:
            raise KeyError(f"Element '{element_id}' not found")
        elem = self.elements[element_id]
        if elem.type != ElementType.TEXT:
            raise ValueError(
                f"Element '{element_id}' is {elem.type.value}, not text"
            )
        elem.content = content
        return elem

    def get_elements_sorted_by_z(self) -> list[CanvasElement]:
        """Return all elements sorted by z_index (ascending = back to front)."""
        return sorted(self.elements.values(), key=lambda e: e.z_index)

    def element_count(self) -> int:
        """Return number of elements on canvas."""
        return len(self.elements)

    def to_dict(self) -> dict[str, Any]:
        """Serialize full canvas state to a JSON-compatible dict."""
        return {
            "width": self.width,
            "height": self.height,
            "background_color": self.background_color,
            "element_count": self.element_count(),
            "elements": [
                e.to_dict() for e in self.get_elements_sorted_by_z()
            ],
        }
