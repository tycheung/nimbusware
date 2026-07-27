from __future__ import annotations

import os
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

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
    active_setup_card_key,
    convert_label,
    format_install_summary,
    postgres_extra_args,
    read_env_file,
    read_install_state,
    run_convert_install,
    uninstall_nimbusware,
)
from env.launcher_theme import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_SOFT,
    BG,
    BG_CARD,
    BG_CARD_HOVER,
    BG_INPUT,
    BG_RAISED,
    BG_STATUS,
    BORDER,
    CTA_BG,
    CTA_FG,
    CTA_HOVER,
    DANGER,
    DANGER_HOVER,
    OK,
    RADIUS,
    RADIUS_SM,
    TEXT,
    TEXT_MUTED,
    TEXT_SOFT,
    WARN,
    LauncherTheme,
    apply_launcher_theme,
    mono_font,
    ui_font,
)
from env.swissarmynoife_install import (
    default_swissarmynoife_target,
    ensure_swissarmynoife,
)


def _state(enabled: bool) -> str:
    return "normal" if enabled else "disabled"


@dataclass
class _SetupCard:
    key: str
    frame: ctk.CTkFrame
    badge: ctk.CTkLabel
    button: ctk.CTkButton
    idle_badge: str


class NimbuswareLauncherApp:
    def __init__(self, root: ctk.CTk, theme: LauncherTheme) -> None:
        self.root = root
        self.repo = repo_root()
        self._busy = False
        self._manage_open = False
        self.theme = theme
        self._logo = theme.logo
        self.product_version = read_poetry_version(self.repo)
        self.install_state: InstallState | None = None
        self._checkout_present = False
        self._setup_cards: dict[str, _SetupCard] = {}

        root.title("Nimbusware")
        root.geometry("920x740")
        root.minsize(800, 640)

        shell = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
        shell.pack(fill="both", expand=True, padx=28, pady=24)

        self._build_header(shell)
        self._build_hero(shell)
        self._build_setup_cards(shell)
        self._build_manage(shell)
        self._build_activity(shell)

        self._append_log(f"Workspace: {self.repo}")
        self._reload_and_render_install_state()
        if updates_check_supported(self.repo):
            self.root.after(400, self.check_updates)

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        if self._logo is not None:
            ctk.CTkLabel(left, text="", image=self._logo).pack(side="left", padx=(0, 14))

        titles = ctk.CTkFrame(left, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(
            titles,
            text="Nimbusware",
            font=ui_font(size=26, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles,
            text="Local-first agentic platform",
            font=ui_font(size=13),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))
        self.version_label = ctk.CTkLabel(
            titles,
            text="",
            font=ui_font(size=12),
            text_color=TEXT_SOFT,
        )
        self.version_label.pack(anchor="w", pady=(8, 0))

        self.status_label = ctk.CTkLabel(
            header,
            text="Ready",
            font=ui_font(size=12, weight="bold"),
            text_color=OK,
            fg_color=BG_STATUS,
            corner_radius=RADIUS_SM,
            height=28,
            width=120,
        )
        self.status_label.pack(side="right", anchor="n")

    def _build_hero(self, parent: ctk.CTkFrame) -> None:
        hero = ctk.CTkFrame(
            parent,
            fg_color=BG_CARD,
            corner_radius=RADIUS,
            border_width=1,
            border_color=BORDER,
        )
        hero.pack(fill="x", pady=(0, 16))
        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)

        copy = ctk.CTkFrame(inner, fg_color="transparent")
        copy.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(
            copy,
            text="Open Maker",
            font=ui_font(size=18, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            copy,
            text="Launch the desktop app for this install — API, Maker UI, and local broker.",
            font=ui_font(size=13),
            text_color=TEXT_MUTED,
            wraplength=480,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(side="right", padx=(16, 0))
        self.run_btn = ctk.CTkButton(
            actions,
            text="Run Nimbusware",
            command=self.run_nimbusware,
            font=ui_font(size=14, weight="bold"),
            fg_color=CTA_BG,
            hover_color=CTA_HOVER,
            text_color=CTA_FG,
            corner_radius=RADIUS_SM,
            height=42,
            width=168,
        )
        self.run_btn.pack(anchor="e")
        self.admin_btn = ctk.CTkButton(
            actions,
            text="Admin Console",
            command=self.run_admin_console,
            font=ui_font(size=13),
            fg_color=ACCENT_SOFT,
            hover_color=ACCENT,
            text_color=TEXT,
            corner_radius=RADIUS_SM,
            height=36,
            width=168,
        )
        self.admin_btn.pack(anchor="e", pady=(10, 0))

    def _build_setup_cards(self, parent: ctk.CTkFrame) -> None:
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            section,
            text="Setup",
            font=ui_font(size=12, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w")
        ctk.CTkLabel(
            section,
            text="Pick a path. Quick is the usual first run.",
            font=ui_font(size=12),
            text_color=TEXT_SOFT,
        ).pack(anchor="w", pady=(2, 10))

        row = ctk.CTkFrame(section, fg_color="transparent")
        row.pack(fill="x")
        row.grid_columnconfigure((0, 1, 2), weight=1, uniform="setup")

        self.install_btn = self._setup_card(
            row,
            key="quick",
            column=0,
            title="Quick",
            badge="Recommended",
            body="Poetry deps + broker. No Postgres or Ollama required.",
            button="Install Quick",
            command=lambda: self.run_install(
                INSTALL_PROFILE_BAREBONES,
                setup_bundle=SETUP_BUNDLE_DEFAULT,
            ),
        )
        self.install_full_btn = self._setup_card(
            row,
            key="full",
            column=1,
            title="Full",
            badge="Local stack",
            body="Adds PostgreSQL connection and Ollama when available.",
            button="Install Full",
            command=lambda: self.run_install(
                INSTALL_PROFILE_FULL,
                setup_bundle=SETUP_BUNDLE_DEFAULT,
            ),
        )
        self.install_enterprise_btn = self._setup_card(
            row,
            key="enterprise",
            column=2,
            title="Enterprise",
            badge="Fleet",
            body="Full setup plus enterprise edition defaults and seeds.",
            button="Install Enterprise",
            command=lambda: self.run_install(
                INSTALL_PROFILE_FULL,
                setup_bundle=SETUP_BUNDLE_ENTERPRISE,
            ),
        )

        tools = ctk.CTkFrame(section, fg_color="transparent")
        tools.pack(fill="x", pady=(12, 0))
        self.check_btn = ctk.CTkButton(
            tools,
            text="Check for updates",
            command=self.check_updates,
            font=ui_font(size=13),
            fg_color="transparent",
            hover_color=BG_CARD_HOVER,
            text_color=TEXT_MUTED,
            border_width=1,
            border_color=BORDER,
            corner_radius=RADIUS_SM,
            height=34,
            width=150,
        )
        self.check_btn.pack(side="left")

    def _setup_card(
        self,
        parent: ctk.CTkFrame,
        *,
        key: str,
        column: int,
        title: str,
        badge: str,
        body: str,
        button: str,
        command: Callable[[], None],
    ) -> ctk.CTkButton:
        card = ctk.CTkFrame(
            parent,
            fg_color=BG_CARD,
            corner_radius=RADIUS,
            border_width=1,
            border_color=BORDER,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=16, pady=16)
        badge_label = ctk.CTkLabel(
            pad,
            text=badge.upper(),
            font=ui_font(size=10, weight="bold"),
            text_color=TEXT_MUTED,
        )
        badge_label.pack(anchor="w")
        ctk.CTkLabel(
            pad,
            text=title,
            font=ui_font(size=17, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(
            pad,
            text=body,
            font=ui_font(size=12),
            text_color=TEXT_MUTED,
            wraplength=220,
            justify="left",
        ).pack(anchor="w", pady=(8, 14))
        btn = ctk.CTkButton(
            pad,
            text=button,
            command=command,
            font=ui_font(size=13),
            fg_color=ACCENT_SOFT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT,
            corner_radius=RADIUS_SM,
            height=36,
        )
        btn.pack(anchor="w", fill="x")
        self._setup_cards[key] = _SetupCard(
            key=key,
            frame=card,
            badge=badge_label,
            button=btn,
            idle_badge=badge.upper(),
        )
        return btn

    def _set_status(self, text: str, *, tone: str = "info") -> None:
        colors = {
            "ok": OK,
            "warn": WARN,
            "info": ACCENT,
        }
        self.status_label.configure(text=text, text_color=colors.get(tone, ACCENT))

    def _reload_install_state(self) -> None:
        """Re-read version + .env into the live state vars (source of truth for the UI)."""
        self.product_version = read_poetry_version(self.repo)
        self._checkout_present = is_nimbusware_checkout(self.repo)
        self.install_state = (
            read_install_state(self.repo) if self._checkout_present else None
        )

    def _render_install_state(self) -> None:
        """Paint header, manage buttons, and setup cards from ``self.install_state``."""
        summary = format_install_summary(
            self.product_version,
            self.install_state,
            installed=self._checkout_present,
        )
        self.version_label.configure(text=summary)
        if self._checkout_present:
            self._set_status("Ready", tone="ok")
        else:
            self._set_status("Setup needed", tone="warn")

        active = active_setup_card_key(
            self.install_state,
            installed=self._checkout_present,
        )
        for key, card in self._setup_cards.items():
            is_active = key == active
            card.frame.configure(
                fg_color=BG_RAISED if is_active else BG_CARD,
                border_color=ACCENT if is_active else BORDER,
            )
            card.badge.configure(
                text="CURRENT" if is_active else card.idle_badge,
                text_color=ACCENT if is_active else TEXT_MUTED,
            )
            card.button.configure(
                fg_color=CTA_BG if is_active else ACCENT_SOFT,
                hover_color=CTA_HOVER if is_active else ACCENT_HOVER,
                text_color=CTA_FG if is_active else TEXT,
                font=ui_font(size=13, weight="bold" if is_active else "normal"),
            )

        if updates_check_supported(self.repo):
            self.check_btn.configure(state="normal")
        else:
            self.check_btn.configure(state="disabled")

        state = self.install_state
        if self._checkout_present and state is not None:
            self.to_full_btn.configure(
                state=_state(state.install_profile == INSTALL_PROFILE_BAREBONES),
            )
            self.to_quick_btn.configure(
                state=_state(state.install_profile == INSTALL_PROFILE_FULL),
            )
            self.to_enterprise_btn.configure(
                state=_state(state.setup_bundle != SETUP_BUNDLE_ENTERPRISE),
            )
            self.to_individual_btn.configure(
                state=_state(state.setup_bundle == SETUP_BUNDLE_ENTERPRISE),
            )
            self.uninstall_btn.configure(state="normal")
            self.run_btn.configure(state="normal")
            self.admin_btn.configure(state="normal")
        else:
            for btn in (
                self.to_full_btn,
                self.to_quick_btn,
                self.to_enterprise_btn,
                self.to_individual_btn,
                self.uninstall_btn,
            ):
                btn.configure(state="disabled")

    def _reload_and_render_install_state(self) -> None:
        self._reload_install_state()
        self._render_install_state()
        try:
            self.root.update_idletasks()
        except Exception:
            pass

    def _finish_setup_success(self, *, title: str, detail: str) -> None:
        """Main-thread: reload state from disk, render, then show completion dialog."""
        self._reload_and_render_install_state()
        current = (
            convert_label(self.install_state)
            if self.install_state is not None
            else "not installed"
        )
        messagebox.showinfo(title, f"{detail}\n\nCurrent setup: {current}")
        self._reload_and_render_install_state()

    def _refresh_version(self) -> None:
        self._reload_and_render_install_state()

    def _sync_repo_ui(self) -> None:
        self._reload_and_render_install_state()

    def _build_manage(self, parent: ctk.CTkFrame) -> None:
        self.manage_shell = ctk.CTkFrame(parent, fg_color="transparent")
        self.manage_shell.pack(fill="x", pady=(0, 12))
        self.manage_toggle = ctk.CTkButton(
            self.manage_shell,
            text="Manage install  ›",
            command=self._toggle_manage,
            font=ui_font(size=12, weight="bold"),
            fg_color="transparent",
            hover_color=BG_CARD,
            text_color=TEXT_MUTED,
            anchor="w",
            height=28,
        )
        self.manage_toggle.pack(fill="x")

        self.manage_body = ctk.CTkFrame(
            self.manage_shell,
            fg_color=BG_CARD,
            corner_radius=RADIUS,
            border_width=1,
            border_color=BORDER,
        )
        inner = ctk.CTkFrame(self.manage_body, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")

        def ghost(text: str, command: Callable[[], None]) -> ctk.CTkButton:
            return ctk.CTkButton(
                row,
                text=text,
                command=command,
                font=ui_font(size=12),
                fg_color=BG_RAISED,
                hover_color=BG_CARD_HOVER,
                text_color=TEXT_SOFT,
                corner_radius=RADIUS_SM,
                height=32,
                width=132,
            )

        self.to_full_btn = ghost(
            "Switch to Full",
            lambda: self.run_convert(
                INSTALL_PROFILE_FULL,
                SETUP_BUNDLE_DEFAULT,
                needs_postgres=True,
            ),
        )
        self.to_full_btn.pack(side="left", padx=(0, 8))
        self.to_quick_btn = ghost(
            "Switch to Quick",
            lambda: self.run_convert(
                INSTALL_PROFILE_BAREBONES,
                SETUP_BUNDLE_DEFAULT,
            ),
        )
        self.to_quick_btn.pack(side="left", padx=(0, 8))
        self.to_enterprise_btn = ghost(
            "Switch to Enterprise",
            lambda: self.run_convert(
                INSTALL_PROFILE_FULL,
                SETUP_BUNDLE_ENTERPRISE,
                needs_postgres=True,
            ),
        )
        self.to_enterprise_btn.pack(side="left", padx=(0, 8))
        self.to_individual_btn = ghost(
            "Switch to Individual",
            lambda: self.run_convert(
                INSTALL_PROFILE_FULL,
                SETUP_BUNDLE_DEFAULT,
                needs_postgres=True,
            ),
        )
        self.to_individual_btn.pack(side="left", padx=(0, 8))
        self.uninstall_btn = ctk.CTkButton(
            row,
            text="Uninstall",
            command=self.run_uninstall,
            font=ui_font(size=12),
            fg_color=DANGER,
            hover_color=DANGER_HOVER,
            text_color=TEXT,
            corner_radius=RADIUS_SM,
            height=32,
            width=100,
        )
        self.uninstall_btn.pack(side="right")

    def _toggle_manage(self) -> None:
        self._manage_open = not self._manage_open
        if self._manage_open:
            self.manage_body.pack(fill="x", pady=(6, 0))
            self.manage_toggle.configure(text="Manage install  ˅")
        else:
            self.manage_body.pack_forget()
            self.manage_toggle.configure(text="Manage install  ›")

    def _build_activity(self, parent: ctk.CTkFrame) -> None:
        section = ctk.CTkFrame(
            parent,
            fg_color=BG_CARD,
            corner_radius=RADIUS,
            border_width=1,
            border_color=BORDER,
        )
        section.pack(fill="both", expand=True)
        head = ctk.CTkFrame(section, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(
            head,
            text="Activity",
            font=ui_font(size=12, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(side="left")
        self.log = ctk.CTkTextbox(
            section,
            font=mono_font(size=12),
            fg_color=BG_INPUT,
            text_color=TEXT_SOFT,
            corner_radius=RADIUS_SM,
            border_width=0,
            wrap="word",
            activate_scrollbars=True,
        )
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log.configure(state="disabled")

    def _set_repo(self, repo: Path) -> None:
        self.repo = repo.resolve()
        os.environ["NIMBUSWARE_REPO_ROOT"] = str(self.repo)
        self._append_log(f"Repository: {self.repo}")
        self._sync_repo_ui()

    def _append_log(self, line: str) -> None:
        def _write() -> None:
            self.log.configure(state="normal")
            self.log.insert("end", line + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")

        self.root.after(0, _write)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = _state(not busy)
        if busy or updates_check_supported(self.repo):
            self.check_btn.configure(state=state)
        elif not updates_check_supported(self.repo):
            self.check_btn.configure(state="disabled")
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
        self._set_status(label, tone="info")

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
        self._set_status("Checking for updates...", tone="info")

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
                self._set_status(f"Updates: {status}", tone="info")
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
        self._set_status("Updating...", tone="info")

        def _worker() -> None:
            ok, message = git_pull(self.repo, log=self._append_log)
            sak_note = ""
            if ok:
                try:
                    sak = ensure_swissarmynoife(
                        self.repo,
                        target=default_swissarmynoife_target(self.repo),
                        skip_build=False,
                        log=self._append_log,
                    )
                    sak_note = f"\n\nSwissArmyNoife updated at:\n{sak}"
                except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
                    sak_note = f"\n\nSwissArmyNoife update skipped: {exc}"
                self.root.after(0, self._refresh_version)
                status, _, detail = check_for_updates(self.repo, fetch=False)

                def _done() -> None:
                    self._set_status(f"Updates: {status}", tone="ok")
                    messagebox.showinfo(
                        "Update complete",
                        (message or detail) + sak_note,
                    )
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
                    "Enterprise setup installs Poetry deps, PostgreSQL connection, Ollama, "
                    "Enterprise env, and the SwissArmyNoife capability broker (sibling checkout)."
                )
            elif full:
                setup_desc = (
                    "Full setup installs Poetry deps, PostgreSQL connection, Ollama, "
                    "and the SwissArmyNoife capability broker (sibling checkout)."
                )
            else:
                setup_desc = (
                    "Quick setup installs Poetry deps (barebones profile, no Postgres/Ollama) "
                    "and the SwissArmyNoife capability broker beside Nimbusware."
                )
            prompt = (
                "No Nimbusware install was found.\n\n"
                f"Source: {clone_url}\n"
                f"Target: {clone_target}\n\n" + setup_desc
            )
        else:
            if enterprise:
                prompt = (
                    "Run Enterprise Nimbusware setup (Postgres + Ollama + strict env + "
                    "SwissArmyNoife broker)?\n\n"
                    "Existing database and .env data are preserved."
                )
            elif full:
                prompt = (
                    "Run full Nimbusware setup (Postgres + Ollama + SwissArmyNoife broker)?\n\n"
                    "Existing database and .env data are preserved."
                )
            else:
                prompt = (
                    "Run quick Nimbusware setup (Poetry deps + SwissArmyNoife broker)?\n\n"
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
                self.root.after(
                    0,
                    lambda: self._finish_setup_success(
                        title="Install complete",
                        detail="Setup finished successfully.",
                    ),
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
                self.root.after(
                    0,
                    lambda: self._finish_setup_success(
                        title="Convert complete",
                        detail="Install updated successfully.",
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

            def _done() -> None:
                self._finish_setup_success(
                    title="Uninstall complete",
                    detail=(
                        "Python environment removed. User data preserved.\n"
                        "Re-run Quick / Full / Enterprise setup to recreate the venv."
                    ),
                )

            self.root.after(0, _done)

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
        self._set_status("Starting Nimbusware...", tone="info")
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
        self._set_status("Starting Admin Console...", tone="info")


def main() -> int:
    root, theme = apply_launcher_theme()
    NimbuswareLauncherApp(root, theme)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
