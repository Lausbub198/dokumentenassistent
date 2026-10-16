"""Retrieval-Eval: misst `dense` (= Suchpfad von `suche.py` seit 21.09.) sowie die Vergleichs-
varianten BM25/Hybrid aus `suche.py` und `retrieval_varianten.py` (gewichtete RRF, BM25 mit
Komposita/Präfix), ohne LLM. Regressionstest für den Retriever: Stufe 200, qwen3-embedding:0.6b,
`dense` muss 79/93/93 (±1 Frage) zeigen.

Fundstellen entstehen wie in `werkstatt.py` (M2 erfassen + M3/M4 auslesen/zerlegen),
ohne Profil/Einordnen. Golden-Fragen mit `status == "gefunden"` liefern den Rang der
ersten Fundstelle aus der Solldatei je Variante; `status == "nicht_gefunden"`-Fragen
zeigen, ob der Top-Score unter der Schwelle bleibt (korrekt abgewiesen).

Zweiter Korpus seit 22.09.2026: `--germanquad` nimmt Fundstellen und Fragen aus
`germanquad.lade()` statt aus einem Ordner — **unabhängige menschliche Fragen zu fremden
Texten**, weil `beispiele/malerbetrieb` synthetisch ist (Dokumente UND Fragen von derselben
Quelle erzeugt, siehe `germanquad.py`). Alles andere bleibt identisch: dieselben Varianten,
dieselben Embeddings, dieselben Kennzahlen, derselbe Bericht. Dort ist der Treffer zusätzlich
**absatzgenau** messbar (`absatz_id` je Frage, Kennzahlen unter `absatzgenau`), bei
malerbetrieb nur dateigenau.

    uv run python -m dokumentenassistent.retrieval_eval --korpus beispiele/malerbetrieb --stufe 25 \\
        --embedding bge-m3 nomic-embed-text qwen3-embedding:0.6b --ausgabe beweise/retrieval/
    uv run --extra eval python -m dokumentenassistent.retrieval_eval --germanquad --fragen 200 \\
        --embedding qwen3-embedding:0.6b --ausgabe beweise/retrieval/
    uv run python -m dokumentenassistent.retrieval_eval --bericht beweise/retrieval/<datum>/
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from dokumentenassistent import germanquad
from dokumentenassistent.lasttest import fragen_der_stufe, kopiere_stufe
from dokumentenassistent.provider import ModelProvider, OllamaProvider
from dokumentenassistent.retrieval_eval_bericht import schreibe_bericht
from dokumentenassistent.retrieval_reranker import CrossEncoderReranker, Reranker, kurzname, rerank
from dokumentenassistent.retrieval_varianten import (
    HYBRID_VARIANTEN,
    LEXIKALISCHE_VARIANTEN,
    rrf_gewichtet,
    vokabular_der_fundstellen,
)
from dokumentenassistent.suche import SCHWELLE, Paare, Rangliste, bm25_rang, dense_rang, rrf
from dokumentenassistent.typen import DokumentenassistentFehler, Fundstelle
from dokumentenassistent.werkstatt import Werkstatt

# SCHWELLE kommt aus `suche.py` (Kosinus, seit 21.09.). Die `nicht_gefunden_treffer_quote` ist damit
# nur für `dense` aussagekräftig; RRF-Punkte der Hybrid-Varianten liegen immer darunter.

# M4 (Reranker, docs/retrieval-massnahmen-2026-09-21.md): Top-k der dense-Liste, die vom
# Cross-Encoder neu sortiert wird. Zwei Werte, damit man sieht, ob mehr Kontext hilft oder nur
# mehr Rechenzeit kostet.
RERANK_K = (8, 20)


class RetrievalEvalFehler(DokumentenassistentFehler):
    """Fehlende golden.json, fehlende Datei oder leere Fundstellenmenge."""


# ------------------------------------------------------------------- Golden


def golden_filter(fragen: tuple[dict, ...]) -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    """(gefunden, nicht_gefunden) — nur diese beiden Sollstatus zählen fürs Retrieval-Eval.
    Fragen mit Sonderprüfung (z. B. `karte_datei_enthaelt` für Summenfragen) bleiben außen vor."""
    gefunden = tuple(f for f in fragen if f.get("status") == "gefunden" and f.get("datei"))
    nicht_gefunden = tuple(f for f in fragen if f.get("status") == "nicht_gefunden")
    return gefunden, nicht_gefunden


# --------------------------------------------------------------- Ranglisten


def rang_der_datei(rangliste: Rangliste, fundstellen_je_id: dict[str, Fundstelle], datei: str) -> int | None:
    """1-basierter Rang der ersten Fundstelle aus `datei` in der Rangliste, sonst None."""
    for rang, (id_, _score) in enumerate(rangliste, start=1):
        if fundstellen_je_id[id_].datei_name == datei:
            return rang
    return None


def rang_des_absatzes(rangliste: Rangliste, absatz_id: str) -> int | None:
    """1-basierter Rang genau dieser Fundstelle, sonst None.

    Der schärfere Maßstab: `rang_der_datei` ist zufrieden, sobald *irgendein* Absatz der
    richtigen Datei oben steht — bei `beispiele/malerbetrieb` ist das der einzige mögliche
    Maßstab, weil golden.json nur die Datei kennt. GermanQuAD nennt den Zielabsatz selbst
    (`absatz_id`), deshalb wird dort beides getrennt ausgewiesen. Dass beide Zahlen bei
    GermanQuAD zusammenfallen, ist kein Zufall, sondern Bauart (eine Korpuszeile = eine
    Fundstelle) — und genau das prüft `tests/test_retrieval_eval.py::test_R13_...`.
    """
    for rang, (id_, _score) in enumerate(rangliste, start=1):
        if id_ == absatz_id:
            return rang
    return None


def ranglisten_frage(
    frage: str, fundstellen: tuple[Fundstelle, ...], paare: Paare, provider: ModelProvider
) -> dict[str, Rangliste]:
    """bm25/dense/hybrid Ranglisten für eine Frage; genau ein Embed-Aufruf für den Fragevektor."""
    bm25 = bm25_rang(frage, fundstellen)
    frage_vektor = provider.embed([frage])[0]
    dense = dense_rang(frage_vektor, paare)
    return {"bm25": bm25, "dense": dense, "hybrid": rrf((bm25, dense))}


# ---------------------------------------------------------------- Kennzahlen


# Recall-Fenster. 1/5/8 sind die bisher berichteten; 3/12/20 kamen am 23.09.2026 dazu,
# weil `top_n` (8) und `rerank_k` (20) nie gemessen waren — ohne @3/@12/@20 lässt sich die
# Wahl des Prompt-Fensters nicht auf Daten stützen, sondern nur auf den alten Default.
RECALL_K = (1, 3, 5, 8, 12, 20)


def kennzahlen_variante(raenge: list[int | None]) -> dict:
    """Recall@1/3/5/8/12/20 und MRR über eine Liste Ränge (None = Solldatei nicht in der Rangliste)."""
    n = len(raenge)
    if not n:
        return {**{f"recall_at_{k}": None for k in RECALL_K}, "mrr": None}

    def recall(k: int) -> float:
        return round(sum(1 for r in raenge if r is not None and r <= k) / n, 3)

    mrr = round(sum((1.0 / r) if r else 0.0 for r in raenge) / n, 3)
    return {**{f"recall_at_{k}": recall(k) for k in RECALL_K}, "mrr": mrr}


def nicht_gefunden_quote(top_scores: list[float], schwelle: float = SCHWELLE) -> float | None:
    """Anteil der `nicht_gefunden`-Fragen, deren Top-Score unter der Schwelle liegt
    (= korrekt abgewiesen, wie `suche()` es täte)."""
    if not top_scores:
        return None
    return round(sum(1 for s in top_scores if s < schwelle) / len(top_scores), 3)


# -------------------------------------------------------------- Fundstellen


def fundstellen_der_stufe(
    korpus: Path, golden: dict, stufe: int, provider: ModelProvider, arbeitsordner: Path
) -> tuple[Fundstelle, ...]:
    """M2 (erfassen) + M3/M4 (auslesen → zerlegen) über die Werkstatt — ohne Profil, Einordnen
    oder Modellaufruf. `provider` wird nur durchgereicht (Werkstatt-Konstruktor verlangt ihn),
    `erfassen`/`auslesen` rufen ihn nicht auf."""
    quelle = Path(arbeitsordner) / "quelle"
    quelle.mkdir(parents=True, exist_ok=True)
    kopiere_stufe(Path(korpus), golden, stufe, quelle)
    w = Werkstatt(quelle, Path(arbeitsordner) / "ablage", provider, arbeitsordner=Path(arbeitsordner) / "arbeit")
    w.erfassen()
    je_datei = w.auslesen()
    fundstellen = tuple(f for fs in je_datei.values() for f in fs)
    if not fundstellen:
        raise RetrievalEvalFehler(f"Keine Fundstellen in Stufe {stufe} von {korpus}")
    return fundstellen


# ------------------------------------------------------------------- Zeilen


def _variante_zeile(
    variante: str, embedding: str | None, korpus: Path, stufe: int, fundstellenzahl: int,
    gefunden: tuple[dict, ...], nicht_gefunden: tuple[dict, ...],
    ranglisten_je_frage: dict[str, Rangliste], fundstellen_je_id: dict[str, Fundstelle],
    dauer_je_frage: dict[str, float], embed_sekunden: float | None, host: str, schwelle: float,
    rerank_dauer_je_frage: dict[str, float] | None = None,
) -> dict:
    def top_score(frage: str) -> float:
        rangliste = ranglisten_je_frage[frage]
        return round(rangliste[0][1], 4) if rangliste else 0.0

    raenge: list[int | None] = []
    raenge_absatz: list[int | None] = []
    fragenzeilen: list[dict] = []
    for f in gefunden:
        rangliste = ranglisten_je_frage[f["frage"]]
        rang = rang_der_datei(rangliste, fundstellen_je_id, f["datei"])
        raenge.append(rang)
        zeile_frage = {
            "frage": f["frage"], "datei_soll": f["datei"], "rang": rang,
            "treffer_at_8": rang is not None and rang <= 8,
            "top_score": top_score(f["frage"]),
            "dauer_s": round(dauer_je_frage.get(f["frage"], 0.0), 4),
        }
        # Nur GermanQuAD kennt den Zielabsatz; malerbetrieb-Fragen nennen nur die Datei und
        # bekommen deshalb weiterhin genau die Felder von vorher (Zeilen bleiben vergleichbar).
        if f.get("absatz_id"):
            rang_absatz = rang_des_absatzes(rangliste, f["absatz_id"])
            raenge_absatz.append(rang_absatz)
            zeile_frage["absatz_soll"] = f["absatz_id"]
            zeile_frage["rang_absatz"] = rang_absatz
        if rerank_dauer_je_frage is not None:
            zeile_frage["rerank_sekunden"] = round(rerank_dauer_je_frage.get(f["frage"], 0.0), 4)
        fragenzeilen.append(zeile_frage)
    # top_score je Frage beider Klassen: Datengrundlage für `suche.SCHWELLE` (Ableitung dort im Kommentar).
    nicht_gefunden_zeilen = [{"frage": f["frage"], "top_score": top_score(f["frage"])} for f in nicht_gefunden]
    top_scores = [z["top_score"] for z in nicht_gefunden_zeilen]
    dauern = list(dauer_je_frage.values())
    dauer_avg = round(sum(dauern) / len(dauern), 4) if dauern else 0.0
    return {
        "datum": date.today().isoformat(), "korpus": str(korpus), "stufe": stufe,
        "embedding": embedding, "variante": variante, "fundstellenzahl": fundstellenzahl,
        "fragenzahl": len(gefunden), "fragenzahl_nicht_gefunden": len(nicht_gefunden),
        "embed_sekunden": round(embed_sekunden, 3) if embed_sekunden is not None else None,
        **kennzahlen_variante(raenge),
        "nicht_gefunden_treffer_quote": nicht_gefunden_quote(top_scores, schwelle),
        "dauer_s_frage_avg": dauer_avg, "host": host, "fragen": fragenzeilen,
        "nicht_gefunden_fragen": nicht_gefunden_zeilen,
        **({"absatzgenau": kennzahlen_variante(raenge_absatz)} if raenge_absatz else {}),
    }


ZeilenBauer = Callable[..., dict]


def _je_frage(alle_fragen: tuple[dict, ...], rangliste: Callable[[str], Rangliste]) -> tuple[dict, dict]:
    """Rangliste und Dauer je Frage für eine Variante."""
    ranglisten: dict[str, Rangliste] = {}
    dauern: dict[str, float] = {}
    for f in alle_fragen:
        start = time.perf_counter()
        ranglisten[f["frage"]] = rangliste(f["frage"])
        dauern[f["frage"]] = time.perf_counter() - start
    return ranglisten, dauern


def _lexikalisch_je_variante(
    alle_fragen: tuple[dict, ...], fundstellen: tuple[Fundstelle, ...]
) -> dict[str, tuple[dict, dict]]:
    """bm25, bm25_komposita, bm25_praefix — embedding-unabhängig, einmal je Lauf."""
    vokabular = vokabular_der_fundstellen(fundstellen)
    return {
        name: _je_frage(alle_fragen, lambda frage, fn=fn: fn(frage, fundstellen, vokabular))
        for name, fn in LEXIKALISCHE_VARIANTEN.items()
    }


def _zeilen_embedding(
    embedding: str, fundstellen: tuple[Fundstelle, ...], alle_fragen: tuple[dict, ...],
    lexikalisch: dict[str, tuple[dict, dict]], provider: ModelProvider, zeile: ZeilenBauer,
    fundstellen_je_id: dict[str, Fundstelle], reranker_je_modell: dict[str, Reranker],
    reranker_k: tuple[int, ...],
) -> list[dict]:
    """dense einmal je Embedding, dann jede Hybrid-Variante und jede Reranker-Variante
    (`dense_rerank_<kurzname>_k<K>`) aus derselben dense-Liste."""
    start = time.perf_counter()
    vektoren = provider.embed([f.text for f in fundstellen])
    embed_sekunden = time.perf_counter() - start
    paare = tuple(zip(fundstellen, vektoren))
    dense, dauern = _je_frage(alle_fragen, lambda frage: dense_rang(provider.embed([frage])[0], paare))
    zeilen = [zeile("dense", embedding, dense, dauern, embed_sekunden)]
    for name, (lex_name, gewicht) in HYBRID_VARIANTEN.items():
        lex = lexikalisch[lex_name][0]
        fusion = {frage: rrf_gewichtet(((lex[frage], gewicht), (dense[frage], 1.0))) for frage in dense}
        zeilen.append(zeile(name, embedding, fusion, dauern, embed_sekunden))
    zeilen.extend(_zeilen_reranker(
        embedding, dense, alle_fragen, fundstellen_je_id, reranker_je_modell, reranker_k, zeile,
    ))
    return zeilen


def _zeilen_reranker(
    embedding: str, dense: dict[str, Rangliste], alle_fragen: tuple[dict, ...],
    fundstellen_je_id: dict[str, Fundstelle], reranker_je_modell: dict[str, Reranker],
    reranker_k: tuple[int, ...], zeile: ZeilenBauer,
) -> list[dict]:
    """`dense_rerank_<kurzname>_k<K>` je Reranker-Modell × K, dieselbe dense-Liste wiederverwendet."""
    zeilen: list[dict] = []
    for modell, reranker in reranker_je_modell.items():
        for k in reranker_k:
            ranglisten: dict[str, Rangliste] = {}
            rerank_dauern: dict[str, float] = {}
            for f in alle_fragen:
                frage = f["frage"]
                start = time.perf_counter()
                ranglisten[frage] = rerank(dense[frage], fundstellen_je_id, frage, reranker, k)
                rerank_dauern[frage] = time.perf_counter() - start
            variante = f"dense_rerank_{kurzname(modell)}_k{k}"
            zeilen.append(zeile(variante, embedding, ranglisten, rerank_dauern, None, rerank_dauern))
    return zeilen


def lauf(
    korpus: Path, golden: dict, stufe: int, embeddings: tuple[str, ...],
    provider_je_embedding: Callable[[str], ModelProvider], ausgabe: Path,
    *, host: str = "", schwelle: float = SCHWELLE,
    reranker_je_modell: dict[str, Reranker] | None = None, reranker_k: tuple[int, ...] = RERANK_K,
    bestand: tuple[tuple[Fundstelle, ...], tuple[dict, ...]] | None = None,
    zusatz: dict | None = None,
) -> tuple[dict, ...]:
    """Lexikalische Varianten einmal, dense + alle Hybrid-Varianten je Embedding-Modell, dann je
    Reranker-Modell × `reranker_k` (Default {}: keine Reranker-Variante — heutiges Verhalten);
    hängt je Zeile an `ausgabe/laeufe.jsonl` an.

    `bestand=(fundstellen, fragen)` übergeht Korpusordner und Stufe: die Fundstellen kommen dann
    fertig herein (GermanQuAD, `germanquad.lade`), `korpus`/`stufe` sind nur noch Beschriftung.
    Alles danach — Varianten, Embeddings, Reranker, Kennzahlen, Bericht — ist identisch; genau
    darum ist der zweite Korpus mit dem ersten vergleichbar. `zusatz` wird in jede Zeile
    gemischt (z. B. die Ziehung der Stichprobe)."""
    if not embeddings:
        raise RetrievalEvalFehler("Mindestens ein --embedding nötig")
    reranker_je_modell = reranker_je_modell or {}
    fragen = bestand[1] if bestand is not None else fragen_der_stufe(golden, stufe)
    gefunden, nicht_gefunden = golden_filter(fragen)
    if not gefunden and not nicht_gefunden:
        raise RetrievalEvalFehler(f"Keine golden-Fragen mit status gefunden/nicht_gefunden in Stufe {stufe}")
    alle_fragen = (*gefunden, *nicht_gefunden)

    with tempfile.TemporaryDirectory(prefix="retrieval_eval_") as tmp:
        fundstellen = bestand[0] if bestand is not None else fundstellen_der_stufe(
            korpus, golden, stufe, provider_je_embedding(embeddings[0]), Path(tmp)
        )
        fundstellen_je_id = {f.id: f for f in fundstellen}

        def zeile(variante: str, embedding: str | None, ranglisten: dict[str, Rangliste],
                  dauern: dict[str, float], embed_sekunden: float | None,
                  rerank_dauern: dict[str, float] | None = None) -> dict:
            return _variante_zeile(variante, embedding, korpus, stufe, len(fundstellen), gefunden, nicht_gefunden,
                                   ranglisten, fundstellen_je_id, dauern, embed_sekunden, host, schwelle,
                                   rerank_dauer_je_frage=rerank_dauern) | (zusatz or {})

        zeilen: list[dict] = []

        def sichere(neue: list[dict]) -> None:
            """Sofort auf die Platte, nicht erst nach dem letzten Embedding: am 22. und
            23.09.2026 haben zwei Läufe je 76 Minuten gekostet und keine einzige Zeile
            hinterlassen, weil `_schreibe_zeilen` ganz am Ende stand."""
            zeilen.extend(neue)
            _schreibe_zeilen(ausgabe, neue)

        lexikalisch = _lexikalisch_je_variante(alle_fragen, fundstellen)
        sichere([zeile(name, None, ranglisten, dauern, None)
                 for name, (ranglisten, dauern) in lexikalisch.items()])
        for embedding in embeddings:
            provider = provider_je_embedding(embedding)
            sichere(_zeilen_embedding(
                embedding, fundstellen, alle_fragen, lexikalisch, provider, zeile,
                fundstellen_je_id, reranker_je_modell, reranker_k,
            ))

    return tuple(zeilen)


def _schreibe_zeilen(ausgabe: Path, zeilen: list[dict]) -> None:
    Path(ausgabe).mkdir(parents=True, exist_ok=True)
    with (Path(ausgabe) / "laeufe.jsonl").open("a", encoding="utf-8") as f:
        for zeile in zeilen:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------ CLI


def _argumente(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--korpus", type=Path, help="Ordner mit Dateien (oder Unterordner Quelle/) und golden.json")
    p.add_argument("--golden", type=Path, help="Sollwerte; Standard: <korpus>/golden.json")
    p.add_argument("--stufe", type=int, help="genau eine Stufe (aus golden['stufen'] oder ab_stufe)")
    p.add_argument(
        "--germanquad", type=Path, nargs="?", const=germanquad.STANDARD_ORDNER,
        help="statt --korpus/--stufe: GermanQuAD-Arrow-Dateien aus diesem Ordner "
             f"(Standard: {germanquad.STANDARD_ORDNER}); Extra `eval` nötig",
    )
    p.add_argument("--fragen", type=int, help="Stichprobe von N Fragen (nur mit --germanquad; Standard: alle)")
    p.add_argument("--geraet", default=None, choices=["mps", "cpu"],
                   help="Rechengeraet fuer die Reranker; Standard: mps wenn verfuegbar. "
                        "Gemessen 22.09.: mps haengt bei 200 langen GermanQuAD-Absaetzen in "
                        "MPSStream::synchronize (0 %% CPU, 50 min ohne Fortschritt) -- dann cpu.")
    p.add_argument("--seed", type=int, default=42, help="Seed der Stichprobe (Standard: 42)")
    p.add_argument("--embedding", nargs="+", help="ein oder mehrere Embedding-Modelle")
    p.add_argument(
        "--reranker", nargs="+", default=(),
        help="HF-IDs für Cross-Encoder-Reranker (M4, Extra `reranker` nötig); Standard: keiner",
    )
    p.add_argument("--host", default="http://localhost:11434")
    p.add_argument("--ausgabe", type=Path, default=Path("beweise/retrieval"))
    p.add_argument("--bericht", type=Path, help="nur Bericht aus <ordner>/laeufe.jsonl schreiben")
    args = p.parse_args(argv)
    if args.bericht is not None:
        return args
    if not args.embedding:
        p.error("--embedding angeben")
    if args.germanquad is None and (args.korpus is None or args.stufe is None):
        p.error("--korpus und --stufe angeben, oder --germanquad, oder --bericht")
    if args.germanquad is not None and args.korpus is not None:
        p.error("--korpus und --germanquad schließen sich aus")
    return args


def _germanquad_bestand(args: argparse.Namespace) -> tuple[tuple, dict]:
    """`(bestand, zusatz)` für den GermanQuAD-Lauf. Die Ziehung steht in jeder Ergebniszeile,
    sonst ließe sich eine Stichprobe später nicht mehr nachvollziehen oder wiederholen."""
    fundstellen, fragen = germanquad.lade(args.germanquad, fragen=args.fragen, seed=args.seed)
    zusatz = {
        "korpus_quelle": "germanquad",
        "ziehung": {
            "seed": args.seed,
            "gezogen": len(fragen),
            "angefordert": args.fragen,
            "ordner": str(args.germanquad),
        },
    }
    return (fundstellen, fragen), zusatz


def main(argv: list[str] | None = None) -> None:
    args = _argumente(argv)
    if args.bericht is not None:
        print(schreibe_bericht(args.bericht))
        return
    ordner = args.ausgabe / date.today().isoformat()

    def provider_je_embedding(embedding: str) -> ModelProvider:
        return OllamaProvider(args.host, embedding, "", timeout=120)

    if args.germanquad is not None:
        bestand, zusatz = _germanquad_bestand(args)
        korpus, golden, stufe = Path(args.germanquad), {}, len(bestand[0])
        print(f"GermanQuAD: {stufe} Absätze, {len(bestand[1])} Fragen (Seed {args.seed})", flush=True)
    else:
        bestand, zusatz = None, None
        golden_pfad = args.golden or args.korpus / "golden.json"
        if not golden_pfad.exists():
            raise RetrievalEvalFehler(f"golden.json nicht gefunden: {golden_pfad}")
        golden = json.loads(golden_pfad.read_text(encoding="utf-8"))
        korpus = args.korpus / "Quelle" if (args.korpus / "Quelle").is_dir() else args.korpus
        stufe = args.stufe

    reranker_je_modell = {modell: CrossEncoderReranker(modell, geraet=args.geraet)
                          for modell in args.reranker}
    print(f"Stufe {stufe}, Embeddings {args.embedding}, Reranker {args.reranker or '–'} …", flush=True)
    lauf(
        korpus, golden, stufe, tuple(args.embedding), provider_je_embedding, ordner,
        host=args.host, reranker_je_modell=reranker_je_modell, bestand=bestand, zusatz=zusatz,
    )
    print(schreibe_bericht(ordner))


if __name__ == "__main__":
    main()
