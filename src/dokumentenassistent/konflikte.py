"""M9: Regelbasierte Konfliktkandidaten zwischen Vorschlägen, Entscheidung, Erklärung.

Konflikte werden nie automatisch entschieden: `finde_konflikte` liefert nur
Kandidaten samt Vorschlag; `entscheide` erzeugt aus einer Nutzerentscheidung
eine neue (unveränderte Eingabe bleibende) Konflikt-Instanz.
"""
from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING, Mapping

from .typen import Feld, Konflikt, Vorschlag

if TYPE_CHECKING:
    from .provider import ModelProvider

_GUELTIGE_ENTSCHEIDUNGEN = ("ersetzt", "verschiedene_sachverhalte", "nicht_entscheidbar", "eigener_wert")


def _feld(vorschlag: Vorschlag, name: str) -> Feld | None:
    for f in vorschlag.felder:
        if f.name == name:
            return f
    return None


def _feld_wert(vorschlag: Vorschlag, name: str) -> str | None:
    f = _feld(vorschlag, name)
    return f.wert if f else None


def _nennt_rechnungsnummer(text: str | None, rechnungsnummer: str | None) -> bool:
    if not text or not rechnungsnummer:
        return False
    return rechnungsnummer in text


_RECHTSFORMEN = frozenset({"gmbh", "mbh", "ag", "kg", "ohg", "gbr", "ug", "eg", "ev", "ek", "co", "se", "kgaa",
                           "haftungsbeschränkt", "inh", "und"})


def _woerter(aussteller: str) -> tuple[str, ...]:
    """Kleinschreibung, Punkte weg ('e.K.' → 'ek', 'Co.' → 'co'), übrige Satzzeichen als Trenner."""
    return tuple(re.sub(r"[^\w]+", " ", aussteller.casefold().replace(".", "")).split())


def _gleicher_aussteller(a: str | None, b: str | None) -> bool:
    """Gleich nach Vereinheitlichung, oder der kürzere Name steckt ganz im längeren und trägt dabei ein
    unterscheidendes Wort (keine Rechtsform, ≥ 4 Zeichen).

    Gesamttest 06.10.2026: Aus dem PaddleOCR-Scan las das Modell 'Krause GmbH', aus dem PDF derselben
    Firma 'Heizung Sanitär Krause GmbH' — die exakte Gleichheit ließ den Konflikt durch, der Scan mit dem
    überholten Betrag wäre ohne Warnung abgelegt worden. Ein falscher Treffer kostet wenig: ein Konflikt
    verlangt zusätzlich gleiche Kategorie, Rechnungsnummer oder Verweis und verschiedene Beträge, und
    entschieden wird er nie automatisch."""
    if a is None or b is None:
        return False
    wa, wb = _woerter(a), _woerter(b)
    if not wa or not wb:
        return False
    if wa == wb:
        return True
    kurz, lang = sorted((set(wa), set(wb)), key=len)
    return kurz <= lang and any(w not in _RECHTSFORMEN and len(w) >= 4 for w in kurz)


def _konflikt_zwischen(a: Vorschlag, b: Vorschlag, texte_je_datei: Mapping[str, str]) -> Konflikt | None:
    if a.status != "sicher" or b.status != "sicher":
        return None
    if a.kategorie is None or a.kategorie != b.kategorie:
        return None

    if not _gleicher_aussteller(_feld_wert(a, "aussteller"), _feld_wert(b, "aussteller")):
        return None

    nr_a = _feld_wert(a, "rechnungsnummer")
    nr_b = _feld_wert(b, "rechnungsnummer")
    gleiche_rechnungsnummer = nr_a is not None and nr_a == nr_b
    textverweis = _nennt_rechnungsnummer(texte_je_datei.get(a.datei_hash), nr_b) or _nennt_rechnungsnummer(
        texte_je_datei.get(b.datei_hash), nr_a
    )
    if not (gleiche_rechnungsnummer or textverweis):
        return None

    betrag_a = _feld_wert(a, "betrag")
    betrag_b = _feld_wert(b, "betrag")
    if betrag_a is None or betrag_b is None or betrag_a == betrag_b:
        return None

    datum_a = _feld_wert(a, "datum")
    datum_b = _feld_wert(b, "datum")
    if datum_a is not None and datum_b is not None and datum_a != datum_b:
        vorschlag = "ersetzt"
    else:
        vorschlag = "nicht_entscheidbar"

    hash_lo, hash_hi = sorted((a.datei_hash, b.datei_hash))

    return Konflikt(
        id=f"{hash_lo}__{hash_hi}__betrag",
        feld="betrag",
        hash_a=a.datei_hash,
        hash_b=b.datei_hash,
        wert_a=betrag_a,
        wert_b=betrag_b,
        beleg_a=_feld(a, "betrag").beleg,
        beleg_b=_feld(b, "betrag").beleg,
        vorschlag=vorschlag,
    )


def finde_konflikte(vorschlaege: tuple[Vorschlag, ...], texte_je_datei: Mapping[str, str]) -> tuple[Konflikt, ...]:
    """Regel: gleiche Kategorie UND gleicher aussteller UND (gleiche rechnungsnummer ODER
    Text der einen Datei nennt die rechnungsnummer der anderen) UND abweichender betrag
    → Konflikt auf Feld "betrag". Nur Vorschläge mit status "sicher" werden verglichen."""
    konflikte: list[Konflikt] = []
    for i in range(len(vorschlaege)):
        for j in range(i + 1, len(vorschlaege)):
            konflikt = _konflikt_zwischen(vorschlaege[i], vorschlaege[j], texte_je_datei)
            if konflikt is not None:
                konflikte.append(konflikt)
    return tuple(konflikte)


def entscheide(k: Konflikt, entscheidung: str, eigener_wert: str | None = None) -> Konflikt:
    """Gibt einen neuen Konflikt mit Entscheidung zurück, verändert `k` nicht."""
    if entscheidung not in _GUELTIGE_ENTSCHEIDUNGEN:
        raise ValueError(f"Ungültige Entscheidung: {entscheidung!r}")
    if entscheidung == "eigener_wert" and eigener_wert is None:
        raise ValueError("Entscheidung 'eigener_wert' braucht einen eigener Wert")
    return dataclasses.replace(k, entscheidung=entscheidung, eigener_wert=eigener_wert)


def erklaerung(k: Konflikt, provider: "ModelProvider") -> str:
    """Bittet das Modell um eine kurze, neutrale Erklärung des Widerspruchs — ohne Entscheidung."""
    prompt = (
        "Erkläre kurz und neutral den folgenden Widerspruch zwischen zwei Dokumenten. "
        "Entscheide NICHT, welcher Wert richtig ist.\n\n"
        f"Feld: {k.feld}\n"
        f"Dokument A ({k.hash_a}): {k.wert_a} (Beleg: {k.beleg_a.wortlaut!r})\n"
        f"Dokument B ({k.hash_b}): {k.wert_b} (Beleg: {k.beleg_b.wortlaut!r})\n"
    )
    return provider.generate_text(prompt)
