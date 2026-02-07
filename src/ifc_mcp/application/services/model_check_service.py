"""Model Check Service.

Performs quality checks on IFC models for completeness, consistency,
and compliance with standards.
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


class CheckSeverity(str, Enum):
    """Check result severity."""

    ERROR = "error"       # Critical issue
    WARNING = "warning"   # Potential problem
    INFO = "info"         # Information only
    PASSED = "passed"     # Check passed


class CheckCategory(str, Enum):
    """Check category."""

    GEOMETRY = "geometry"
    PROPERTIES = "properties"
    RELATIONSHIPS = "relationships"
    COMPLETENESS = "completeness"
    NAMING = "naming"
    CLASSIFICATION = "classification"
    CONSISTENCY = "consistency"


@dataclass
class CheckResult:
    """Single check result."""

    check_id: str
    name: str
    category: CheckCategory
    severity: CheckSeverity
    message: str
    element_count: int = 0
    element_ids: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckSummary:
    """Summary of all checks."""

    total_checks: int = 0
    passed: int = 0
    errors: int = 0
    warnings: int = 0
    info: int = 0

    @property
    def pass_rate(self) -> float:
        """Pass rate percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.passed / self.total_checks) * 100


@dataclass
class ModelCheckResult:
    """Complete model check result."""

    project_name: str
    results: list[CheckResult] = field(default_factory=list)
    summary: CheckSummary = field(default_factory=CheckSummary)


