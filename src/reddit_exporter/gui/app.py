from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from reddit_exporter.config import load_config
from reddit_exporter.core.app_service import ExporterService
from reddit_exporter.core.credentials import CredentialStore, SessionOnlyCredentialStore
from reddit_exporter.core.exporters import export_snapshot
from reddit_exporter.core.subscriptions import filter_subscriptions
from reddit_exporter.gui.dialogs import ScriptLoginDialog
from reddit_exporter.gui.workers import WorkerRunner
from reddit_exporter.models import SubscriptionSnapshot

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class GuiState:
    snapshot: SubscriptionSnapshot | None = None
    filtered_count: int = 0


class ExporterGui(tk.Tk):
    def __init__(self, service: ExporterService):
        super().__init__()
        self.title("Reddit Subreddit Exporter")
        self.geometry("780x540")
        self.service = service
        self.worker = WorkerRunner()
        self.state = GuiState()

        self.status_var = tk.StringVar(value="Not signed in")
        self.account_var = tk.StringVar(value="-")
        self.mode_var = tk.StringVar(value="-")
        self.count_var = tk.StringVar(value="Total: 0 | Filtered: 0")
        self.search_var = tk.StringVar(value="")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="Reddit Subreddit Exporter", font=("TkDefaultFont", 14, "bold")).pack(
            anchor="w"
        )
        ttk.Label(top, textvariable=self.account_var).pack(anchor="w")
        ttk.Label(top, textvariable=self.mode_var).pack(anchor="w")
        ttk.Label(top, textvariable=self.status_var).pack(anchor="w")

        controls = ttk.Frame(self, padding=12)
        controls.pack(fill="x")

        self.signin_btn = ttk.Button(controls, text="Sign in with Reddit", command=self._login_oauth)
        self.signin_btn.pack(side="left", padx=4)
        self.advanced_btn = ttk.Button(controls, text="Advanced authentication", command=self._login_script)
        self.advanced_btn.pack(side="left", padx=4)
        self.refresh_btn = ttk.Button(controls, text="Refresh", command=self._refresh)
        self.refresh_btn.pack(side="left", padx=4)
        self.export_btn = ttk.Button(controls, text="Export", command=self._export)
        self.export_btn.pack(side="left", padx=4)
        self.logout_btn = ttk.Button(controls, text="Sign out", command=self._logout)
        self.logout_btn.pack(side="left", padx=4)

        search_row = ttk.Frame(self, padding=(12, 0, 12, 8))
        search_row.pack(fill="x")
        ttk.Label(search_row, text="Search:").pack(side="left")
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.search_var.trace_add("write", lambda *_: self._refresh_tree_local())

        list_frame = ttk.Frame(self, padding=12)
        list_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(list_frame, columns=("name",), show="headings")
        self.tree.heading("name", text="Subreddit", command=self._toggle_sort)
        self.tree.pack(fill="both", expand=True)
        ttk.Label(self, textvariable=self.count_var, padding=(12, 0, 12, 12)).pack(anchor="w")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in [self.signin_btn, self.advanced_btn, self.refresh_btn, self.export_btn, self.logout_btn]:
            button.configure(state=state)

    def _run_async(self, action, success_msg: str | None = None) -> None:
        if self.worker.active:
            return
        self._set_busy(True)
        self.status_var.set("Working...")
        self.worker.run(action)

        def poll() -> None:
            result = self.worker.poll()
            if result is None:
                self.after(100, poll)
                return
            self._set_busy(False)
            if result.ok:
                if success_msg:
                    self.status_var.set(success_msg)
                self._on_worker_success(result.value)
            else:
                self.status_var.set("Operation failed")
                messagebox.showerror("Error", str(result.error))

        self.after(100, poll)

    def _on_worker_success(self, value) -> None:
        if isinstance(value, SubscriptionSnapshot):
            self.state.snapshot = value
            self.account_var.set(f"Authenticated account: {value.account.username}")
            self._refresh_tree_local()

    def _refresh_tree_local(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        snapshot = self.state.snapshot
        if snapshot is None:
            self.count_var.set("Total: 0 | Filtered: 0")
            return

        filtered = filter_subscriptions(snapshot.subscriptions, self.search_var.get())
        for sub in filtered:
            self.tree.insert("", "end", values=(sub.display_name_prefixed,))
        self.state.filtered_count = len(filtered)
        self.count_var.set(f"Total: {len(snapshot.subscriptions)} | Filtered: {len(filtered)}")

    def _toggle_sort(self) -> None:
        snapshot = self.state.snapshot
        if snapshot is None:
            return
        reversed_subs = tuple(reversed(snapshot.subscriptions))
        self.state.snapshot = SubscriptionSnapshot(
            account=snapshot.account,
            retrieved_at_utc=snapshot.retrieved_at_utc,
            subscriptions=reversed_subs,
        )
        self._refresh_tree_local()

    def _login_oauth(self) -> None:
        def action():
            auth = self.service.login_oauth()
            self.mode_var.set(f"Authentication mode: {auth.mode}")
            return self.service.fetch_snapshot()

        self._run_async(action, "Signed in")

    def _login_script(self) -> None:
        dialog = ScriptLoginDialog(self)
        self.wait_window(dialog)
        if dialog.result is None:
            return

        def action():
            payload = dialog.result or {}
            auth = self.service.login_script(
                client_id=payload.get("client_id", ""),
                client_secret=payload.get("client_secret", ""),
                username=payload.get("username", ""),
                **{"password": payload.get("password", "")},
                otp=payload.get("otp") or None,
            )
            self.mode_var.set(f"Authentication mode: {auth.mode}")
            return self.service.fetch_snapshot()

        self._run_async(action, "Signed in")

    def _refresh(self) -> None:
        self._run_async(self.service.fetch_snapshot, "Refreshed subscriptions")

    def _export(self) -> None:
        snapshot = self.state.snapshot
        if snapshot is None:
            messagebox.showinfo("Export", "Load subscriptions before exporting.")
            return
        path = filedialog.asksaveasfilename(
            title="Export subscriptions",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("CSV", "*.csv"), ("JSON", "*.json")],
        )
        if not path:
            return
        suffix = Path(path).suffix.lower().lstrip(".")
        fmt = suffix if suffix in {"txt", "csv", "json"} else "txt"
        try:
            export_snapshot(snapshot, Path(path), fmt=fmt, force=True)
            self.status_var.set(f"Exported to {path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Export failed", str(exc))

    def _logout(self) -> None:
        self.service.logout()
        self.state.snapshot = None
        self.search_var.set("")
        self.account_var.set("-")
        self.mode_var.set("-")
        self.status_var.set("Signed out")
        self._refresh_tree_local()


def run(config_path: Path | None = None) -> None:
    config = load_config(config_path)
    try:
        store = CredentialStore()
        if not store.is_available():
            store = SessionOnlyCredentialStore()
    except Exception as exc:  # noqa: BLE001
        LOGGER.info("Secure keyring unavailable; using session-only credentials: %s", exc.__class__.__name__)
        store = SessionOnlyCredentialStore()
    service = ExporterService(config=config, credential_store=store)
    app = ExporterGui(service)
    app.mainloop()
