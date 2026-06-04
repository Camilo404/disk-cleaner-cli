"""Tests for the get_all_locations helper."""

from disk_cleaner.locations import get_all_locations, get_temp_locations
from disk_cleaner.scanner import Scanner


class TestGetAllLocations:
    def test_default_matches_get_temp_locations(self):
        """When include_extended is False, the result equals get_temp_locations()."""
        default = get_temp_locations()
        all_locs = get_all_locations(include_extended=False)
        assert [l.name for l in all_locs] == [l.name for l in default]

    def test_extended_can_add_more(self):
        """When include_extended is True, the result is a superset (or equal)."""
        base = get_temp_locations()
        all_locs = get_all_locations(include_extended=True)
        base_names = {l.name for l in base}
        all_names = {l.name for l in all_locs}
        assert base_names.issubset(all_names)

    def test_scanner_respects_include_extended_flag(self):
        """The Scanner should call get_all_locations with the include_extended flag."""
        from unittest.mock import patch
        scanner = Scanner(include_extended=True)
        with patch("disk_cleaner.scanner.get_all_locations", return_value=[]) as mock:
            scanner.scan_all()
            # Confirm that include_extended=True was forwarded
            assert mock.call_args.kwargs.get("include_extended") is True

        scanner2 = Scanner(include_extended=False)
        with patch("disk_cleaner.scanner.get_all_locations", return_value=[]) as mock2:
            scanner2.scan_all()
            assert mock2.call_args.kwargs.get("include_extended") is False