class ModelCheckService:
    """Service for IFC model quality checks."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize service."""
        self._uow = uow

    async def run_all_checks(
        self,
        project_id: UUID,
        storey_id: UUID | None = None,
    ) -> ModelCheckResult:
        """Run all quality checks on a project.

        Args:
            project_id: Project UUID
            storey_id: Optional storey filter

        Returns:
            ModelCheckResult with all check results
        """
        # Get project
        project = await self._uow.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        result = ModelCheckResult(project_name=project.name)

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
        result.results.extend(await self._check_geometry(elements))
        result.results.extend(await self._check_properties(elements))
        result.results.extend(await self._check_relationships(elements, spaces))
        result.results.extend(await self._check_completeness(elements, spaces))
        result.results.extend(await self._check_naming(elements, spaces))
        result.results.extend(await self._check_consistency(elements, spaces))

        # Calculate summary
        result.summary.total_checks = len(result.results)
        result.summary.passed = sum(
            1 for r in result.results if r.severity == CheckSeverity.PASSED
        )
        result.summary.errors = sum(
            1 for r in result.results if r.severity == CheckSeverity.ERROR
        )
        result.summary.warnings = sum(
            1 for r in result.results if r.severity == CheckSeverity.WARNING
        )
        result.summary.info = sum(
            1 for r in result.results if r.severity == CheckSeverity.INFO
        )

        return result

    # =========================================================================
    # Geometry Checks
    # =========================================================================

    async def _check_geometry(self, elements: list[BuildingElement]) -> list[CheckResult]:
        """Run geometry checks."""
        results = []

        # Check for zero-dimension elements
        zero_dims = [
            e for e in elements
            if (e.length_m is not None and e.length_m == 0)
            or (e.width_m is not None and e.width_m == 0)
            or (e.height_m is not None and e.height_m == 0)
        ]

        if zero_dims:
            results.append(CheckResult(
                check_id="GEO_001",
                name="Zero Dimensions",
                category=CheckCategory.GEOMETRY,
                severity=CheckSeverity.ERROR,
                message=f"{len(zero_dims)} elements have zero dimensions",
                element_count=len(zero_dims),
                element_ids=[str(e.id) for e in zero_dims[:20]],
            ))
        else:
            results.append(CheckResult(
                check_id="GEO_001",
                name="Zero Dimensions",
                category=CheckCategory.GEOMETRY,
                severity=CheckSeverity.PASSED,
                message="No elements with zero dimensions found",
            ))

        # Check for negative dimensions
        neg_dims = [
            e for e in elements
            if (e.length_m is not None and e.length_m < 0)
            or (e.width_m is not None and e.width_m < 0)
            or (e.height_m is not None and e.height_m < 0)
        ]

        if neg_dims:
            results.append(CheckResult(
                check_id="GEO_002",
                name="Negative Dimensions",
                category=CheckCategory.GEOMETRY,
                severity=CheckSeverity.ERROR,
                message=f"{len(neg_dims)} elements have negative dimensions",
                element_count=len(neg_dims),
                element_ids=[str(e.id) for e in neg_dims[:20]],
            ))
        else:
            results.append(CheckResult(
                check_id="GEO_002",
                name="Negative Dimensions",
                category=CheckCategory.GEOMETRY,
                severity=CheckSeverity.PASSED,
                message="No elements with negative dimensions found",
            ))

        # Check for missing positions
        no_position = [
            e for e in elements
            if e.position_x is None or e.position_y is None
        ]

        if no_position:
            ratio = len(no_position) / len(elements) * 100 if elements else 0
            severity = (
                CheckSeverity.WARNING if ratio < 50
                else CheckSeverity.ERROR
            )
            results.append(CheckResult(
                check_id="GEO_003",
                name="Missing Positions",
                category=CheckCategory.GEOMETRY,
                severity=severity,
                message=f"{len(no_position)} elements ({ratio:.0f}%) have no position",
                element_count=len(no_position),
                element_ids=[str(e.id) for e in no_position[:20]],
            ))
        else:
            results.append(CheckResult(
                check_id="GEO_003",
                name="Missing Positions",
                category=CheckCategory.GEOMETRY,
                severity=CheckSeverity.PASSED,
                message="All elements have positions",
            ))

        return results

    # =========================================================================
    # Property Checks
    # =========================================================================

    async def _check_properties(self, elements: list[BuildingElement]) -> list[CheckResult]:
        """Run property checks."""
        results = []

        # Check for missing names
        no_name = [e for e in elements if not e.name]

        if no_name:
            results.append(CheckResult(
                check_id="PROP_001",
                name="Missing Names",
                category=CheckCategory.PROPERTIES,
                severity=CheckSeverity.WARNING,
                message=f"{len(no_name)} elements have no name",
                element_count=len(no_name),
                element_ids=[str(e.id) for e in no_name[:20]],
            ))
        else:
            results.append(CheckResult(
                check_id="PROP_001",
                name="Missing Names",
                category=CheckCategory.PROPERTIES,
                severity=CheckSeverity.PASSED,
                message="All elements have names",
            ))

        # Check fire ratings on walls
        walls = [e for e in elements if e.category in (
            ElementCategory.WALL, ElementCategory.WALL_STANDARD_CASE
        )]
        walls_no_fire = [w for w in walls if w.fire_rating is None]

        if walls and walls_no_fire:
            ratio = len(walls_no_fire) / len(walls) * 100
            results.append(CheckResult(
                check_id="PROP_002",
                name="Missing Fire Ratings (Walls)",
                category=CheckCategory.PROPERTIES,
                severity=CheckSeverity.WARNING,
                message=f"{len(walls_no_fire)} of {len(walls)} walls ({ratio:.0f}%) have no fire rating",
                element_count=len(walls_no_fire),
                element_ids=[str(w.id) for w in walls_no_fire[:20]],
            ))
        elif walls:
            results.append(CheckResult(
                check_id="PROP_002",
                name="Missing Fire Ratings (Walls)",
                category=CheckCategory.PROPERTIES,
                severity=CheckSeverity.PASSED,
                message="All walls have fire ratings",
            ))

        # Check fire ratings on doors
        doors = [e for e in elements if e.category == ElementCategory.DOOR]
        doors_no_fire = [d for d in doors if d.fire_rating is None]

        if doors and doors_no_fire:
            ratio = len(doors_no_fire) / len(doors) * 100
            results.append(CheckResult(
                check_id="PROP_003",
                name="Missing Fire Ratings (Doors)",
                category=CheckCategory.PROPERTIES,
                severity=CheckSeverity.INFO,
                message=f"{len(doors_no_fire)} of {len(doors)} doors ({ratio:.0f}%) have no fire rating",
                element_count=len(doors_no_fire),
            ))

        return results

    # =========================================================================
    # Relationship Checks
    # =========================================================================

    async def _check_relationships(
        self,
        elements: list[BuildingElement],
        spaces: list[Space],
    ) -> list[CheckResult]:
        """Run relationship checks."""
        results = []

        # Check for orphan elements (no storey assignment)
        orphans = [e for e in elements if e.storey_id is None]

        if orphans:
            results.append(CheckResult(
                check_id="REL_001",
                name="Orphan Elements",
                category=CheckCategory.RELATIONSHIPS,
                severity=CheckSeverity.WARNING,
                message=f"{len(orphans)} elements have no storey assignment",
                element_count=len(orphans),
                element_ids=[str(e.id) for e in orphans[:20]],
            ))
        else:
            results.append(CheckResult(
                check_id="REL_001",
                name="Orphan Elements",
                category=CheckCategory.RELATIONSHIPS,
                severity=CheckSeverity.PASSED,
                message="All elements are assigned to storeys",
            ))

        # Check space-element relationships
        spaces_no_elements = [
            s for s in spaces if not s.boundary_element_ids
        ] if spaces else []

        if spaces_no_elements:
            results.append(CheckResult(
                check_id="REL_002",
                name="Spaces Without Elements",
                category=CheckCategory.RELATIONSHIPS,
                severity=CheckSeverity.INFO,
                message=f"{len(spaces_no_elements)} spaces have no boundary elements",
                element_count=len(spaces_no_elements),
            ))

        return results

    # =========================================================================
    # Completeness Checks
    # =========================================================================

    async def _check_completeness(
        self,
        elements: list[BuildingElement],
        spaces: list[Space],
    ) -> list[CheckResult]:
        """Run completeness checks."""
        results = []

        # Check space properties
        spaces_no_area = [
            s for s in spaces
            if s.net_floor_area_m2 is None or s.net_floor_area_m2 == 0
        ]

        if spaces and spaces_no_area:
            results.append(CheckResult(
                check_id="COMP_001",
                name="Spaces Without Area",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.WARNING,
                message=f"{len(spaces_no_area)} of {len(spaces)} spaces have no floor area",
                element_count=len(spaces_no_area),
            ))
        elif spaces:
            results.append(CheckResult(
                check_id="COMP_001",
                name="Spaces Without Area",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.PASSED,
                message="All spaces have floor areas",
            ))

        # Check door widths
        doors = [e for e in elements if e.category == ElementCategory.DOOR]
        doors_no_width = [d for d in doors if d.width_m is None]

        if doors and doors_no_width:
            results.append(CheckResult(
                check_id="COMP_002",
                name="Doors Without Width",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.WARNING,
                message=f"{len(doors_no_width)} of {len(doors)} doors have no width",
                element_count=len(doors_no_width),
            ))

        # Check window properties
        windows = [e for e in elements if e.category == ElementCategory.WINDOW]
        windows_no_dims = [
            w for w in windows
            if w.width_m is None or w.height_m is None
        ]

        if windows and windows_no_dims:
            results.append(CheckResult(
                check_id="COMP_003",
                name="Windows Without Dimensions",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.WARNING,
                message=f"{len(windows_no_dims)} of {len(windows)} windows missing dimensions",
                element_count=len(windows_no_dims),
            ))

        return results

    # =========================================================================
    # Naming Checks
    # =========================================================================

    async def _check_naming(
        self,
        elements: list[BuildingElement],
        spaces: list[Space],
    ) -> list[CheckResult]:
        """Run naming convention checks."""
        results = []

        # Check for generic names
        generic_indicators = [
            "generic", "default", "standard", "unnamed", "copy", "kopie",
        ]
        generic_names = [
            e for e in elements
            if e.name and any(g in e.name.lower() for g in generic_indicators)
        ]

        if generic_names:
            results.append(CheckResult(
                check_id="NAME_001",
                name="Generic Names",
                category=CheckCategory.NAMING,
                severity=CheckSeverity.INFO,
                message=f"{len(generic_names)} elements have generic names",
                element_count=len(generic_names),
                element_ids=[str(e.id) for e in generic_names[:20]],
            ))
        else:
            results.append(CheckResult(
                check_id="NAME_001",
                name="Generic Names",
                category=CheckCategory.NAMING,
                severity=CheckSeverity.PASSED,
                message="No elements with generic names found",
            ))

        # Check for duplicate names within same type
        name_type_counts: dict[tuple[str, str], int] = {}
        for e in elements:
            if e.name:
                key = (e.name, e.category.value)
                name_type_counts[key] = name_type_counts.get(key, 0) + 1

        duplicates = {
            k: v for k, v in name_type_counts.items() if v > 1
        }

        if duplicates:
            total_dupes = sum(v for v in duplicates.values())
            results.append(CheckResult(
                check_id="NAME_002",
                name="Duplicate Names",
                category=CheckCategory.NAMING,
                severity=CheckSeverity.INFO,
                message=f"{len(duplicates)} duplicate name patterns ({total_dupes} elements)",
                details={
                    "top_duplicates": [
                        {"name": k[0], "type": k[1], "count": v}
                        for k, v in sorted(
                            duplicates.items(), key=lambda x: x[1], reverse=True
                        )[:10]
                    ]
                },
            ))

        return results

    # =========================================================================
    # Consistency Checks
    # =========================================================================

    async def _check_consistency(
        self,
        elements: list[BuildingElement],
        spaces: list[Space],
    ) -> list[CheckResult]:
        """Run consistency checks."""
        results = []

        # Check storey references consistency
        storey_ids = set()
        for e in elements:
            if e.storey_id:
                storey_ids.add(e.storey_id)

        for s in spaces:
            if s.storey_id:
                storey_ids.add(s.storey_id)

        if len(storey_ids) > 0:
            results.append(CheckResult(
                check_id="CONS_001",
                name="Storey References",
                category=CheckCategory.CONSISTENCY,
                severity=CheckSeverity.PASSED,
                message=f"Elements reference {len(storey_ids)} distinct storeys",
                details={"storey_count": len(storey_ids)},
            ))

        # Check measurement units consistency
        # (all dimensions should be in consistent units)
        walls = [e for e in elements if e.category in (
            ElementCategory.WALL, ElementCategory.WALL_STANDARD_CASE
        )]

        if walls:
            widths = [float(w.width_m) for w in walls if w.width_m is not None]
            if widths:
                min_w = min(widths)
                max_w = max(widths)
                # Check if values suggest mixed units (mm vs m)
                if max_w > 100:
                    results.append(CheckResult(
                        check_id="CONS_002",
                        name="Measurement Units",
                        category=CheckCategory.CONSISTENCY,
                        severity=CheckSeverity.WARNING,
                        message=f"Wall widths range {min_w:.3f}-{max_w:.3f}m "
                                f"- possible mixed units (mm/m)",
                        details={
                            "min_width": min_w,
                            "max_width": max_w,
                        },
                    ))
                else:
                    results.append(CheckResult(
                        check_id="CONS_002",
                        name="Measurement Units",
                        category=CheckCategory.CONSISTENCY,
                        severity=CheckSeverity.PASSED,
                        message="Measurement units appear consistent",
                    ))

        return results
