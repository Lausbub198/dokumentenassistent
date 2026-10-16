"""Warum ist MLX mal schneller, mal langsamer? Isolationstest (geplant 21.09.2026, gemessen ab 06.10.2026).

Befund damals: LM Studio MLX generierte bei kurzen Prompts schneller als Ollama (80–91 gegen 77–82 tok/s),
brauchte beim Einordnen aber 48 s je Datei gegen 10 s. Drei Hypothesen: (1) Prefill langer Prompts,
(2) erzwungenes JSON-Schema, (3) Laufzeit-Overhead. Dieser Test trennt sie: vier Anfragearten je
Konfiguration — kurzer/langer Prompt × Freitext/Schema —, gleiche Prompts für alle Laufzeiten.

Prompts aus öffentlichen GermanQuAD-Absätzen (CC-BY-4.0), nie aus dem privaten Bestand. Gemessen wird die
Wandzeit je Aufruf über den Produkt-Provider (also inklusive Protokoll-Overhead); der erste Aufruf jeder
Konfiguration ist Aufwärmen und zählt nicht.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time
from dokumentenassistent.pfade_privat import GERMANQUAD, LAEUFE

SCHEMA = {"type": "object", "properties": {"thema": {"type": "string"}, "jahr": {"type": "string"}},
          "required": ["thema", "jahr"]}
AUFTRAG = "Nenne in einem Satz das Thema der folgenden Absätze und eine darin genannte Jahreszahl.\n\n"


def prompts(bestand: Path, kurz_woerter: int = 150, lang_woerter: int = 7000) -> dict[str, str]:
    # exFAT legt neben jede Datei eine macOS-Hilfsdatei „._*" — die ist kein Text (07.10.: UnicodeDecodeError)
    texte = [p.read_text(encoding="utf-8") for p in sorted(bestand.glob("*.txt")) if not p.name.startswith("._")]
    woerter = " ".join(texte).split()
    return {"kurz": AUFTRAG + " ".join(woerter[:kurz_woerter]), "lang": AUFTRAG + " ".join(woerter[:lang_woerter])}


def miss(provider, p: dict[str, str], wiederholungen: int) -> dict:
    arten = {"kurz_text": lambda: provider.generate_text(p["kurz"]),
             "lang_text": lambda: provider.generate_text(p["lang"]),
             "kurz_json": lambda: provider.generate_json(p["kurz"], SCHEMA),
             "lang_json": lambda: provider.generate_json(p["lang"], SCHEMA)}
    arten["kurz_text"]()  # Aufwärmen: Modell laden
    raus = {}
    for name, aufruf in arten.items():
        zeiten = []
        try:
            for _ in range(wiederholungen):
                start = time.monotonic()
                aufruf()
                zeiten.append(time.monotonic() - start)
        except Exception as fehler:  # eine Laufzeit ohne Schema-Unterstützung ist ein Befund, kein Abbruch
            raus[name] = {"fehler": f"{type(fehler).__name__}: {str(fehler)[:160]}"}
            continue
        raus[name] = {"median_s": round(statistics.median(zeiten), 2), "min_s": round(min(zeiten), 2),
                      "max_s": round(max(zeiten), 2)}
    return raus


def main() -> None:
    from dokumentenassistent.provider import lade_modelle
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("modelle", nargs="+", type=Path, help="je Konfiguration eine modelle.yaml")
    a.add_argument("--bestand", type=Path, default=GERMANQUAD / "bestand")
    a.add_argument("--wiederholungen", type=int, default=3)
    a.add_argument("--ausgabe", type=Path, default=LAEUFE / "laufzeit-vergleich.json")
    args = a.parse_args()
    p = prompts(args.bestand)
    bericht = json.loads(args.ausgabe.read_text()) if args.ausgabe.exists() else {}
    for pfad in args.modelle:
        prov = lade_modelle(pfad)
        schluessel = f"{type(prov).__name__}:{prov.llm_modell}"
        bericht[schluessel] = miss(prov, p, args.wiederholungen)
        args.ausgabe.write_text(json.dumps(bericht, indent=1))
        print(schluessel, json.dumps(bericht[schluessel]), flush=True)


if __name__ == "__main__":
    main()
