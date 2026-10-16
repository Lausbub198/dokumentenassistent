"""Belastungstest: je (Stufe × LLM) ein voller Werkstatt-Lauf in frischen Temp-Ordnern,
eine JSON-Zeile je Lauf (append-only), Bericht daraus. Ausgabeformat: beweise/last/README.md.

    uv run python -m dokumentenassistent.lasttest --korpus beispiele/malerbetrieb \\
        --stufen 10 25 50 100 --llm qwen3.5:9b qwen3:4b --embedding bge-m3 --ausgabe beweise/last/
    uv run python -m dokumentenassistent.lasttest --bericht beweise/last/2026-09-19/

Mit Reranker (braucht `uv sync --extra reranker`):

    uv run python -m dokumentenassistent.lasttest --korpus beispiele/malerbetrieb --stufen 200 \\
        --llm gemma4:12b-it-q4_K_M --embedding bge-m3 \\
        --reranker BAAI/bge-reranker-v2-m3 --rerank-k 20 --rerank-geraet mps --top-n 8 \\
        --ausgabe beweise/last/
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from dokumentenassistent.lasttest_bericht import (
    frage_zeile,
    kennzahlen,
    schreibe_bericht,
)
from dokumentenassistent.provider import OllamaProvider, Sucheinstellungen
from dokumentenassistent.werkstatt import Werkstatt

ARTEN = ("embed", "generate_json", "generate_text")


class Protokollierender:
    """Zählt Modellaufrufe und Modellzeit je Art; delegiert an den echten Provider."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.zaehler: dict[str, int] = dict.fromkeys(ARTEN, 0)
        self.sekunden: dict[str, float] = dict.fromkeys(ARTEN, 0.0)

    def _messe(self, art: str, fn: Callable, *args):
        start = time.perf_counter()
        try:
            return fn(*args)
        finally:
            self.zaehler[art] += 1
            self.sekunden[art] += time.perf_counter() - start

    def embed(self, texte: list[str]) -> list[list[float]]:
        return self._messe("embed", self.inner.embed, texte)

    def embedding_revision(self) -> str:
        return self.inner.embedding_revision()

    def generate_json(self, prompt: str, schema: dict) -> dict:
        return self._messe("generate_json", self.inner.generate_json, prompt, schema)

    def generate_text(self, prompt: str) -> str:
        return self._messe("generate_text", self.inner.generate_text, prompt)


# ------------------------------------------------------------------ Stufe


def _golden_dateien(golden: dict) -> dict[str, dict]:
    return {**golden.get("dateien", {}), **golden.get("weitere_dateien", {})}


def stufen_aus_golden(golden: dict) -> list[int]:
    """`stufen` ist ein Dict Stufe → Pfadliste (Malerbetrieb) oder eine Liste von Zahlen."""
    stufen = golden.get("stufen") or []
    return sorted(int(s) for s in (stufen.keys() if isinstance(stufen, dict) else stufen))


def waehle_dateien(korpus: Path, golden: dict, stufe: int) -> tuple[Path, ...]:
    """Dateien der Stufe, in dieser Reihenfolge: `golden.stufen[str(stufe)]` als Liste relativer
    Pfade; sonst `ab_stufe <= stufe` je golden-Eintrag (Dateien ohne Angabe immer dabei);
    sonst die ersten `stufe` Dateien in Pfadreihenfolge."""
    stufen = golden.get("stufen")
    if isinstance(stufen, dict) and str(stufe) in stufen:
        return tuple(sorted(korpus / p for p in stufen[str(stufe)]))
    alle = tuple(
        p for p in sorted(korpus.rglob("*"))
        if p.is_file() and not any(t.startswith(".") for t in p.relative_to(korpus).parts)
        and p.name != "golden.json"
    )
    eintraege = _golden_dateien(golden)
    ab_stufe = {p: eintraege.get(p.name, {}).get("ab_stufe") for p in alle}
    if any(s is not None for s in ab_stufe.values()):
        return tuple(p for p in alle if (ab_stufe[p] or 0) <= stufe)
    return alle[:stufe]


def kopiere_stufe(korpus: Path, golden: dict, stufe: int, ziel: Path) -> tuple[Path, ...]:
    """Kopiert die Dateien der Stufe (relative Pfade erhalten) — der Korpus wird nur gelesen."""
    kopien = []
    for quelle in waehle_dateien(korpus, golden, stufe):
        kopie = ziel / quelle.relative_to(korpus)
        kopie.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(quelle, kopie)
        kopien.append(kopie)
    return tuple(kopien)


