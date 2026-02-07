"""Accessibility Check Service.

Checks IFC models for compliance with accessibility standards,
primarily DIN 18040 parts 1 and 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from ifc_mcp.domain import BuildingElement, ElementCategory, Space
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork
from ifc_mcp.shared.logging import get_logger

logger = get_logger(__name__)


class AccessibilityStandard(str, Enum):
    """Accessibility standards."""

    DIN_18040_1 = "DIN 18040-1"  # Public buildings
    DIN_18040_2 = "DIN 18040-2"  # Residential


class ComplianceLevel(str, Enum):
    """Compliance assessment level."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class AccessibilityCheck:
    """Single accessibility check result."""

    check_id: str
    name: str
    section: str  # Standard section reference
    requirement: str
    compliance: ComplianceLevel
    message: str
    measured_value: float | None = None
    required_value: float | None = None
    unit: str | None = None
    element_count: int = 0
    element_ids: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class AccessibilitySummary:
    """Summary of accessibility checks."""

    total_checks: int = 0
    compliant: int = 0
    non_compliant: int = 0
    partially_compliant: int = 0
    insufficient_data: int = 0
    not_applicable: int = 0

    @property
    def compliance_rate(self) -> float:
        """Compliance rate percentage."""
        applicable = self.total_checks - self.not_applicable - self.insufficient_data
        if applicable == 0:
            return 0.0
        return (self.compliant / applicable) * 100


@dataclass
class AccessibilityCheckResult:
    """Complete accessibility check result."""

    project_name: str
    standard: AccessibilityStandard
    checks: list[AccessibilityCheck] = field(default_factory=list)
    summary: AccessibilitySummary = field(default_factory=AccessibilitySummary)


