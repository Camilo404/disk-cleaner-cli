# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed
- `is_locked()` now actually tests for an open file handle via `CreateFileW`. Previously it only checked the read-only/system/hidden attribute bits, which caused many deletable files to be wrongly skipped.
- Cancellation bug in `Cleaner.delete_files_iterator`: when a scan was cancelled, the iterator used to yield a "Cancelled" entry for **every** remaining file in **every** location. It now stops after the first cancelled file, matching the documented contract.
- `Scanner.scan_all` now uses `get_all_locations` (configurable), so the previously-dead `get_extended_locations` is reachable from both the CLI and the interactive menu.
- `load_config` always returns a dict that includes the resolved config path, so `disk-cleaner config show` can point users to the file it actually read.
- `disk-cleaner.spec` no longer references a hardcoded user-specific icon path; the icon is now optional and falls back to the PyInstaller default when `icon.ico` is not present in the project root.
- `build.bat` now installs the `[dev]` extras (pytest, pyinstaller) and runs the test suite as the last build step.

### Added
- `--min-size N` filter on `scan` and `clean`: only consider files whose size is at least N bytes. Implemented as a new `min_size_bytes` parameter on `Scanner` and `walk_directory`.
- `--include-extended` flag on `scan` and `clean`: include browser, package manager, GPU, and application caches that live under `%LOCALAPPDATA%` / `%APPDATA%` / `%USERPROFILE%`.
- New `get_all_locations(include_extended=...)` helper in `disk_cleaner.locations` that combines built-in and extended locations.
- The interactive menu's location selector (option `[6]`) now accepts `E` to toggle extended locations on/off, and reuses `get_all_locations` for an accurate progress-bar total.
- `disk-cleaner config show` now prints every configured exclusion pattern and path, plus the resolved config file path.
- New tests covering: cancellation fix, progress callback, dry-run iterator, min-size filter, `get_all_locations`, and the `include_extended` flag.

### Changed
- `pyproject.toml` declares a `[dev]` extras group (`pytest`, `pyinstaller`) and a `[tool.pytest.ini_options]` block.
