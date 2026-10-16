"""Abweisung: trennt ein Retrieval- oder Reranker-Score beantwortbare von unbeantwortbaren
Fragen — mit großer Stichprobe statt 14 gegen 6.

**Der Befund, der geprüft wird** (malerbetrieb Stufe 200, 22.09.2026): kein Retrieval-Score
trennt die beiden Klassen (Kosinus qwen3 0.5062 gegen 0.5161, Kosinus bge-m3 0.4965 gegen
0.5613, BM25 8.74 gegen 10.48, RRF 0.0253 gegen 0.0323 — alle überlappen), jeder
Reranker-Score aber schon (bge-reranker-v2-m3 0.0592 gegen 0.0080, Qwen3-Reranker 5.13 gegen
3.63). Das waren **14 beantwortbare gegen 6 unbeantwortbare** Fragen. Genug für eine
Beobachtung, nicht für eine Schwelle im Produkt: bei 6 Negativen verschiebt eine einzige
Frage die Spezifität um 17 Punkte.

**Die Idee: unbeantwortbar entsteht durch Weglassen.** GermanQuAD hat 2204 von Menschen
gestellte Fragen, aber ausschließlich beantwortbare. Entfernt man den Zielabsatz einer Frage
aus dem Bestand, ist sie sicher nicht mehr beantwortbar — und die Frage bleibt
fremdgeschrieben. Es entsteht kein neuer Autorenschafts-Bias, und man braucht niemanden, der
sich unbeantwortbare Fragen ausdenkt (genau das hat die sechs malerbetrieb-Negative erzeugt).
Dieselbe Konstruktion trägt bei malerbetrieb: je beantwortbare Frage einmal ohne ihre
Zieldatei.

**Was die Konstruktion nicht garantiert** (und was deshalb geprüft wird): zeigen zwei Fragen
auf denselben Absatz, ist das harmlos — weggelassen wird je Fall, nicht global. Hat aber
*eine* Frage zwei Zielabsätze, bliebe nach dem Weglassen des einen der andere stehen, und die
„unbeantwortbare" Frage wäre in Wahrheit beantwortbar. Solche Fragen fliegen raus
(`faelle_germanquad`, geprüft in `tests/test_abweisung.py::test_A6_...`).

**Eine Näherung, ausdrücklich benannt:** BM25 wird einmal über den vollen Bestand gerechnet
und der weggelassene Absatz danach aus der Rangliste gestrichen. Exakt wäre, den Bestand
vorher zu verkleinern; IDF und mittlere Dokumentlänge ändern sich dann um 1 von 474 Absätzen.
Der Effekt ist für beide Klassen derselbe und liegt weit unter den gemessenen Abständen.
Kosinus, RRF und Reranker sind unberührt — sie bewerten je Absatz unabhängig, das Streichen
ist dort exakt.

    uv run --extra eval --extra reranker python -m dokumentenassistent.abweisung \\
        --germanquad --abweisung 250 --embedding bge-m3 qwen3-embedding:0.6b \\
        --reranker BAAI/bge-reranker-v2-m3 --rerank-k 8 20 --geraet cpu --ausgabe beweise/abweisung/
    uv run --extra reranker python -m dokumentenassistent.abweisung \\
        --korpus beispiele/malerbetrieb --stufe 200 --embedding bge-m3 qwen3-embedding:0.6b \\
        --reranker BAAI/bge-reranker-v2-m3 --rerank-k 8 20 --ausgabe beweise/abweisung/
"""
from __future__ import annotations

import argparse
import json
import math
import random
import tempfile
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from dokumentenassistent import germanquad
from dokumentenassistent.provider import ModelProvider, OllamaProvider
from dokumentenassistent.retrieval_reranker import (
    CrossEncoderReranker,
    Reranker,
    kurzname,
)
from dokumentenassistent.suche import Rangliste, bm25_rang, dense_rang, rrf
from dokumentenassistent.typen import DokumentenassistentFehler, Fundstelle

BEANTWORTBAR = "beantwortbar"
UNBEANTWORTBAR = "unbeantwortbar"


