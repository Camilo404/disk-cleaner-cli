# Disk Cleaner CLI

A professional-grade Windows disk cleanup utility for CLI users. Clean temporary files safely with full control over what gets deleted.

## Features

- **Multiple Cleaning Locations** - Built-in Windows temp locations plus browser, package manager, and application caches
- **Safe Deletion** - Recycle Bin support allows reversible deletions
- **Dry-Run Mode** - Preview what will be deleted before committing
- **Protected Files** - System-critical files are never deleted
- **Locked File Handling** - Skips files in use by other processes
- **Admin Detection** - Gracefully skips locations requiring elevation
- **Cancellation Support** - Press Ctrl+C to cancel long-running operations
- **JSON Reports** - Save deletion reports for auditing
- **Progress Feedback** - Real-time progress bars with speed (MB/s) and space recovered during scans and deletions
- **Interactive Mode** - User-friendly menu interface
- **Configurable Exclusions** - Define custom patterns and paths to exclude

## Distribution (No Python Required)

The executable is a **single file** (~12 MB) that works on any Windows computer without Python installed.

### To Distribute:
1. Copy `dist/disk-cleaner.exe` to another computer
2. Run it - no installation needed!

**Note:** On first run, Windows may show a security warning. Click "More info" → "Run anyway".

## Installation (For Development)

```bash
pip install -e .
```

## Usage

### Interactive Mode

Launch the menu-driven interface:

```bash
disk-cleaner interactive
```

### Scan Commands

Scan all temp locations:

```bash
disk-cleaner scan
```

Scan with detailed file listing:

```bash
disk-cleaner scan --verbose
```

Show all files (no truncation):

```bash
disk-cleaner scan --preview-full
```

Output as JSON:

```bash
disk-cleaner scan --format json
```

### Clean Commands

Dry-run (preview what would be deleted):

```bash
disk-cleaner clean
```

Clean with auto-confirmation:

```bash
disk-cleaner clean --yes
```

Clean files older than 7 days:

```bash
disk-cleaner clean --min-age 7 --yes
```

Use Recycle Bin instead of permanent delete:

```bash
disk-cleaner clean --recycle --yes
```

Save deletion report:

```bash
disk-cleaner clean --yes --report deletion_report.json
```

### Configuration

Show current configuration:

```bash
disk-cleaner config show
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--min-age N` | Only scan/delete files older than N days |
| `--format table\|json` | Output format (default: table) |
| `--verbose` | Show detailed file listing (up to 10 per location) |
| `--preview-full` | Show all files without truncation |
| `--yes` | Skip confirmation prompt |
| `--recycle` | Send files to Recycle Bin instead of permanent delete |
| `--report FILE` | Save deletion report to JSON file |

## Temp Locations

### Built-in Locations

| Location | Path | Requires Admin |
|----------|-------|---------------|
| User Temp | `%TEMP%` | No |
| System Temp | `C:\Windows\Temp` | Yes |
| Prefetch | `C:\Windows\Prefetch` | Yes |
| Thumbnail Cache | `%LOCALAPPDATA%\Microsoft\Windows\Explorer` | No |
| Windows Update Cache | `C:\Windows\SoftwareDistribution\Download` | Yes |
| Windows.old | `C:\Windows\Windows.old` (if exists) | Yes |
| Crash Dumps | `C:\Windows\Minidump` | Yes |
| Error Reporting | `C:\ProgramData\Microsoft\Windows\WER` | Yes |
| Event Logs | `C:\Windows\System32\Winevt\Logs` | Yes |

### Extended Locations (Browser & Application Caches)

These must be explicitly enabled in interactive mode:

| Category | Locations |
|----------|-----------|
| **Browsers** | Chrome, Firefox, Edge, Brave, Opera caches |
| **Package Managers** | npm, pip, pip global, Cargo, NuGet, Yarn |
| **GPU Caches** | NVIDIA DX/GL Cache, AMD DX Cache, Intel Graphics |
| **Applications** | Discord, Slack, Teams, VSCode, Spotify |

## Safety Features

1. **Protected Files** - System-critical Windows files are never deleted
2. **Path Validation** - Files outside configured directories cannot be deleted
3. **Dry-Run Default** - Deletion requires explicit `--yes` flag
4. **Recycle Bin Mode** - Use `--recycle` to send files to trash instead of permanent delete
5. **Locked File Handling** - Files in use by other processes are skipped
6. **Admin Detection** - Locations requiring privileges are gracefully skipped
7. **Cancellation** - Press Ctrl+C at any time to cancel operations

## Configuration

Edit `config.json` to customize exclusions:

```json
{
  "exclusions": {
    "patterns": [
      "*.important",
      "ntuser.dat",
      "thumbs.db"
    ],
    "paths": [
      "C:\\Important\\Files"
    ]
  }
}
```

## Development

Install in development mode:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest tests/
```

## Building the Executable

To rebuild the standalone executable:

```bash
build.bat
```

This creates `dist/disk-cleaner.exe` as a single portable file (~12 MB).

## License

MIT
