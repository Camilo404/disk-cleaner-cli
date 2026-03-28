"""CLI interface for disk-cleaner."""

import json
import os
import signal
import sys
import time
from typing import List, Optional, Set, Tuple

import click

from disk_cleaner import __version__
from disk_cleaner.cleaner import Cleaner, DeletionSummary
from disk_cleaner.locations import get_temp_locations, is_admin
from disk_cleaner.scanner import ScanSummary, Scanner
from disk_cleaner.utils import format_size, load_config


def run_interactive():
    """Run the interactive menu."""
    menu = InteractiveMenu()
    menu.run()


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx):
    """Windows temporary file cleaner CLI."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(interactive_cmd)


@main.command(name="interactive")
def interactive_cmd():
    """Run interactive menu mode."""
    run_interactive()


class MenuFormatter:
    """Handles all menu UI output formatting."""

    DIVIDER = "  " + "=" * 46

    @staticmethod
    def print_header():
        click.echo(click.style("  " + "=" * 46, fg="cyan", bold=True))
        click.echo(click.style("  *", fg="cyan") + click.style("    D I S K   C L E A N E R    ", fg="cyan", bold=True) + click.style("*", fg="cyan"))
        click.echo(click.style("  " + "=" * 46, fg="cyan", bold=True))
        click.echo(click.style("  *  Limpiador de archivos temporales  *", fg="white", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="cyan", bold=True))

    @staticmethod
    def print_status_bar(
        is_admin: bool,
        enabled_locations: Set[str],
        all_locations: list,
        use_recycle_bin: bool = False,
    ):
        click.echo()
        admin_icon = click.style(" [ADMIN]", fg="green", bold=True) if is_admin else click.style(" [User]", fg="yellow")
        click.echo(click.style("  Modo:", fg="white") + admin_icon)

        if enabled_locations:
            count = len(enabled_locations)
            total = len(all_locations)
            click.echo(
                click.style(f"  Ubicaciones: ", fg="white")
                + click.style(f"{count}/{total}", fg="cyan", bold=True)
                + click.style(" seleccionadas", fg="white")
            )
        else:
            click.echo(
                click.style(f"  Ubicaciones: ", fg="white")
                + click.style("Todas", fg="green", bold=True)
                + click.style(" habilitadas", fg="white")
            )

        recycle_icon = click.style(" [RECYCLE]", fg="blue", bold=True) if use_recycle_bin else ""
        click.echo(click.style("  Seguridad:", fg="white") + recycle_icon + click.style(" Eliminacion", fg="red" if not use_recycle_bin else "white"))

    @staticmethod
    def print_menu():
        click.echo()
        click.echo(click.style("  [1] ", fg="yellow", bold=True) + click.style("Escanear archivos", fg="white"))
        click.echo(click.style("  [2] ", fg="yellow", bold=True) + click.style("Ver resumen de espacios", fg="white"))
        click.echo(click.style("  [3] ", fg="yellow", bold=True) + click.style("Limpiar (vista previa)", fg="white"))
        click.echo(click.style("  [4] ", fg="yellow", bold=True) + click.style("Limpiar (con confirmacion)", fg="white"))
        click.echo(click.style("  [5] ", fg="red", bold=True) + click.style("Limpiar (automatico)", fg="white"))
        click.echo(click.style("  [6] ", fg="yellow", bold=True) + click.style("Seleccionar ubicaciones", fg="white"))
        click.echo(click.style("  [7] ", fg="cyan", bold=True) + click.style("Configurar modo de eliminacion", fg="white"))
        click.echo()
        click.echo(click.style("  [0] ", fg="yellow", bold=True) + click.style("Salir", fg="white"))

    @staticmethod
    def print_scan_results(
        summary: ScanSummary,
        admin_required_count: int,
        verbose: bool = False,
        preview_full: bool = False,
    ):
        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="cyan"))
        click.echo(click.style("    RESULTADOS DEL ESCANEO", fg="cyan", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="cyan"))

        summary_total_files = 0
        summary_total_size = 0

        for result in sorted(summary.results, key=lambda x: x.total_size, reverse=True):
            location = result.location
            if result.accessible and result.total_size > 0:
                size_str = click.style(format_size(result.total_size), fg="green", bold=True)
                files_str = click.style(str(result.file_count), fg="yellow", bold=True)
                bar_width = min(result.total_size / (1024 * 1024), 20)
                bar = click.style("#" * int(bar_width), fg="green")
                empty = click.style(" " * (20 - int(bar_width)), fg="white")

                click.echo(f"\n  {click.style('[+]', fg='green', bold=True)} {click.style(location.name, fg='white', bold=True)}")
                click.echo(f"     {bar}{empty} {size_str} ({files_str} archivos)")

                if preview_full:
                    for file_path, file_size, file_age in result.files:
                        fname = os.path.basename(file_path)
                        click.echo(f"       {click.style('>', fg='yellow')} {fname} ({format_size(file_size)}, {file_age}d)")
                elif verbose and result.files:
                    for file_path, _, _ in result.files[:10]:
                        fname = os.path.basename(file_path)
                        if len(fname) > 40:
                            fname = fname[:37] + "..."
                        click.echo(f"       {click.style('>', fg='yellow')} {fname}")

                    if len(result.files) > 10:
                        click.echo(f"       {click.style('...', fg='white')} y {click.style(str(len(result.files) - 10), fg='yellow')} archivos mas")
                elif result.files:
                    for file_path, _, _ in result.files[:3]:
                        fname = os.path.basename(file_path)
                        if len(fname) > 35:
                            fname = fname[:32] + "..."
                        click.echo(f"       {click.style('>', fg='yellow')} {fname}")

                    if len(result.files) > 3:
                        click.echo(f"       {click.style('...', fg='white')} y {click.style(str(len(result.files) - 3), fg='yellow')} archivos mas")

                summary_total_files += result.file_count
                summary_total_size += result.total_size

            elif result.error:
                if result.error == "Path does not exist":
                    info_msg = (
                        click.style("[i]", fg="cyan", bold=True)
                        + click.style(f" {location.name}", fg="white")
                        + click.style(" (no encontrado)", fg="yellow")
                    )
                    click.echo(f"\n  {info_msg}")
                else:
                    error_msg = (
                        click.style(f"[X] {location.name}", fg="red", bold=True)
                        + click.style(f" ({result.error})", fg="white")
                    )
                    click.echo(f"\n  {error_msg}")

        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="cyan"))
        click.echo(
            click.style("    TOTAL: ", fg="white")
            + click.style(str(summary_total_files), fg="green", bold=True)
            + click.style(" archivos | ", fg="white")
            + click.style(format_size(summary_total_size), fg="green", bold=True)
        )

        if admin_required_count > 0:
            click.echo(
                click.style("    [!] ", fg="yellow", bold=True)
                + click.style(f"{admin_required_count} ubicaciones requieren admin", fg="white")
            )

        click.echo(click.style("  " + "=" * 46, fg="cyan"))

    @staticmethod
    def print_summary(summary: ScanSummary, enabled_locations: Set[str]):
        click.echo()
        click.echo(click.style("  [" + "*" + "] Analizando...", fg="cyan", bold=True))

        locations = get_temp_locations()
        enabled = enabled_locations or {loc.name for loc in locations}
        max_size = max((r.total_size for r in summary.results if r.accessible), default=1)

        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="cyan"))
        click.echo(click.style("    ESPACIO RECUPERABLE", fg="cyan", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="cyan"))

        for result in sorted(summary.results, key=lambda x: x.total_size, reverse=True):
            if result.accessible and result.total_size > 0 and result.location.name in enabled:
                size_str = format_size(result.total_size)
                bar_len = int((result.total_size / max_size) * 20)
                bar = click.style("#" * bar_len, fg="cyan")
                empty = click.style(" " * (20 - bar_len), fg="white")

                click.echo(f"\n  {result.location.name}")
                click.echo(
                    f"  {bar}{empty} {click.style(size_str, fg='green', bold=True)} {click.style(f'({(result.total_size / max_size) * 100:.0f}%)', fg='white')}"
                )

        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="cyan"))
        total = click.style(format_size(summary.total_size), fg="green", bold=True)
        count = click.style(str(summary.total_files), fg="yellow", bold=True)
        click.echo(click.style(f"    TOTAL: {count} archivos | {total}", fg="white", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="cyan"))

    @staticmethod
    def print_clean_summary(summary: ScanSummary, dry_run: bool, use_recycle_bin: bool):
        total_size = click.style(format_size(summary.total_size), fg="green", bold=True)
        total_files = click.style(str(summary.total_files), fg="yellow", bold=True)
        click.echo(f"\n  Archivos a procesar: {total_files}")
        click.echo(f"  Espacio a liberar: {total_size}")

        click.echo()
        mode = "VISTA PREVIA (dry-run)" if dry_run else "ELIMINACION REAL"
        mode_color = "cyan" if dry_run else "red"
        click.echo(click.style(f"  Modo: ", fg="white") + click.style(mode, fg=mode_color, bold=True))

        if use_recycle_bin:
            click.echo(click.style("  [!] Usando papelera de reciclaje", fg="blue"))
        else:
            click.echo(click.style("  [!] ELIMINACION PERMANENTE", fg="red", bold=True))

        if dry_run:
            click.echo(click.style("  [!] No se eliminara nada todavia", fg="yellow"))
        else:
            click.echo(click.style("  [!] SE ELIMINARAN LOS ARCHIVOS!", fg="red", bold=True))

    @staticmethod
    def print_clean_result(summary: DeletionSummary, dry_run: bool, use_recycle_bin: bool, failed_details: Optional[List[Tuple[str, str]]] = None):
        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="green"))
        mode = "VISTA PREVIA" if dry_run else "COMPLETADO"
        click.echo(click.style(f"    {mode}", fg="green", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="green"))

        deleted = click.style(str(summary.total_deleted), fg="green", bold=True)
        freed = click.style(format_size(summary.total_freed_bytes), fg="green", bold=True)
        click.echo(f"\n  {click.style('[OK]', fg='green', bold=True)} Eliminados: {deleted} archivos")
        click.echo(f"  {click.style('[OK]', fg='green', bold=True)} Liberado: {freed}")

        if use_recycle_bin and summary.total_recycled > 0:
            recycled = click.style(str(summary.total_recycled), fg="blue", bold=True)
            click.echo(f"  {click.style('[i]', fg='blue', bold=True)} Enviados a papelera: {recycled} archivos")

        if summary.total_failed > 0:
            failed = click.style(str(summary.total_failed), fg="red", bold=True)
            click.echo(f"\n  {click.style('[X]', fg='red', bold=True)} Errores: {failed} archivos")
            if failed_details:
                click.echo(click.style("  Detalles:", fg="yellow"))
                for fname, error in failed_details[:10]:
                    if len(fname) > 30:
                        fname = fname[:27] + "..."
                    click.echo(f"    {click.style('[X]', fg='red')} {fname}: {click.style(error, fg='white')}")
                if len(failed_details) > 10:
                    click.echo(f"    {click.style('...', fg='white')} y {len(failed_details) - 10} errores mas")

    @staticmethod
    def print_location_selector(locations, enabled_locations: Set[str]):
        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="magenta"))
        click.echo(click.style("    SELECCIONAR UBICACIONES", fg="magenta", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="magenta"))
        click.echo(click.style("  Ingrese numeros (1,3,5) o 'all' / 'none'", fg="white"))
        click.echo()

        for i, loc in enumerate(locations, 1):
            is_enabled = loc.name in enabled_locations
            marker = click.style("[X]", fg="green", bold=True) if is_enabled else click.style("[ ]", fg="red")
            name = click.style(f"{i}. {loc.name}", fg="white")
            admin = click.style(" (admin)", fg="yellow") if loc.requires_admin else ""
            click.echo(f"  {marker} {name}{admin}")

    @staticmethod
    def print_error(message: str):
        click.echo()
        click.echo(click.style(f"  [X] {message}", fg="red", bold=True))

    @staticmethod
    def print_farewell():
        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="green"))
        click.echo(click.style("    HASTA LUEGO!", fg="green", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="green"))
        click.echo(click.style("    Tu disco te lo agradece!", fg="white"))
        click.echo()

    @staticmethod
    def print_no_files_found():
        click.echo()
        click.echo(click.style("  [i] ", fg="cyan", bold=True) + click.style("No se encontraron archivos temporales.", fg="white"))

    @staticmethod
    def print_prompt(prompt_text: str):
        click.echo(click.style(f"\n  {prompt_text}", fg="cyan"))

    @staticmethod
    def print_message(message: str, color: str = "white"):
        click.echo(click.style(f"  {message}", fg=color))


class InteractiveMenu:
    """Interactive menu for disk cleaner."""

    def __init__(self):
        self.scanner: Optional[Scanner] = None
        self.cleaner: Optional[Cleaner] = None
        self.enabled_locations: Set[str] = set()
        self._all_locations = [loc.name for loc in get_temp_locations()]
        self._is_admin = is_admin()
        self._fmt = MenuFormatter()
        self._use_recycle_bin = False
        self._cancelled: List[bool] = [False]

    def run(self):
        """Run the interactive menu loop."""
        signal.signal(signal.SIGINT, self._handle_sigint)

        while True:
            click.clear()
            self._fmt.print_header()
            self._fmt.print_status_bar(self._is_admin, self.enabled_locations, self._all_locations, self._use_recycle_bin)
            self._fmt.print_menu()

            choice = click.prompt(
                click.style("  > ", fg="cyan", bold=True),
                type=str,
                default="0",
                show_default=False,
            )

            try:
                choice = int(choice)
            except ValueError:
                choice = -1

            if choice == 0:
                self._fmt.print_farewell()
                break
            elif choice == 1:
                self._scan()
            elif choice == 2:
                self._summary()
            elif choice == 3:
                self._clean(dry_run=True, auto_confirm=True)
            elif choice == 4:
                self._clean(dry_run=True, auto_confirm=False)
            elif choice == 5:
                self._clean(dry_run=False, auto_confirm=True)
            elif choice == 6:
                self._select_locations()
            elif choice == 7:
                self._configure_delete_mode()
            else:
                self._fmt.print_error("Opcion invalida!")
                self._pause()

    def _handle_sigint(self, signum, frame):
        """Handle Ctrl+C to gracefully cancel operations."""
        click.echo(click.style("\n\n  [!] Operacion cancelada por el usuario", fg="yellow"))
        if self.scanner:
            self.scanner.cancel()
        if self.cleaner:
            self.cleaner.cancel()
        self._cancelled[0] = True

    def _reset_cancelled(self):
        """Reset the cancelled flag."""
        self._cancelled[0] = False

    def _scan(self):
        """Scan and show detailed results with progress."""
        from tqdm import tqdm
        self._reset_cancelled()
        locations = get_temp_locations()
        enabled = self.enabled_locations or {loc.name for loc in locations}
        locations_to_scan = [loc for loc in locations if loc.name in enabled]

        click.echo()
        with tqdm(
            total=len(locations_to_scan),
            unit="ubic",
            desc="Escaneando",
            ncols=60,
        ) as pbar:
            def on_location_complete(name: str, file_count: int, total_size: int):
                pbar.set_description(f"{name[:12]}")
                pbar.update(1)
                pbar.set_postfix_str(f"{file_count} arch | {format_size(total_size)}")

            self.scanner = Scanner(
                enabled_locations=self.enabled_locations or None,
                cancelled=self._cancelled,
                location_progress_callback=on_location_complete,
            )
            summary = self.scanner.scan_all(parallel=False)

        self._fmt.print_scan_results(summary, self.scanner.get_admin_required_count())
        self._pause()

    def _summary(self):
        """Show quick summary with visual bars."""
        from tqdm import tqdm
        self._reset_cancelled()
        locations = get_temp_locations()
        enabled = self.enabled_locations or {loc.name for loc in locations}
        locations_to_scan = [loc for loc in locations if loc.name in enabled]

        click.echo()
        with tqdm(
            total=len(locations_to_scan),
            unit="ubic",
            desc="Analizando",
            ncols=60,
        ) as pbar:
            def on_location_complete(name: str, file_count: int, total_size: int):
                pbar.set_description(f"{name[:12]}")
                pbar.update(1)
                pbar.set_postfix_str(f"{format_size(total_size)}")

            self.scanner = Scanner(
                enabled_locations=self.enabled_locations or None,
                cancelled=self._cancelled,
                location_progress_callback=on_location_complete,
            )
            summary = self.scanner.scan_all(parallel=False)

        self._fmt.print_summary(summary, self.enabled_locations)
        self._pause()

    def _clean(self, dry_run: bool, auto_confirm: bool):
        """Clean temp files with visual feedback."""
        from tqdm import tqdm
        self._reset_cancelled()
        locations = get_temp_locations()
        enabled = self.enabled_locations or {loc.name for loc in locations}
        locations_to_scan = [loc for loc in locations if loc.name in enabled]

        click.echo()
        with tqdm(
            total=len(locations_to_scan),
            unit="ubic",
            desc="Escaneando",
            ncols=60,
        ) as pbar:

            def on_scan_location(name: str, file_count: int, total_size: int):
                pbar.set_description(f"{name[:12]}")
                pbar.update(1)
                pbar.set_postfix_str(f"{file_count} arch | {format_size(total_size)}")

            self.scanner = Scanner(
                enabled_locations=self.enabled_locations or None,
                cancelled=self._cancelled,
                location_progress_callback=on_scan_location,
            )
            summary = self.scanner.scan_all(parallel=False)

        if summary.total_files == 0:
            self._fmt.print_no_files_found()
            self._pause()
            return

        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="cyan"))
        click.echo(click.style("    RESUMEN", fg="cyan", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="cyan"))

        self._fmt.print_clean_summary(summary, dry_run, self._use_recycle_bin)

        if not auto_confirm:
            click.echo()
            if not click.confirm(click.style("  [?] Continuar?", fg="cyan", bold=True), default=False):
                self._fmt.print_error("Operacion cancelada.")
                self._pause()
                return

        self.cleaner = Cleaner(
            dry_run=dry_run,
            use_recycle_bin=self._use_recycle_bin,
            cancelled=self._cancelled,
        )

        total_files = sum(len(sr.files) for sr in summary.results)
        total_size = summary.total_size
        del_summary = DeletionSummary()
        failed_details: List[Tuple[str, str]] = []

        click.echo()
        with tqdm(
            total=total_files,
            unit="arch",
            desc="Eliminando",
            ncols=70,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}",
        ) as pbar:
            last_update = time.time()
            bytes_since_last = 0

            for file_path, success, freed, loc_name, error_msg in self.cleaner.delete_files_iterator(summary):
                pbar.set_description(f"{loc_name[:10]}")
                pbar.update(1)

                del_summary.total_freed_bytes += freed
                bytes_since_last += freed

                if success:
                    del_summary.total_deleted += 1
                    if self._use_recycle_bin and freed == 0:
                        del_summary.total_recycled += 1
                else:
                    del_summary.total_failed += 1
                    failed_details.append((os.path.basename(file_path), error_msg or "Error desconocido"))

                current_time = time.time()
                elapsed = current_time - last_update
                if elapsed >= 0.5:
                    speed = bytes_since_last / elapsed
                    speed_str = f"{format_size(speed)}/s"
                    progress_str = f"{format_size(del_summary.total_freed_bytes)}/{format_size(total_size)}"
                    pbar.set_postfix_str(f"{progress_str} {speed_str}")
                    last_update = current_time
                    bytes_since_last = 0

        self._fmt.print_clean_result(del_summary, dry_run, self._use_recycle_bin, failed_details)
        self._pause()

    def _select_locations(self):
        """Select which locations to clean with interactive UI."""
        locations = get_temp_locations()
        all_names = [loc.name for loc in locations]

        if not self.enabled_locations:
            self.enabled_locations = set(all_names)

        self._fmt.print_location_selector(locations, self.enabled_locations)

        click.echo()
        choice = click.prompt(
            click.style("  > Seleccion: ", fg="cyan", bold=True),
            default="",
            show_default=False,
        )

        choice = choice.strip().lower()

        if choice == "all":
            self.enabled_locations = set(all_names)
            self._fmt.print_message("[OK] Todas las ubicaciones seleccionadas", "green")
        elif choice == "none":
            self.enabled_locations = set()
            self._fmt.print_message("[OK] Ninguna ubicacion seleccionada", "yellow")
        else:
            selected = set()
            for part in choice.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(locations):
                        selected.add(locations[idx].name)
            if selected:
                self.enabled_locations = selected
                self._fmt.print_message(f"[OK] {len(selected)} ubicaciones seleccionadas", "green")
            else:
                self._fmt.print_error("Seleccion invalida")

        self._pause()

    def _configure_delete_mode(self):
        """Configure delete mode (permanent or recycle bin)."""
        click.echo()
        click.echo(click.style("  " + "=" * 46, fg="blue"))
        click.echo(click.style("    MODO DE ELIMINACION", fg="blue", bold=True))
        click.echo(click.style("  " + "=" * 46, fg="blue"))
        click.echo()

        current_mode = click.style("PAPELERA DE RECICLAJE", fg="blue") if self._use_recycle_bin else click.style("ELIMINACION PERMANENTE", fg="red")
        click.echo(f"  Modo actual: {current_mode}")
        click.echo()

        click.echo(click.style("  [1] ", fg="yellow") + click.style("Eliminar permanentemente (no reversible)", fg="white"))
        click.echo(click.style("  [2] ", fg="yellow") + click.style("Enviar a papelera de reciclaje (reversible)", fg="white"))
        click.echo(click.style("  [0] ", fg="yellow") + click.style("Cancelar", fg="white"))
        click.echo()

        choice = click.prompt(
            click.style("  > Seleccion: ", fg="cyan", bold=True),
            default="0",
            show_default=False,
        )

        if choice == "1":
            self._use_recycle_bin = False
            self._fmt.print_message("[OK] Modo: Eliminacion permanente", "red")
        elif choice == "2":
            self._use_recycle_bin = True
            self._fmt.print_message("[OK] Modo: Papelera de reciclaje", "blue")
        else:
            self._fmt.print_message("[i] Sin cambios", "yellow")

        self._pause()

    def _pause(self):
        """Pause and wait for user."""
        try:
            self._fmt.print_prompt("Presione Enter para continuar...")
            input()
        except (EOFError, KeyboardInterrupt):
            pass


@main.command()
@click.option("--min-age", type=int, default=0, help="Only scan files older than N days")
@click.option("--verbose", is_flag=True, help="Show detailed file listing (up to 10 per location)")
@click.option("--preview-full", is_flag=True, help="Show all files in results")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def scan(min_age: int, verbose: bool, preview_full: bool, output_format: str):
    """Scan temporary file locations."""
    cancelled: List[bool] = [False]

    def signal_handler(signum, frame):
        cancelled[0] = True
        click.echo(click.style("\nCancelled.", fg="yellow"))

    signal.signal(signal.SIGINT, signal_handler)

    scanner = Scanner(min_age_days=min_age, cancelled=cancelled)
    summary = scanner.scan_all()

    if output_format == "json":
        _print_summary_json(summary)
    else:
        _print_summary_table(summary, verbose, preview_full)


@main.command()
@click.option("--dry-run", is_flag=True, default=True)
@click.option("--yes", "auto_confirm", is_flag=True)
@click.option("--min-age", type=int, default=0)
@click.option("--recycle", "use_recycle_bin", is_flag=True, help="Send files to Recycle Bin instead of permanent delete")
@click.option("--report", "report_file", type=click.Path(), default=None, help="Save deletion report to file (JSON)")
def clean(
    dry_run: bool,
    auto_confirm: bool,
    min_age: int,
    use_recycle_bin: bool,
    report_file: str,
):
    """Clean temporary files."""
    cancelled: List[bool] = [False]

    def signal_handler(signum, frame):
        cancelled[0] = True
        click.echo(click.style("\nCancelled.", fg="yellow"))

    signal.signal(signal.SIGINT, signal_handler)

    scanner = Scanner(min_age_days=min_age, cancelled=cancelled)
    summary = scanner.scan_all()

    if summary.total_files == 0:
        click.echo("No temporary files found.")
        return

    click.echo(f"Found {summary.total_files} files ({format_size(summary.total_size)})")

    if use_recycle_bin:
        click.echo(click.style("Files will be sent to Recycle Bin (reversible)", fg="blue"))
    else:
        click.echo(click.style("WARNING: Files will be PERMANENTLY DELETED", fg="red", bold=True))

    if not auto_confirm:
        if not click.confirm(f"Delete {summary.total_files} files ({format_size(summary.total_size)})?"):
            click.echo("Cancelled.")
            return

    cleaner = Cleaner(dry_run=dry_run, use_recycle_bin=use_recycle_bin, cancelled=cancelled)
    del_summary = cleaner.delete_all(summary)

    if report_file:
        _save_report(del_summary, report_file, use_recycle_bin)

    _print_delete_result(del_summary, dry_run, use_recycle_bin)


@main.group(name="config")
def config():
    """Manage configuration settings."""
    pass


@config.command()
def show():
    """Show current configuration."""
    cfg = load_config()
    click.echo("\n=== Current Configuration ===\n")
    click.echo(f"Exclusion patterns: {len(cfg.get('exclusions', {}).get('patterns', []))}")
    click.echo(f"Exclusion paths: {len(cfg.get('exclusions', {}).get('paths', []))}")


def _print_summary_table(summary: ScanSummary, verbose: bool, preview_full: bool):
    """Print summary in table format."""
    click.echo("\n=== Scan Results ===\n")
    for result in summary.results:
        status = click.style("[OK]", fg="green") if result.accessible else click.style(f"[SKIP: {result.error}]", fg="yellow")
        click.echo(f"{result.location.name}: {status}")
        if result.accessible:
            click.echo(f"  Files: {result.file_count}, Size: {format_size(result.total_size)}")
            if preview_full:
                for file_path, file_size, file_age in result.files:
                    click.echo(f"    - {os.path.basename(file_path)} ({format_size(file_size)}, {file_age}d)")
            elif verbose and result.files:
                for file_path, _, _ in result.files[:10]:
                    click.echo(f"    - {os.path.basename(file_path)}")
                if len(result.files) > 10:
                    click.echo(f"    ... and {len(result.files) - 10} more")
    click.echo(f"\nTotal: {summary.total_files} files, {format_size(summary.total_size)}")


def _print_summary_json(summary: ScanSummary):
    """Print summary in JSON format."""
    data = {
        "total_files": summary.total_files,
        "total_size": summary.total_size,
        "locations": [
            {
                "name": r.location.name,
                "path": r.location.path,
                "accessible": r.accessible,
                "error": r.error,
                "file_count": r.file_count,
                "total_size": r.total_size,
                "files": [
                    {"path": f[0], "size": f[1], "age_days": f[2]}
                    for f in r.files
                ],
            }
            for r in summary.results
        ],
    }
    click.echo(json.dumps(data, indent=2))


def _print_delete_result(summary: DeletionSummary, dry_run: bool, use_recycle_bin: bool):
    """Print deletion result."""
    mode = "[DRY RUN] " if dry_run else ""
    click.echo(f"\n=== {mode}Complete ===\n")
    click.echo(f"Deleted: {summary.total_deleted} files")
    click.echo(f"Freed: {format_size(summary.total_freed_bytes)}")
    if use_recycle_bin:
        click.echo(f"Recycled: {summary.total_recycled} files")
    if summary.total_failed > 0:
        click.echo(f"Failed: {summary.total_failed} files")


def _save_report(summary: DeletionSummary, report_file: str, use_recycle_bin: bool):
    """Save deletion report to JSON file."""
    data = {
        "total_deleted": summary.total_deleted,
        "total_failed": summary.total_failed,
        "total_freed_bytes": summary.total_freed_bytes,
        "total_recycled": summary.total_recycled,
        "used_recycle_bin": use_recycle_bin,
        "results": [
            {
                "location": r.location.name,
                "deleted": r.deleted,
                "failed": r.failed,
                "errors": r.errors,
            }
            for r in summary.results
        ],
    }
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    click.echo(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