class AbweisungFehler(DokumentenassistentFehler):
    """Zu wenige brauchbare Fragen für die verlangte Stichprobe, oder leerer Bestand."""


# ============================================================ Auswertung (rein)


def roc_auc(beantwortbar: list[float], unbeantwortbar: list[float]) -> float | None:
    """Anteil der Paare (beantwortbar, unbeantwortbar), die das Signal richtig herum ordnet;
    Gleichstand zählt halb. Das ist die Mann-Whitney-U-Form der Fläche unter der ROC-Kurve —
    ohne sklearn, damit der Befund an einer Funktion hängt, die hier geprüft ist.

    1.0 = trennt vollständig, 0.5 = Münzwurf, `None` = eine Klasse fehlt."""
    n_pos, n_neg = len(beantwortbar), len(unbeantwortbar)
    if not n_pos or not n_neg:
        return None
    treffer = sum(
        1.0 if p > n else 0.5 if p == n else 0.0 for p in beantwortbar for n in unbeantwortbar
    )
    return round(treffer / (n_pos * n_neg), 4)


def _kandidaten(beantwortbar: list[float], unbeantwortbar: list[float]) -> list[float]:
    """Jeder beobachtete Wert ist eine mögliche Schwelle, dazu die beiden Randpunkte: einer
    unter allen (nichts abweisen) und einer knapp über allen (alles abweisen). Mehr Kandidaten
    gibt es nicht — zwischen zwei beobachteten Werten ändert sich keine der Kennzahlen.

    Der obere Randpunkt ist nicht Zierde: liegt jeder unbeantwortbare Wert über jedem
    beantwortbaren, ist er die **einzige** Schwelle, die 95 % Spezifität erreicht. Ohne ihn
    meldete die Funktion dort ein „Ziel unerreichbar", das nur an der Kandidatenliste liegt."""
    alle = sorted(set(beantwortbar) | set(unbeantwortbar))
    return [alle[0] - 1.0, *alle, math.nextafter(alle[-1], math.inf)]


def _bewerte_schwelle(schwelle: float, beantwortbar: list[float], unbeantwortbar: list[float]) -> dict:
    """Durchgelassen wird, wer `score >= schwelle` hat."""
    richtig_pos = sum(1 for s in beantwortbar if s >= schwelle)
    richtig_neg = sum(1 for s in unbeantwortbar if s < schwelle)
    n = len(beantwortbar) + len(unbeantwortbar)
    return {
        "schwelle": round(schwelle, 6),
        "genauigkeit": round((richtig_pos + richtig_neg) / n, 4),
        "sensitivitaet": round(richtig_pos / len(beantwortbar), 4),
        "spezifitaet": round(richtig_neg / len(unbeantwortbar), 4),
    }


def beste_schwelle(beantwortbar: list[float], unbeantwortbar: list[float]) -> dict:
    """Die Schwelle mit der höchsten Genauigkeit, dazu Sensitivität (beantwortbare
    durchgelassen) und Spezifität (unbeantwortbare abgewiesen).

    Bei Gleichstand gewinnt die **niedrigere** Schwelle — Recall vor Abweisung, dieselbe
    Regel, nach der `suche.SCHWELLE` am 21.09. abgeleitet wurde."""
    bewertet = [_bewerte_schwelle(s, beantwortbar, unbeantwortbar) for s in _kandidaten(beantwortbar, unbeantwortbar)]
    return max(bewertet, key=lambda e: (e["genauigkeit"], -e["schwelle"]))


def ueberlappung(beantwortbar: list[float], unbeantwortbar: list[float]) -> dict:
    """Niedrigster Wert der beantwortbaren gegen höchsten der unbeantwortbaren — genau die
    Zahlen aus dem Befund vom 22.09. Überlappen sie, kann keine Schwelle beide Klassen sauber
    trennen, egal wie sie gelegt wird."""
    min_pos, max_neg = min(beantwortbar), max(unbeantwortbar)
    return {
        "min_beantwortbar": round(min_pos, 6),
        "max_unbeantwortbar": round(max_neg, 6),
        "ueberlappt": max_neg >= min_pos,
    }


