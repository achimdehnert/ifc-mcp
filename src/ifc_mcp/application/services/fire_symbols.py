"""Fire Safety Symbols.

Standard symbols according to DIN 14034 / ISO 7010 for fire escape plans.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SymbolCategory(str, Enum):
    """Symbol categories."""

    ESCAPE = "escape"  # Fluchtweg-Symbole (grün)
    FIRE = "fire"  # Brandschutz-Symbole (rot)
    PROHIBITION = "prohibition"  # Verbotszeichen (rot/weiß)
    WARNING = "warning"  # Warnzeichen (gelb)
    MANDATORY = "mandatory"  # Gebotszeichen (blau)


@dataclass
class FireSymbol:
    """Fire safety symbol definition."""

    id: str
    name_de: str
    name_en: str
    category: SymbolCategory
    svg_content: str
    width: float = 40
    height: float = 40


# =============================================================================
# Symbol Definitions (SVG as strings)
# =============================================================================

# Colors according to ISO 7010
GREEN_ESCAPE = "#009639"  # RAL 6032
RED_FIRE = "#CC0000"  # RAL 3001
WHITE = "#FFFFFF"
BLACK = "#000000"


def _create_escape_symbol(inner_content: str, size: float = 40) -> str:
    """Create escape symbol with green background."""
    return f'''<g>
  <rect x="0" y="0" width="{size}" height="{size}" fill="{GREEN_ESCAPE}" rx="2"/>
  {inner_content}
</g>'''


def _create_fire_symbol(inner_content: str, size: float = 40) -> str:
    """Create fire symbol with red background."""
    return f'''<g>
  <rect x="0" y="0" width="{size}" height="{size}" fill="{RED_FIRE}" rx="2"/>
  {inner_content}
</g>'''


# =============================================================================
# Escape Route Symbols (Rettungszeichen - Grün)
# =============================================================================

# E001 - Notausgang links / Emergency exit left
SYMBOL_EXIT_LEFT = FireSymbol(
    id="E001",
    name_de="Notausgang links",
    name_en="Emergency exit left",
    category=SymbolCategory.ESCAPE,
    svg_content=_create_escape_symbol(f'''
  <path d="M8 12 L8 28 L14 28 L14 18 L20 18 L20 14 L14 14 L14 12 Z" fill="{WHITE}"/>
  <path d="M18 20 L32 20 L28 16 M32 20 L28 24" stroke="{WHITE}" stroke-width="2" fill="none"/>
  <circle cx="11" cy="9" r="3" fill="{WHITE}"/>
'''),
)

# E002 - Notausgang rechts / Emergency exit right
SYMBOL_EXIT_RIGHT = FireSymbol(
    id="E002",
    name_de="Notausgang rechts",
    name_en="Emergency exit right",
    category=SymbolCategory.ESCAPE,
    svg_content=_create_escape_symbol(f'''
  <path d="M32 12 L32 28 L26 28 L26 18 L20 18 L20 14 L26 14 L26 12 Z" fill="{WHITE}"/>
  <path d="M22 20 L8 20 L12 16 M8 20 L12 24" stroke="{WHITE}" stroke-width="2" fill="none"/>
  <circle cx="29" cy="9" r="3" fill="{WHITE}"/>
'''),
)

# E003 - Erste Hilfe / First aid
SYMBOL_FIRST_AID = FireSymbol(
    id="E003",
    name_de="Erste Hilfe",
    name_en="First aid",
    category=SymbolCategory.ESCAPE,
    svg_content=_create_escape_symbol(f'''
  <rect x="17" y="8" width="6" height="24" fill="{WHITE}"/>
  <rect x="8" y="17" width="24" height="6" fill="{WHITE}"/>
'''),
)

# E004 - Sammelstelle / Assembly point
SYMBOL_ASSEMBLY_POINT = FireSymbol(
    id="E004",
    name_de="Sammelstelle",
    name_en="Assembly point",
    category=SymbolCategory.ESCAPE,
    svg_content=_create_escape_symbol(f'''
  <circle cx="12" cy="10" r="3" fill="{WHITE}"/>
  <circle cx="28" cy="10" r="3" fill="{WHITE}"/>
  <circle cx="12" cy="30" r="3" fill="{WHITE}"/>
  <circle cx="28" cy="30" r="3" fill="{WHITE}"/>
  <path d="M12 14 L12 26 M28 14 L28 26" stroke="{WHITE}" stroke-width="2"/>
  <path d="M16 20 L24 20" stroke="{WHITE}" stroke-width="2"/>
'''),
)

# E007 - Richtungspfeil / Direction arrow
SYMBOL_ARROW_UP = FireSymbol(
    id="E007_UP",
    name_de="Richtungspfeil oben",
    name_en="Direction arrow up",
    category=SymbolCategory.ESCAPE,
    svg_content=_create_escape_symbol(f'''
  <path d="M20 8 L30 20 L24 20 L24 32 L16 32 L16 20 L10 20 Z" fill="{WHITE}"/>
'''),
)

SYMBOL_ARROW_DOWN = FireSymbol(
    id="E007_DOWN",
    name_de="Richtungspfeil unten",
    name_en="Direction arrow down",
    category=SymbolCategory.ESCAPE,
    svg_content=_create_escape_symbol(f'''
  <path d="M20 32 L30 20 L24 20 L24 8 L16 8 L16 20 L10 20 Z" fill="{WHITE}"/>
'''),
)

SYMBOL_ARROW_LEFT = FireSymbol(
    id="E007_LEFT",
    name_de="Richtungspfeil links",
    name_en="Direction arrow left",
    category=SymbolCategory.ESCAPE,
    svg_content=_create_escape_symbol(f'''
  <path d="M8 20 L20 10 L20 16 L32 16 L32 24 L20 24 L20 30 Z" fill="{WHITE}"/>
'''),
)

SYMBOL_ARROW_RIGHT = FireSymbol(
    id="E007_RIGHT",
    name_de="Richtungspfeil rechts",
    name_en="Direction arrow right",
    category=SymbolCategory.ESCAPE,
    svg_content=_create_escape_symbol(f'''
  <path d="M32 20 L20 10 L20 16 L8 16 L8 24 L20 24 L20 30 Z" fill="{WHITE}"/>
'''),
)


# =============================================================================
# Fire Protection Symbols (Brandschutzzeichen - Rot)
# =============================================================================

# F001 - Feuerlöscher / Fire extinguisher
SYMBOL_FIRE_EXTINGUISHER = FireSymbol(
    id="F001",
    name_de="Feuerlöscher",
    name_en="Fire extinguisher",
    category=SymbolCategory.FIRE,
    svg_content=_create_fire_symbol(f'''
  <path d="M16 8 L16 12 L14 12 L14 32 L26 32 L26 12 L24 12 L24 8 L20 8 L20 6 L22 6 L22 4 L18 4 L18 6 L20 6 L20 8 Z" fill="{WHITE}"/>
  <rect x="16" y="14" width="8" height="4" fill="{RED_FIRE}"/>
'''),
)

# F002 - Löschschlauch / Fire hose
SYMBOL_FIRE_HOSE = FireSymbol(
    id="F002",
    name_de="Löschschlauch",
    name_en="Fire hose",
    category=SymbolCategory.FIRE,
    svg_content=_create_fire_symbol(f'''
  <rect x="8" y="8" width="24" height="24" fill="none" stroke="{WHITE}" stroke-width="2"/>
  <circle cx="20" cy="20" r="6" fill="none" stroke="{WHITE}" stroke-width="2"/>
  <path d="M20 14 L20 8 M20 26 L20 32 M14 20 L8 20 M26 20 L32 20" stroke="{WHITE}" stroke-width="2"/>
'''),
)

# F003 - Feuerleiter / Fire ladder
SYMBOL_FIRE_LADDER = FireSymbol(
    id="F003",
    name_de="Feuerleiter",
    name_en="Fire ladder",
    category=SymbolCategory.FIRE,
    svg_content=_create_fire_symbol(f'''
  <path d="M12 8 L12 32 M28 8 L28 32" stroke="{WHITE}" stroke-width="2"/>
  <path d="M12 12 L28 12 M12 18 L28 18 M12 24 L28 24 M12 30 L28 30" stroke="{WHITE}" stroke-width="2"/>
'''),
)

# F004 - Brandmelder / Fire alarm call point
SYMBOL_FIRE_ALARM = FireSymbol(
    id="F004",
    name_de="Brandmelder",
    name_en="Fire alarm call point",
    category=SymbolCategory.FIRE,
    svg_content=_create_fire_symbol(f'''
  <rect x="10" y="8" width="20" height="24" fill="{WHITE}" rx="2"/>
  <rect x="14" y="12" width="12" height="8" fill="{RED_FIRE}"/>
  <circle cx="20" cy="26" r="3" fill="{RED_FIRE}"/>
'''),
)

# F005 - Brandmeldetelefon / Fire alarm telephone
SYMBOL_FIRE_PHONE = FireSymbol(
    id="F005",
    name_de="Brandmeldetelefon",
    name_en="Fire alarm telephone",
    category=SymbolCategory.FIRE,
    svg_content=_create_fire_symbol(f'''
  <path d="M10 12 Q10 8 14 8 L26 8 Q30 8 30 12 L30 14 Q30 18 26 18 L22 18 L22 28 Q22 32 18 32 Q14 32 14 28 L14 18 L10 18 Q6 18 6 14 Z" fill="{WHITE}"/>
'''),
)


# =============================================================================
# Door Symbols
# =============================================================================

SYMBOL_DOOR_NORMAL = '''<g>
  <rect x="0" y="0" width="10" height="40" fill="#FFFFFF" stroke="#0000FF" stroke-width="0.5"/>
  <circle cx="8" cy="20" r="1.5" fill="#0000FF"/>
</g>'''

SYMBOL_DOOR_FIRE = '''<g>
  <rect x="0" y="0" width="10" height="40" fill="#FF6B6B" stroke="#FF0000" stroke-width="1"/>
  <circle cx="8" cy="20" r="1.5" fill="#FF0000"/>
  <text x="5" y="35" font-size="6" fill="#FF0000" text-anchor="middle">T30</text>
</g>'''

SYMBOL_DOOR_ESCAPE = '''<g>
  <rect x="0" y="0" width="10" height="40" fill="#90EE90" stroke="#009639" stroke-width="1"/>
  <path d="M5 15 L5 25 L8 20 Z" fill="#009639"/>
</g>'''


# =============================================================================
# Symbol Registry
# =============================================================================

FIRE_SYMBOLS: dict[str, FireSymbol] = {
    # Escape symbols
    "E001": SYMBOL_EXIT_LEFT,
    "E002": SYMBOL_EXIT_RIGHT,
    "E003": SYMBOL_FIRST_AID,
    "E004": SYMBOL_ASSEMBLY_POINT,
    "E007_UP": SYMBOL_ARROW_UP,
    "E007_DOWN": SYMBOL_ARROW_DOWN,
    "E007_LEFT": SYMBOL_ARROW_LEFT,
    "E007_RIGHT": SYMBOL_ARROW_RIGHT,
    # Fire symbols
    "F001": SYMBOL_FIRE_EXTINGUISHER,
    "F002": SYMBOL_FIRE_HOSE,
    "F003": SYMBOL_FIRE_LADDER,
    "F004": SYMBOL_FIRE_ALARM,
    "F005": SYMBOL_FIRE_PHONE,
}


def get_symbol(symbol_id: str) -> FireSymbol | None:
    """Get symbol by ID."""
    return FIRE_SYMBOLS.get(symbol_id)


def get_symbol_svg(symbol_id: str, x: float = 0, y: float = 0, scale: float = 1.0) -> str:
    """Get symbol SVG with position and scale."""
    symbol = FIRE_SYMBOLS.get(symbol_id)
    if not symbol:
        return ""

    return f'''<g transform="translate({x},{y}) scale({scale})">
  {symbol.svg_content}
</g>'''


def get_symbols_defs() -> str:
    """Get all symbols as SVG defs for reuse."""
    defs = []
    for symbol_id, symbol in FIRE_SYMBOLS.items():
        defs.append(f'''<symbol id="sym_{symbol_id}" viewBox="0 0 40 40">
  {symbol.svg_content}
</symbol>''')
    return "\n".join(defs)


def use_symbol(symbol_id: str, x: float, y: float, width: float = 40, height: float = 40) -> str:
    """Create SVG use element for symbol."""
    return f'<use xlink:href="#sym_{symbol_id}" x="{x}" y="{y}" width="{width}" height="{height}"/>'
