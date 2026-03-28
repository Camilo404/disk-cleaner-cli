"""Tests for locations module."""

from unittest.mock import patch

import pytest

from disk_cleaner.locations import TempLocation, get_temp_locations, is_admin


class TestGetTempLocations:
    """Tests for get_temp_locations function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        locations = get_temp_locations()
        assert isinstance(locations, list)

    def test_locations_have_required_fields(self):
        """Test that each location has required fields."""
        locations = get_temp_locations()

        for loc in locations:
            assert hasattr(loc, "name")
            assert hasattr(loc, "path")
            assert hasattr(loc, "requires_admin")
            assert loc.name
            assert loc.path

    def test_user_temp_not_requires_admin(self):
        """Test that User Temp doesn't require admin."""
        locations = get_temp_locations()

        user_temp = next((loc for loc in locations if loc.name == "User Temp"), None)
        assert user_temp is not None
        assert user_temp.requires_admin is False

    def test_system_temp_requires_admin(self):
        """Test that System Temp requires admin."""
        locations = get_temp_locations()

        system_temp = next(
            (loc for loc in locations if loc.name == "System Temp"), None
        )
        assert system_temp is not None
        assert system_temp.requires_admin is True

    def test_filters_empty_paths(self):
        """Test that locations with empty paths are filtered out."""
        locations = get_temp_locations()

        for loc in locations:
            assert loc.path != ""


class TestIsAdmin:
    """Tests for is_admin function."""

    def test_returns_bool(self):
        """Test that is_admin returns a boolean."""
        result = is_admin()
        assert isinstance(result, bool)