def verlust_bei_spezifitaet(
    beantwortbar: list[float], unbeantwortbar: list[float], ziel: float = 0.95
) -> dict:
    """Die Zahl, die im Produkt zählt: legt man die Schwelle so, dass `ziel` der
    unbeantwortbaren abgewiesen wird — wie viele beantwortbare Fragen verliert man dabei?

    Genommen wird die **niedrigste** Schwelle, die das Ziel erreicht (höchste Sensitivität).
    Ist das Ziel unerreichbar, steht das Erreichte in `spezifitaet` — keine stille Aufweichung."""
    bewertet = [_bewerte_schwelle(s, beantwortbar, unbeantwortbar) for s in _kandidaten(beantwortbar, unbeantwortbar)]
    treffer = [e for e in bewertet if e["spezifitaet"] >= ziel]
    gewaehlt = min(treffer, key=lambda e: e["schwelle"]) if treffer else max(
        bewertet, key=lambda e: (e["spezifitaet"], e["sensitivitaet"])
    )
    verlorene = sum(1 for s in beantwortbar if s < gewaehlt["schwelle"])
    return {**gewaehlt, "ziel_spezifitaet": ziel, "verlorene": verlorene, "ziel_erreicht": bool(treffer)}


def auswertung(zeilen: list[dict], ziel: float = 0.95) -> list[dict]:
    """Je Signal eine Zeile, nach AUC absteigend sortiert."""
    signale: dict[str, dict[str, list[float]]] = {}
    for z in zeilen:
        signale.setdefault(z["signal"], {BEANTWORTBAR: [], UNBEANTWORTBAR: []})[z["klasse"]].append(z["score"])
    ergebnis = []
    for signal, punkte_je_klasse in signale.items():
        pos, neg = punkte_je_klasse[BEANTWORTBAR], punkte_je_klasse[UNBEANTWORTBAR]
        if not pos or not neg:
            raise AbweisungFehler(f"Signal {signal}: eine der beiden Klassen ist leer")
        ergebnis.append({
            "signal": signal, "n_beantwortbar": len(pos), "n_unbeantwortbar": len(neg),
            "auc": roc_auc(pos, neg), "beste_schwelle": beste_schwelle(pos, neg),
            "ueberlappung": ueberlappung(pos, neg),
            "bei_spezifitaet_95": verlust_bei_spezifitaet(pos, neg, ziel),
        })
    return sorted(ergebnis, key=lambda e: -e["auc"])


SPALTEN = (
    "Signal", "AUC", "beste Schwelle", "Genauigkeit %", "Sensitivität %", "Spezifität %",
    "Überlappung (min b / max u)", "trennt", "Schwelle bei 95 % Spez.", "Verlust bei 95 % Spez.",
)


def _bericht_zeile(e: dict) -> str:
    s, v, u = e["beste_schwelle"], e["bei_spezifitaet_95"], e["ueberlappung"]
    verlust = f"{v['verlorene']}/{e['n_beantwortbar']} ({100 * (1 - v['sensitivitaet']):.0f} %)"
    if not v["ziel_erreicht"]:
        verlust += f" — 95 % nie erreicht (max {100 * v['spezifitaet']:.0f} %)"
    werte = (
        e["signal"], f"{e['auc']:.4f}", f"{s['schwelle']:.4f}",
        f"{100 * s['genauigkeit']:.0f}", f"{100 * s['sensitivitaet']:.0f}", f"{100 * s['spezifitaet']:.0f}",
        f"{u['min_beantwortbar']:.4f} / {u['max_unbeantwortbar']:.4f}",
        "nein" if u["ueberlappt"] else "ja", f"{v['schwelle']:.4f}", verlust,
    )
    return "| " + " | ".join(werte) + " |"


