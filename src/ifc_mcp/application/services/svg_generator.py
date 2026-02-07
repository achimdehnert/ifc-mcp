"""SVG Generator Base.

Base class for generating SVG drawings from IFC geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass
class Point2D:
    """2D Point."""

    x: float
    y: float

    def __add__(self, other: "Point2D") -> "Point2D":
        return Point2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point2D") -> "Point2D":
        return Point2D(self.x - other.x, self.y - other.y)

    def scale(self, factor: float) -> "Point2D":
        return Point2D(self.x * factor, self.y * factor)


@dataclass
class BoundingBox:
    """2D Bounding Box."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def center(self) -> Point2D:
        return Point2D(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
        )

    def expand(self, margin: float) -> "BoundingBox":
        """Expand bounding box by margin."""
        return BoundingBox(
            min_x=self.min_x - margin,
            min_y=self.min_y - margin,
            max_x=self.max_x + margin,
            max_y=self.max_y + margin,
        )

    @classmethod
    def from_points(cls, points: list[Point2D]) -> "BoundingBox":
        """Create from list of points."""
        if not points:
            return cls(0, 0, 0, 0)
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        return cls(min(xs), min(ys), max(xs), max(ys))


@dataclass
class SVGStyle:
    """SVG styling options."""

    fill: str = "none"
    stroke: str = "#000000"
    stroke_width: float = 1.0
    stroke_dasharray: str | None = None
    opacity: float = 1.0
    font_size: float = 12.0
    font_family: str = "Arial, sans-serif"

    def to_style_string(self) -> str:
        """Convert to CSS style string."""
        parts = [
            f"fill:{self.fill}",
            f"stroke:{self.stroke}",
            f"stroke-width:{self.stroke_width}",
        ]
        if self.stroke_dasharray:
            parts.append(f"stroke-dasharray:{self.stroke_dasharray}")
        if self.opacity < 1.0:
            parts.append(f"opacity:{self.opacity}")
        return ";".join(parts)


# =============================================================================
# Predefined Styles
# =============================================================================

STYLE_WALL = SVGStyle(fill="#333333", stroke="#000000", stroke_width=0.5)
STYLE_WALL_FIRE = SVGStyle(fill="#8B0000", stroke="#FF0000", stroke_width=1.0)
STYLE_DOOR = SVGStyle(fill="#FFFFFF", stroke="#0000FF", stroke_width=0.5)
STYLE_DOOR_FIRE = SVGStyle(fill="#FF6B6B", stroke="#FF0000", stroke_width=1.0)
STYLE_WINDOW = SVGStyle(fill="#87CEEB", stroke="#4169E1", stroke_width=0.5)
STYLE_SPACE = SVGStyle(fill="#F5F5F5", stroke="#CCCCCC", stroke_width=0.3)
STYLE_SPACE_EX = SVGStyle(fill="#FFCCCC", stroke="#FF0000", stroke_width=0.5)
STYLE_ESCAPE_ROUTE = SVGStyle(
    fill="none", stroke="#00AA00", stroke_width=3.0, stroke_dasharray="10,5"
)
STYLE_FIRE_COMPARTMENT = SVGStyle(
    fill="none", stroke="#FF0000", stroke_width=2.0, stroke_dasharray="15,5"
)


@dataclass
class SVGElement:
    """Base class for SVG elements."""

    element_id: str | None = None
    style: SVGStyle = field(default_factory=SVGStyle)
    css_class: str | None = None
    title: str | None = None

    def render(self) -> str:
        """Render to SVG string."""
        raise NotImplementedError


@dataclass
class SVGRect(SVGElement):
    """SVG Rectangle."""

    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    rx: float = 0  # Corner radius

    def render(self) -> str:
        attrs = [
            f'x="{self.x:.2f}"',
            f'y="{self.y:.2f}"',
            f'width="{self.width:.2f}"',
            f'height="{self.height:.2f}"',
        ]
        if self.rx > 0:
            attrs.append(f'rx="{self.rx:.2f}"')
        if self.element_id:
            attrs.append(f'id="{self.element_id}"')
        if self.css_class:
            attrs.append(f'class="{self.css_class}"')
        attrs.append(f'style="{self.style.to_style_string()}"')

        title_elem = f"<title>{self.title}</title>" if self.title else ""
        return f'<rect {" ".join(attrs)}>{title_elem}</rect>'


@dataclass
class SVGLine(SVGElement):
    """SVG Line."""

    x1: float = 0
    y1: float = 0
    x2: float = 0
    y2: float = 0

    def render(self) -> str:
        attrs = [
            f'x1="{self.x1:.2f}"',
            f'y1="{self.y1:.2f}"',
            f'x2="{self.x2:.2f}"',
            f'y2="{self.y2:.2f}"',
        ]
        if self.element_id:
            attrs.append(f'id="{self.element_id}"')
        if self.css_class:
            attrs.append(f'class="{self.css_class}"')
        attrs.append(f'style="{self.style.to_style_string()}"')
        return f'<line {" ".join(attrs)}/>'


