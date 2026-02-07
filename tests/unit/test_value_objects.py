"""Tests for domain value objects."""
from __future__ import annotations

import pytest

from ifc_mcp.domain.value_objects import (
    ExZone,
    ExZoneType,
    FireRating,
    FireRatingStandard,
    GlobalId,
)


class TestGlobalId:
    """Tests for GlobalId value object."""

    def test_valid_global_id(self) -> None:
        """Test creating valid GlobalId."""
        gid = GlobalId("2XQ$n5SLP5MBLyL442paFx")
        assert str(gid) == "2XQ$n5SLP5MBLyL442paFx"

    def test_invalid_global_id_length(self) -> None:
        """Test that invalid length raises error."""
        with pytest.raises(ValueError, match="Invalid GlobalId format"):
            GlobalId("too_short")

    def test_invalid_global_id_characters(self) -> None:
        """Test that invalid characters raise error."""
        with pytest.raises(ValueError, match="Invalid GlobalId format"):
            GlobalId("2XQ@n5SLP5MBLyL442paFx")  # @ is invalid

    def test_global_id_equality(self) -> None:
        """Test GlobalId equality."""
        gid1 = GlobalId("2XQ$n5SLP5MBLyL442paFx")
        gid2 = GlobalId("2XQ$n5SLP5MBLyL442paFx")
        assert gid1 == gid2

    def test_global_id_from_string(self) -> None:
        """Test from_string factory."""
        gid = GlobalId.from_string("2XQ$n5SLP5MBLyL442paFx")
        assert gid is not None
        assert str(gid) == "2XQ$n5SLP5MBLyL442paFx"

    def test_global_id_from_string_invalid(self) -> None:
        """Test from_string with invalid input."""
        assert GlobalId.from_string("invalid") is None
        assert GlobalId.from_string(None) is None


class TestFireRating:
    """Tests for FireRating value object."""

    @pytest.mark.parametrize(
        "value,expected_minutes,expected_standard",
        [
            ("F30", 30, FireRatingStandard.GERMAN),
            ("F60", 60, FireRatingStandard.GERMAN),
            ("F90", 90, FireRatingStandard.GERMAN),
            ("F120", 120, FireRatingStandard.GERMAN),
            ("EI30", 30, FireRatingStandard.EUROPEAN),
            ("EI60", 60, FireRatingStandard.EUROPEAN),
            ("REI90", 90, FireRatingStandard.EUROPEAN),
            ("30", 30, FireRatingStandard.GERMAN),
            ("90 min", 90, FireRatingStandard.GERMAN),
        ],
    )
    def test_parse_valid_ratings(
        self,
        value: str,
        expected_minutes: int,
        expected_standard: FireRatingStandard,
    ) -> None:
        """Test parsing various fire rating formats."""
        rating = FireRating.parse(value)
        assert rating is not None
        assert rating.minutes == expected_minutes
        assert rating.standard == expected_standard

    def test_parse_invalid_rating(self) -> None:
        """Test parsing invalid rating returns None."""
        assert FireRating.parse("invalid") is None
        assert FireRating.parse("") is None
        assert FireRating.parse(None) is None

    def test_fire_rating_comparison(self) -> None:
        """Test comparing fire ratings."""
        f30 = FireRating.parse("F30")
        f60 = FireRating.parse("F60")
        f90 = FireRating.parse("F90")

        assert f30 is not None
        assert f60 is not None
        assert f90 is not None

        assert f30 < f60 < f90
        assert f90 > f60 > f30
        assert f60.meets_requirement(60)
        assert f60.meets_requirement(30)
        assert not f60.meets_requirement(90)

    def test_fire_rating_conversions(self) -> None:
        """Test rating format conversions."""
        rating = FireRating.parse("EI90")
        assert rating is not None
        assert rating.to_german() == "F90"
        assert rating.to_european_ei() == "EI90"


class TestExZone:
    """Tests for ExZone value object."""

    @pytest.mark.parametrize(
        "value,expected_type",
        [
            ("Zone 0", ExZoneType.ZONE_0),
            ("Zone 1", ExZoneType.ZONE_1),
            ("Zone 2", ExZoneType.ZONE_2),
            ("Zone 20", ExZoneType.ZONE_20),
            ("Zone 21", ExZoneType.ZONE_21),
            ("Zone 22", ExZoneType.ZONE_22),
            ("0", ExZoneType.ZONE_0),
            ("1", ExZoneType.ZONE_1),
            ("zone_1", ExZoneType.ZONE_1),
            ("Ex-Zone 2", ExZoneType.ZONE_2),
        ],
    )
    def test_parse_valid_zones(
        self,
        value: str,
        expected_type: ExZoneType,
    ) -> None:
        """Test parsing various Ex-Zone formats."""
        zone = ExZone.parse(value)
        assert zone is not None
        assert zone.zone_type == expected_type

    def test_parse_invalid_zone(self) -> None:
        """Test parsing invalid zone returns None."""
        assert ExZone.parse("invalid") is None
        assert ExZone.parse("") is None
        assert ExZone.parse(None) is None

    def test_zone_properties(self) -> None:
        """Test zone property methods."""
        zone0 = ExZone.parse("Zone 0")
        zone1 = ExZone.parse("Zone 1")
        zone20 = ExZone.parse("Zone 20")
        none_zone = ExZone.none()

        assert zone0 is not None
        assert zone1 is not None
        assert zone20 is not None

        # Gas zones
        assert zone0.is_gas_zone
        assert zone1.is_gas_zone
        assert not zone20.is_gas_zone

        # Dust zones
        assert not zone0.is_dust_zone
        assert zone20.is_dust_zone

        # Hazardous
        assert zone0.is_hazardous
        assert zone1.is_hazardous
        assert not none_zone.is_hazardous

        # Equipment categories
        assert zone0.required_equipment_category == 1
        assert zone1.required_equipment_category == 2
        assert none_zone.required_equipment_category is None

    def test_zone_comparison(self) -> None:
        """Test hazard level comparison."""
        zone0 = ExZone.parse("Zone 0")
        zone1 = ExZone.parse("Zone 1")
        zone2 = ExZone.parse("Zone 2")

        assert zone0 is not None
        assert zone1 is not None
        assert zone2 is not None

        assert zone0.is_more_hazardous_than(zone1)
        assert zone1.is_more_hazardous_than(zone2)
        assert not zone2.is_more_hazardous_than(zone0)