def baue_bericht(ergebnisse: list[dict], korpus: str) -> str:
    kopf = "| " + " | ".join(SPALTEN) + " |\n|" + "---|" * len(SPALTEN)
    n = ergebnisse[0] if ergebnisse else {}
    titel = (
        f"# Abweisung — {korpus}\n\n"
        f"{n.get('n_beantwortbar', 0)} beantwortbare gegen {n.get('n_unbeantwortbar', 0)} "
        "unbeantwortbare Fragen. „trennt\" = niedrigster Wert der beantwortbaren liegt über dem "
        "höchsten der unbeantwortbaren.\n\n"
    )
    return titel + kopf + "\n" + "\n".join(_bericht_zeile(e) for e in ergebnisse) + "\n"


# ================================================================== Stichprobe


def faelle_germanquad(fragen: tuple[dict, ...], n: int, seed: int) -> tuple[dict, ...]:
    """2*n Fälle: erste Hälfte `beantwortbar` (Bestand unverändert), zweite Hälfte
    `unbeantwortbar` (genau ihr Zielabsatz wird weggelassen).

    Vorher fliegen raus: Fragen mit mehr als einem Zielabsatz (nach dem Weglassen des einen
    stünde der andere noch im Bestand — die Frage wäre weiterhin beantwortbar) und
    Fragen ohne `absatz_id`."""
    je_frage: dict[str, set[str]] = {}
    for f in fragen:
        if f.get("absatz_id"):
            je_frage.setdefault(f["frage"], set()).add(f["absatz_id"])
    brauchbar = tuple(
        {"frage": frage, "absatz_id": next(iter(ids))} for frage, ids in je_frage.items() if len(ids) == 1
    )
    if len(brauchbar) < 2 * n:
        raise AbweisungFehler(
            f"{len(brauchbar)} brauchbare Fragen (eindeutiger Zielabsatz), {2 * n} gebraucht"
        )
    gezogen = random.Random(seed).sample(brauchbar, 2 * n)
    return tuple(
        {**f, "klasse": BEANTWORTBAR, "weglassen": frozenset()} for f in gezogen[:n]
    ) + tuple(
        {**f, "klasse": UNBEANTWORTBAR, "weglassen": frozenset({f["absatz_id"]})} for f in gezogen[n:]
    )


def faelle_malerbetrieb(
    gefunden: tuple[dict, ...], nicht_gefunden: tuple[dict, ...], fundstellen: tuple[Fundstelle, ...]
) -> tuple[dict, ...]:
    """Die vorhandenen Klassen plus je beantwortbare Frage einen Weglass-Fall: ihre **ganze
    Zieldatei** verschwindet aus dem Bestand (hier ist der Zielabsatz nicht bekannt, golden.json
    nennt nur die Datei — bliebe ein Absatz derselben Rechnung stehen, wäre die Frage weiter
    beantwortbar)."""
    ids_je_datei: dict[str, set[str]] = {}
    for f in fundstellen:
        ids_je_datei.setdefault(f.datei_name, set()).add(f.id)
    return (
        *({"frage": f["frage"], "absatz_id": None, "klasse": BEANTWORTBAR, "weglassen": frozenset()}
          for f in gefunden),
        *({"frage": f["frage"], "absatz_id": None, "klasse": UNBEANTWORTBAR, "weglassen": frozenset()}
          for f in nicht_gefunden),
        *({"frage": f["frage"], "absatz_id": None, "klasse": UNBEANTWORTBAR,
           "weglassen": frozenset(ids_je_datei.get(f["datei"], set()))} for f in gefunden),
    )