def fragen_der_stufe(golden: dict, stufe: int) -> tuple[dict, ...]:
    return tuple(f for f in golden.get("fragen", ()) if f.get("ab_stufe", 0) <= stufe)


# ----------------------------------------------------------------- Phasen


def _p_erfassen(w: Werkstatt, golden: dict, stufe: int) -> dict:
    w.erfassen()
    return {}


def _p_auslesen(w: Werkstatt, golden: dict, stufe: int) -> dict:
    je_datei = w.auslesen()
    alle = [f for fs in je_datei.values() for f in fs]
    return {"seiten": len({(f.datei_hash, f.seite) for f in alle}), "fundstellen": len(alle)}


def _p_profil(w: Werkstatt, golden: dict, stufe: int) -> dict:
    profil = w.profil_vorschlagen(golden["zweck"])
    w.profil_bestaetigen(profil)
    return {"profil": {"kategorien": list(profil.kategorien), "dokumenttypen": list(profil.dokumenttypen),
                       "felder": list(profil.felder), "namensschema": profil.namensschema}}


def _p_einordnen(w: Werkstatt, golden: dict, stufe: int) -> dict:
    vorschlaege = w.einordnen()
    return {
        "vorschlaege": vorschlaege,
        "konflikte": w.index.konflikte(),
        "duplikate": tuple(d.name for d in w.index.duplikate()),
    }


def _p_konflikte(w: Werkstatt, golden: dict, stufe: int) -> dict:
    for k in w.index.konflikte(offen=True):
        w.entscheide_konflikt(k.id, "ersetzt")
    return {}


def _p_freigeben(w: Werkstatt, golden: dict, stufe: int) -> dict:
    return {"freigegeben": len(w.freigeben(tuple(d.hash for d in w.index.dateien())))}


def _p_fragen(w: Werkstatt, golden: dict, stufe: int) -> dict:
    ergebnisse = []
    for soll in fragen_der_stufe(golden, stufe):
        start = time.perf_counter()
        antwort = w.frage(soll["frage"])
        ergebnisse.append(frage_zeile(soll, antwort, time.perf_counter() - start))
    return {"fragen": ergebnisse}


PHASEN: tuple[tuple[str, Callable[[Werkstatt, dict, int], dict]], ...] = (
    ("erfassen", _p_erfassen),
    ("auslesen", _p_auslesen),
    ("profil_vorschlagen", _p_profil),
    ("einordnen", _p_einordnen),
    ("konflikte_entscheiden", _p_konflikte),
    ("freigeben", _p_freigeben),
    ("fragen", _p_fragen),
)


def _fahre(w: Werkstatt, golden: dict, stufe: int, speicher: Callable[[], str]) -> dict:
    """Phasen der Reihe nach; ein Fehler beendet diesen Lauf und steht als `fehler` in der Zeile."""
    zeiten: dict[str, float] = {}
    stand: dict = {}
    for name, schritt in PHASEN:
        start = time.perf_counter()
        try:
            stand = {**stand, **schritt(w, golden, stufe)}
        except Exception as e:  # noqa: BLE001 — jede Ursache gehört in die Zeile, der nächste Lauf startet
            stand = {**stand, "fehler": {"phase": name, "typ": type(e).__name__, "text": str(e)}}
            break
        finally:
            zeiten[name] = round(time.perf_counter() - start, 3)
        if name == "einordnen":
            stand = {**stand, "speicher": speicher()}
    return {**stand, "zeit_s": {**zeiten, "gesamt": round(sum(zeiten.values()), 3)}}


# ------------------------------------------------------------------- Lauf


def ollama_ps() -> str:
    return _befehl("ollama", "ps")