class AccessibilityCheckService:
    """Service for accessibility compliance checks."""

    # DIN 18040-1 requirements (public buildings)
    REQUIREMENTS_18040_1 = {
        "door_width_min": 0.90,       # m
        "door_height_min": 2.10,      # m
        "corridor_width_min": 1.50,   # m
        "turning_circle": 1.50,       # m diameter
        "bathroom_min_area": 4.50,    # m2
        "bathroom_door_width": 0.90,  # m
        "stair_width_min": 1.20,      # m
        "handrail_height": 0.85,      # m (0.85-0.90)
        "threshold_max": 0.02,        # m (20mm)
        "clear_height_min": 2.30,     # m
    }

    # DIN 18040-2 requirements (residential)
    REQUIREMENTS_18040_2 = {
        "door_width_min": 0.80,       # m
        "door_height_min": 2.10,      # m
        "corridor_width_min": 1.20,   # m
        "turning_circle": 1.50,       # m diameter
        "bathroom_min_area": 3.60,    # m2
        "bathroom_door_width": 0.80,  # m
        "stair_width_min": 1.00,      # m
        "handrail_height": 0.85,      # m
        "threshold_max": 0.02,        # m
        "clear_height_min": 2.30,     # m
    }

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize service."""
        self._uow = uow

    def _get_requirements(self, standard: AccessibilityStandard) -> dict[str, float]:
        """Get requirements for standard."""
        if standard == AccessibilityStandard.DIN_18040_1:
            return self.REQUIREMENTS_18040_1
        return self.REQUIREMENTS_18040_2

    async def check_accessibility(
        self,
        project_id: UUID,
        standard: AccessibilityStandard = AccessibilityStandard.DIN_18040_1,
        storey_id: UUID | None = None,
    ) -> AccessibilityCheckResult:
        """Run accessibility checks on project.

        Args:
            project_id: Project UUID
            standard: Accessibility standard to check against
            storey_id: Optional storey filter

        Returns:
            AccessibilityCheckResult with all check results
        """
        # Get project
        project = await self._uow.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        result = AccessibilityCheckResult(
            project_name=project.name,
            standard=standard,
        )

        reqs = self._get_requirements(standard)

        # Get data
        elements = await self._uow.elements.find_by_project(
            project_id,
            storey_id=storey_id,
            limit=50000,
        )
        spaces = await self._uow.spaces.find_by_project(
            project_id,
            storey_id=storey_id,
            limit=5000,
        )

        # Run checks
        result.checks.extend(self._check_door_widths(elements, reqs, standard))
        result.checks.extend(self._check_door_heights(elements, reqs, standard))
        result.checks.extend(self._check_door_thresholds(elements, reqs, standard))
        result.checks.extend(self._check_corridor_widths(spaces, reqs, standard))
        result.checks.extend(self._check_turning_circles(spaces, reqs, standard))
        result.checks.extend(self._check_bathroom_sizes(spaces, reqs, standard))
        result.checks.extend(self._check_stair_widths(elements, reqs, standard))
        result.checks.extend(self._check_handrails(elements, reqs, standard))
        result.checks.extend(self._check_level_differences(elements, reqs, standard))
        result.checks.extend(self._check_clear_heights(spaces, reqs, standard))

        # Calculate summary
        result.summary.total_checks = len(result.checks)
        for check in result.checks:
            if check.compliance == ComplianceLevel.COMPLIANT:
                result.summary.compliant += 1
            elif check.compliance == ComplianceLevel.NON_COMPLIANT:
                result.summary.non_compliant += 1
            elif check.compliance == ComplianceLevel.PARTIALLY_COMPLIANT:
                result.summary.partially_compliant += 1
            elif check.compliance == ComplianceLevel.INSUFFICIENT_DATA:
                result.summary.insufficient_data += 1
            elif check.compliance == ComplianceLevel.NOT_APPLICABLE:
                result.summary.not_applicable += 1

        return result

    # =========================================================================
    # Door Checks
    # =========================================================================

    def _check_door_widths(
        self,
        elements: list[BuildingElement],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check door widths."""
        doors = [e for e in elements if e.category == ElementCategory.DOOR]
        min_width = reqs["door_width_min"]

        if not doors:
            return [AccessibilityCheck(
                check_id="ACC_DOOR_001",
                name="Door Width Check",
                section="4.3.3" if standard == AccessibilityStandard.DIN_18040_1 else "4.3.3",
                requirement=f"Minimum door width: {min_width * 100:.0f} cm",
                compliance=ComplianceLevel.NOT_APPLICABLE,
                message="No doors found in model",
            )]

        doors_with_width = [d for d in doors if d.width_m is not None]

        if not doors_with_width:
            return [AccessibilityCheck(
                check_id="ACC_DOOR_001",
                name="Door Width Check",
                section="4.3.3",
                requirement=f"Minimum door width: {min_width * 100:.0f} cm",
                compliance=ComplianceLevel.INSUFFICIENT_DATA,
                message=f"{len(doors)} doors found but none have width data",
                element_count=len(doors),
            )]

        # Check each door
        non_compliant = [
            d for d in doors_with_width
            if float(d.width_m) < min_width
        ]

        if non_compliant:
            min_found = min(float(d.width_m) for d in non_compliant)
            return [AccessibilityCheck(
                check_id="ACC_DOOR_001",
                name="Door Width Check",
                section="4.3.3",
                requirement=f"Minimum door width: {min_width * 100:.0f} cm",
                compliance=ComplianceLevel.NON_COMPLIANT,
                message=f"{len(non_compliant)} of {len(doors_with_width)} doors are too narrow",
                measured_value=min_found,
                required_value=min_width,
                unit="m",
                element_count=len(non_compliant),
                element_ids=[str(d.id) for d in non_compliant[:20]],
                recommendations=[
                    f"Widen doors to at least {min_width * 100:.0f} cm clear width",
                    "Consider automatic door openers for heavy doors",
                ],
            )]

        return [AccessibilityCheck(
            check_id="ACC_DOOR_001",
            name="Door Width Check",
            section="4.3.3",
            requirement=f"Minimum door width: {min_width * 100:.0f} cm",
            compliance=ComplianceLevel.COMPLIANT,
            message=f"All {len(doors_with_width)} doors meet minimum width requirement",
            element_count=len(doors_with_width),
        )]

    def _check_door_heights(
        self,
        elements: list[BuildingElement],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check door heights."""
        doors = [e for e in elements if e.category == ElementCategory.DOOR]
        min_height = reqs["door_height_min"]

        doors_with_height = [d for d in doors if d.height_m is not None]

        if not doors_with_height:
            return [AccessibilityCheck(
                check_id="ACC_DOOR_002",
                name="Door Height Check",
                section="4.3.3",
                requirement=f"Minimum door height: {min_height * 100:.0f} cm",
                compliance=ComplianceLevel.INSUFFICIENT_DATA,
                message="No door height data available",
            )]

        non_compliant = [
            d for d in doors_with_height
            if float(d.height_m) < min_height
        ]

        if non_compliant:
            return [AccessibilityCheck(
                check_id="ACC_DOOR_002",
                name="Door Height Check",
                section="4.3.3",
                requirement=f"Minimum door height: {min_height * 100:.0f} cm",
                compliance=ComplianceLevel.NON_COMPLIANT,
                message=f"{len(non_compliant)} doors are too low",
                element_count=len(non_compliant),
                element_ids=[str(d.id) for d in non_compliant[:20]],
            )]

        return [AccessibilityCheck(
            check_id="ACC_DOOR_002",
            name="Door Height Check",
            section="4.3.3",
            requirement=f"Minimum door height: {min_height * 100:.0f} cm",
            compliance=ComplianceLevel.COMPLIANT,
            message=f"All {len(doors_with_height)} doors meet minimum height",
        )]

    def _check_door_thresholds(
        self,
        elements: list[BuildingElement],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check door thresholds (level differences at doors)."""
        # Threshold data is rarely available in IFC models
        return [AccessibilityCheck(
            check_id="ACC_DOOR_003",
            name="Door Threshold Check",
            section="4.3.3.5",
            requirement=f"Maximum threshold: {reqs['threshold_max'] * 1000:.0f} mm",
            compliance=ComplianceLevel.INSUFFICIENT_DATA,
            message="Threshold data not available in IFC model",
            recommendations=[
                "Verify thresholds on-site or add to IFC model",
                "Maximum 20mm according to standard",
            ],
        )]

    # =========================================================================
    # Corridor Checks
    # =========================================================================

    def _check_corridor_widths(
        self,
        spaces: list[Space],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check corridor widths."""
        min_width = reqs["corridor_width_min"]

        # Identify corridors by name
        corridor_keywords = ["flur", "gang", "corridor", "hall", "diele"]
        corridors = [
            s for s in spaces
            if s.name and any(kw in s.name.lower() for kw in corridor_keywords)
        ]

        if not corridors:
            return [AccessibilityCheck(
                check_id="ACC_CORR_001",
                name="Corridor Width Check",
                section="4.3.4",
                requirement=f"Minimum corridor width: {min_width * 100:.0f} cm",
                compliance=ComplianceLevel.INSUFFICIENT_DATA,
                message="No corridors identified in model",
                recommendations=["Add corridor space types to IFC model"],
            )]

        # Check corridor widths (approximated from area and length)
        narrow_corridors = []
        for corridor in corridors:
            if corridor.net_floor_area_m2 and corridor.net_floor_area_m2 > 0:
                # Estimate width from area (assume rectangular)
                area = float(corridor.net_floor_area_m2)
                # Use width from properties if available
                estimated_width = area ** 0.5  # Rough estimate
                if estimated_width < min_width:
                    narrow_corridors.append(corridor)

        if narrow_corridors:
            return [AccessibilityCheck(
                check_id="ACC_CORR_001",
                name="Corridor Width Check",
                section="4.3.4",
                requirement=f"Minimum corridor width: {min_width * 100:.0f} cm",
                compliance=ComplianceLevel.PARTIALLY_COMPLIANT,
                message=f"{len(narrow_corridors)} corridors may be too narrow (estimated from area)",
                element_count=len(narrow_corridors),
                recommendations=[
                    "Verify actual corridor widths on-site",
                    f"Minimum width: {min_width * 100:.0f} cm",
                ],
            )]

        return [AccessibilityCheck(
            check_id="ACC_CORR_001",
            name="Corridor Width Check",
            section="4.3.4",
            requirement=f"Minimum corridor width: {min_width * 100:.0f} cm",
            compliance=ComplianceLevel.COMPLIANT,
            message=f"All {len(corridors)} corridors appear to meet minimum width",
        )]

    def _check_turning_circles(
        self,
        spaces: list[Space],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check turning circle availability."""
        min_diameter = reqs["turning_circle"]
        min_area = (min_diameter / 2) ** 2 * 3.14159  # Circle area

        return [AccessibilityCheck(
            check_id="ACC_TURN_001",
            name="Turning Circle Check",
            section="4.3.4",
            requirement=f"Turning circle diameter: {min_diameter * 100:.0f} cm",
            compliance=ComplianceLevel.INSUFFICIENT_DATA,
            message="Turning circle verification requires detailed geometry analysis",
            required_value=min_diameter,
            unit="m",
            recommendations=[
                f"Ensure {min_diameter * 100:.0f} cm turning circle in all key areas",
                "Required at: corridor junctions, elevator landings, bathrooms",
            ],
        )]

    # =========================================================================
    # Bathroom Checks
    # =========================================================================

    def _check_bathroom_sizes(
        self,
        spaces: list[Space],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check bathroom sizes."""
        min_area = reqs["bathroom_min_area"]

        bathroom_keywords = ["bad", "wc", "dusch", "bath", "toilet", "sanit"]
        bathrooms = [
            s for s in spaces
            if s.name and any(kw in s.name.lower() for kw in bathroom_keywords)
        ]

        if not bathrooms:
            return [AccessibilityCheck(
                check_id="ACC_BATH_001",
                name="Bathroom Size Check",
                section="5.5",
                requirement=f"Minimum bathroom area: {min_area:.1f} m\u00b2",
                compliance=ComplianceLevel.INSUFFICIENT_DATA,
                message="No bathrooms identified in model",
            )]

        small_bathrooms = [
            b for b in bathrooms
            if b.net_floor_area_m2 and float(b.net_floor_area_m2) < min_area
        ]

        if small_bathrooms:
            min_found = min(
                float(b.net_floor_area_m2)
                for b in small_bathrooms
                if b.net_floor_area_m2
            )
            return [AccessibilityCheck(
                check_id="ACC_BATH_001",
                name="Bathroom Size Check",
                section="5.5",
                requirement=f"Minimum bathroom area: {min_area:.1f} m\u00b2",
                compliance=ComplianceLevel.NON_COMPLIANT,
                message=f"{len(small_bathrooms)} bathrooms are too small",
                measured_value=min_found,
                required_value=min_area,
                unit="m\u00b2",
                element_count=len(small_bathrooms),
                recommendations=[
                    f"Enlarge bathrooms to at least {min_area:.1f} m\u00b2",
                    "Ensure wheelchair turning circle in bathroom",
                ],
            )]

        return [AccessibilityCheck(
            check_id="ACC_BATH_001",
            name="Bathroom Size Check",
            section="5.5",
            requirement=f"Minimum bathroom area: {min_area:.1f} m\u00b2",
            compliance=ComplianceLevel.COMPLIANT,
            message=f"All {len(bathrooms)} bathrooms meet minimum size",
        )]

    # =========================================================================
    # Stair Checks
    # =========================================================================

    def _check_stair_widths(
        self,
        elements: list[BuildingElement],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check stair widths."""
        min_width = reqs["stair_width_min"]

        stairs = [e for e in elements if e.category == ElementCategory.STAIR]

        if not stairs:
            return [AccessibilityCheck(
                check_id="ACC_STAIR_001",
                name="Stair Width Check",
                section="4.3.6",
                requirement=f"Minimum stair width: {min_width * 100:.0f} cm",
                compliance=ComplianceLevel.NOT_APPLICABLE,
                message="No stairs found in model",
            )]

        stairs_with_width = [s for s in stairs if s.width_m is not None]

        if not stairs_with_width:
            return [AccessibilityCheck(
                check_id="ACC_STAIR_001",
                name="Stair Width Check",
                section="4.3.6",
                requirement=f"Minimum stair width: {min_width * 100:.0f} cm",
                compliance=ComplianceLevel.INSUFFICIENT_DATA,
                message=f"{len(stairs)} stairs found but no width data",
            )]

        narrow = [s for s in stairs_with_width if float(s.width_m) < min_width]

        if narrow:
            return [AccessibilityCheck(
                check_id="ACC_STAIR_001",
                name="Stair Width Check",
                section="4.3.6",
                requirement=f"Minimum stair width: {min_width * 100:.0f} cm",
                compliance=ComplianceLevel.NON_COMPLIANT,
                message=f"{len(narrow)} stairs are too narrow",
                element_count=len(narrow),
                element_ids=[str(s.id) for s in narrow[:20]],
            )]

        return [AccessibilityCheck(
            check_id="ACC_STAIR_001",
            name="Stair Width Check",
            section="4.3.6",
            requirement=f"Minimum stair width: {min_width * 100:.0f} cm",
            compliance=ComplianceLevel.COMPLIANT,
            message=f"All {len(stairs_with_width)} stairs meet minimum width",
        )]

    def _check_handrails(
        self,
        elements: list[BuildingElement],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check handrail presence on stairs."""
        stairs = [e for e in elements if e.category == ElementCategory.STAIR]

        if not stairs:
            return [AccessibilityCheck(
                check_id="ACC_STAIR_002",
                name="Handrail Check",
                section="4.3.6.3",
                requirement="Handrails on both sides of stairs",
                compliance=ComplianceLevel.NOT_APPLICABLE,
                message="No stairs found",
            )]

        # Handrail data rarely available in IFC
        return [AccessibilityCheck(
            check_id="ACC_STAIR_002",
            name="Handrail Check",
            section="4.3.6.3",
            requirement="Handrails on both sides of stairs",
            compliance=ComplianceLevel.INSUFFICIENT_DATA,
            message="Handrail data not available in IFC model",
            recommendations=[
                "Verify handrails on both sides on-site",
                f"Required height: {reqs['handrail_height'] * 100:.0f} cm",
                "Continuous grip, round profile 30-45mm",
            ],
        )]

    # =========================================================================
    # Level / Height Checks
    # =========================================================================

    def _check_level_differences(
        self,
        elements: list[BuildingElement],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check for level differences."""
        return [AccessibilityCheck(
            check_id="ACC_LEVEL_001",
            name="Level Difference Check",
            section="4.3.2",
            requirement="No level differences > 20mm without ramp",
            compliance=ComplianceLevel.INSUFFICIENT_DATA,
            message="Level difference analysis requires detailed geometry",
            recommendations=[
                "Check for steps at entrances and between rooms",
                "Ramps required for height differences > 20mm",
                "Ramp gradient: max 6% (DIN 18040-1)",
            ],
        )]

    def _check_clear_heights(
        self,
        spaces: list[Space],
        reqs: dict[str, float],
        standard: AccessibilityStandard,
    ) -> list[AccessibilityCheck]:
        """Check clear heights in spaces."""
        min_height = reqs["clear_height_min"]

        spaces_with_height = [
            s for s in spaces
            if s.net_height_m is not None and s.net_height_m > 0
        ]

        if not spaces_with_height:
            return [AccessibilityCheck(
                check_id="ACC_HEIGHT_001",
                name="Clear Height Check",
                section="4.3.2",
                requirement=f"Minimum clear height: {min_height * 100:.0f} cm",
                compliance=ComplianceLevel.INSUFFICIENT_DATA,
                message="No room height data available",
            )]

        low_spaces = [
            s for s in spaces_with_height
            if float(s.net_height_m) < min_height
        ]

        if low_spaces:
            min_found = min(float(s.net_height_m) for s in low_spaces)
            return [AccessibilityCheck(
                check_id="ACC_HEIGHT_001",
                name="Clear Height Check",
                section="4.3.2",
                requirement=f"Minimum clear height: {min_height * 100:.0f} cm",
                compliance=ComplianceLevel.NON_COMPLIANT,
                message=f"{len(low_spaces)} spaces have insufficient clear height",
                measured_value=min_found,
                required_value=min_height,
                unit="m",
                element_count=len(low_spaces),
            )]

        return [AccessibilityCheck(
            check_id="ACC_HEIGHT_001",
            name="Clear Height Check",
            section="4.3.2",
            requirement=f"Minimum clear height: {min_height * 100:.0f} cm",
            compliance=ComplianceLevel.COMPLIANT,
            message=f"All {len(spaces_with_height)} spaces meet minimum clear height",
        )]
