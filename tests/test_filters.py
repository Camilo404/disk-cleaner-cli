"""Tests for the new min_size_bytes filter and include_extended option in Scanner."""

import os
import tempfile

from disk_cleaner.locations import TempLocation
from disk_cleaner.scanner import Scanner


class TestMinSizeFilter:
    """Verify that the min_size_bytes filter drops small files."""

    def test_min_size_filters_small_files(self):
        scanner = Scanner(min_size_bytes=1024)

        with tempfile.TemporaryDirectory() as tmpdir:
            small = os.path.join(tmpdir, "small.tmp")
            large = os.path.join(tmpdir, "large.tmp")
            with open(small, "wb") as f:
                f.write(b"x" * 100)
            with open(large, "wb") as f:
                f.write(b"x" * 4096)

            loc = TempLocation(name="Test", path=tmpdir, requires_admin=False)
            result = scanner.scan_location(loc)

            assert result.file_count == 1
            assert result.files[0][0] == large

    def test_default_min_size_does_not_filter(self):
        """With min_size_bytes=0, all non-zero files are returned (backwards compatible)."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = os.path.join(tmpdir, "a.tmp")
            f2 = os.path.join(tmpdir, "b.tmp")
            with open(f1, "wb") as f:
                f.write(b"x" * 5)
            with open(f2, "wb") as f:
                f.write(b"y" * 10)

            loc = TempLocation(name="Test", path=tmpdir, requires_admin=False)
            result = scanner.scan_location(loc)

            assert result.file_count == 2
