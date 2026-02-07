"""Domain Value Objects.

Immutable objects that represent domain concepts without identity.
"""
from __future__ import annotations

from ifc_mcp.domain.value_objects.ex_zone import (
    ExplosionType,
    ExZone,
    ExZoneType,
)
from ifc_mcp.domain.value_objects.fire_rating import (
    FireRating,
    FireRatingStandard,
)
from ifc_mcp.domain.value_objects.global_id import GlobalId

__all__ = [
    "GlobalId",
    "FireRating", "FireRatingStandard",
    "ExZone", "ExZoneType", "ExplosionType",
]
