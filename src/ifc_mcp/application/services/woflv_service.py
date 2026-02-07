"""WoFlV Service (Wohnfl\u00e4chenverordnung).

German residential area calculation regulation.
Migrated from cad_hub with proper async architecture.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork


@dataclass
class WoFlVSpace:
    """Single space with WoFlV calculation."""

    name: str
    number: str = ""
    storey_name: str = ""

    # Areas
    grundflaeche: Decimal = Decimal("0")
    hoehe: Decimal = Decimal("2.50")

    # Factors
    hoehen_faktor: Decimal = Decimal("1.0")
    raumtyp: str = "wohnraum"
    raumtyp_faktor: Decimal = Decimal("1.0")

    @property
    def gesamt_faktor(self) -> Decimal:
        """Combined factor (height \u00d7 room type)."""
        return self.hoehen_faktor * self.raumtyp_faktor

    @property
    def wohnflaeche(self) -> Decimal:
        """Counted residential area."""
        return self.grundflaeche * self.gesamt_faktor

    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "name": self.name,
            "number": self.number,
            "storey_name": self.storey_name,
            "grundflaeche": float(self.grundflaeche),
            "hoehe": float(self.hoehe),
            "hoehen_faktor": float(self.hoehen_faktor),
            "raumtyp": self.raumtyp,
            "raumtyp_faktor": float(self.raumtyp_faktor),
            "gesamt_faktor": float(self.gesamt_faktor),
            "wohnflaeche": float(self.wohnflaeche),
        }


@dataclass
class WoFlVResult:
    """Result of WoFlV calculation."""

    # Totals
    grundflaeche_gesamt: Decimal = Decimal("0")
    wohnflaeche_gesamt: Decimal = Decimal("0")

    # By counting factor
    wohnflaeche_100: Decimal = Decimal("0")  # 100% counted
    wohnflaeche_50: Decimal = Decimal("0")  # 50% counted
    wohnflaeche_25: Decimal = Decimal("0")  # 25% counted
    nicht_angerechnet: Decimal = Decimal("0")  # Not counted

    # Spaces
    spaces: list[WoFlVSpace] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def _round(self, value: Decimal, decimals: int = 2) -> Decimal:
        """Round decimal value."""
        return value.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)

    @property
    def anrechnungsquote(self) -> float:
        """Counting ratio (Wohnfl\u00e4che/Grundfl\u00e4che)."""
        if self.grundflaeche_gesamt == 0:
            return 0.0
        return float(self.wohnflaeche_gesamt / self.grundflaeche_gesamt)

    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "grundflaeche_gesamt": float(self._round(self.grundflaeche_gesamt)),
            "wohnflaeche_gesamt": float(self._round(self.wohnflaeche_gesamt)),
            "wohnflaeche_100": float(self._round(self.wohnflaeche_100)),
            "wohnflaeche_50": float(self._round(self.wohnflaeche_50)),
            "wohnflaeche_25": float(self._round(self.wohnflaeche_25)),
            "nicht_angerechnet": float(self._round(self.nicht_angerechnet)),
            "anrechnungsquote": round(self.anrechnungsquote, 3),
            "space_count": len(self.spaces),
            "warnings": self.warnings,
        }


class WoFlVService:
    """Service for WoFlV (Wohnfl\u00e4chenverordnung) calculations.

    German residential area calculation regulation.

    Rules:
    - Height >= 2.00m: 100% counting
    - Height 1.00-2.00m: 50% counting
    - Height < 1.00m: no counting
    - Balconies/terraces: 25% (max 50%)
    - Cellars/garages: 0%
    """

    # Room type factors according to WoFlV
    RAUMTYP_FAKTOREN = {
        "wohnraum": {
            "faktor": Decimal("1.0"),
            "keywords": [
                "wohn",
                "schlaf",
                "kind",
                "k\u00fcche",
                "bad",
                "dusch",
                "ess",
                "arbeits",
            ],
        },
        "wintergarten_beheizt": {
            "faktor": Decimal("1.0"),
            "keywords": ["wintergarten beheizt"],
        },
        "wintergarten_unbeheizt": {
            "faktor": Decimal("0.5"),
            "keywords": ["wintergarten"],
        },
        "schwimmbad": {
            "faktor": Decimal("0.5"),
            "keywords": ["schwimm", "pool", "sauna"],
        },
        "balkon": {
            "faktor": Decimal("0.25"),
            "keywords": ["balkon", "loggia", "dachgarten"],
        },
        "terrasse": {
            "faktor": Decimal("0.25"),
            "keywords": ["terrasse", "freisitz"],
        },
        "keller": {
            "faktor": Decimal("0.0"),
            "keywords": ["keller", "wasch", "trocken", "heizung", "technik"],
        },
        "garage": {
            "faktor": Decimal("0.0"),
            "keywords": ["garage", "carport", "stellplatz"],
        },
        "flur": {"faktor": Decimal("1.0"), "keywords": ["flur", "diele", "gang"]},
    }

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize service.

        Args:
            uow: Unit of Work instance
        """
        self._uow = uow

    def _get_hoehen_faktor(self, hoehe: float) -> Decimal:
        """Get counting factor by room height.

        Args:
            hoehe: Room height in meters

        Returns:
            Counting factor (0.0, 0.5, or 1.0)
        """
        if hoehe >= 2.0:
            return Decimal("1.0")
        elif hoehe >= 1.0:
            return Decimal("0.5")
        else:
            return Decimal("0.0")

    def _get_raumtyp_faktor(self, name: str) -> tuple[str, Decimal]:
        """Get room type and factor from name.

        Args:
            name: Space name

        Returns:
            Tuple of (room_type, factor)
        """
        search_text = name.lower()

        # Check order (specific \u2192 general)
        type_order = [
            "wintergarten_beheizt",
            "wintergarten_unbeheizt",
            "schwimmbad",
            "balkon",
            "terrasse",
            "keller",
            "garage",
            "flur",
            "wohnraum",
        ]

        for raumtyp in type_order:
            config = self.RAUMTYP_FAKTOREN.get(raumtyp, {})
            keywords = config.get("keywords", [])

            if any(kw in search_text for kw in keywords):
                return raumtyp, config.get("faktor", Decimal("1.0"))

        # Default: living space
        return "wohnraum", Decimal("1.0")

    def _calculate_space(
        self,
        name: str,
        area: Decimal,
        hoehe: Decimal,
        number: str = "",
        storey_name: str = "",
    ) -> WoFlVSpace:
        """Calculate WoFlV for single space.

        Args:
            name: Space name
            area: Floor area in m\u00b2
            hoehe: Height in m
            number: Space number
            storey_name: Storey name

        Returns:
            WoFlVSpace with calculation
        """
        hoehen_faktor = self._get_hoehen_faktor(float(hoehe))
        raumtyp, raumtyp_faktor = self._get_raumtyp_faktor(name)

        return WoFlVSpace(
            name=name,
            number=number,
            grundflaeche=area,
            hoehe=hoehe,
            hoehen_faktor=hoehen_faktor,
            raumtyp=raumtyp,
            raumtyp_faktor=raumtyp_faktor,
            storey_name=storey_name,
        )

    async def calculate(
        self,
        project_id: UUID,
        default_hoehe: float = 2.50,
    ) -> WoFlVResult:
        """Calculate WoFlV for a project.

        Args:
            project_id: Project UUID
            default_hoehe: Default height if not specified (m)

        Returns:
            WoFlVResult with calculated residential area
        """
        result = WoFlVResult()

        # Get all spaces from project
        spaces = await self._uow.spaces.find_by_project(project_id)

        for space in spaces:
            name = space.name or "Raum"
            area = space.net_floor_area_m2 or Decimal("0")
            hoehe = space.net_height_m or Decimal(str(default_hoehe))
            number = space.number or ""

            # Get storey name if available
            storey_name = ""
            if space.storey_id:
                storey = await self._uow.storeys.get(space.storey_id)
                if storey:
                    storey_name = storey.name or ""

            woflv_space = self._calculate_space(
                name=name,
                area=area,
                hoehe=hoehe,
                number=number,
                storey_name=storey_name,
            )

            result.spaces.append(woflv_space)
            result.grundflaeche_gesamt += woflv_space.grundflaeche
            result.wohnflaeche_gesamt += woflv_space.wohnflaeche

            # Group by counting factor
            faktor = woflv_space.gesamt_faktor
            if faktor == Decimal("1.0"):
                result.wohnflaeche_100 += woflv_space.wohnflaeche
            elif faktor == Decimal("0.5"):
                result.wohnflaeche_50 += woflv_space.wohnflaeche
            elif faktor == Decimal("0.25"):
                result.wohnflaeche_25 += woflv_space.wohnflaeche
            else:
                result.nicht_angerechnet += woflv_space.grundflaeche

        return result
