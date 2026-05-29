"""Tkinter desktop launcher: install, update, and run Hermes."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, scrolledtext, ttk

from hermes_env.desktop_common import (
    check_for_updates,
    default_install_script_args,
    git_pull,
    read_poetry_version,
    repo_root,
    resolve_python_command,
    run_script,
    subprocess_spawn_kwargs,
    ui_mono_font,
    ui_title_font,
)


class HermesLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.repo = repo_root()
        self._busy = False
        self._updates_available = False

        root.title("Hermes")
        root.geometry("640x520")
        root.minsize(520, 420)

        header = ttk.Frame(root, padding=12)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Hermes", font=ui_title_font()).pack(anchor=tk.W)
        self.version_label = ttk.Label(header, text="")
        self.version_label.pack(anchor=tk.W, pady=(4, 0))
        self.status_label = ttk.Label(header, text="Ready.")
        self.status_label.pack(anchor=tk.W, pady=(4, 0))

        buttons = ttk.Frame(root, padding=(12, 0))
        buttons.pack(fill=tk.X)
        self.check_btn = ttk.Button(buttons, text="Check for updates", command=self.check_updates)
        self.check_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.update_btn = ttk.Button(
            buttons,
            text="Update (git pull)",
            command=self.apply_update,
            state=tk.DISABLED,
        )
        self.update_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.install_btn = ttk.Button(buttons, text="Install / setup", command=self.run_install)
        self.install_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.run_btn = ttk.Button(buttons, text="Run Hermes", command=self.run_hermes)
        self.run_btn.pack(side=tk.LEFT)

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

        self._refresh_version()
        self._append_log(f"Repository: {self.repo}")
        self.root.after(400, self.check_updates)

    def _refresh_version(self) -> None:
        version = read_poetry_version(self.repo)
        self.version_label.configure(text=f"Installed version: {version}")

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
        self.check_btn.configure(state=state)
        self.install_btn.configure(state=state)
        self.run_btn.configure(state=state)
        if busy:
            self.update_btn.configure(state=tk.DISABLED)
        else:
            self.update_btn.configure(
                state=tk.NORMAL if self._updates_available else tk.DISABLED,
            )

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
        def _worker() -> None:
            self._append_log("Checking for updates...")
            status, available, detail = check_for_updates(self.repo, fetch=True)
            self._updates_available = available

            def _finish() -> None:
                self.status_label.configure(text=f"Updates: {status}")
                self.update_btn.configure(state=tk.NORMAL if available else tk.DISABLED)
                self._append_log(detail)

            self.root.after(0, _finish)

        self._run_background("Checking for updates...", _worker)

    def apply_update(self) -> None:
        if not self._updates_available:
            return
        if not messagebox.askyesno(
            "Update Hermes",
            "Pull the latest code from git?\n\nUncommitted local changes may block the pull.",
        ):
            return

        def _worker() -> None:
            ok, message = git_pull(self.repo, log=self._append_log)
            if ok:
                self._updates_available = False
                self.root.after(0, self._refresh_version)
                status, available, detail = check_for_updates(self.repo, fetch=False)
                self._updates_available = available

                def _done() -> None:
                    self.status_label.configure(text=f"Updates: {status}")
                    self.update_btn.configure(state=tk.NORMAL if available else tk.DISABLED)
                    messagebox.showinfo("Update complete", message or "Updated.")

                self.root.after(0, _done)
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Update failed", message),
                )

        self._run_background("Updating...", _worker)

    def run_install(self) -> None:
        if not messagebox.askyesno(
            "Install Hermes",
            "Run the Hermes setup script?\n\n"
            "This installs Poetry dependencies and bootstraps PostgreSQL (Docker when available).",
        ):
            return

        def _worker() -> None:
            try:
                code = run_script(
                    self.repo,
                    "scripts/install_hermes.py",
                    *default_install_script_args(),
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

    def run_hermes(self) -> None:
        run_py = self.repo / "run.py"
        if not run_py.is_file():
            messagebox.showerror("Run failed", f"Missing {run_py}")
            return
        cmd = [*resolve_python_command(self.repo), str(run_py)]
        self._append_log(f"$ {' '.join(cmd)}")
        env = os.environ.copy()
        env.setdefault("HERMES_REPO_ROOT", str(self.repo))
        try:
            subprocess.Popen(  # noqa: S603
                cmd,
                cwd=str(self.repo),
                env=env,
                **subprocess_spawn_kwargs(detach=True),
            )
        except OSError as exc:
            messagebox.showerror("Run failed", str(exc))
            return
        self.status_label.configure(text="Hermes is running in a separate window.")
        self._append_log("Started Hermes (API + console window).")


def main() -> int:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista" if sys.platform == "win32" else "default")
    except tk.TclError:
        pass
    HermesLauncherApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
