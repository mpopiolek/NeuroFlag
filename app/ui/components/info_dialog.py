from __future__ import annotations

import tkinter.messagebox
import webbrowser

import customtkinter as ctk

from app.ui import info_content as content
from app.ui import theme as t
from app.ui.components import widgets as w


def show_info_dialog(parent: ctk.CTkBaseClass, *, app_window: ctk.CTk) -> None:
    existing = getattr(parent, "_info_dialog", None)
    if isinstance(existing, InfoDialog) and existing.winfo_exists():
        existing.lift()
        existing.focus_set()
        return
    dialog = InfoDialog(parent, app_window=app_window)
    setattr(parent, "_info_dialog", dialog)
    dialog.bind(
        "<Destroy>",
        lambda _event: setattr(parent, "_info_dialog", None),
        add="+",
    )


class InfoDialog(ctk.CTkToplevel):
    _DIALOG_WIDTH = 560
    _DIALOG_MAX_HEIGHT = 620
    _STRIPE_WIDTH = 4

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

    def _section_card(self, parent: ctk.CTkScrollableFrame, title: str) -> ctk.CTkFrame:
        card = w.surface_card(parent)
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=0, pady=0)
        inner.columnconfigure(1, weight=1)

        stripe = ctk.CTkFrame(
            inner,
            fg_color=t.COLOR_NAVY,
            width=self._STRIPE_WIDTH,
            corner_radius=0,
        )
        stripe.grid(row=0, column=0, rowspan=2, sticky="ns")
        stripe.grid_propagate(False)

        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.grid(row=0, column=1, sticky="ew", padx=(12, 16), pady=(12, 8))

        ctk.CTkLabel(
            header,
            text=title,
            font=t.font_subheading(),
            text_color=t.COLOR_NAVY,
            anchor="w",
        ).pack(anchor="w", fill="x")

        body = ctk.CTkFrame(inner, fg_color="transparent")
        body.grid(row=1, column=1, sticky="ew", padx=(12, 16), pady=(0, 12))
        body.columnconfigure(0, weight=1)
        return body

    def _add_section(self, parent: ctk.CTkScrollableFrame, title: str, text: str) -> None:
        body = self._section_card(parent, title)
        w.body_label(
            body,
            text,
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w")

    def _add_bullet_section(
        self,
        parent: ctk.CTkScrollableFrame,
        title: str,
        bullets: tuple[str, ...],
    ) -> None:
        body = self._section_card(parent, title)
        bullet_text = "\n".join(f"• {item}" for item in bullets)
        w.body_label(
            body,
            bullet_text,
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w")

    def _add_contact_section(
        self,
        parent: ctk.CTkScrollableFrame,
        title: str,
        contact: content.ContactInfo,
    ) -> None:
        body = self._section_card(parent, title)
        lines = [contact.name, contact.role]
        if contact.phone is not None:
            lines.append(f"tel. {contact.phone}")
        lines.append(contact.email)
        w.body_label(
            body,
            "\n".join(lines),
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w")

    def _add_technical_section(self, parent: ctk.CTkScrollableFrame) -> None:
        body = self._section_card(parent, "Problemy z aplikacją")
        contact = content.TECH_CONTACT
        w.body_label(
            body,
            f"{contact.name}\n{contact.email}",
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 8))

        w.body_label(
            body,
            content.GITHUB_REPO_URL,
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 8))

        w.body_label(
            body,
            content.OFFLINE_NOTE,
            secondary=True,
            wraplength=t.WRAP_WIDTH - 80,
        ).pack(anchor="w", pady=(0, 8))

        w.primary_button(
            body,
            text="Zgłoś błąd na GitHubie",
            command=self._open_github_issue,
            width=220,
        ).pack(anchor="w")

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
