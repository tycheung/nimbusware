from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from nimbusware_env.desktop_common import (
    check_for_updates,
    default_clone_target,
    default_clone_url,
    git_pull,
    is_git_checkout,
    is_nimbusware_checkout,
    read_poetry_version,
    repo_root,
    resolve_python_command,
    run_log_path,
    subprocess_spawn_kwargs,
    ui_mono_font,
    ui_title_font,
    updates_supported,
)
from nimbusware_env.launcher_fetch import (
    INSTALL_PROFILE_BAREBONES,
    INSTALL_PROFILE_FULL,
    SETUP_BUNDLE_DEFAULT,
    SETUP_BUNDLE_ENTERPRISE,
    fetch_nimbusware_source,
    run_install_script,
)


class NimbuswareLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.repo = repo_root()
        self._busy = False

        root.title("Nimbusware")
        root.geometry("640x520")
        root.minsize(520, 420)

        header = ttk.Frame(root, padding=12)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Nimbusware", font=ui_title_font()).pack(anchor=tk.W)
        self.version_label = ttk.Label(header, text="")
        self.version_label.pack(anchor=tk.W, pady=(4, 0))
        self.status_label = ttk.Label(header, text="Ready.")
        self.status_label.pack(anchor=tk.W, pady=(4, 0))

        buttons = ttk.Frame(root, padding=(12, 0))
        buttons.pack(fill=tk.X)
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
        self.run_btn = ttk.Button(buttons, text="Run Nimbusware", command=self.run_nimbusware)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.admin_btn = ttk.Button(
            buttons,
            text="Admin Console…",
            command=self.run_admin_console,
        )
        self.admin_btn.pack(side=tk.LEFT)

        log_frame = ttk.LabelFrame(root, text="Activity", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.log = scrolledtext.ScrolledText(
            log_frame,
            height=16,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=ui_mono_font(),
        )
        self.log.pack(fill=tk.BOTH, expand=True)

        self._append_log(f"Workspace: {self.repo}")
        self._sync_repo_ui()
        if updates_supported(self.repo):
            self.root.after(400, self.check_updates)

    def _refresh_version(self) -> None:
        version = read_poetry_version(self.repo)
        self.version_label.configure(text=f"Installed version: {version}")

    def _sync_repo_ui(self) -> None:
        self._refresh_version()
        if is_nimbusware_checkout(self.repo):
            self.status_label.configure(text="Ready.")
        else:
            self.status_label.configure(text="No Nimbusware install found — use Install / setup.")
        if updates_supported(self.repo):
            self.check_btn.configure(state=tk.NORMAL)
        else:
            self.check_btn.configure(state=tk.DISABLED)
            if not is_git_checkout(self.repo):
                self._append_log(
                    "Updates disabled: no git checkout (clone first via Install / setup)."
                )

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
        if busy or updates_supported(self.repo):
            self.check_btn.configure(state=state)
        else:
            self.check_btn.configure(state=tk.DISABLED)
        self.install_btn.configure(state=state)
        self.install_full_btn.configure(state=state)
        self.install_enterprise_btn.configure(state=state)
        self.run_btn.configure(state=state)
        self.admin_btn.configure(state=state)

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

    def check_updates(self) -> None:
        if not updates_supported(self.repo):
            return
        if self._busy:
            return
        self._set_busy(True)
        self.status_label.configure(text="Checking for updates...")

        def _worker() -> None:
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

        if needs_source:
            if enterprise:
                setup_desc = (
                    "Enterprise setup installs Poetry deps, Docker Postgres when available, "
                    "Ollama with default models, and Enterprise strict env defaults."
                )
            elif full:
                setup_desc = (
                    "Full setup installs Poetry deps, Docker Postgres when available, "
                    "and Ollama with default models."
                )
            else:
                setup_desc = (
                    "Quick setup installs Poetry deps only (barebones profile, no Postgres/Ollama)."
                )
            prompt = (
                "No Nimbusware install was found.\n\n"
                f"Source: {clone_url}\n"
                f"Target: {clone_target}\n\n"
                + setup_desc
            )
        else:
            if enterprise:
                prompt = "Run Enterprise Nimbusware setup (Postgres + Ollama + strict env)?"
            elif full:
                prompt = "Run full Nimbusware setup (Postgres + Ollama)?"
            else:
                prompt = "Run quick Nimbusware setup (Poetry deps, barebones profile)?"
        if not messagebox.askyesno("Install Nimbusware", prompt):
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
    try:
        ttk.Style().theme_use("vista" if sys.platform == "win32" else "default")
    except tk.TclError:
        pass
    NimbuswareLauncherApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
