from __future__ import annotations

from dataclasses import dataclass

GITHUB_REPO_URL: str = "https://github.com/mpopiolek/NeuroFlag"
GITHUB_NEW_ISSUE_URL: str = f"{GITHUB_REPO_URL}/issues/new"


@dataclass(frozen=True)
class ContactInfo:
    name: str
    role: str
    phone: str | None
    email: str


EXPERT_CONTACT = ContactInfo(
    name="dr Małgorzata Chojak",
    role="Kierownik Laboratorium Badań nad Neuroedukacją UMCS",
    phone="508 216 957",
    email="malgorzata.chojak@mail.umcs.pl",
)

EXPERT_CONTACT_SHORT_ROLE: str = "Kierownik Lab. Neuroedukacji UMCS"

TECH_CONTACT = ContactInfo(
    name="Małgorzata Popiołek",
    role="Wsparcie techniczne aplikacji NeuroFlag",
    phone=None,
    email="malgorzata.pe@gmail.com",
)

PRODUCT_DESCRIPTION: str = (
    "NeuroFlag to aplikacja do przesiewowej analizy sygnału EEG u dzieci "
    "w wieku 6–10 lat. Umożliwia pedagogom i psychologom szybką ocenę na "
    "podstawie pliku .edf lub .vhdr — bez wysyłania danych medycznych do internetu."
)

VALUE_BULLETS: tuple[str, ...] = (
    "Analiza lokalna — dane dziecka nie opuszczają komputera",
    "Empiryczna baza norm dla dzieci 6–10 lat (N=200)",
    "Wynik w trzech kategoriach: Wskazanie / Obserwacja / Brak wskazań",
    "Kompatybilność z popularnymi aparatami EEG i Biofeedback",
    "Raport PDF do dokumentacji placówki",
)

OFFLINE_NOTE: str = (
    "Otwarcie strony GitHub w przeglądarce to jedyna akcja w aplikacji "
    "wymagająca połączenia z internetem. Cała analiza EEG odbywa się "
    "lokalnie na Twoim komputerze."
)
