from __future__ import annotations

from app.ui import info_content as content


def test_tech_contact_email() -> None:
    assert content.TECH_CONTACT.email == "malgorzata.pe@gmail.com"


def test_github_new_issue_url() -> None:
    assert "github.com/mpopiolek/NeuroFlag" in content.GITHUB_NEW_ISSUE_URL


def test_expert_contact_phone() -> None:
    assert content.EXPERT_CONTACT.phone is not None
    assert "508" in content.EXPERT_CONTACT.phone


def test_product_description_has_no_neurod_branding() -> None:
    assert "NEUROD" not in content.PRODUCT_DESCRIPTION.upper()