def lauf(
    korpus: Path, golden: dict, stufe: int, provider, ausgabe: Path,
    *, llm: str = "", embedding: str = "", speicher: Callable[[], str] = ollama_ps,
    provider_suche=None, llm_suche: str = "",
    sucheinstellungen: Sucheinstellungen | None = None, reranker_name: str = "",
) -> dict:
    """Ein Lauf in frischen Temp-Ordnern; hängt genau eine Zeile an `ausgabe/laeufe.jsonl` an.

    `provider_suche` misst die Aufteilung, die der Assistent seit dem 21.09. kennt:
    ein Modell ordnet ein, ein anderes beantwortet Fragen. Gemessen am 22.09.
    (Stufe 200): gemma4:12b bringt 159 von 163 soll-sicheren Dateien in den Index,
    qwen3.5:4b nur 127 -- was nicht eingeordnet ist, findet auch der beste
    Retriever nicht.

    `sucheinstellungen` misst den Reranker (23.09.): auf beiden Korpora die einzige
    Massnahme, die Rang 1 hebt -- malerbetrieb Stufe 200 R@1 79 -> 93, GermanQuAD
    88 -> 98 (bge-reranker-v2-m3, k=20). `reranker_name` steht nur in der Zeile;
    das Objekt selbst hat keinen Namen, den der Bericht lesen koennte."""
    messung = Protokollierender(provider)
    messung_suche = Protokollierender(provider_suche) if provider_suche is not None else None
    einstellungen = sucheinstellungen or Sucheinstellungen()
    with tempfile.TemporaryDirectory(prefix="lasttest_") as tmp:
        basis = Path(tmp)
        kopien = kopiere_stufe(Path(korpus), golden, stufe, basis / "quelle")
        w = Werkstatt(basis / "quelle", basis / "ablage", messung, arbeitsordner=basis / "arbeit",
                      provider_suche=messung_suche, sucheinstellungen=einstellungen)
        stand = _fahre(w, golden, stufe, speicher)
        zeile = {
            "zeit": datetime.now().isoformat(timespec="seconds"),
            "stufe": stufe, "llm": llm, "llm_suche": llm_suche or None,
            "embedding": embedding, "kontext": getattr(provider, "kontext", None), "dateien": len(kopien),
            "reranker": reranker_name or None,
            "rerank_k": einstellungen.rerank_k, "top_n": einstellungen.top_n,
            **kennzahlen(golden, {k.name for k in kopien}, stand, w.index.protokoll()),
            "modellaufrufe": dict(messung.zaehler),
            "modellzeit_s": {a: round(s, 3) for a, s in messung.sekunden.items()},
            "modellaufrufe_suche": dict(messung_suche.zaehler) if messung_suche else None,
            "modellzeit_suche_s": ({a: round(s, 3) for a, s in messung_suche.sekunden.items()}
                                   if messung_suche else None),
        }
    Path(ausgabe).mkdir(parents=True, exist_ok=True)
    with (Path(ausgabe) / "laeufe.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    return zeile


# -------------------------------------------------------------- Umgebung


def _befehl(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=30, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError) as e:
        return f"nicht ermittelbar ({e})"


def _ollama_umgebung() -> str:
    """Ollama-Variablen, die Messungen verfaelschen koennen (KV-Cache-Typ, Flash Attention,
    Parallelitaet, Modellpfad) — aus dem LaunchAgent und der Prozessumgebung, sonst 'Standard'."""
    zeilen = []
    plist = Path.home() / "Library/LaunchAgents/local.ollama-env.plist"
    text = plist.read_text(encoding="utf-8") if plist.exists() else ""
    for name in ("OLLAMA_KV_CACHE_TYPE", "OLLAMA_FLASH_ATTENTION", "OLLAMA_NUM_PARALLEL", "OLLAMA_MODELS", "OLLAMA_CONTEXT_LENGTH"):
        wert = _befehl("launchctl", "getenv", name)
        if not wert and f"<string>{name}</string>" in text:
            wert = text.split(f"<string>{name}</string>", 1)[1].split("<string>", 1)[1].split("</string>", 1)[0]
        zeilen.append(f"- {name}: {wert or 'nicht gesetzt (Ollama-Standard)'}")
    zeilen.append("- KV-Cache: f16 (Standard), solange OLLAMA_KV_CACHE_TYPE nicht gesetzt ist")
    return "\n".join(zeilen)


def schreibe_umgebung(ordner: Path) -> None:
    batt = "\n".join(_befehl("pmset", "-g", "batt").splitlines()[:2])
    ram = _befehl("sysctl", "-n", "hw.memsize")
    ram_gb = f"{int(ram) / 2**30:.0f} GB" if ram.isdigit() else ram
    (ordner / "umgebung.md").write_text(
        "# Umgebung des Belastungstests\n\n"
        f"- Zeit (lokal): {datetime.now().isoformat(timespec='seconds')}\n"
        f"- ollama --version: {_befehl('ollama', '--version')}\n"
        f"- macOS: {_befehl('sw_vers', '-productVersion')}\n"
        f"- Rechner: {_befehl('sysctl', '-n', 'hw.model')}, RAM {ram_gb}\n"
        f"- Netzteil angeschlossen: {'ja' if 'AC Power' in batt else 'nein'}\n"
        f"- pmset -g batt:\n\n```\n{batt}\n```\n\n"
        f"## Ollama-Umgebung\n\n{_ollama_umgebung()}\n",
        encoding="utf-8",
    )


# ------------------------------------------------------------------- CLI


def _argumente(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--korpus", type=Path, help="Ordner mit Dateien (oder Unterordner Quelle/) und golden.json")
    p.add_argument("--golden", type=Path, help="Sollwerte; Standard: <korpus>/golden.json")
    p.add_argument("--stufen", type=int, nargs="+", help="Standard: golden['stufen'], sonst alle Dateien")
    p.add_argument("--llm", nargs="+", default=["qwen3.5:9b"])
    p.add_argument("--llm-suche", default=None,
                   help="eigenes Modell nur fuer die Frage-Antwort-Suche; Standard: wie --llm")
    p.add_argument("--embedding", default="bge-m3")
    p.add_argument("--host", default="http://localhost:11434")
    p.add_argument("--kontext", type=int, default=None, help="num_ctx fuer das LLM; Standard: Ollama (4096)")
    p.add_argument("--reranker", default=None,
                   help="HF-Id eines Cross-Encoders, z. B. BAAI/bge-reranker-v2-m3; "
                        "Standard: keiner (heutiges Verhalten). Gemessen 22.09.: R@1 79 -> 93 "
                        "(malerbetrieb 200) und 88 -> 98 (GermanQuAD)")
    p.add_argument("--rerank-k", type=int, default=20,
                   help="wie viele dense-Treffer der Reranker neu sortiert (Standard 20 = die gemessene Zahl)")
    p.add_argument("--rerank-geraet", default=None, choices=["mps", "cpu"],
                   help="Standard: automatisch (mps auf Apple Silicon). 0,5 s/Frage auf MPS, 3-10 s auf CPU")
    p.add_argument("--top-n", type=int, default=8, help="Absaetze im Prompt; Standard 8")
    p.add_argument("--ausgabe", type=Path, default=Path("beweise/last"))
    p.add_argument("--bericht", type=Path, help="nur Bericht aus <ordner>/laeufe.jsonl schreiben")
    args = p.parse_args(argv)
    if args.bericht is None and args.korpus is None:
        p.error("--korpus oder --bericht angeben")
    return args


def main(argv: list[str] | None = None) -> None:
    args = _argumente(argv)
    if args.bericht is not None:
        print(schreibe_bericht(args.bericht))
        return
    golden = json.loads((args.golden or args.korpus / "golden.json").read_text(encoding="utf-8"))
    korpus = args.korpus / "Quelle" if (args.korpus / "Quelle").is_dir() else args.korpus
    ordner = args.ausgabe / date.today().isoformat()
    ordner.mkdir(parents=True, exist_ok=True)
    if not (ordner / "umgebung.md").exists():
        schreibe_umgebung(ordner)
    stufen = args.stufen or stufen_aus_golden(golden) or [len(waehle_dateien(korpus, golden, 10**9))]
    # Cross-Encoder einmal vor der Schleife laden, nicht je Lauf: das Modell ist ueber alle
    # Stufen dasselbe, und ein fehlendes Extra soll vor dem ersten Lauf auffallen, nicht danach.
    from dokumentenassistent.provider import CrossEncoderReranker

    einstellungen = Sucheinstellungen(
        reranker=CrossEncoderReranker(args.reranker, args.rerank_geraet) if args.reranker else None,
        rerank_k=args.rerank_k,
        top_n=args.top_n,
    )
    for llm in args.llm:
        provider = OllamaProvider(args.host, args.embedding, llm, think=False, timeout=900, kontext=args.kontext)
        p_suche = (OllamaProvider(args.host, args.embedding, args.llm_suche, think=False,
                                  timeout=900, kontext=args.kontext)
                   if args.llm_suche and args.llm_suche != llm else None)
        for stufe in stufen:
            print(f"[{llm}{' + ' + args.llm_suche if p_suche else ''}] Stufe {stufe} …", flush=True)
            z = lauf(korpus, golden, stufe, provider, ordner, llm=llm, embedding=args.embedding,
                     provider_suche=p_suche, llm_suche=args.llm_suche if p_suche else "",
                     sucheinstellungen=einstellungen, reranker_name=args.reranker or "")
            print(f"  {z['dateien']} Dateien, {z['zeit_s']['gesamt']} s, fehler={z['fehler']}", flush=True)
    print(schreibe_bericht(ordner))


if __name__ == "__main__":
    main()
