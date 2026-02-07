"""DIN 277 Service.

Area calculations according to DIN 277:2021 - Areas and volumes
of buildings (Grundfl\u00e4chen und Rauminhalte im Hochbau).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from ifc_mcp.domain import Space
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)


class AreaCategory(str, Enum):
    """DIN 277 area categories."""

    # NRF - Netto-Raumfl\u00e4che (Net Room Area)
    NUF = "NUF"    # Nutzungsfl\u00e4che (Usable Area)
    NUF_1 = "NUF 1"  # Wohnen und Aufenthalt
    NUF_2 = "NUF 2"  # B\u00fcroarbeit
    NUF_3 = "NUF 3"  # Produktion, Werkstatt
    NUF_4 = "NUF 4"  # Lagern, Verteilen
    NUF_5 = "NUF 5"  # Bildung, Unterricht
    NUF_6 = "NUF 6"  # Heilen, Pflegen
    NUF_7 = "NUF 7"  # Sonstige Nutzungen

    TF = "TF"      # Technische Funktionsfl\u00e4che (Technical Area)
    VF = "VF"      # Verkehrsfl\u00e4che (Circulation Area)

    # BGF - Brutto-Grundfl\u00e4che (Gross Floor Area)
    # KGF - Konstruktions-Grundfl\u00e4che (Construction Area)


@dataclass
class DIN277Result:
    """DIN 277 calculation result."""

    project_name: str

    # Brutto-Grundfl\u00e4che (Gross Floor Area)
    bgf: Decimal = Decimal("0")

    # Konstruktions-Grundfl\u00e4che (Construction Floor Area)
    kgf: Decimal = Decimal("0")

    # Netto-Raumfl\u00e4che (Net Room Area) = NUF + TF + VF
    nrf: Decimal = Decimal("0")

    # Nutzungsfl\u00e4che (Usable Area)
    nuf: Decimal = Decimal("0")
    nuf_1: Decimal = Decimal("0")  # Wohnen
    nuf_2: Decimal = Decimal("0")  # B\u00fcro
    nuf_3: Decimal = Decimal("0")  # Produktion
    nuf_4: Decimal = Decimal("0")  # Lagern
    nuf_5: Decimal = Decimal("0")  # Bildung
    nuf_6: Decimal = Decimal("0")  # Heilen
    nuf_7: Decimal = Decimal("0")  # Sonstige

    # Technische Funktionsfl\u00e4che
    tf: Decimal = Decimal("0")

    # Verkehrsfl\u00e4che
    vf: Decimal = Decimal("0")

    # Brutto-Rauminhalt (Gross Volume)
    bri: Decimal = Decimal("0")

    # Netto-Rauminhalt (Net Volume)
    nri: Decimal = Decimal("0")

    # Space details
    spaces: list[dict[str, Any]] = field(default_factory=list)

    # Ratios
    @property
    def nuf_nrf_ratio(self) -> float:
        """NUF/NRF ratio (Nutzfl\u00e4chenfaktor)."""
        if self.nrf == 0:
            return 0.0
        return float(self.nuf / self.nrf)

    @property
    def nrf_bgf_ratio(self) -> float:
        """NRF/BGF ratio (Fl\u00e4cheneffizienz)."""
        if self.bgf == 0:
            return 0.0
        return float(self.nrf / self.bgf)

    @property
    def vf_nrf_ratio(self) -> float:
        """VF/NRF ratio (Verkehrsfl\u00e4chenanteil)."""
        if self.nrf == 0:
            return 0.0
        return float(self.vf / self.nrf)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "project_name": self.project_name,
            "bgf_m2": float(self.bgf),
            "kgf_m2": float(self.kgf),
            "nrf_m2": float(self.nrf),
            "nuf_m2": float(self.nuf),
            "nuf_1_m2": float(self.nuf_1),
            "nuf_2_m2": float(self.nuf_2),
            "nuf_3_m2": float(self.nuf_3),
            "nuf_4_m2": float(self.nuf_4),
            "nuf_5_m2": float(self.nuf_5),
            "nuf_6_m2": float(self.nuf_6),
            "nuf_7_m2": float(self.nuf_7),
            "tf_m2": float(self.tf),
            "vf_m2": float(self.vf),
            "bri_m3": float(self.bri),
            "nri_m3": float(self.nri),
            "nuf_nrf_ratio": round(self.nuf_nrf_ratio, 3),
            "nrf_bgf_ratio": round(self.nrf_bgf_ratio, 3),
            "vf_nrf_ratio": round(self.vf_nrf_ratio, 3),
            "space_count": len(self.spaces),
        }


class DIN277Service:
    """Service for DIN 277:2021 area calculations."""

    # Keywords for space classification
    CLASSIFICATION_KEYWORDS: dict[str, list[str]] = {
        "NUF 1": ["wohn", "schlaf", "kind", "aufenthalt", "living", "bedroom"],
        "NUF 2": ["b\u00fcro", "office", "besprechung", "meeting", "konferenz"],
        "NUF 3": ["werkstatt", "produktion", "labor", "workshop"],
        "NUF 4": ["lager", "archiv", "abstellraum", "storage"],
        "NUF 5": ["schule", "unterricht", "seminar", "h\u00f6rsaal", "classroom"],
        "NUF 6": ["behandlung", "pflege", "patient", "arzt", "medical"],
        "NUF 7": ["k\u00fcche", "bad", "wc", "dusch", "essen", "kitchen", "bath",
                   "toilet", "restaurant", "kantine"],
        "TF": ["technik", "heizung", "l\u00fcftung", "elektro", "server",
               "hausanschluss", "technical"],
        "VF": ["flur", "gang", "treppe", "aufzug", "foyer", "eingang",
               "corridor", "stair", "elevator", "lobby", "hall"],
    }

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize service."""
        self._uow = uow

    def _classify_space(self, name: str) -> str:
        """Classify space into DIN 277 category.

        Args:
            name: Space name

        Returns:
            Category string (e.g., 'NUF 1', 'TF', 'VF')
        """
        search_text = name.lower()

        for category, keywords in self.CLASSIFICATION_KEYWORDS.items():
            if any(kw in search_text for kw in keywords):
                return category

        # Default: NUF 7 (Sonstige)
        return "NUF 7"

    async def calculate(
        self,
        project_id: UUID,
        storey_id: UUID | None = None,
    ) -> DIN277Result:
        """Calculate DIN 277 areas for project.

        Args:
            project_id: Project UUID
            storey_id: Optional storey filter

        Returns:
            DIN277Result with all area calculations
        """
        # Get project
        project = await self._uow.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        result = DIN277Result(project_name=project.name)

        # Get spaces
        spaces = await self._uow.spaces.find_by_project(
            project_id,
            storey_id=storey_id,
            limit=5000,
        )

        for space in spaces:
            area = space.net_floor_area_m2 or Decimal("0")
            volume = space.net_volume_m3 or Decimal("0")
            category = self._classify_space(space.name or "")

            # Add to NRF total
            result.nrf += area
            result.nri += volume

            # Add to category
            if category.startswith("NUF"):
                result.nuf += area
                if category == "NUF 1":
                    result.nuf_1 += area
                elif category == "NUF 2":
                    result.nuf_2 += area
                elif category == "NUF 3":
                    result.nuf_3 += area
                elif category == "NUF 4":
                    result.nuf_4 += area
                elif category == "NUF 5":
                    result.nuf_5 += area
                elif category == "NUF 6":
                    result.nuf_6 += area
                elif category == "NUF 7":
                    result.nuf_7 += area
            elif category == "TF":
                result.tf += area
            elif category == "VF":
                result.vf += area

            # Store space detail
            result.spaces.append({
                "id": str(space.id),
                "name": space.name,
                "number": space.number,
                "category": category,
                "area_m2": float(area),
                "volume_m3": float(volume),
            })

        # Estimate BGF and KGF if we have NRF
        if result.nrf > 0:
            # Typical ratio: NRF/BGF = 0.75-0.85
            result.bgf = result.nrf / Decimal("0.80")
            result.kgf = result.bgf - result.nrf

            # Estimate BRI from BGF and average height
            avg_height = Decimal("3.0")  # Default assumption
            if spaces:
                heights = [
                    s.net_height_m for s in spaces
                    if s.net_height_m and s.net_height_m > 0
                ]
                if heights:
                    avg_height = sum(heights, Decimal("0")) / len(heights)

            result.bri = result.bgf * avg_height

        return result
