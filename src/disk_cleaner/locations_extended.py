"""Extended temporary file locations for various applications."""

import os
from typing import List

from disk_cleaner.locations import TempLocation


def get_extended_locations() -> List[TempLocation]:
    """
    Get extended temporary file locations for browsers and applications.
    These are disabled by default and must be explicitly enabled.
    """
    localappdata = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")
    userprofile = os.environ.get("USERPROFILE", "")

    locations = []

    locations.extend(_get_browser_cache_locations(localappdata))
    locations.extend(_get_package_cache_locations(appdata, localappdata, userprofile))
    locations.extend(_get_gpu_cache_locations(localappdata))
    locations.extend(_get_app_cache_locations(localappdata, appdata))

    return [loc for loc in locations if loc.path]


def _get_browser_cache_locations(localappdata: str) -> List[TempLocation]:
    """Get browser cache locations."""
    locations = []

    chrome_path = os.path.join(localappdata, r"Google\Chrome\User Data\Default\Cache") if localappdata else ""
    if chrome_path and os.path.exists(os.path.dirname(chrome_path)):
        locations.append(TempLocation(
            name="Chrome Cache",
            path=chrome_path,
            requires_admin=False,
            description="Archivos cache de Google Chrome",
        ))

    firefox_profiles = os.path.join(localappdata, r"Mozilla\Firefox\Profiles") if localappdata else ""
    if firefox_profiles and os.path.exists(firefox_profiles):
        try:
            for profile in os.listdir(firefox_profiles):
                cache_path = os.path.join(firefox_profiles, profile, "cache2")
                if os.path.exists(cache_path):
                    locations.append(TempLocation(
                        name=f"Firefox Cache ({profile})",
                        path=cache_path,
                        requires_admin=False,
                        description="Archivos cache de Mozilla Firefox",
                    ))
        except PermissionError:
            pass

    edge_path = os.path.join(localappdata, r"Microsoft\Edge\User Data\Default\Cache") if localappdata else ""
    if edge_path and os.path.exists(os.path.dirname(edge_path)):
        locations.append(TempLocation(
            name="Edge Cache",
            path=edge_path,
            requires_admin=False,
            description="Archivos cache de Microsoft Edge",
        ))

    brave_path = os.path.join(localappdata, r"BraveSoftware\Brave-Browser\User Data\Default\Cache") if localappdata else ""
    if brave_path and os.path.exists(os.path.dirname(brave_path)):
        locations.append(TempLocation(
            name="Brave Cache",
            path=brave_path,
            requires_admin=False,
            description="Archivos cache de Brave Browser",
        ))

    opera_path = os.path.join(localappdata, r"Opera Software\Opera Stable\Cache") if localappdata else ""
    if opera_path and os.path.exists(os.path.dirname(opera_path)):
        locations.append(TempLocation(
            name="Opera Cache",
            path=opera_path,
            requires_admin=False,
            description="Archivos cache de Opera",
        ))

    return locations


def _get_package_cache_locations(appdata: str, localappdata: str, userprofile: str) -> List[TempLocation]:
    """Get package manager cache locations."""
    locations = []

    npm_cache = os.path.join(appdata, r"npm-cache") if appdata else ""
    if npm_cache and os.path.exists(npm_cache):
        locations.append(TempLocation(
            name="npm Cache",
            path=npm_cache,
            requires_admin=False,
            description="Cache del gestor de paquetes npm",
        ))

    pip_cache = os.path.join(localappdata, r"pip\cache") if localappdata else ""
    if pip_cache and os.path.exists(pip_cache):
        locations.append(TempLocation(
            name="pip Cache",
            path=pip_cache,
            requires_admin=False,
            description="Cache del gestor de paquetes pip",
        ))

    pip_global_cache = os.path.join(userprofile, r".cache\pip") if userprofile else ""
    if pip_global_cache and os.path.exists(pip_global_cache):
        locations.append(TempLocation(
            name="pip Global Cache",
            path=pip_global_cache,
            requires_admin=False,
            description="Cache global del gestor de paquetes pip",
        ))

    cargo_cache = os.path.join(userprofile, r".cargo\registry\cache") if userprofile else ""
    if cargo_cache and os.path.exists(cargo_cache):
        locations.append(TempLocation(
            name="Cargo Cache",
            path=cargo_cache,
            requires_admin=False,
            description="Cache del gestor de paquetes Cargo (Rust)",
        ))

    nuget_cache = os.path.join(userprofile, r".nuget\packages") if userprofile else ""
    if nuget_cache and os.path.exists(nuget_cache):
        locations.append(TempLocation(
            name="NuGet Cache",
            path=nuget_cache,
            requires_admin=False,
            description="Cache del gestor de paquetes NuGet",
        ))

    yarn_cache = os.path.join(appdata, r"yarn\Cache") if appdata else ""
    if yarn_cache and os.path.exists(yarn_cache):
        locations.append(TempLocation(
            name="Yarn Cache",
            path=yarn_cache,
            requires_admin=False,
            description="Cache del gestor de paquetes Yarn",
        ))

    return locations


