from __future__ import annotations

import tkinter.messagebox
import webbrowser

import customtkinter as ctk

from app.ui import info_content as content
from app.ui import theme as t
from app.ui.components import widgets as w


def show_info_dialog(parent: ctk.CTkBaseClass, *, app_window: ctk.CTk) -> None:
    InfoDialog(parent, app_window=app_window)


class InfoDialog(ctk.CTkToplevel):
    _DIALOG_WIDTH = 560
    _DIALOG_MAX_HEIGHT = 620

    def __init__(self, parent: ctk.CTkBaseClass, *, app_window: ctk.CTk) -> None:
        super().__init__(parent)
        self.title("Informacje — NeuroFlag")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=24, pady=(20, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            body,
            fg_color="transparent",
            width=self._DIALOG_WIDTH - 48,
            height=self._DIALOG_MAX_HEIGHT - 160,
        )
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        w.bind_auto_hide_scrollbar(scroll)

        self._add_section(scroll, "Produkt", content.PRODUCT_DESCRIPTION)
        self._add_bullet_section(scroll, "Wartości", content.VALUE_BULLETS)
        self._add_contact_section(
            scroll,
            "Konsultacje merytoryczne",
            content.EXPERT_CONTACT,
        )
        self._add_technical_section(scroll)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 20))

        w.primary_button(
            footer,
            text="Zamknij",
            command=self.destroy,
            width=110,
        ).pack(side="right")

        self.bind("<Escape>", lambda _event: self.destroy())

        self.update_idletasks()
        self.grab_set()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self._center_on_window(app_window)

    def _add_section(self, parent: ctk.CTkScrollableFrame, title: str, text: str) -> None:
        self._section_header(parent, title).pack(fill="x", pady=(0, 6))
        w.body_label(
            parent,
            text,
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 16))

    def _add_bullet_section(
        self,
        parent: ctk.CTkScrollableFrame,
        title: str,
        bullets: tuple[str, ...],
    ) -> None:
        self._section_header(parent, title).pack(fill="x", pady=(0, 6))
        bullet_text = "\n".join(f"• {item}" for item in bullets)
        w.body_label(
            parent,
            bullet_text,
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 16))

    def _add_contact_section(
        self,
        parent: ctk.CTkScrollableFrame,
        title: str,
        contact: content.ContactInfo,
    ) -> None:
        self._section_header(parent, title).pack(fill="x", pady=(0, 6))
        lines = [contact.name, contact.role]
        if contact.phone is not None:
            lines.append(f"tel. {contact.phone}")
        lines.append(contact.email)
        w.body_label(
            parent,
            "\n".join(lines),
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 16))

    def _add_technical_section(self, parent: ctk.CTkScrollableFrame) -> None:
        self._section_header(parent, "Problemy z aplikacją").pack(fill="x", pady=(0, 6))
        contact = content.TECH_CONTACT
        w.body_label(
            parent,
            f"{contact.name}\n{contact.email}",
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 8))

        w.body_label(
            parent,
            content.GITHUB_REPO_URL,
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 8))

        w.body_label(
            parent,
            content.OFFLINE_NOTE,
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 8))

        w.primary_button(
            parent,
            text="Zgłoś błąd na GitHubie",
            command=self._open_github_issue,
            width=220,
        ).pack(anchor="w", pady=(0, 8))

    def _section_header(self, parent: ctk.CTkBaseClass, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(
            parent,
            fg_color=t.COLOR_SECTION_NAVY,
            corner_radius=t.CORNER_RADIUS_SM,
        )
        ctk.CTkLabel(
            frame,
            text=title,
            font=t.font_subheading(),
            text_color=t.COLOR_ON_NAVY,
            anchor="w",
        ).pack(padx=12, pady=8, anchor="w", fill="x")
        return frame

    def _open_github_issue(self) -> None:
        try:
            webbrowser.open(content.GITHUB_NEW_ISSUE_URL)
        except OSError:
            tkinter.messagebox.showerror(
                "Nie można otworzyć przeglądarki",
                "Skopiuj adres i otwórz go ręcznie w przeglądarce:\n\n"
                f"{content.GITHUB_NEW_ISSUE_URL}",
            )

    def _center_on_window(self, app_window: ctk.CTk) -> None:
        self.update_idletasks()
        window_x = app_window.winfo_x()
        window_y = app_window.winfo_y()
        window_w = app_window.winfo_width()
        window_h = app_window.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = window_x + max(0, (window_w - dialog_w) // 2)
        y = window_y + max(0, (window_h - dialog_h) // 2)
        self.geometry(f"+{x}+{y}")
