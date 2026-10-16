"""Auswertung des Belastungstests.

Teil 1 — Kennzahlen je Lauf: Ist (Vorschläge, Konflikte, Antworten) gegen golden.
Teil 2 — Bericht aus `laeufe.jsonl`: je LLM eine Tabelle (Zeile je Stufe), dann
„Wo es bricht" (je Frage über die Stufen grün/rot). Der Bericht rechnet nichts nach.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from dokumentenassistent.typen import Antwort, Konflikt, Vorschlag

STATUS = ("sicher", "konflikt", "unklar", "duplikat", "ocr_unsicher")


# ------------------------------------------------------------- Kennzahlen


def _golden_dateien(golden: dict) -> dict[str, dict]:
    return {**golden.get("dateien", {}), **golden.get("weitere_dateien", {})}


def frage_zeile(soll: dict, antwort: Antwort, dauer: float) -> dict:
    """Treffer = Sollstatus erreicht und (falls golden eine Datei nennt) eine Belegkarte aus
    dieser Datei, deren Wortlaut `wortlaut_enthaelt` enthält — wie E8/E9 im e2e."""
    dateien = [k.fundstelle.datei_name for k in antwort.karten]
    passend = [
        k for k in antwort.karten
        if k.fundstelle.datei_name == soll.get("datei")
        and soll.get("wortlaut_enthaelt", "") in k.wortlaut
    ]
    return {
        "frage": soll["frage"],
        "status_ist": antwort.status,
        "status_soll": soll.get("status"),
        "datei_ist": dateien[0] if dateien else None,
        "datei_soll": soll.get("datei"),
        "treffer": _frage_treffer(soll, antwort, bool(passend), dateien),
        "dauer_s": round(dauer, 3),
    }


def _frage_treffer(soll: dict, antwort: Antwort, passend: bool, dateien: list[str]) -> bool:
    """Regelfall: Sollstatus erreicht und Solldatei belegt. Prüfung `karte_datei_enthaelt`
    (Summenfragen, die das Werkzeug nicht beantworten kann): erste Belegkarte aus der Liste."""
    if soll.get("pruefung") == "karte_datei_enthaelt":
        return bool(dateien) and dateien[0] in soll.get("dateien", [])
    return antwort.status == soll.get("status") and (soll.get("datei") is None or passend)


def _kategorie_passt(ist: str | None, soll: str, golden: dict, eintrag: dict) -> bool:
    """Synonymlisten: `profil_muss_enthalten.kategorien` als Dict Kanon → Liste (Malerbetrieb),
    `synonyme` als Dict Kanon → Liste, `kategorie_synonyme` je Datei-Eintrag."""
    kanon = golden.get("profil_muss_enthalten", {}).get("kategorien", {})
    synonyme = [
        *(kanon.get(soll, []) if isinstance(kanon, dict) else []),
        *golden.get("synonyme", {}).get(soll, []),
        *eintrag.get("kategorie_synonyme", []),
    ]
    return ist == soll or ist in synonyme


def _anteil(treffer: list[bool]) -> float | None:
    return round(sum(treffer) / len(treffer), 3) if treffer else None


def _soll_vergleich(golden: dict, namen: set[str], ist: dict[str, str], kategorien: dict) -> dict:
    """Status: jede golden-Datei der Stufe. Kategorie: nur Dateien, die das Werkzeug `sicher`
    nennt und für die golden eine Kategorie kennt (misst, ob „sicher" auch richtig ist)."""
    eintraege = {n: e for n, e in _golden_dateien(golden).items() if n in namen}
    status = [ist.get(n) == e["status"] for n, e in eintraege.items() if "status" in e]
    kategorie = [
        _kategorie_passt(kategorien.get(n), e["kategorie"], golden, e)
        for n, e in eintraege.items() if "kategorie" in e and ist.get(n) == "sicher"
    ]
    return {"soll_status_treffer": _anteil(status), "soll_kategorie_treffer": _anteil(kategorie)}


def _belege(vorschlaege: tuple[Vorschlag, ...]) -> dict:
    """`unklar` = vom Modell behauptet, von M8 verworfen; `fehlt` zählt nicht.
    Dateien ohne Modellaufruf (ocr_unsicher) bleiben außen vor."""
    felder = [f for v in vorschlaege if v.status != "ocr_unsicher" for f in v.felder]
    return {
        "belege_gesamt": sum(f.status in ("belegt", "unklar") for f in felder),
        "belege_ungueltig": sum(f.status == "unklar" for f in felder),
    }


def _konflikte(golden: dict, namen: set[str], ist: tuple[Konflikt, ...], name_je_hash: dict) -> dict:
    gefunden = {(k.feld, frozenset((name_je_hash.get(k.hash_a), name_je_hash.get(k.hash_b)))) for k in ist}
    soll = {
        (k["feld"], frozenset(k["dateien"])) for k in golden.get("konflikte", ())
        if set(k["dateien"]) <= namen
    }
    return {
        "konflikte_gefunden": len(gefunden),
        "konflikte_soll": len(soll),
        "konflikte_treffer": len(gefunden & soll),
    }


def kennzahlen(golden: dict, namen: set[str], stand: dict, protokoll: tuple[dict, ...]) -> dict:
    """Alle Messfelder einer Zeile aus dem Phasen-Stand; fehlt eine Phase (Fehler), bleiben
    ihre Felder None/0."""
    vorschlaege: tuple[Vorschlag, ...] = stand.get("vorschlaege", ())
    ist = {**{v.datei_name: v.status for v in vorschlaege}, **dict.fromkeys(stand.get("duplikate", ()), "duplikat")}
    fragen = stand.get("fragen", [])
    return {
        "seiten": stand.get("seiten"),
        "fundstellen": stand.get("fundstellen"),
        "status_verteilung": {s: Counter(ist.values())[s] for s in STATUS},
        "profil": stand.get("profil"),
        "einordnung": {v.datei_name: {"status": v.status, "kategorie": v.kategorie, "typ": v.typ, "zielname": v.zielname}
                       for v in vorschlaege},
        **_soll_vergleich(golden, namen, ist, {v.datei_name: v.kategorie for v in vorschlaege}),
        **_belege(vorschlaege),
        **_konflikte(golden, namen, stand.get("konflikte", ()), {v.datei_hash: v.datei_name for v in vorschlaege}),
        "fragen": fragen,
        "fragen_treffer_quote": _anteil([f["treffer"] for f in fragen]),
        "korrekturen_mensch": sum(e["art"] == "korrektur" for e in protokoll),
        "speicher": stand.get("speicher"),
        "fehler": stand.get("fehler"),
        "zeit_s": stand.get("zeit_s"),
    }


# ---------------------------------------------------------------- Bericht

SPALTEN = (
    "Stufe", "Dateien", "Einordnen s", "s/Datei", "sicher %", "unklar %", "Kategorie-Treffer %",
    "Belege ungültig", "Konflikte ist/soll", "Fragen-Treffer", "Fragen-Dauer Ø s",
)


def lese_laeufe(pfad: Path) -> tuple[dict, ...]:
    if not pfad.exists():
        return ()
    return tuple(json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip())


def _lauf_name(z: dict) -> str:
    """LLM + Embedding: seit 21.09. ist das Embedding Teil des Retrievers (dense allein),
    zwei Läufe mit gleichem LLM und anderem Embedding dürfen sich nicht überschreiben."""
    return f"{z['llm']} · {z['embedding']}" if z.get("embedding") else z["llm"]


def _letzte_je_lauf(zeilen: tuple[dict, ...]) -> dict[tuple[str, int], dict]:
    """Bei Wiederholung derselben (LLM · Embedding, Stufe) zählt die letzte Zeile."""
    return {(_lauf_name(z), z["stufe"]): z for z in zeilen}


def _prozent(wert: float | None) -> str:
    return "–" if wert is None else f"{wert * 100:.0f}"


def _anteil_status(z: dict, status: str) -> str:
    verteilung = z.get("status_verteilung") or {}
    gesamt = sum(verteilung.values())
    return _prozent(verteilung.get(status, 0) / gesamt) if gesamt else "–"


def _zeile(z: dict) -> str:
    if z.get("fehler"):
        f = z["fehler"]
        return f"| {z['stufe']} | {z['dateien']} | FEHLER in {f['phase']}: {f['typ']} — {f['text'][:80]} |"
    einordnen = (z.get("zeit_s") or {}).get("einordnen", 0.0)
    fragen = z.get("fragen") or []
    dauer = sum(f["dauer_s"] for f in fragen) / len(fragen) if fragen else 0.0
    werte = (
        z["stufe"], z["dateien"], f"{einordnen:.1f}",
        f"{einordnen / z['dateien']:.1f}" if z["dateien"] else "–",
        _anteil_status(z, "sicher"), _anteil_status(z, "unklar"), _prozent(z.get("soll_kategorie_treffer")),
        f"{z.get('belege_ungueltig', 0)}/{z.get('belege_gesamt', 0)}",
        f"{z.get('konflikte_gefunden', 0)}/{z.get('konflikte_soll', 0)}",
        f"{sum(f['treffer'] for f in fragen)}/{len(fragen)}", f"{dauer:.1f}",
    )
    return "| " + " | ".join(str(w) for w in werte) + " |"


def _tabelle_llm(llm: str, zeilen: list[dict]) -> str:
    kopf = "| " + " | ".join(SPALTEN) + " |\n|" + "---|" * len(SPALTEN)
    return f"## {llm}\n\n{kopf}\n" + "\n".join(_zeile(z) for z in sorted(zeilen, key=lambda z: z["stufe"]))


def _wo_es_bricht(laeufe: dict[tuple[str, int], dict]) -> str:
    """Matrix Frage × (LLM, Stufe): grün = Treffer, rot = Fehltreffer, – = nicht gestellt."""
    schluessel = sorted(laeufe, key=lambda s: (s[0], s[1]))
    fragen: list[str] = []
    for z in laeufe.values():
        fragen.extend(f["frage"] for f in z.get("fragen") or [] if f["frage"] not in fragen)
    kopf = "| Frage | " + " | ".join(f"{llm} @{stufe}" for llm, stufe in schluessel) + " |\n|---|" + "---|" * len(schluessel)
    zeilen = []
    for frage in fragen:
        zellen = []
        for s in schluessel:
            treffer = {f["frage"]: f["treffer"] for f in laeufe[s].get("fragen") or []}
            zellen.append("–" if frage not in treffer else ("grün" if treffer[frage] else "rot"))
        zeilen.append(f"| {frage} | " + " | ".join(zellen) + " |")
    return "## Wo es bricht\n\n" + kopf + "\n" + "\n".join(zeilen)


def baue_bericht(zeilen: tuple[dict, ...]) -> str:
    laeufe = _letzte_je_lauf(zeilen)
    llms = list(dict.fromkeys(llm for llm, _ in laeufe))
    tabellen = [_tabelle_llm(llm, [z for (l, _), z in laeufe.items() if l == llm]) for llm in llms]
    return "# Belastungstest\n\n" + "\n\n".join([*tabellen, _wo_es_bricht(laeufe)]) + "\n"


def schreibe_bericht(ordner: Path) -> Path:
    zeilen = lese_laeufe(Path(ordner) / "laeufe.jsonl")
    ziel = Path(ordner) / "bericht.md"
    ziel.write_text(baue_bericht(zeilen), encoding="utf-8")
    return ziel
