from __future__ import annotations

import tkinter.messagebox
import webbrowser

import customtkinter as ctk

from app.ui import info_content as content
from app.ui import theme as t
from app.ui.components import widgets as w

_STRIPE_WIDTH = 4


def _section_card(parent: ctk.CTkScrollableFrame, title: str) -> ctk.CTkFrame:
    card = w.surface_card(parent)
    card.pack(fill="x", pady=(0, 16))

    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="x", padx=0, pady=0)
    inner.columnconfigure(1, weight=1)

    stripe = ctk.CTkFrame(
        inner,
        fg_color=t.COLOR_NAVY,
        width=_STRIPE_WIDTH,
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


def _open_github_issue() -> None:
    try:
        webbrowser.open(content.GITHUB_NEW_ISSUE_URL)
    except OSError:
        tkinter.messagebox.showerror(
            "Nie można otworzyć przeglądarki",
            "Skopiuj adres i otwórz go ręcznie w przeglądarce:\n\n"
            f"{content.GITHUB_NEW_ISSUE_URL}",
        )


def build_info_content(parent: ctk.CTkScrollableFrame, *, wraplength: int) -> None:
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
        command=_open_github_issue,
        width=220,
    ).pack(anchor="w")