@dataclass
class SVGPath(SVGElement):
    """SVG Path."""

    d: str = ""  # Path data

    def render(self) -> str:
        attrs = [f'd="{self.d}"']
        if self.element_id:
            attrs.append(f'id="{self.element_id}"')
        if self.css_class:
            attrs.append(f'class="{self.css_class}"')
        attrs.append(f'style="{self.style.to_style_string()}"')

        title_elem = f"<title>{self.title}</title>" if self.title else ""
        return f'<path {" ".join(attrs)}>{title_elem}</path>'


@dataclass
class SVGPolygon(SVGElement):
    """SVG Polygon."""

    points: list[Point2D] = field(default_factory=list)

    def render(self) -> str:
        points_str = " ".join(f"{p.x:.2f},{p.y:.2f}" for p in self.points)
        attrs = [f'points="{points_str}"']
        if self.element_id:
            attrs.append(f'id="{self.element_id}"')
        if self.css_class:
            attrs.append(f'class="{self.css_class}"')
        attrs.append(f'style="{self.style.to_style_string()}"')

        title_elem = f"<title>{self.title}</title>" if self.title else ""
        return f'<polygon {" ".join(attrs)}>{title_elem}</polygon>'


@dataclass
class SVGCircle(SVGElement):
    """SVG Circle."""

    cx: float = 0
    cy: float = 0
    r: float = 10

    def render(self) -> str:
        attrs = [
            f'cx="{self.cx:.2f}"',
            f'cy="{self.cy:.2f}"',
            f'r="{self.r:.2f}"',
        ]
        if self.element_id:
            attrs.append(f'id="{self.element_id}"')
        if self.css_class:
            attrs.append(f'class="{self.css_class}"')
        attrs.append(f'style="{self.style.to_style_string()}"')

        title_elem = f"<title>{self.title}</title>" if self.title else ""
        return f'<circle {" ".join(attrs)}>{title_elem}</circle>'


@dataclass
class SVGText(SVGElement):
    """SVG Text."""

    x: float = 0
    y: float = 0
    text: str = ""
    anchor: str = "middle"  # start, middle, end
    rotate: float = 0

    def render(self) -> str:
        attrs = [
            f'x="{self.x:.2f}"',
            f'y="{self.y:.2f}"',
            f'text-anchor="{self.anchor}"',
            f'font-size="{self.style.font_size}"',
            f'font-family="{self.style.font_family}"',
        ]
        if self.rotate != 0:
            attrs.append(f'transform="rotate({self.rotate} {self.x:.2f} {self.y:.2f})"')
        if self.element_id:
            attrs.append(f'id="{self.element_id}"')
        if self.css_class:
            attrs.append(f'class="{self.css_class}"')

        return f'<text {" ".join(attrs)}>{self.text}</text>'


@dataclass
class SVGGroup(SVGElement):
    """SVG Group."""

    children: list[SVGElement] = field(default_factory=list)
    transform: str | None = None

    def add(self, element: SVGElement) -> None:
        """Add child element."""
        self.children.append(element)

    def render(self) -> str:
        attrs = []
        if self.element_id:
            attrs.append(f'id="{self.element_id}"')
        if self.css_class:
            attrs.append(f'class="{self.css_class}"')
        if self.transform:
            attrs.append(f'transform="{self.transform}"')

        children_str = "\n".join(c.render() for c in self.children)
        attr_str = " ".join(attrs)
        return f"<g {attr_str}>\n{children_str}\n</g>"


@dataclass
class SVGDocument:
    """Complete SVG Document."""

    width: float = 800
    height: float = 600
    viewbox: BoundingBox | None = None
    elements: list[SVGElement] = field(default_factory=list)
    defs: list[str] = field(default_factory=list)  # For symbols, gradients, etc.
    title: str = "Floor Plan"
    background_color: str = "#FFFFFF"

    def add(self, element: SVGElement) -> None:
        """Add element to document."""
        self.elements.append(element)

    def add_def(self, definition: str) -> None:
        """Add definition (symbol, gradient, etc.)."""
        self.defs.append(definition)

    def render(self) -> str:
        """Render complete SVG document."""
        # Calculate viewBox
        if self.viewbox:
            vb = self.viewbox
            viewbox_str = f'viewBox="{vb.min_x:.2f} {vb.min_y:.2f} {vb.width:.2f} {vb.height:.2f}"'
        else:
            viewbox_str = f'viewBox="0 0 {self.width:.2f} {self.height:.2f}"'

        # Defs section
        defs_str = ""
        if self.defs:
            defs_content = "\n".join(self.defs)
            defs_str = f"<defs>\n{defs_content}\n</defs>"

        # Background
        bg_rect = f'<rect width="100%" height="100%" fill="{self.background_color}"/>'

        # Elements
        elements_str = "\n".join(e.render() for e in self.elements)

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{self.width:.0f}" 
     height="{self.height:.0f}" 
     {viewbox_str}>
  <title>{self.title}</title>
  {defs_str}
  {bg_rect}
  {elements_str}
</svg>'''