def _get_gpu_cache_locations(localappdata: str) -> List[TempLocation]:
    """Get GPU cache locations."""
    locations = []

    nvidia_dxcache = os.path.join(localappdata, r"NVIDIA\DXCache") if localappdata else ""
    if nvidia_dxcache and os.path.exists(nvidia_dxcache):
        locations.append(TempLocation(
            name="NVIDIA DX Cache",
            path=nvidia_dxcache,
            requires_admin=False,
            description="Cache DirectX de NVIDIA",
        ))

    nvidia_glcache = os.path.join(localappdata, r"NVIDIA\GLCache") if localappdata else ""
    if nvidia_glcache and os.path.exists(nvidia_glcache):
        locations.append(TempLocation(
            name="NVIDIA GL Cache",
            path=nvidia_glcache,
            requires_admin=False,
            description="Cache OpenGL de NVIDIA",
        ))

    amd_dxcache = os.path.join(localappdata, r"AMD\DxCache") if localappdata else ""
    if amd_dxcache and os.path.exists(amd_dxcache):
        locations.append(TempLocation(
            name="AMD DX Cache",
            path=amd_dxcache,
            requires_admin=False,
            description="Cache DirectX de AMD",
        ))

    intel_cache = os.path.join(localappdata, r"Intel\GraphicsCache") if localappdata else ""
    if intel_cache and os.path.exists(intel_cache):
        locations.append(TempLocation(
            name="Intel Graphics Cache",
            path=intel_cache,
            requires_admin=False,
            description="Cache de graficos Intel",
        ))

    return locations


def _get_app_cache_locations(localappdata: str, appdata: str) -> List[TempLocation]:
    """Get application-specific cache locations."""
    locations = []

    discord_cache = os.path.join(appdata, r"discord") if appdata else ""
    if discord_cache and os.path.exists(discord_cache):
        locations.append(TempLocation(
            name="Discord Cache",
            path=os.path.join(discord_cache, "Cache"),
            requires_admin=False,
            description="Archivos cache de Discord",
        ))

    slack_cache = os.path.join(localappdata, r"Slack\logs") if localappdata else ""
    if slack_cache and os.path.exists(slack_cache):
        locations.append(TempLocation(
            name="Slack Logs",
            path=slack_cache,
            requires_admin=False,
            description="Logs de Slack",
        ))

    teams_cache = os.path.join(localappdata, r"Microsoft\Teams\logs") if localappdata else ""
    if teams_cache and os.path.exists(teams_cache):
        locations.append(TempLocation(
            name="Teams Logs",
            path=teams_cache,
            requires_admin=False,
            description="Logs de Microsoft Teams",
        ))

    vscode_cache = os.path.join(appdata, r"Code\Cache") if appdata else ""
    if vscode_cache and os.path.exists(vscode_cache):
        locations.append(TempLocation(
            name="VSCode Cache",
            path=vscode_cache,
            requires_admin=False,
            description="Cache de Visual Studio Code",
        ))

    spotify_cache = os.path.join(localappdata, r"Spotify\Data") if localappdata else ""
    if spotify_cache and os.path.exists(spotify_cache):
        locations.append(TempLocation(
            name="Spotify Cache",
            path=spotify_cache,
            requires_admin=False,
            description="Archivos cache de Spotify",
        ))

    return locations