def mit_geschwistern(faelle: tuple[dict, ...], fundstellen: tuple[Fundstelle, ...]) -> tuple[dict, ...]:
    """Je Fall: wie viele Absätze **desselben Wikipedia-Artikels** nach dem Weglassen im
    Bestand bleiben (`geschwister`).

    Das ist die Schwachstelle der Konstruktion, und sie wird deshalb gezählt statt beteuert:
    der GermanQuAD-Bestand hat 474 Absätze aus 233 Artikeln. Nur bei den 110 Ein-Absatz-
    Artikeln nimmt das Weglassen den Artikel komplett aus dem Bestand; sonst bleiben ein bis
    sechs Nachbarabsätze stehen, und einer davon könnte die Frage doch beantworten. Dann wäre
    der Fall falsch als `unbeantwortbar` beschriftet. Mit dem Feld lässt sich der Befund für
    `geschwister == 0` getrennt nachrechnen — eine Kontrollgruppe statt einer Fußnote.

    Der Artikel ist die erste Zeile des Absatztextes (so liegt der Korpus vor). Bei
    malerbetrieb verschwindet ohnehin die ganze Datei, dort ist das Feld 0."""
    artikel_je_id = {f.id: f.text.split("\n", 1)[0].strip() for f in fundstellen}
    absaetze_je_artikel: dict[str, int] = {}
    for artikel in artikel_je_id.values():
        absaetze_je_artikel[artikel] = absaetze_je_artikel.get(artikel, 0) + 1

    def rest(weglassen: frozenset[str]) -> int:
        artikel = {artikel_je_id[i] for i in weglassen if i in artikel_je_id}
        return sum(absaetze_je_artikel[a] for a in artikel) - len(weglassen)

    return tuple({**f, "geschwister": rest(f["weglassen"])} for f in faelle)


# =================================================================== Messung


class _Zwischenspeicher:
    """Merkt sich den Cross-Encoder-Score je (Frage, Absatztext). k=8 und k=20 bewerten
    dieselben ersten acht Absätze — ohne diesen Speicher kostet die zweite k-Stufe die volle
    Zeit noch einmal (auf CPU 3,2 s je Frage), und zwei Embeddings liefern überlappende
    Top-Listen. Der Score ist eine reine Funktion des Paares, der Speicher ändert nichts."""

    def __init__(self, reranker: Reranker):
        self.reranker = reranker
        self._speicher: dict[tuple[str, str], float] = {}

    def bewerte(self, frage: str, texte: list[str]) -> list[float]:
        offen = [t for t in dict.fromkeys(texte) if (frage, t) not in self._speicher]
        if offen:
            for text, score in zip(offen, self.reranker.bewerte(frage, offen)):
                self._speicher[(frage, text)] = score
        return [self._speicher[(frage, t)] for t in texte]


def _gefiltert(rangliste: Rangliste, weglassen: frozenset[str]) -> Rangliste:
    return tuple((id_, s) for id_, s in rangliste if id_ not in weglassen)


def _top(rangliste: Rangliste) -> float:
    return round(float(rangliste[0][1]), 6) if rangliste else 0.0


