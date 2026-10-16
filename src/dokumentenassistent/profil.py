"""Stichprobe → Profil. Schlägt Kategorien, Dokumenttypen, Felder und Namensschema vor."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

import yaml

from dokumentenassistent.typen import DokumentenassistentFehler, Fundstelle, Profil

if TYPE_CHECKING:
    from dokumentenassistent.provider import ModelProvider, SchemaFehler


class ProfilFehler(DokumentenassistentFehler):
    """Profilvorschlag ist unvollständig, unlesbar oder das Namensschema ist ungültig."""


PROFIL_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "kategorien": {"type": "array", "items": {"type": "string"}},
        "dokumenttypen": {"type": "array", "items": {"type": "string"}},
        "felder": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "namensschema": {"type": "string"},
        "eigentuemer": {"type": "string"},
    },
    "required": ["kategorien", "dokumenttypen", "felder", "namensschema", "eigentuemer"],
}


def waehle_stichprobe(
    fundstellen_je_datei: Mapping[str, tuple[Fundstelle, ...]],
    n_dateien: int = 5,
    n_absaetze: int = 4,
) -> tuple[Fundstelle, ...]:
    """Gleichmäßig über den Bestand verteilt statt „die ersten fünf" — sonst fehlt in
    einem alphabetisch sortierten Steuerordner jede Rechnung in der Stichprobe."""
    alle = [fs for fs in fundstellen_je_datei.values() if fs]
    if not alle:
        return ()
    schritt = max(len(alle) / n_dateien, 1.0)
    gewaehlt = [alle[int(i * schritt)] for i in range(min(n_dateien, len(alle)))]
    return tuple(f for fundstellen in gewaehlt for f in fundstellen[:n_absaetze])


_GRUNDFELDER = "datum, aussteller, betrag, rechnungsnummer"
_GRUNDTYPEN = "Rechnung, Angebot, Vertrag, Bescheid, Abrechnung, Bescheinigung, Quittung, Notiz"


def _baue_prompt(zweck: str, stichprobe: tuple[Fundstelle, ...]) -> str:
    """Die Stichprobe ist nur ein Auszug (erste Dateien in Pfadreihenfolge); der
    Prompt muss deshalb Feldwahl und Dokumenttypen vom Zweck her führen, sonst
    schlägt das Modell je Stichproben-Dokument eigene Felder vor (Lauf 1: 20
    Felder, davon war kein einziges bei allen Dokumenten belegbar)."""
    texte = "\n".join(f"- {f.text}" for f in stichprobe)
    return (
        f"Zweck des Dokumentenbestands: {zweck}\n\n"
        f"Stichprobe aus den Dokumenten (nur ein Auszug, der Bestand enthält weitere "
        f"Dokumentarten):\n{texte}\n\n"
        "Schlage für DIESEN Bestand vor: Kategorien (Ordnungsgruppen), Dokumenttypen, "
        "Felder (die je Dokument erfasst werden sollen) und ein Namensschema für "
        "Zieldateinamen. Antworte auf Deutsch.\n\n"
        "Kategorien: zwei bis acht Ordner, wie ein Mensch sie für diesen Zweck anlegen "
        "würde; sie ordnen den ganzen Bestand. Zwei Fälle:\n"
        "(a) Der Zweck nennt wenige konkrete Objekte (z. B. zwei Wohnungen, drei Fahrzeuge, "
        "einzelne Mandanten): dann ist jedes Objekt eine Kategorie und heißt GENAU so, wie "
        "die Dokumente es bezeichnen — wörtlich, mit Leerzeichen und Umlauten.\n"
        "(b) Sonst — etwa bei einem Betrieb, einem Verein, einem Haushalt mit vielen "
        "Geschäftspartnern — sind die Kategorien Dokumentarten oder Sachgebiete: z. B. "
        "Eingangsrechnungen, Ausgangsrechnungen, Angebote, Verträge, Behörden, Belege, "
        "Interne Unterlagen. Wähle die, die zum Zweck passen.\n"
        "In beiden Fällen: Geschäftspartner (Kunden, Lieferanten, Firmen, Vereine, Ämter) "
        "sind NIEMALS Kategorien — sie stehen im Feld aussteller. Dazu genau eine "
        "Sammelkategorie \"Sonstiges\".\n\n"
        f"Dokumenttypen: die Liste beginnt mit GENAU diesen acht Grundtypen in dieser "
        f"Reihenfolge: {_GRUNDTYPEN}. Sie bleiben auch dann alle drin, wenn die Stichprobe "
        "keinen Beleg dafür zeigt (der Bestand ist größer als die Stichprobe). Danach "
        "höchstens zwei weitere kurze Gattungsbegriffe. Keine Unterarten eines Grundtyps "
        "(eine Nebenkostenabrechnung ist eine Abrechnung).\n\n"
        f"Felder: GENAU diese vier, keine weiteren: {_GRUNDFELDER} "
        "(datum = Datum des Dokuments, aussteller = wer es herausgegeben hat, betrag = "
        "Hauptbetrag des Dokuments, rechnungsnummer = die Nummer, unter der der Aussteller "
        "das Dokument führt). Jedes weitere Feld, das in einem Dokument fehlt, macht dieses "
        "Dokument unklar und erzwingt Handarbeit — deshalb keine Felder für Objektbezug, "
        "Kategorie, Dokumentart oder einzelne Rechnungsposten.\n\n"
        "Eigentümer: die Person, Firma oder Stelle, der dieser Bestand gehört — meist im Zweck "
        "genannt, sonst der Aussteller, der in der Stichprobe als Absender von Rechnungen oder "
        "Angeboten auftritt. Voller Name wie in den Dokumenten; leer lassen, wenn nicht erkennbar.\n\n"
        "Namensschema: nimm \"{datum}_{typ}_{aussteller}\". Es darf ausschließlich "
        "Platzhalter aus deiner Feldliste oder 'typ'/'kategorie' enthalten; jeder andere "
        "Platzhalter (etwa {jahr}) macht das Profil ungültig."
    )


def _pruefe_antwort(antwort: dict) -> None:
    if not antwort.get("kategorien"):
        raise ProfilFehler("Kategorien dürfen nicht leer sein")
    if not antwort.get("dokumenttypen"):
        raise ProfilFehler("Dokumenttypen dürfen nicht leer sein")
    if not antwort.get("felder"):
        raise ProfilFehler("Felder dürfen nicht leer sein")


def _pruefe_namensschema(namensschema: str, felder: tuple[str, ...]) -> None:
    platzhalter = re.findall(r"\{(\w+)\}", namensschema)
    if not platzhalter:
        raise ProfilFehler("Namensschema braucht mindestens einen Platzhalter")
    erlaubt = set(felder) | {"typ", "kategorie"}
    for name in platzhalter:
        if name not in erlaubt:
            raise ProfilFehler(f"Namensschema enthält unbekanntes Feld '{name}'")


def _dedupliziere(werte: list[str]) -> tuple[str, ...]:
    gesehen: list[str] = []
    for wert in werte:
        if wert not in gesehen:
            gesehen.append(wert)
    return tuple(gesehen)


def schlage_profil_vor(zweck: str, stichprobe: tuple[Fundstelle, ...], provider: "ModelProvider") -> Profil:
    from dokumentenassistent.provider import ProviderFehler

    if not stichprobe:
        raise ProfilFehler("Stichprobe darf nicht leer sein")

    prompt = _baue_prompt(zweck, stichprobe)
    try:
        antwort = provider.generate_json(prompt, PROFIL_SCHEMA)
    except ProviderFehler as e:
        raise ProfilFehler(f"Modell konnte kein Profil vorschlagen: {e}") from e

    _pruefe_antwort(antwort)

    felder = _dedupliziere(list(antwort["felder"]))
    namensschema = antwort["namensschema"]
    _pruefe_namensschema(namensschema, felder)
    eigentuemer = str(antwort.get("eigentuemer") or "").strip() or None

    return Profil(
        zweck=zweck,
        kategorien=_dedupliziere(list(antwort["kategorien"])),
        dokumenttypen=_dedupliziere(list(antwort["dokumenttypen"])),
        felder=felder,
        namensschema=namensschema,
        eigentuemer=eigentuemer,
    )


def speichere_profil(profil: Profil, pfad: Path) -> None:
    daten = {
        "zweck": profil.zweck,
        "kategorien": list(profil.kategorien),
        "dokumenttypen": list(profil.dokumenttypen),
        "felder": list(profil.felder),
        "namensschema": profil.namensschema,
        "eigentuemer": profil.eigentuemer,
    }
    pfad.write_text(yaml.safe_dump(daten, allow_unicode=True, sort_keys=False))


def lade_profil(pfad: Path) -> Profil:
    try:
        daten = yaml.safe_load(pfad.read_text()) or {}
    except FileNotFoundError as e:
        raise ProfilFehler(f"Profil nicht gefunden: {pfad}") from e
    try:
        return Profil(
            zweck=daten["zweck"],
            kategorien=tuple(daten["kategorien"]),
            dokumenttypen=tuple(daten["dokumenttypen"]),
            felder=tuple(daten["felder"]),
            namensschema=daten["namensschema"],
            eigentuemer=daten.get("eigentuemer") or None,
        )
    except KeyError as e:
        raise ProfilFehler(f"Profil unvollständig: Schlüssel {e} fehlt") from e
