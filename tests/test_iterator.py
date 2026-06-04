"""Tests for the delete_files_iterator cancellation fix and progress callbacks."""

import os
import tempfile
from unittest.mock import patch

from disk_cleaner.cleaner import Cleaner, DeletionResult
from disk_cleaner.locations import TempLocation
from disk_cleaner.scanner import ScanResult, ScanSummary


def _make_summary(files_per_location):
    """Build a ScanSummary where each location contains the given files."""
    results = []
    total_files = 0
    total_size = 0
    for i, files in enumerate(files_per_location):
        loc = TempLocation(name=f"Loc{i}", path="", requires_admin=False)
        sr = ScanResult(location=loc)
        sr.files = files
        sr.file_count = len(files)
        sr.total_size = sum(f[1] for f in files)
        results.append(sr)
        total_files += sr.file_count
        total_size += sr.total_size
    summary = ScanSummary(results=results)
    summary.total_files = total_files
    summary.total_size = total_size
    return summary


class TestDeleteFilesIterator:
    """Tests for the cancellation bug fix in Cleaner.delete_files_iterator."""

    def test_cancellation_stops_after_first_yield(self):
        """Cancelling mid-way should not yield for every remaining file in every location."""
        cancelled = [False]
        cleaner = Cleaner(dry_run=True, cancelled=cancelled)

        loc = TempLocation(name="Loc", path="", requires_admin=False)
        many_files = [(f"C:\\fake\\file_{i}.tmp", 100, 1) for i in range(50)]
        summary = _make_summary([many_files, many_files])  # 100 files total

        # Cancel after the first file is yielded
        def cancel_after_first(*args, **kwargs):
            cancelled[0] = True

        # Inject a side-effect that flips the flag while iterating
        original_delete = cleaner._delete_single_file
        def spy(file_path, size):
            result = original_delete(file_path, size)
            cancelled[0] = True
            return result
        cleaner._delete_single_file = spy  # type: ignore[assignment]

        yielded = list(cleaner.delete_files_iterator(summary))
        # We should bail out: at most a handful of files, not all 100.
        assert len(yielded) < 50, f"iterator should stop on cancellation, got {len(yielded)} yields"
        # The last yielded file should be a cancelled entry
        assert yielded[-1][3] == "Loc" or "Cancelled" in str(yielded[-1])

    def test_progress_callback_invoked(self):
        """The progress callback should be called once per file processed."""
        calls = []
        cleaner = Cleaner(dry_run=True, progress_callback=lambda loc, n, t: calls.append((loc, n, t)))

        files = [(f"C:\\fake\\file_{i}.tmp", 10, 1) for i in range(3)]
        summary = _make_summary([files])

        list(cleaner.delete_files_iterator(summary))

        assert len(calls) == 3
        # n is 1, 2, 3 in order
        assert [c[1] for c in calls] == [1, 2, 3]
        assert all(c[2] == 3 for c in calls)

    def test_dry_run_yields_success(self):
        cleaner = Cleaner(dry_run=True)
        files = [(f"C:\\fake\\file_{i}.tmp", 10, 1) for i in range(2)]
        summary = _make_summary([files])

        yielded = list(cleaner.delete_files_iterator(summary))

        assert len(yielded) == 2
        for file_path, success, freed, loc_name, error in yielded:
            assert success is True
            assert freed == 10  # size reported in dry-run
            assert error == ""
