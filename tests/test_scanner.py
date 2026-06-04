"""Tests for scanner module."""

import os
import tempfile
from unittest.mock import patch

import pytest

from disk_cleaner.locations import TempLocation
from disk_cleaner.scanner import ScanResult, ScanSummary, Scanner


class TestScanner:
    """Tests for Scanner class."""

    def test_is_protected_file(self):
        """Test protected file detection."""
        scanner = Scanner()

        assert scanner.is_protected_file("ntuser.dat") is True
        assert scanner.is_protected_file("NTUSER.DAT") is True
        assert scanner.is_protected_file("thumbs.db") is True
        assert scanner.is_protected_file("C:\\Windows\\System32\\config\\ntuser.dat") is True
        assert scanner.is_protected_file("normal_file.txt") is False
        assert scanner.is_protected_file("document.pdf") is False

    def test_scan_empty_directory(self):
        """Test scanning an empty directory."""
        scanner = Scanner()
        location = TempLocation(name="Test", path="", requires_admin=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            location.path = tmpdir
            result = scanner.scan_location(location)

            assert result.file_count == 0
            assert result.total_size == 0
            assert result.accessible is True

    def test_scan_nonexistent_directory(self):
        """Test scanning a directory that doesn't exist."""
        scanner = Scanner()
        location = TempLocation(
            name="Test", path="C:\\nonexistent\\path\\12345", requires_admin=False
        )

        result = scanner.scan_location(location)

        assert result.accessible is False
        assert "does not exist" in result.error

    @patch("disk_cleaner.scanner.is_admin", return_value=False)
    def test_scan_admin_location_without_privileges(self, mock_is_admin):
        """Test scanning admin location without admin privileges."""
        scanner = Scanner()
        location = TempLocation(
            name="Admin Test", path="C:\\Windows\\Temp", requires_admin=True
        )

        result = scanner.scan_location(location)

        assert result.accessible is False
        assert "Admin privileges required" in result.error

    def test_scan_with_files(self):
        """Test scanning a directory with files."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file1 = os.path.join(tmpdir, "test1.tmp")
            test_file2 = os.path.join(tmpdir, "test2.tmp")

            with open(test_file1, "w") as f:
                f.write("x" * 1024)
            with open(test_file2, "w") as f:
                f.write("y" * 2048)

            location = TempLocation(name="Test", path=tmpdir, requires_admin=False)
            result = scanner.scan_location(location)

            assert result.file_count == 2
            assert result.total_size == 3072
            assert result.accessible is True

    def test_scan_excludes_protected_files(self):
        """Test that protected files are excluded from scan."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "ntuser.dat")
            normal_file = os.path.join(tmpdir, "normal.txt")

            with open(test_file, "w") as f:
                f.write("x" * 100)
            with open(normal_file, "w") as f:
                f.write("y" * 200)

            location = TempLocation(name="Test", path=tmpdir, requires_admin=False)
            result = scanner.scan_location(location)

            assert result.file_count == 1
            assert result.files[0][0] == normal_file

    def test_scan_all(self):
        """Test scanning all locations."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("disk_cleaner.scanner.get_all_locations") as mock_get_locs:
                mock_get_locs.return_value = [
                    TempLocation(name="Test1", path=tmpdir, requires_admin=False),
                    TempLocation(
                        name="Test2",
                        path="C:\\nonexistent\\path",
                        requires_admin=False,
                    ),
                ]

                test_file = os.path.join(tmpdir, "test.tmp")
                with open(test_file, "w") as f:
                    f.write("x" * 500)

                summary = scanner.scan_all()

                assert summary.total_files == 1
                assert summary.total_size == 500
                assert len(summary.results) == 2


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_accessible_without_error(self):
        """Test accessible property when no error."""
        location = TempLocation(name="Test", path="", requires_admin=False)
        result = ScanResult(location=location)

        assert result.accessible is True

    def test_accessible_with_error(self):
        """Test accessible property when error exists."""
        location = TempLocation(name="Test", path="", requires_admin=False)
        result = ScanResult(location=location, error="Some error")

        assert result.accessible is False
