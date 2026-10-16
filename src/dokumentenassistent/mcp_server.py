"""MCP-Server: drei lesende Werkzeuge über dem freigegebenen Bestand.

Kein Schreibzugriff, keine Freigabe, keine Korrektur. Sichtbar ist nur, was
ein Mensch bestätigt hat; `datei_oeffnen` nennt die Kopie in der Zielablage,
nie das Original. Jeder Aufruf steht als Zeile `art="mcp"` im Protokoll —
das Gästebuch dessen, was den Rechner verlassen hat.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.mcpserver import MCPServer

from dokumentenassistent.typen import Belegkarte, Fundstelle

if TYPE_CHECKING:
    from dokumentenassistent.werkstatt import Werkstatt

HINWEIS = (
    "Liefert ausschließlich Fundstellen aus Dateien, die ein Mensch freigegeben hat. "
    "Nicht freigegebene oder unbekannte Fundstellen werden abgelehnt."
)


def _karte(karte: Belegkarte) -> dict:
    f = karte.fundstelle
    return {
        "fundstelle_id": f.id,
        "datei": f.datei_name,
        "seite": f.seite,
        "seiten": list(f.seiten),
        "absatz": f.absatz,
        "wortlaut": karte.wortlaut,
    }


class Lesezugriff:
    """Die drei Werkzeuge als reine Funktionen — testbar ohne MCP-Laufzeit."""

    def __init__(self, werkstatt: Werkstatt) -> None:
        self._w = werkstatt

    def suchen(self, frage: str) -> dict:
        """Nur Freigegebenes -- diese Schnittstelle bedient FREMDE Agenten.

        Seit 24.09.2026 ist die eigene Suche von der Ablage entkoppelt: was ein
        Embedding hat, ist auffindbar, auch ohne Kategorie. Diese Lockerung gilt
        hier ausdruecklich NICHT. Die Regel dieser Schnittstelle ist dieselbe wie
        bei `fundstelle_lesen` und `datei_oeffnen` (Test P4): ein fremder Agent
        sieht nur, was ein Mensch freigegeben hat. Ein Dokument, das niemand
        angesehen hat, ist keine Freigabe.
        """
        antwort = self._w.frage(frage, nur_freigegeben=True)
        karten = [_karte(k) for k in antwort.karten
                  if self._freigegebene(k.fundstelle.id)[0] is not None]
        if not karten:
            self._protokoll("suchen", {"frage": frage}, [])
            return {"status": "nicht_gefunden", "text": "nicht gefunden", "karten": [],
                    "antwortstuetzung": "ungeprueft", "pruefverfahren": "keine_semantische_pruefung"}
        self._protokoll("suchen", {"frage": frage}, [k["fundstelle_id"] for k in karten])
        return {"status": antwort.status, "text": antwort.text, "karten": karten,
                "antwortstuetzung": antwort.stuetzung.status,
                "pruefverfahren": antwort.stuetzung.verfahren}

    def fundstelle_lesen(self, id: str) -> dict:
        fundstelle, grund = self._freigegebene(id)
        if fundstelle is None:
            return self._ablehnung("fundstelle_lesen", {"id": id}, grund)
        self._protokoll("fundstelle_lesen", {"id": id}, [fundstelle.id])
        return {
            "id": fundstelle.id,
            "datei": fundstelle.datei_name,
            "seite": fundstelle.seite,
            "seiten": list(fundstelle.seiten),
            "absatz": fundstelle.absatz,
            "text": fundstelle.text,
        }

    def datei_oeffnen(self, fundstelle_id: str) -> dict:
        fundstelle, grund = self._freigegebene(fundstelle_id)
        if fundstelle is None:
            return self._ablehnung("datei_oeffnen", {"fundstelle_id": fundstelle_id}, grund)
        zielpfad = self._w.index.zielpfad(fundstelle.datei_hash)
        self._protokoll("datei_oeffnen", {"fundstelle_id": fundstelle_id}, [fundstelle.id])
        return {"fundstelle_id": fundstelle.id, "datei": fundstelle.datei_name, "pfad": str(zielpfad)}

    def _freigegebene(self, id: str) -> tuple[Fundstelle | None, str]:
        fundstelle = self._w.index.fundstelle(id)
        if fundstelle is None:
            return None, f"Fundstelle unbekannt: {id!r}"
        if self._w.index.zielpfad(fundstelle.datei_hash) is None:
            return None, f"Datei nicht freigegeben: {fundstelle.datei_name!r}"
        return fundstelle, ""

    def _protokoll(self, werkzeug: str, argumente: dict, fundstellen: list[str]) -> None:
        self._w.index.protokolliere(
            "mcp", werkzeug=werkzeug, argumente=argumente, fundstellen=fundstellen
        )

    def _ablehnung(self, werkzeug: str, argumente: dict, grund: str) -> dict:
        self._w.index.protokolliere(
            "mcp", werkzeug=werkzeug, argumente=argumente, fundstellen=[], abgelehnt=True, grund=grund
        )
        return {"abgelehnt": True, "grund": grund}


def erzeuge_server(werkstatt: Werkstatt) -> MCPServer:
    """Registriert genau die drei Werkzeuge von `Lesezugriff` als MCP-Tools."""
    zugriff = Lesezugriff(werkstatt)
    server = MCPServer(
        "dokumentenassistent",
        instructions="Lesender Zugriff auf den freigegebenen Dokumentenbestand. " + HINWEIS,
    )

    @server.tool(name="suchen", description="Beantwortet eine Frage mit Belegkarten. " + HINWEIS)
    def suchen(frage: str) -> dict:
        return zugriff.suchen(frage)

    @server.tool(name="fundstelle_lesen", description="Liest den Text einer Fundstelle. " + HINWEIS)
    def fundstelle_lesen(id: str) -> dict:
        return zugriff.fundstelle_lesen(id)

    @server.tool(
        name="datei_oeffnen",
        description="Nennt den Pfad der freigegebenen Kopie in der Zielablage, nie das Original. " + HINWEIS,
    )
    def datei_oeffnen(fundstelle_id: str) -> dict:
        return zugriff.datei_oeffnen(fundstelle_id)

    return server


def _argumente(argv: list[str] | None) -> argparse.Namespace:
    zerleger = argparse.ArgumentParser(
        prog="dokumentenassistent-mcp", description="Lokaler Dokumentenassistent — MCP-Server (nur lesend)"
    )
    zerleger.add_argument("--quelle", type=Path, required=True, help="Quellordner, bleibt unverändert")
    zerleger.add_argument("--ziel", type=Path, required=True, help="Zielablage mit den freigegebenen Kopien")
    zerleger.add_argument("--modelle", type=Path, default=Path("modelle.yaml"))
    zerleger.add_argument("--arbeitsordner", type=Path, default=None, help="Index/Protokoll (Standard: Quelle)")
    return zerleger.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    from dokumentenassistent.provider import (
        lade_modelle,
        lade_ocr_einstellungen,
        lade_provider_suche,
        lade_seitenuebergreifend,
        lade_sucheinstellungen,
    )
    from dokumentenassistent.werkstatt import Werkstatt

    args = _argumente(argv)
    werkstatt = Werkstatt(
        quelle=args.quelle,
        zielablage=args.ziel,
        provider=lade_modelle(args.modelle),
        arbeitsordner=args.arbeitsordner,
        provider_suche=lade_provider_suche(args.modelle),
        sucheinstellungen=lade_sucheinstellungen(args.modelle),
        ocr=lade_ocr_einstellungen(args.modelle),
        seitenuebergreifend=lade_seitenuebergreifend(args.modelle),
    )
    werkstatt.index.protokolliere(
        "mcp_start", hinweis="Ab jetzt kann ein externer MCP-Client den freigegebenen Bestand lesen."
    )
    erzeuge_server(werkstatt).run(transport="stdio")


__all__ = ["Lesezugriff", "erzeuge_server", "main"]
