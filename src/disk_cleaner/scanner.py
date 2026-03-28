"""Scanner for discovering temporary files."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from disk_cleaner.locations import TempLocation, get_temp_locations, is_admin
from disk_cleaner.utils import PathValidator, get_file_age_days, load_config, walk_directory


ProgressCallback = Optional[Callable[[str, int, int], None]]
LocationProgressCallback = Optional[Callable[[str, int, int], None]]


@dataclass
class ScanResult:
    """Result of scanning a single location."""

    location: TempLocation
    files: List[Tuple[str, int, int]] = field(default_factory=list)
    total_size: int = 0
    file_count: int = 0
    error: str = ""

    @property
    def accessible(self) -> bool:
        """Check if the location was accessible."""
        return not bool(self.error)


@dataclass
class ScanSummary:
    """Summary of scanning all locations."""

    results: List[ScanResult] = field(default_factory=list)
    total_size: int = 0
    total_files: int = 0

    def by_category(self) -> Dict[str, ScanResult]:
        """Group results by location name."""
        return {r.location.name: r for r in self.results}


class Scanner:
    """Scans Windows temp directories for files."""

    PROTECTED_FILENAMES = {
        "ntuser.dat",
        "ntuser.ini",
        "ntuser.dat.LOG",
        "thumbs.db",
        "desktop.ini",
        "iconcache.db",
        "wcache.dat",
    }

    def __init__(
        self,
        min_age_days: int = 0,
        enabled_locations: Optional[Set[str]] = None,
        cancelled: Optional[List[bool]] = None,
        progress_callback: ProgressCallback = None,
        location_progress_callback: LocationProgressCallback = None,
    ):
        """
        Initialize scanner.

        Args:
            min_age_days: Only scan files older than this many days
            enabled_locations: Set of location names to scan (None = all)
            cancelled: Shared cancellation flag list [cancelled]
            progress_callback: Optional callback(location_name, current, total) for progress per file
            location_progress_callback: Optional callback(location_name, file_count, total_size) for progress per location
        """
        self.min_age_days = min_age_days
        self.enabled_locations = enabled_locations
        self._cancelled = cancelled
        self._progress_callback = progress_callback
        self._location_progress_callback = location_progress_callback
        self._results: List[ScanResult] = []
        self._config = load_config()
        self._exclusions = self._config.get("exclusions", {})
        self._has_exclusions = bool(self._exclusions.get("patterns") or self._exclusions.get("paths"))
        self._path_validator = PathValidator(self._exclusions)

    def cancel(self) -> None:
        """Request cancellation of the current operation."""
        if self._cancelled is not None:
            self._cancelled[0] = True

    def _is_cancelled(self) -> bool:
        """Check if operation has been cancelled."""
        return self._cancelled is not None and self._cancelled[0]

    def is_safe_to_delete(self, file_path: str, base_directory: str) -> bool:
        """Check if a file is safe to delete using PathValidator."""
        return self._path_validator.should_delete(file_path, base_directory)

    def is_protected_file(self, file_path: str) -> bool:
        """Check if a file is protected and should not be deleted."""
        filename = os.path.basename(file_path).lower()
        return filename in self.PROTECTED_FILENAMES

    def scan_location(self, location: TempLocation) -> ScanResult:
        """Scan a single temp location."""
        if self._is_cancelled():
            result = ScanResult(location=location)
            result.error = "Cancelled"
            return result

        result = ScanResult(location=location)

        if self.enabled_locations and location.name not in self.enabled_locations:
            result.error = "Disabled by user"
            return result

        if location.requires_admin and not is_admin():
            result.error = "Admin privileges required"
            return result

        if not os.path.exists(location.path):
            result.error = "Path does not exist"
            return result

        try:
            files = []
            base_path = location.path
            for file_path, size, age in walk_directory(base_path, self.min_age_days):
                if self._is_cancelled():
                    result.error = "Cancelled"
                    break

                if not self._has_exclusions or self.is_safe_to_delete(file_path, base_path):
                    files.append((file_path, size, age))
                    result.total_size += size
                    result.file_count += 1

                    if self._progress_callback:
                        self._progress_callback(location.name, result.file_count, -1)

            result.files = files

        except PermissionError:
            result.error = "Permission denied"
        except Exception as e:
            result.error = str(e)

        return result

    def scan_all(self, parallel: bool = True) -> ScanSummary:
        """Scan all temp locations."""
        locations = get_temp_locations()
        summary = ScanSummary()

        if parallel and len(locations) > 1:
            summary = self._scan_parallel(locations)
        else:
            summary = self._scan_sequential(locations)

        return summary

    def _scan_sequential(self, locations: List[TempLocation]) -> ScanSummary:
        """Scan locations sequentially."""
        summary = ScanSummary()

        for location in locations:
            if self._is_cancelled():
                break

            result = self.scan_location(location)
            self._results.append(result)
            summary.results.append(result)

            if result.accessible:
                summary.total_size += result.total_size
                summary.total_files += result.file_count

                if self._location_progress_callback:
                    self._location_progress_callback(
                        location.name, result.file_count, result.total_size
                    )

        return summary

    def _scan_parallel(self, locations: List[TempLocation]) -> ScanSummary:
        """Scan locations in parallel using ThreadPoolExecutor."""
        summary = ScanSummary()

        with ThreadPoolExecutor(max_workers=min(8, len(locations))) as executor:
            future_to_location = {
                executor.submit(self.scan_location, loc): loc
                for loc in locations
            }

            for future in as_completed(future_to_location):
                if self._is_cancelled():
                    break

                try:
                    result = future.result(timeout=30)
                    self._results.append(result)
                    summary.results.append(result)

                    if result.accessible:
                        summary.total_size += result.total_size
                        summary.total_files += result.file_count
                except TimeoutError:
                    continue
                except Exception:
                    continue

        return summary

    def get_inaccessible_count(self) -> int:
        """Count how many locations were inaccessible."""
        return sum(1 for r in self._results if r.error)

    def get_admin_required_count(self) -> int:
        """Count how many locations require admin privileges."""
        return sum(1 for r in self._results if r.error == "Admin privileges required")

    def get_enabled_locations(self) -> Set[str]:
        """Get set of currently enabled location names."""
        return self.enabled_locations.copy() if self.enabled_locations else set()
