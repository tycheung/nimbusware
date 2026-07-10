"""Tkinter dialogs used by the desktop launcher."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from env.launcher_theme import style_dialog

DEFAULT_DATABASE_URL = "postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware"


@dataclass(frozen=True)
class PostgresDialogResult:
    database_url: str
    admin_url: str
    skipped: bool = False


class PostgresSetupDialog(tk.Toplevel):
    """Collect an application or admin PostgreSQL URL for Full / Enterprise setup."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        default_database_url: str = DEFAULT_DATABASE_URL,
        default_admin_url: str = "",
    ) -> None:
        super().__init__(parent)
        self.title("PostgreSQL connection")
        self.resizable(False, False)
        self.result: PostgresDialogResult | None = None
        style_dialog(self)

        frame = ttk.Frame(self, padding=16, style="Dialog.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="PostgreSQL for Full / Enterprise setup",
            style="Dialog.TLabel",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(
            frame,
            text=(
                "Use an application URL if the nimbusware database already exists,\n"
                "or an admin URL (superuser) to create the role and database."
            ),
            style="DialogMuted.TLabel",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 12))

        ttk.Label(frame, text="Application database URL", style="Dialog.TLabel").pack(anchor=tk.W)
        self.database_var = tk.StringVar(value=default_database_url)
        db_entry = ttk.Entry(frame, textvariable=self.database_var, width=72, style="Dialog.TEntry")
        db_entry.pack(fill=tk.X, pady=(4, 10))

        ttk.Label(frame, text="Admin URL (optional)", style="Dialog.TLabel").pack(anchor=tk.W)
        self.admin_var = tk.StringVar(value=default_admin_url)
        ttk.Entry(frame, textvariable=self.admin_var, width=72, style="Dialog.TEntry").pack(
            fill=tk.X,
            pady=(4, 8),
        )

        ttk.Label(
            frame,
            text="Example: postgresql://postgres:secret@dbhost:5432/postgres",
            style="DialogMuted.TLabel",
        ).pack(anchor=tk.W, pady=(0, 12))

        buttons = ttk.Frame(frame, style="Dialog.TFrame")
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Continue", style="Accent.TButton", command=self._ok).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_visibility()
        db_entry.focus_set()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def _ok(self) -> None:
        database_url = self.database_var.get().strip()
        admin_url = self.admin_var.get().strip()
        if not database_url and not admin_url:
            return
        self.result = PostgresDialogResult(
            database_url=database_url or DEFAULT_DATABASE_URL,
            admin_url=admin_url,
        )
        self.destroy()


def prompt_postgres_setup(
    parent: tk.Misc,
    *,
    default_database_url: str = DEFAULT_DATABASE_URL,
    default_admin_url: str = "",
) -> PostgresDialogResult | None:
    dialog = PostgresSetupDialog(
        parent,
        default_database_url=default_database_url,
        default_admin_url=default_admin_url,
    )
    parent.wait_window(dialog)
    return dialog.result
