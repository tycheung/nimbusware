from __future__ import annotations

import os
import subprocess
import threading
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from env.desktop_common import (
    can_init_git_updates,
    check_for_updates,
    default_clone_target,
    default_clone_url,
    git_pull,
    init_git_remote_for_updates,
    is_git_checkout,
    is_nimbusware_checkout,
    read_poetry_version,
    repo_root,
    resolve_python_command,
    run_log_path,
    subprocess_spawn_kwargs,
    updates_check_supported,
    updates_supported,
)
from env.launcher_dialogs import prompt_postgres_setup
from env.launcher_fetch import (
    INSTALL_PROFILE_BAREBONES,
    INSTALL_PROFILE_FULL,
    SETUP_BUNDLE_DEFAULT,
    SETUP_BUNDLE_ENTERPRISE,
    fetch_nimbusware_source,
    run_install_script,
)
from env.launcher_manage import (
    InstallState,
    convert_label,
    postgres_extra_args,
    read_env_file,
    read_install_state,
    run_convert_install,
    uninstall_nimbusware,
)
from env.launcher_theme import (
    BG,
    apply_launcher_theme,
    mono_font,
    style_log_widget,
)


class NimbuswareLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.repo = repo_root()
        self._busy = False

        self.theme = apply_launcher_theme(root)
        self._logo_photo = self.theme.logo

        root.title("Nimbusware")
        root.geometry("820x660")
        root.minsize(700, 540)

        shell = ttk.Frame(root, padding=16)
        shell.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(shell)
        header.pack(fill=tk.X, pady=(0, 14))
        header_left = ttk.Frame(header)
        header_left.pack(side=tk.LEFT)
        if self._logo_photo is not None:
            ttk.Label(header_left, image=self._logo_photo).pack(side=tk.LEFT, padx=(0, 14))
        header_text = ttk.Frame(header_left)
        header_text.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(header_text, text="Nimbusware", style="Title.TLabel").pack(anchor=tk.W)
        self.version_label = ttk.Label(header_text, text="", style="Muted.TLabel")
        self.version_label.pack(anchor=tk.W, pady=(2, 0))
        self.status_label = ttk.Label(header_text, text="Ready.", style="Muted.TLabel")
        self.status_label.pack(anchor=tk.W, pady=(2, 0))

        setup_panel = ttk.LabelFrame(shell, text="  Setup  ", padding=(12, 10), style="TLabelframe")
        setup_panel.pack(fill=tk.X, pady=(0, 10))
        buttons = ttk.Frame(setup_panel, style="Panel.TFrame")
        buttons.pack(fill=tk.X)
        buttons_row2 = ttk.Frame(setup_panel, style="Panel.TFrame")
        buttons_row2.pack(fill=tk.X, pady=(8, 0))
        self.check_btn = ttk.Button(
            buttons,
            text="Check for updates",
            command=self.check_updates,
        )
        self.check_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.install_btn = ttk.Button(
            buttons,
            text="Quick setup",
            command=lambda: self.run_install(
                INSTALL_PROFILE_BAREBONES,
                setup_bundle=SETUP_BUNDLE_DEFAULT,
            ),
        )
        self.install_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.install_full_btn = ttk.Button(
            buttons,
            text="Full setup",
            command=lambda: self.run_install(
                INSTALL_PROFILE_FULL,
                setup_bundle=SETUP_BUNDLE_DEFAULT,
            ),
        )
        self.install_full_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.install_enterprise_btn = ttk.Button(
            buttons,
            text="Enterprise setup",
            command=lambda: self.run_install(
                INSTALL_PROFILE_FULL,
                setup_bundle=SETUP_BUNDLE_ENTERPRISE,
            ),
        )
        self.install_enterprise_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.run_btn = ttk.Button(
            buttons_row2,
            text="Run Nimbusware",
            style="Accent.TButton",
            command=self.run_nimbusware,
        )
        self.run_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.admin_btn = ttk.Button(
            buttons_row2,
            text="Admin Console",
            command=self.run_admin_console,
        )
        self.admin_btn.pack(side=tk.LEFT)

        manage = ttk.LabelFrame(shell, text="  Manage install  ", padding=(12, 10))
        manage.pack(fill=tk.X, pady=(0, 10))
        manage_row = ttk.Frame(manage, style="Panel.TFrame")
        manage_row.pack(fill=tk.X)
        self.to_full_btn = ttk.Button(
            manage_row,
            text="Switch to Full",
            command=lambda: self.run_convert(
                INSTALL_PROFILE_FULL,
                SETUP_BUNDLE_DEFAULT,
                needs_postgres=True,
            ),
        )
        self.to_full_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.to_quick_btn = ttk.Button(
            manage_row,
            text="Switch to Quick",
            command=lambda: self.run_convert(
                INSTALL_PROFILE_BAREBONES,
                SETUP_BUNDLE_DEFAULT,
            ),
        )
        self.to_quick_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.to_enterprise_btn = ttk.Button(
            manage_row,
            text="Switch to Enterprise",
            command=lambda: self.run_convert(
                INSTALL_PROFILE_FULL,
                SETUP_BUNDLE_ENTERPRISE,
                needs_postgres=True,
            ),
        )
        self.to_enterprise_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.to_individual_btn = ttk.Button(
            manage_row,
            text="Switch to Individual",
            command=lambda: self.run_convert(
                INSTALL_PROFILE_FULL,
                SETUP_BUNDLE_DEFAULT,
                needs_postgres=True,
            ),
        )
        self.to_individual_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.uninstall_btn = ttk.Button(
            manage_row,
            text="Uninstall",
            command=self.run_uninstall,
        )
        self.uninstall_btn.pack(side=tk.LEFT)

        log_frame = ttk.LabelFrame(shell, text="  Activity  ", padding=(10, 8))
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log = scrolledtext.ScrolledText(
            log_frame,
            height=16,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=mono_font(root),
        )
        style_log_widget(self.log)
        self.log.pack(fill=tk.BOTH, expand=True)

        self._append_log(f"Workspace: {self.repo}")
        self._sync_repo_ui()
        if updates_check_supported(self.repo):
            self.root.after(400, self.check_updates)

    def _refresh_version(self) -> None:
        version = read_poetry_version(self.repo)
        if is_nimbusware_checkout(self.repo):
            state = read_install_state(self.repo)
            self.version_label.configure(
                text=f"Installed version: {version}  |  {convert_label(state)}",
            )
        else:
            self.version_label.configure(text=f"Installed version: {version}")

    def _sync_repo_ui(self) -> None:
        self._refresh_version()
        installed = is_nimbusware_checkout(self.repo)
        if installed:
            self.status_label.configure(text="Ready.")
        else:
            self.status_label.configure(text="No Nimbusware install found — use Install / setup.")
        if updates_check_supported(self.repo):
            self.check_btn.configure(state=tk.NORMAL)
        else:
            self.check_btn.configure(state=tk.DISABLED)
            if installed and not is_git_checkout(self.repo):
                self._append_log(
                    "Updates: archive install — use Check for updates to connect git.",
                )
        if installed:
            state = read_install_state(self.repo)
            self.to_full_btn.configure(
                state=tk.NORMAL
                if state.install_profile == INSTALL_PROFILE_BAREBONES
                else tk.DISABLED,
            )
            self.to_quick_btn.configure(
                state=tk.NORMAL if state.install_profile == INSTALL_PROFILE_FULL else tk.DISABLED,
            )
            self.to_enterprise_btn.configure(
                state=tk.NORMAL if state.setup_bundle != SETUP_BUNDLE_ENTERPRISE else tk.DISABLED,
            )
            self.to_individual_btn.configure(
                state=tk.NORMAL if state.setup_bundle == SETUP_BUNDLE_ENTERPRISE else tk.DISABLED,
            )
            self.uninstall_btn.configure(state=tk.NORMAL)
        else:
            for btn in (
                self.to_full_btn,
                self.to_quick_btn,
                self.to_enterprise_btn,
                self.to_individual_btn,
                self.uninstall_btn,
            ):
                btn.configure(state=tk.DISABLED)

    def _set_repo(self, repo: Path) -> None:
        self.repo = repo.resolve()
        os.environ["NIMBUSWARE_REPO_ROOT"] = str(self.repo)
        self._append_log(f"Repository: {self.repo}")
        self._sync_repo_ui()

    def _append_log(self, line: str) -> None:
        def _write() -> None:
            self.log.configure(state=tk.NORMAL)
            self.log.insert(tk.END, line + "\n")
            self.log.see(tk.END)
            self.log.configure(state=tk.DISABLED)

        self.root.after(0, _write)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        if busy or updates_check_supported(self.repo):
            self.check_btn.configure(state=state)
        elif not updates_check_supported(self.repo):
            self.check_btn.configure(state=tk.DISABLED)
        for btn in (
            self.install_btn,
            self.install_full_btn,
            self.install_enterprise_btn,
            self.run_btn,
            self.admin_btn,
            self.to_full_btn,
            self.to_quick_btn,
            self.to_enterprise_btn,
            self.to_individual_btn,
            self.uninstall_btn,
        ):
            btn.configure(state=state)
        if not busy:
            self._sync_repo_ui()

    def _run_background(self, label: str, worker: Callable[[], None]) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self.status_label.configure(text=label)

        def _target() -> None:
            try:
                worker()
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        threading.Thread(target=_target, daemon=True).start()

    def _ensure_git_for_updates(self) -> bool:
        if updates_supported(self.repo):
            return True
        if not can_init_git_updates(self.repo):
            messagebox.showerror(
                "Updates unavailable",
                "Install git to receive updates, or run setup from a git clone.",
            )
            return False
        if not messagebox.askyesno(
            "Connect git for updates",
            "This install came from a zip archive and is not a git checkout.\n\n"
            f"Initialize git and connect to {default_clone_url()}?\n\n"
            "Your .env and database data are preserved.",
        ):
            return False

        ok, message = init_git_remote_for_updates(
            self.repo,
            default_clone_url(),
            log=self._append_log,
        )
        self._append_log(message)
        if not ok:
            messagebox.showerror("Git setup failed", message)
            return False
        self._sync_repo_ui()
        messagebox.showinfo("Git ready", message)
        return True

    def check_updates(self) -> None:
        if not updates_check_supported(self.repo):
            messagebox.showinfo(
                "Updates unavailable",
                "Install Nimbusware first, then install git to check for updates.",
            )
            return
        if self._busy:
            return
        self._set_busy(True)
        self.status_label.configure(text="Checking for updates...")

        def _worker() -> None:
            if not updates_supported(self.repo):
                if not can_init_git_updates(self.repo):

                    def _no_git() -> None:
                        messagebox.showerror(
                            "Updates unavailable",
                            "Install git to receive updates.",
                        )
                        self._set_busy(False)

                    self.root.after(0, _no_git)
                    return

                def _offer_init() -> None:
                    if self._ensure_git_for_updates():
                        self._set_busy(False)
                        self.check_updates()
                    else:
                        self._set_busy(False)

                self.root.after(0, _offer_init)
                return

            self._append_log("Checking for updates...")
            status, available, detail = check_for_updates(self.repo, fetch=True)
            self._append_log(detail)

            def _finish() -> None:
                self.status_label.configure(text=f"Updates: {status}")
                if available and messagebox.askyesno(
                    "Update available",
                    f"{detail}\n\nPull the latest code now?\n\n"
                    "Uncommitted local changes may block the pull.",
                ):
                    self._start_pull_updates()
                    return
                if not available and status == "up to date":
                    messagebox.showinfo("No updates", detail)
                self._set_busy(False)

            self.root.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _start_pull_updates(self) -> None:
        self._set_busy(True)
        self.status_label.configure(text="Updating...")

        def _worker() -> None:
            ok, message = git_pull(self.repo, log=self._append_log)
            if ok:
                self.root.after(0, self._refresh_version)
                status, _, detail = check_for_updates(self.repo, fetch=False)

                def _done() -> None:
                    self.status_label.configure(text=f"Updates: {status}")
                    messagebox.showinfo("Update complete", message or detail)
                    self._set_busy(False)

                self.root.after(0, _done)
            else:

                def _failed() -> None:
                    messagebox.showerror("Update failed", message)
                    self._set_busy(False)

                self.root.after(0, _failed)

        threading.Thread(target=_worker, daemon=True).start()

    def _postgres_extra_args(self, *, needs_postgres: bool) -> list[str] | None:
        if not needs_postgres:
            return None
        env = read_env_file(self.repo)
        default_db = env.get(
            "NIMBUSWARE_DATABASE_URL",
            "postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware",
        )
        default_admin = env.get("NIMBUSWARE_POSTGRES_ADMIN_URL", "")
        result = prompt_postgres_setup(
            self.root,
            default_database_url=default_db,
            default_admin_url=default_admin,
        )
        if result is None:
            return None
        extras = postgres_extra_args(
            self.repo,
            database_url=result.database_url,
            admin_url=result.admin_url,
        )
        return extras

    def run_install(
        self,
        profile: str = INSTALL_PROFILE_BAREBONES,
        *,
        setup_bundle: str = SETUP_BUNDLE_DEFAULT,
    ) -> None:
        needs_source = not is_nimbusware_checkout(self.repo)
        clone_target = default_clone_target(self.repo)
        clone_url = default_clone_url()
        full = profile == INSTALL_PROFILE_FULL
        enterprise = setup_bundle == SETUP_BUNDLE_ENTERPRISE
        needs_postgres = full

        if needs_source:
            if enterprise:
                setup_desc = (
                    "Enterprise setup installs Poetry deps, connects to your PostgreSQL "
                    "(application or admin URL), Ollama with default models, and Enterprise env."
                )
            elif full:
                setup_desc = (
                    "Full setup installs Poetry deps, connects to your PostgreSQL "
                    "(application or admin URL), and Ollama with default models."
                )
            else:
                setup_desc = (
                    "Quick setup installs Poetry deps only (barebones profile, no Postgres/Ollama)."
                )
            prompt = (
                "No Nimbusware install was found.\n\n"
                f"Source: {clone_url}\n"
                f"Target: {clone_target}\n\n" + setup_desc
            )
        else:
            if enterprise:
                prompt = (
                    "Run Enterprise Nimbusware setup (Postgres + Ollama + strict env)?\n\n"
                    "Existing database and .env data are preserved."
                )
            elif full:
                prompt = (
                    "Run full Nimbusware setup (Postgres + Ollama)?\n\n"
                    "Existing database and .env data are preserved."
                )
            else:
                prompt = (
                    "Run quick Nimbusware setup (Poetry deps, barebones profile)?\n\n"
                    "Existing database and .env data are preserved."
                )
        if not messagebox.askyesno("Install Nimbusware", prompt):
            return

        extra_args = self._postgres_extra_args(needs_postgres=needs_postgres)
        if needs_postgres and extra_args is None:
            return

        def _worker() -> None:
            repo = self.repo
            if needs_source:
                try:
                    repo = fetch_nimbusware_source(
                        clone_url,
                        clone_target,
                        log=self._append_log,
                    )
                except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
                    message = str(exc)
                    self._append_log(f"ERROR: {message}")
                    self.root.after(
                        0,
                        lambda msg=message: messagebox.showerror("Source fetch failed", msg),
                    )
                    return
                self.root.after(0, lambda: self._set_repo(repo))

            label = "full" if full else "quick"
            self._append_log(f"Running {label} Nimbusware setup...")
            try:
                code = run_install_script(
                    repo,
                    profile=profile,
                    setup_bundle=setup_bundle,
                    extra_args=extra_args,
                    log=self._append_log,
                )
            except FileNotFoundError as exc:
                message = str(exc)
                self._append_log(message)
                self.root.after(
                    0,
                    lambda msg=message: messagebox.showerror("Install failed", msg),
                )
                return
            if code == 0:
                self.root.after(0, self._sync_repo_ui)
                self.root.after(
                    0,
                    lambda: messagebox.showinfo("Install complete", "Setup finished successfully."),
                )
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Install failed", f"Exit code {code}"),
                )

        self._run_background("Installing...", _worker)

    def run_convert(
        self,
        profile: str,
        setup_bundle: str,
        *,
        needs_postgres: bool = False,
    ) -> None:
        if not is_nimbusware_checkout(self.repo):
            messagebox.showerror("Convert failed", "Install Nimbusware before converting.")
            return
        state = read_install_state(self.repo)
        target = InstallState(
            install_profile=profile,
            setup_bundle=setup_bundle,
            edition="enterprise" if setup_bundle == SETUP_BUNDLE_ENTERPRISE else "individual",
            database_url=state.database_url,
        )
        target_label = convert_label(target)
        prompt = (
            f"Switch from {convert_label(state)} to {target_label}?\n\n"
            "This re-runs setup for the selected profile and bundle.\n"
            "Your database, .env, and Ollama models are preserved."
        )
        if not messagebox.askyesno("Convert install", prompt):
            return

        extra_args = self._postgres_extra_args(needs_postgres=needs_postgres)
        if needs_postgres and extra_args is None:
            return

        def _worker() -> None:
            self._append_log(f"Converting install to {target_label}...")
            try:
                code = run_convert_install(
                    self.repo,
                    profile=profile,
                    setup_bundle=setup_bundle,
                    extra_args=extra_args,
                    log=self._append_log,
                )
            except FileNotFoundError as exc:
                message = str(exc)
                self._append_log(message)
                self.root.after(
                    0,
                    lambda msg=message: messagebox.showerror("Convert failed", msg),
                )
                return
            if code == 0:
                self.root.after(0, self._sync_repo_ui)
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Convert complete", "Install updated successfully."
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Convert failed", f"Exit code {code}"),
                )

        self._run_background("Converting...", _worker)

    def run_uninstall(self) -> None:
        if not is_nimbusware_checkout(self.repo):
            messagebox.showerror("Uninstall failed", "No Nimbusware install found.")
            return
        if not messagebox.askyesno(
            "Uninstall Nimbusware",
            "Remove the Python virtualenv and Poetry environment?\n\n"
            "Your .env, PostgreSQL data, and Ollama models are preserved.\n"
            "Re-run any setup button to reinstall dependencies.",
        ):
            return

        def _worker() -> None:
            try:
                uninstall_nimbusware(self.repo, log=self._append_log)
            except OSError as exc:
                message = str(exc)
                self._append_log(f"ERROR: {message}")
                self.root.after(
                    0,
                    lambda msg=message: messagebox.showerror("Uninstall failed", msg),
                )
                return
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Uninstall complete",
                    "Python environment removed. User data preserved.",
                ),
            )

        self._run_background("Uninstalling...", _worker)

    def run_nimbusware(self) -> None:
        run_py = self.repo / "run.py"
        if not run_py.is_file():
            messagebox.showerror("Run failed", f"Missing {run_py}")
            return
        try:
            cmd = [*resolve_python_command(self.repo), str(run_py)]
        except FileNotFoundError as exc:
            messagebox.showerror("Run failed", str(exc))
            self._append_log(f"ERROR: {exc}")
            return

        log_file = run_log_path(self.repo)
        self._append_log(f"$ {' '.join(cmd)}")
        self._append_log(f"Run log: {log_file}")
        env = os.environ.copy()
        env.setdefault("NIMBUSWARE_REPO_ROOT", str(self.repo))
        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                cwd=str(self.repo),
                env=env,
                **subprocess_spawn_kwargs(detach=True, hide_window=False),
            )
        except OSError as exc:
            messagebox.showerror("Run failed", str(exc))
            return

        def _watch() -> None:
            time.sleep(4.0)
            if proc.poll() is None:
                return
            tail = ""
            if log_file.is_file():
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                tail = "\n".join(lines[-12:])
            detail = tail or f"Process exited immediately (code {proc.returncode})."
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Nimbusware did not start",
                    "The desktop run exited before opening a window.\n\n"
                    f"{detail}\n\nFull log:\n{log_file}",
                ),
            )
            self.root.after(
                0, lambda: self._append_log(f"ERROR: run.py exited (code {proc.returncode})")
            )

        threading.Thread(target=_watch, daemon=True).start()
        self.status_label.configure(text="Starting Nimbusware...")
        self._append_log("Starting Nimbusware (maker app + desktop window)...")

    def run_admin_console(self) -> None:
        run_py = self.repo / "run.py"
        if not run_py.is_file():
            messagebox.showerror("Run failed", f"Missing {run_py}")
            return
        if not messagebox.askyesno(
            "Admin Console",
            "Open the Admin Console?\n\nYou will need your admin token to sign in.",
        ):
            return
        try:
            cmd = [*resolve_python_command(self.repo), str(run_py), "--admin"]
        except FileNotFoundError as exc:
            messagebox.showerror("Run failed", str(exc))
            return
        env = os.environ.copy()
        env.setdefault("NIMBUSWARE_REPO_ROOT", str(self.repo))
        try:
            subprocess.Popen(  # noqa: S603
                cmd,
                cwd=str(self.repo),
                env=env,
                **subprocess_spawn_kwargs(detach=True, hide_window=False),
            )
        except OSError as exc:
            messagebox.showerror("Run failed", str(exc))
            return
        self._append_log(f"$ {' '.join(cmd)}")
        self.status_label.configure(text="Starting Admin Console...")


def main() -> int:
    root = tk.Tk()
    root.configure(bg=BG)
    NimbuswareLauncherApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
