"""Tests for cleaner module."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from disk_cleaner.cleaner import Cleaner, DeletionResult, DeletionSummary
from disk_cleaner.locations import TempLocation
from disk_cleaner.scanner import ScanResult


class TestCleaner:
    """Tests for Cleaner class."""

    def test_delete_from_empty_location(self):
        """Test deleting from an empty location."""
        cleaner = Cleaner(dry_run=True)
        location = TempLocation(name="Test", path="", requires_admin=False)
        scan_result = ScanResult(location=location)

        result = cleaner.delete_from_location(scan_result)

        assert result.deleted == 0
        assert result.failed == 0

    def test_dry_run_does_not_delete(self):
        """Test that dry_run doesn't actually delete files."""
        cleaner = Cleaner(dry_run=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.tmp")
            with open(test_file, "w") as f:
                f.write("test content")

            location = TempLocation(name="Test", path=tmpdir, requires_admin=False)
            scan_result = ScanResult(location=location)
            scan_result.files = [(test_file, 100, 1)]
            scan_result.total_size = 100
            scan_result.file_count = 1

            result = cleaner.delete_from_location(scan_result)

            assert result.deleted == 1
            assert result.failed == 0
            assert os.path.exists(test_file)

    def test_delete_locked_file(self):
        """Test handling of locked files."""
        cleaner = Cleaner(dry_run=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.tmp")
            with open(test_file, "w") as f:
                f.write("test content")

            location = TempLocation(name="Test", path=tmpdir, requires_admin=False)
            scan_result = ScanResult(location=location)
            scan_result.files = [(test_file, 100, 1)]
            scan_result.total_size = 100
            scan_result.file_count = 1

            with patch("disk_cleaner.cleaner.is_locked", return_value=True):
                result = cleaner.delete_from_location(scan_result)

            assert result.failed == 1
            assert result.deleted == 0
            assert "Locked" in result.errors[0]

    def test_delete_all(self):
        """Test deleting from multiple locations."""
        cleaner = Cleaner(dry_run=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "file1.tmp")
            file2 = os.path.join(tmpdir, "file2.tmp")

            with open(file1, "w") as f:
                f.write("x" * 100)
            with open(file2, "w") as f:
                f.write("y" * 200)

            loc1 = TempLocation(name="Test1", path=tmpdir, requires_admin=False)
            loc2 = TempLocation(name="Test2", path=tmpdir, requires_admin=False)

            scan1 = ScanResult(location=loc1)
            scan1.files = [(file1, 100, 1)]
            scan1.total_size = 100
            scan1.file_count = 1

            scan2 = ScanResult(location=loc2)
            scan2.files = [(file2, 200, 1)]
            scan2.total_size = 200
            scan2.file_count = 1

            from disk_cleaner.scanner import ScanSummary

            summary = ScanSummary(results=[scan1, scan2])
            summary.total_files = 2
            summary.total_size = 300

            result = cleaner.delete_all(summary)

            assert result.total_deleted == 2
            assert result.total_freed_bytes == 300


class TestDeletionResult:
    """Tests for DeletionResult dataclass."""

    def test_default_errors_list(self):
        """Test that errors defaults to empty list."""
        location = TempLocation(name="Test", path="", requires_admin=False)
        result = DeletionResult(location=location)

        assert result.errors == []


class TestDeletionSummary:
    """Tests for DeletionSummary dataclass."""

    def test_default_results_list(self):
        """Test that results defaults to empty list."""
        summary = DeletionSummary()

        assert summary.results == []
        assert summary.total_deleted == 0
