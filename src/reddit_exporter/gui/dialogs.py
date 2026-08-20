from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ScriptLoginDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("Advanced authentication")
        self.resizable(False, False)
        self.result: dict[str, str] | None = None

        self.client_id = tk.StringVar()
        self.client_secret = tk.StringVar()
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.otp = tk.StringVar()

        fields = [
            ("Client ID", self.client_id, None),
            ("Client secret", self.client_secret, "*"),
            ("Username", self.username, None),
            ("Password", self.password, "*"),
            ("2FA code (optional)", self.otp, "*"),
        ]

        for idx, (label, variable, show) in enumerate(fields):
            ttk.Label(self, text=label).grid(row=idx, column=0, sticky="w", padx=8, pady=4)
            entry = ttk.Entry(self, textvariable=variable, width=40)
            if show:
                entry.configure(show=show)
            entry.grid(row=idx, column=1, padx=8, pady=4)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side="right", padx=4)
        ttk.Button(button_frame, text="Sign in", command=self._submit).pack(side="right", padx=4)

        self.transient(master)
        self.grab_set()

    def _submit(self) -> None:
        self.result = {
            "client_id": self.client_id.get().strip(),
            "client_secret": self.client_secret.get().strip(),
            "username": self.username.get().strip(),
            "password": self.password.get(),
            "otp": self.otp.get().strip(),
        }
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
