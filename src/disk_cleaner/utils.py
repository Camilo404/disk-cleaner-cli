"""Utility functions for disk cleaner."""

import ctypes
import fnmatch
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, List, Optional, Set, Tuple

FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004


class RecycleBinOperation:
    """Result of a recycle bin operation."""

    def __init__(self, success: bool, error: str = ""):
        self.success = success
        self.error = error


def send_to_recycle_bin(file_path: str) -> RecycleBinOperation:
    """
    Send a file to the Windows Recycle Bin instead of permanent deletion.

    Args:
        file_path: Absolute path to the file to recycle

    Returns:
        RecycleBinOperation with success status and error message
    """
    if not os.path.exists(file_path):
        return RecycleBinOperation(False, "File does not exist")

    try:
        buffer = ctypes.create_unicode_buffer(file_path)
        sizeof_buf = len(buffer) + 1

        class SHFILEOPSTRUCT(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("wFunc", ctypes.c_uint),
                ("pFrom", ctypes.c_wchar_p),
                ("pTo", ctypes.c_wchar_p),
                ("fFlags", ctypes.c_ushort),
                ("fAnyOperationsAborted", ctypes.c_bool),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p),
            ]

        fileop = SHFILEOPSTRUCT()
        fileop.wFunc = 0x0003  # FO_DELETE
        fileop.pFrom = file_path
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT

        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))

        if result == 0 and not fileop.fAnyOperationsAborted:
            return RecycleBinOperation(True)
        elif result == 32:
            return RecycleBinOperation(False, "Archivo en uso por otro proceso")
        elif result == 5:
            return RecycleBinOperation(False, "Acceso denegado")
        elif result == 2:
            return RecycleBinOperation(False, "Archivo no encontrado")
        else:
            return RecycleBinOperation(False, f"Error {result}")

    except Exception as e:
        return RecycleBinOperation(False, str(e))


def permanently_delete(file_path: str) -> RecycleBinOperation:
    """
    Permanently delete a file (bypass Recycle Bin).

    Args:
        file_path: Absolute path to the file to delete

    Returns:
        RecycleBinOperation with success status and error message
    """
    if not os.path.exists(file_path):
        return RecycleBinOperation(False, "File does not exist")

    try:
        os.remove(file_path)
        return RecycleBinOperation(True)
    except PermissionError as e:
        return RecycleBinOperation(False, "En uso por otro proceso")
    except OSError as e:
        return RecycleBinOperation(False, f"Error del sistema: {e.strerror}")
    except Exception as e:
        return RecycleBinOperation(False, str(e))


class PathValidator:
    """Validates and sanitizes file paths for safety."""

    PROTECTED_DIRECTORIES = {
        "windows",
        "system32",
        "syswow64",
        "program files",
        "program files (x86)",
        "boot",
        "recovery",
    }

    def __init__(self, exclusions: Optional[dict] = None):
        self.exclusions = exclusions or {}
        self._exclusion_patterns: Set[str] = set()
        self._exclusion_paths: Set[str] = set()

        if "patterns" in self.exclusions:
            self._exclusion_patterns = set(self.exclusions["patterns"])
        if "paths" in self.exclusions:
            self._exclusion_paths = {os.path.normpath(p) for p in self.exclusions["paths"]}

    def is_safe_path(self, file_path: str, base_directory: str) -> bool:
        """Check if a path is safe to delete."""
        try:
            real_path = os.path.realpath(file_path)
            real_base = os.path.realpath(base_directory)

            if not real_path.startswith(real_base):
                return False

            path_parts = Path(real_path).parts
            base_parts = Path(real_base).parts

            for i, part in enumerate(path_parts):
                part_lower = part.lower()
                if part_lower in self.PROTECTED_DIRECTORIES:
                    if i < len(base_parts) or part_lower != base_parts[min(i, len(base_parts) - 1)].lower():
                        return False

            if real_path in self._exclusion_paths:
                return False

            return True

        except (OSError, ValueError):
            return False

    def is_excluded_by_pattern(self, file_path: str) -> bool:
        """Check if file matches any exclusion pattern."""
        filename = os.path.basename(file_path)
        for pattern in self._exclusion_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(file_path, pattern):
                return True
        return False

    def should_delete(self, file_path: str, base_directory: str) -> bool:
        """Determine if a file should be deleted."""
        if not self.is_safe_path(file_path, base_directory):
            return False
        if self.is_excluded_by_pattern(file_path):
            return False
        return True


def load_config(config_path: Optional[str] = None) -> dict:
    """Load configuration from JSON file."""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "config.json"
        )
        config_path = os.path.normpath(config_path)

    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

    return {"exclusions": {"patterns": [], "paths": []}}


def format_size(size_bytes: float) -> str:
    """Format bytes into human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def get_file_age_days(file_path: str) -> int:
    """Get the age of a file in days based on modification time."""
    try:
        mtime = os.path.getmtime(file_path)
        age_days = int((datetime.now().timestamp() - mtime) / 86400)
        if age_days < 0:
            return 0
        return age_days
    except (OSError, ValueError, OverflowError):
        return 0


def walk_directory(
    directory: str, min_age_days: int = 0
) -> Iterator[Tuple[str, int, int]]:
    """
    Walk a directory and yield (file_path, size, age_days) tuples.
    Optimized for speed using os.scandir().

    Args:
        directory: Path to walk
        min_age_days: Only include files older than this many days

    Yields:
        Tuples of (file_path, size_in_bytes, age_in_days)
    """
    try:
        dirs_to_visit = [directory]
        while dirs_to_visit:
            current_dir = dirs_to_visit.pop()
            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                if not entry.is_symlink():
                                    dirs_to_visit.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                stat = entry.stat(follow_symlinks=False)
                                if stat.st_size > 0:
                                    mtime = stat.st_mtime
                                    age_days = int((datetime.now().timestamp() - mtime) / 86400)
                                    if age_days >= min_age_days:
                                        yield (entry.path, stat.st_size, age_days)
                        except (PermissionError, OSError, ValueError, RuntimeError):
                            continue
            except (PermissionError, OSError):
                continue
    except Exception:
        return


def is_locked(file_path: str) -> bool:
    """Check if a file is likely locked by another process (less aggressive)."""
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(file_path)
        if attrs == -1:
            return False
        FILE_ATTRIBUTE_READONLY = 0x1
        FILE_ATTRIBUTE_SYSTEM = 0x4
        FILE_ATTRIBUTE_HIDDEN = 0x2
        if attrs & (FILE_ATTRIBUTE_READONLY | FILE_ATTRIBUTE_SYSTEM):
            return True
        return False
    except Exception:
        return False


def confirm_deletion(total_size: int, total_files: int) -> bool:
    """Prompt user for deletion confirmation."""
    import click

    size_str = format_size(total_size)
    return click.confirm(
        f"Delete {total_files} files ({size_str})?",
        default=False,
    )