def punkte(
    faelle: tuple[dict, ...], fundstellen: tuple[Fundstelle, ...], embeddings: tuple[str, ...],
    provider_je_embedding: Callable[[str], ModelProvider],
    reranker_je_modell: dict[str, Reranker], reranker_k: tuple[int, ...],
    sichere: Callable[[list[dict]], None] | None = None,
) -> list[dict]:
    """Je Fall und Signal der Top-Score — genau der Wert, den `suche()` gegen eine Schwelle
    prüfen würde. Signale: `bm25`, `dense@<emb>`, `rrf@<emb>`,
    `rerank_<kurzname>_k<K>@<emb>`.

    `sichere` wird nach jedem Embedding mit dessen Zeilen gerufen — ein Lauf über 400 Fälle
    dauert über eine Stunde, und am 23.09.2026 hat ein Abbruch 76 Minuten und jede Zeile
    gekostet, weil erst ganz am Ende geschrieben wurde."""
    if not fundstellen:
        raise AbweisungFehler("Leerer Bestand")
    text_je_id = {f.id: f.text for f in fundstellen}
    fragen = tuple(dict.fromkeys(f["frage"] for f in faelle))
    bm25 = {frage: bm25_rang(frage, fundstellen) for frage in fragen}

    def zeile(signal: str, fall: dict, score: float) -> dict:
        return {"signal": signal, "frage": fall["frage"], "klasse": fall["klasse"], "score": score,
                "geschwister": fall.get("geschwister", 0)}

    zeilen = [zeile("bm25", fall, _top(_gefiltert(bm25[fall["frage"]], fall["weglassen"]))) for fall in faelle]
    if sichere is not None:
        sichere(list(zeilen))
    speicher = {modell: _Zwischenspeicher(r) for modell, r in reranker_je_modell.items()}
    for embedding in embeddings:
        angefangen = len(zeilen)
        provider = provider_je_embedding(embedding)
        paare = tuple(zip(fundstellen, provider.embed([f.text for f in fundstellen])))
        dense = {frage: dense_rang(provider.embed([frage])[0], paare) for frage in fragen}
        for nummer, fall in enumerate(faelle, start=1):
            if nummer % 25 == 0:
                # Ein Lauf über 400 Fälle dauert auf CPU über eine Stunde. Ohne diese Zeile
                # ist nicht zu unterscheiden, ob er rechnet oder hängt — am 23.09. wurde ein
                # Lauf nach 76 Minuten abgeräumt, und niemand konnte sagen, wie weit er war.
                print(f"  {embedding}: {nummer}/{len(faelle)} Fälle", flush=True)
            frage, weg = fall["frage"], fall["weglassen"]
            d, b = _gefiltert(dense[frage], weg), _gefiltert(bm25[frage], weg)
            zeilen.append(zeile(f"dense@{embedding}", fall, _top(d)))
            zeilen.append(zeile(f"rrf@{embedding}", fall, _top(rrf((b, d)))))
            for modell, reranker in speicher.items():
                for k in reranker_k:
                    texte = [text_je_id[id_] for id_, _ in d[:k]]
                    scores = reranker.bewerte(frage, texte) if texte else []
                    signal = f"rerank_{kurzname(modell)}_k{k}@{embedding}"
                    zeilen.append(zeile(signal, fall, round(max(scores), 6) if scores else 0.0))
        if sichere is not None:
            sichere(zeilen[angefangen:])
    return zeilen


def lauf(
    faelle: tuple[dict, ...], fundstellen: tuple[Fundstelle, ...], embeddings: tuple[str, ...],
    provider_je_embedding: Callable[[str], ModelProvider], ausgabe: Path, *, korpus: str,
    reranker_je_modell: dict[str, Reranker] | None = None, reranker_k: tuple[int, ...] = (),
    zusatz: dict | None = None,
) -> list[dict]:
    """Misst, wertet aus, schreibt `abweisung-scores.jsonl` (eine Zeile je Signal × Fall),
    `abweisung.jsonl` (eine Zeile je Signal) und `abweisung-bericht.md`."""
    start = time.perf_counter()
    kopf = {"korpus": korpus, "datum": date.today().isoformat(), **(zusatz or {})}
    ausgabe = Path(ausgabe)
    ausgabe.mkdir(parents=True, exist_ok=True)
    zeilen = punkte(faelle, fundstellen, embeddings, provider_je_embedding,
                    reranker_je_modell or {}, reranker_k,
                    sichere=lambda neue: _haenge_an(ausgabe / "abweisung-scores.jsonl",
                                                    [z | kopf for z in neue]))
    ergebnisse = auswertung(zeilen)
    _haenge_an(ausgabe / "abweisung.jsonl",
               [e | kopf | {"dauer_s": round(time.perf_counter() - start, 1)} for e in ergebnisse])
    # Der Berichtsname trägt den Korpus: beide Korpora schreiben in denselben Tagesordner,
    # und ein fester Name hätte den malerbetrieb-Bericht vom GermanQuAD-Lauf überschreiben
    # lassen — in einem Ordner, der ausdrücklich append-only gedacht ist.
    (ausgabe / f"abweisung-bericht-{_slug(korpus)}.md").write_text(
        baue_bericht(ergebnisse, korpus), encoding="utf-8")
    return ergebnisse


def _slug(korpus: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in korpus.lower()).strip("-")


