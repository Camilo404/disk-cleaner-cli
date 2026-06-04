"""Cleaner for safely deleting temporary files."""

import os
from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Optional, Tuple

ProgressCallback = Callable[[str, int, int], None]

from disk_cleaner.locations import TempLocation
from disk_cleaner.scanner import ScanResult, ScanSummary
from disk_cleaner.utils import is_locked, permanently_delete, send_to_recycle_bin


@dataclass
class DeletionResult:
    """Result of deleting files from a location."""

    location: TempLocation
    deleted: int = 0
    failed: int = 0
    freed_bytes: int = 0
    recycled: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class DeletionSummary:
    """Summary of deletion across all locations."""

    results: List[DeletionResult] = field(default_factory=list)
    total_deleted: int = 0
    total_failed: int = 0
    total_freed_bytes: int = 0
    total_recycled: int = 0


class Cleaner:
    """Safely deletes temporary files."""

    def __init__(
        self,
        dry_run: bool = True,
        use_recycle_bin: bool = False,
        cancelled: Optional[List[bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        """
        Initialize cleaner.

        Args:
            dry_run: If True, only simulate deletion without actually deleting
            use_recycle_bin: If True, send files to Recycle Bin instead of permanent delete
            cancelled: Reference to a cancellation flag (True = cancel operation)
            progress_callback: Optional callback(location_name, processed, total) for progress
        """
        self.dry_run = dry_run
        self.use_recycle_bin = use_recycle_bin
        self._cancelled = cancelled
        self._progress_callback = progress_callback

    def cancel(self) -> None:
        """Request cancellation of the current operation."""
        if self._cancelled is not None:
            self._cancelled[0] = True

    def _is_cancelled(self) -> bool:
        """Check if operation has been cancelled."""
        return self._cancelled is not None and self._cancelled[0]

    def _delete_single_file(self, file_path: str, size: int) -> Tuple[bool, int, str]:
        """
        Delete a single file and return result.

        Returns:
            Tuple of (success, bytes_freed, error_message)
        """
        if self._is_cancelled():
            return (False, 0, "Cancelled")

        if self.dry_run:
            return (True, size, "")

        if is_locked(file_path):
            return (False, 0, "Locked")

        if self.use_recycle_bin:
            result = send_to_recycle_bin(file_path)
            if result.success:
                return (True, 0, "")  # Recycle bin doesn't free disk space immediately
            return (False, 0, result.error)

        result = permanently_delete(file_path)
        if result.success:
            return (True, size, "")
        return (False, 0, result.error)

    def delete_from_location(self, scan_result: ScanResult) -> DeletionResult:
        """Delete files from a single location."""
        result = DeletionResult(location=scan_result.location)

        if not scan_result.accessible:
            return result

        if self._is_cancelled():
            result.errors.append("Operation cancelled")
            return result

        for file_path, size, _ in scan_result.files:
            if self._is_cancelled():
                result.errors.append("Operation cancelled")
                break

            success, freed, error = self._delete_single_file(file_path, size)
            if success:
                result.deleted += 1
                result.freed_bytes += freed
                if self.use_recycle_bin:
                    result.recycled += 1
            else:
                result.failed += 1
                result.errors.append(f"{error}: {file_path}")

        return result

    def delete_all(self, summary: ScanSummary) -> DeletionSummary:
        """Delete files from all scanned locations."""
        delete_summary = DeletionSummary()

        for scan_result in summary.results:
            if self._is_cancelled():
                break
            del_result = self.delete_from_location(scan_result)
            delete_summary.results.append(del_result)
            delete_summary.total_deleted += del_result.deleted
            delete_summary.total_failed += del_result.failed
            delete_summary.total_freed_bytes += del_result.freed_bytes
            delete_summary.total_recycled += del_result.recycled

        return delete_summary

    def delete_files_iterator(
        self, summary: ScanSummary
    ) -> Iterator[Tuple[str, bool, int, str, str]]:
        """
        Iterate over all files in summary, yielding results for progress tracking.

        Args:
            summary: ScanSummary containing files to delete

        Yields:
            Tuples of (file_path, success, bytes_freed, location_name, error_msg)
        """
        cancelled_once = False
        for scan_result in summary.results:
            if cancelled_once:
                break
            location_name = scan_result.location.name
            total_files = len(scan_result.files)
            processed = 0

            for file_path, size, _ in scan_result.files:
                if self._is_cancelled():
                    cancelled_once = True
                    yield (file_path, False, 0, location_name, "Cancelled")
                    break

                success, freed, error = self._delete_single_file(file_path, size)
                processed += 1

                if self._progress_callback:
                    self._progress_callback(location_name, processed, total_files)

                yield (file_path, success, freed, location_name, error)

    def delete_files(
        self, files: List[Tuple[str, int, int]]
    ) -> Iterator[Tuple[str, bool, int]]:
        """
        Delete a list of files.

        Args:
            files: List of (file_path, size, age_days) tuples

        Yields:
            Tuples of (file_path, success, bytes_freed)
        """
        for file_path, size, _ in files:
            if self._is_cancelled():
                yield (file_path, False, 0)
                continue
            success, freed, _ = self._delete_single_file(file_path, size)
            yield (file_path, success, freed)
