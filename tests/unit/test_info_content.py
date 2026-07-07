from __future__ import annotations

import pytest

from app.ui import info_content as content


def _all_info_strings() -> tuple[str, ...]:
    strings: list[str] = [
        content.PRODUCT_DESCRIPTION,
        content.OFFLINE_NOTE,
        content.EXPERT_CONTACT.name,
        content.EXPERT_CONTACT.role,
        content.EXPERT_CONTACT.email,
        content.TECH_CONTACT.name,
        content.TECH_CONTACT.role,
        content.TECH_CONTACT.email,
        *content.VALUE_BULLETS,
    ]
    if content.EXPERT_CONTACT.phone is not None:
        strings.append(content.EXPERT_CONTACT.phone)
    return tuple(strings)


def test_tech_contact_email() -> None:
    assert content.TECH_CONTACT.email == "malgorzata.pe@gmail.com"


def test_github_new_issue_url() -> None:
    assert "github.com/mpopiolek/NeuroFlag" in content.GITHUB_NEW_ISSUE_URL


def test_expert_contact_phone() -> None:
    assert content.EXPERT_CONTACT.phone is not None
    assert "508" in content.EXPERT_CONTACT.phone


@pytest.mark.parametrize("text", _all_info_strings())
def test_info_strings_have_no_neurod_branding(text: str) -> None:
    assert "NEUROD" not in text.upper()