def _haenge_an(pfad: Path, zeilen: list[dict]) -> None:
    with pfad.open("a", encoding="utf-8") as f:
        for z in zeilen:
            f.write(json.dumps(z, ensure_ascii=False, default=str) + "\n")


# ======================================================================== CLI


def _argumente(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--abweisung", type=int, help="N: N beantwortbare + N unbeantwortbare Fragen (nur GermanQuAD)")
    p.add_argument("--germanquad", type=Path, nargs="?", const=germanquad.STANDARD_ORDNER)
    p.add_argument("--korpus", type=Path, help="statt --germanquad: Ordner mit golden.json")
    p.add_argument("--stufe", type=int)
    p.add_argument("--embedding", nargs="+", required=True)
    p.add_argument("--reranker", nargs="+", default=())
    p.add_argument("--rerank-k", type=int, nargs="+", default=[8, 20])
    p.add_argument("--geraet", default=None, choices=["mps", "cpu"])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--host", default="http://localhost:11434")
    p.add_argument("--ausgabe", type=Path, default=Path("beweise/abweisung"))
    args = p.parse_args(argv)
    if args.germanquad is None and args.korpus is None:
        p.error("--germanquad oder --korpus angeben")
    if args.germanquad is not None and args.abweisung is None:
        p.error("--abweisung N angeben")
    if args.korpus is not None and args.stufe is None:
        p.error("--stufe angeben")
    return args


def _bestand(args: argparse.Namespace) -> tuple[tuple[Fundstelle, ...], tuple[dict, ...], str, dict]:
    if args.germanquad is not None:
        fundstellen, fragen = germanquad.lade(args.germanquad)
        faelle = mit_geschwistern(faelle_germanquad(fragen, args.abweisung, args.seed), fundstellen)
        zusatz = {"ziehung": {"seed": args.seed, "n": args.abweisung, "quelle": "germanquad"}}
        return fundstellen, faelle, f"germanquad ({len(fundstellen)} Absätze)", zusatz

    # malerbetrieb: derselbe Bestandsaufbau wie im Retrieval-Eval (M2/M3/M4 über die Werkstatt).
    from dokumentenassistent.lasttest import fragen_der_stufe
    from dokumentenassistent.retrieval_eval import fundstellen_der_stufe, golden_filter

    golden = json.loads((args.korpus / "golden.json").read_text(encoding="utf-8"))
    quelle = args.korpus / "Quelle" if (args.korpus / "Quelle").is_dir() else args.korpus
    provider = OllamaProvider(args.host, args.embedding[0], "", timeout=120)
    with tempfile.TemporaryDirectory(prefix="abweisung_") as tmp:
        fundstellen = fundstellen_der_stufe(quelle, golden, args.stufe, provider, Path(tmp))
    gefunden, nicht_gefunden = golden_filter(fragen_der_stufe(golden, args.stufe))
    faelle = faelle_malerbetrieb(gefunden, nicht_gefunden, fundstellen)
    return fundstellen, faelle, f"{args.korpus} Stufe {args.stufe}", {"stufe": args.stufe}


def main(argv: list[str] | None = None) -> None:
    args = _argumente(argv)
    fundstellen, faelle, korpus, zusatz = _bestand(args)
    anzahl = {k: sum(1 for f in faelle if f["klasse"] == k) for k in (BEANTWORTBAR, UNBEANTWORTBAR)}
    print(f"{korpus}: {anzahl[BEANTWORTBAR]} beantwortbar, {anzahl[UNBEANTWORTBAR]} unbeantwortbar", flush=True)
    reranker_je_modell = {m: CrossEncoderReranker(m, geraet=args.geraet) for m in args.reranker}
    ergebnisse = lauf(
        faelle, fundstellen, tuple(args.embedding),
        lambda e: OllamaProvider(args.host, e, "", timeout=120),
        args.ausgabe / date.today().isoformat(), korpus=korpus,
        reranker_je_modell=reranker_je_modell, reranker_k=tuple(args.rerank_k), zusatz=zusatz,
    )
    print(baue_bericht(ergebnisse, korpus))


if __name__ == "__main__":
    main()
