from __future__ import annotations

import tkinter.messagebox
import webbrowser
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.ui import info_content as content
from app.ui import theme as t
from app.ui.bug_report import collect_bug_report_context, open_bug_report
from app.ui.components import widgets as w

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_STRIPE_WIDTH = 4


def _section_card(parent: ctk.CTkScrollableFrame, title: str) -> ctk.CTkFrame:
    card = w.surface_card(parent)
    card.pack(fill="x", pady=(0, 16))

    inner = ctk.CTkFrame(card, fg_color="transparent", height=0)
    inner.pack(fill="x")

    stripe = ctk.CTkFrame(
        inner,
        fg_color=t.COLOR_NAVY,
        width=_STRIPE_WIDTH,
        height=0,
        corner_radius=0,
    )
    stripe.pack(side="left", fill="y")

    content = ctk.CTkFrame(inner, fg_color="transparent", height=0)
    content.pack(side="left", fill="x", expand=True, padx=(12, 16), pady=12)

    ctk.CTkLabel(
        content,
        text=title,
        font=t.font_subheading(),
        text_color=t.COLOR_NAVY,
        anchor="w",
    ).pack(anchor="w", pady=(0, 4))

    return content


def _open_github_issue(app_window: AppWindow | None = None) -> None:
    if app_window is not None:
        ctx = collect_bug_report_context(app_window, manual=True)
        open_bug_report(ctx)
        return
    try:
        webbrowser.open(content.GITHUB_NEW_ISSUE_URL)
    except OSError:
        tkinter.messagebox.showerror(
            "Nie można otworzyć przeglądarki",
            "Skopiuj adres i otwórz go ręcznie w przeglądarce:\n\n"
            f"{content.GITHUB_NEW_ISSUE_URL}",
        )


def build_info_content(
    parent: ctk.CTkScrollableFrame,
    *,
    wraplength: int,
    app_window: AppWindow | None = None,
) -> None:
    """Buduje sekcje treści Informacji (współdzielone przez widok główny)."""
    body = _section_card(parent, "Produkt")
    w.body_label(
        body,
        content.PRODUCT_DESCRIPTION,
        secondary=True,
        wraplength=wraplength,
    ).pack(anchor="w")

    body = _section_card(parent, "Wartości")
    bullet_text = "\n".join(f"• {item}" for item in content.VALUE_BULLETS)
    w.body_label(
        body,
        bullet_text,
        secondary=True,
        wraplength=wraplength,
    ).pack(anchor="w")

    body = _section_card(parent, "Konsultacje merytoryczne")
    contact = content.EXPERT_CONTACT
    lines = [contact.name, contact.role]
    if contact.phone is not None:
        lines.append(f"tel. {contact.phone}")
    lines.append(contact.email)
    w.body_label(
        body,
        "\n".join(lines),
        secondary=True,
        wraplength=wraplength,
    ).pack(anchor="w")

    body = _section_card(parent, "Problemy z aplikacją")
    tech = content.TECH_CONTACT
    w.body_label(
        body,
        f"{tech.name}\n{tech.email}",
        secondary=True,
        wraplength=wraplength,
    ).pack(anchor="w", pady=(0, 8))

    w.body_label(
        body,
        content.GITHUB_REPO_URL,
        secondary=True,
        wraplength=wraplength,
    ).pack(anchor="w", pady=(0, 8))

    w.body_label(
        body,
        content.OFFLINE_NOTE,
        secondary=True,
        wraplength=wraplength,
    ).pack(anchor="w", pady=(0, 8))

    w.primary_button(
        body,
        text="Zgłoś błąd na GitHubie",
        command=lambda: _open_github_issue(app_window),
        width=220,
    ).pack(anchor="w")
