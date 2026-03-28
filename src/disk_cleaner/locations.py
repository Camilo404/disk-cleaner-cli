"""Windows temp file location definitions."""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class TempLocation:
    """Represents a temporary file location."""

    name: str
    path: str
    requires_admin: bool = False
    description: str = ""


def get_temp_locations() -> List[TempLocation]:
    """Get all configured temporary file locations for Windows."""
    temp = os.environ.get("TEMP", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"))
    localappdata = os.environ.get("LOCALAPPDATA", "")
    programdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    systemroot = os.environ.get("SYSTEMROOT", r"C:\Windows")

    locations = [
        TempLocation(
            name="User Temp",
            path=temp,
            requires_admin=False,
            description="Archivos temporales del usuario",
        ),
        TempLocation(
            name="System Temp",
            path=os.path.join(systemroot, "Temp"),
            requires_admin=True,
            description="Archivos temporales del sistema",
        ),
        TempLocation(
            name="Prefetch",
            path=os.path.join(systemroot, "Prefetch"),
            requires_admin=True,
            description="Archivos de prefetch de Windows",
        ),
        TempLocation(
            name="Thumbnail Cache",
            path=os.path.join(localappdata, r"Microsoft\Windows\Explorer")
            if localappdata
            else "",
            requires_admin=False,
            description="Cache de miniaturas del explorador",
        ),
        TempLocation(
            name="Windows Update Cache",
            path=os.path.join(systemroot, r"SoftwareDistribution\Download"),
            requires_admin=True,
            description="Cache de actualizaciones de Windows",
        ),
        TempLocation(
            name="Windows.old",
            path=os.path.join(systemroot, "Windows.old") if os.path.exists(os.path.join(systemroot, "Windows.old")) else "",
            requires_admin=True,
            description="Respaldo del Windows anterior (puede ocupar 10-30 GB)",
        ),
        TempLocation(
            name="Crash Dumps",
            path=os.path.join(systemroot, "Minidump"),
            requires_admin=True,
            description="Archivos de volcado por fallas",
        ),
        TempLocation(
            name="Error Reporting",
            path=os.path.join(programdata, r"Microsoft\Windows\WER"),
            requires_admin=True,
            description="Reportes de errores de Windows",
        ),
        TempLocation(
            name="Event Logs",
            path=os.path.join(systemroot, r"System32\Winevt\Logs"),
            requires_admin=True,
            description="Registros de eventos del sistema",
        ),

    ]

    return [loc for loc in locations if loc.path]


def is_admin() -> bool:
    """Check if the current process has admin privileges."""
    try:
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
