"""Multi-Vector-Retrieval (ColBERT-artig): ein Vektor je Token statt einer je Absatz.

Anlass, gemessen 25.09.2026 auf dem echten Bestand (1643 Absätze, 85 Fragen): das
heutige dense-Retrieval erreicht R@50 = 81 %, und der Reranker sättigt bei k = 50
(MRR 0,474, bei k = 100 wieder schlechter). Die Stellen sind auffindbar, aber nicht
sortierbar — 16 von 85 Antworten erscheinen nie unter den ersten fünfzig.

Der Verdacht: ein Absatz wird auf EINEN Vektor reduziert. Bei 0,11 Wortüberlappung
zwischen Frage und Zielabsatz und Fragen, die auf Rechnungsnummern, Daten und
Eigennamen zielen, ist das die gröbste denkbare Darstellung. Late Interaction behält
einen Vektor je Token und vergleicht erst beim Suchen:

    score(frage, absatz) = Σ über Fragetoken  max über Absatztoken  (q · d)

Das ist eine Zeile Mathematik. Die fertigen Bibliotheken sind es nicht: `pylate`
pinnt `sentence-transformers==5.3.0` und würde die hier installierte 6.1 — und
damit den gemessen wirksamen Reranker — herunterreißen; `colbert-ai` zieht `flask`
und `GitPython` nach. `transformers` und `torch` liegen über das Reranker-Extra
ohnehin im Projekt, also wird gerechnet statt installiert.

**Dieses Modul hängt an keinem Produktpfad.** `suche()` ruft es nicht auf. Es wird
zuerst gemessen; erst wenn es auf diesem Bestand gewinnt, bekommt `modelle.yaml`
einen Schalter. Ein `retriever`-Wechsel bräuchte ohnehin eine neu abgeleitete
Schwelle — `SCHWELLE = 0.49` ist ein Kosinus und gilt für MaxSim nicht.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from dokumentenassistent.typen import DokumentenassistentFehler, Fundstelle

if TYPE_CHECKING:
    import torch

# Eine Matrix je Text: (Tokens × Dimensionen), Zeilen auf Länge 1 normiert.
Kodierer = Callable[[Sequence[str]], "list[torch.Tensor]"]
Rangliste = tuple[tuple[str, float], ...]


class MultiVectorFehler(DokumentenassistentFehler):
    """Modell nicht ladbar, leerer Bestand oder leere Frage."""


def maxsim(frage: "torch.Tensor", absatz: "torch.Tensor") -> float:
    """Σ über Fragetoken, max über Absatztoken. Beide Matrizen zeilenweise normiert.

    Die Summe (nicht der Mittelwert) ist die ColBERT-Definition: eine längere Frage
    kann mehr Punkte sammeln. Das ist beim Vergleich ZWEIER Absätze für dieselbe
    Frage unerheblich — und nur darum geht es beim Ranking.
    """
    if frage.numel() == 0 or absatz.numel() == 0:
        return 0.0
    return float((frage @ absatz.T).max(dim=1).values.sum())


def rang(frage: str, fundstellen: tuple[Fundstelle, ...], kodierer: Kodierer,
         absatz_vektoren: "list[torch.Tensor] | None" = None) -> Rangliste:
    """Absätze nach MaxSim sortiert — gleicher Rückgabetyp wie `suche.dense_rang`.

    `absatz_vektoren` erlaubt, die teure Kodierung einmal zu machen und über viele
    Fragen wiederzuverwenden; ohne sie wird bei jedem Aufruf neu kodiert.
    """
    if not frage.strip():
        raise MultiVectorFehler("Leere Frage")
    if not fundstellen:
        raise MultiVectorFehler("Leerer Bestand")
    if absatz_vektoren is None:
        absatz_vektoren = kodierer([f.text for f in fundstellen])
    if len(absatz_vektoren) != len(fundstellen):
        raise MultiVectorFehler(
            f"{len(absatz_vektoren)} Vektormatrizen zu {len(fundstellen)} Absätzen")
    q = kodierer([frage])[0]
    punkte = [(f.id, maxsim(q, d)) for f, d in zip(fundstellen, absatz_vektoren)]
    return tuple(sorted(punkte, key=lambda p: -p[1]))



def _kopfgewichte(quelle: str, revision: str | None) -> dict:
    """Projektionsgewichte aus einer .pt-Datei ODER aus den Modellgewichten selbst.

    Zwei Ablageorte, beide real angetroffen (25.09.2026):

    * bge-m3 legt den Kopf als eigene Datei `colbert_linear.pt` daneben.
    * jina-colbert-v2 hat ihn IN `model.safetensors` unter `linear.weight` — und
      `AutoModel` wirft ihn beim Laden weg (`linear.weight | UNEXPECTED`). Ohne
      Nachladen misst man die rohen XLM-RoBERTa-Vektoren und haelt das Ergebnis
      faelschlich fuer "ColBERT bringt nichts". Der Hinweis darauf ist die
      Ausgabedimension: 1024 statt der 128, auf die ein ColBERT komprimiert.

    `quelle` ist entweder ein Dateipfad oder ein HF-Repo-Name.
    """
    import torch
    pfad = Path(quelle)
    if not pfad.exists():
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file
        datei = hf_hub_download(quelle, "model.safetensors", revision=revision)
        roh = load_file(datei)
        treffer = {k.split(".")[-1]: v for k, v in roh.items()
                   if k in ("linear.weight", "linear.bias")}
        if "weight" not in treffer:
            raise MultiVectorFehler(f"Kein Projektionskopf `linear.weight` in {quelle!r}")
        return treffer
    return torch.load(pfad, map_location="cpu", weights_only=True)


def lade_kodierer(modell: str, geraet: str | None = None, max_tokens: int = 256,
                  projektion: str | None = None, revision: str | None = None,
                  fremdcode: str | None = None) -> Kodierer:
    """Ein Kodierer aus einem HuggingFace-Modell. Lazy-Import, damit `pytest` ohne
    das Reranker-Extra grün bleibt (dieselbe Regel wie in `retrieval_reranker`).

    Normiert jede Tokenzeile auf Länge 1 und wirft Padding-Positionen weg — sonst
    zählt MaxSim Füllzeichen mit, und lange Absätze bekämen allein durch ihre Länge
    einen Vorteil.

    `projektion` ist der Pfad zu einer gespeicherten Linearschicht (`weight`/`bias`),
    die VOR der Normierung angewandt wird. Ohne sie misst man die rohen Tokenvektoren
    des Encoders — das ist Late Interaction, aber ungelernte: gemessen 25.09.2026 mit
    bge-m3 roh R@1 25 %, MRR 0,372. Ein echtes ColBERT-Modell hat einen auf MaxSim
    TRAINIERTEN Kopf, und bge-m3 liefert ihn als `colbert_linear.pt` mit — `AutoModel`
    laedt ihn nur nicht, weil er nicht zur Standardarchitektur gehoert.

    `fremdcode` erlaubt eigenen Modellcode (`trust_remote_code=True`) und nagelt ihn auf
    einen geprueften Commit fest. NUR mit ausdruecklicher Freigabe setzen: ohne Pin laedt
    HF den jeweils neuesten Code, und dann laeuft etwas anderes als auditiert wurde.

    ZWEI Repos, zwei Pins — ein Fehler, der hier schon passiert ist. `revision` gilt fuer
    das MODELL-Repo, `code_revision` fuer das Repo, aus dem der Fremdcode stammt; sie haben
    getrennte Historien. Bei jina-colbert-v2 liegt der Code in
    `jinaai/xlm-roberta-flash-implementation` (4564 Zeilen, Commit bd55a5ec geprueft
    25.09.2026: keine Netzwerkbibliothek, kein subprocess, kein eval, nur Modellmathematik
    aus Flash-Attention). Den Code-Commit als `revision` zu setzen ergibt "Invalid rev id".
    """
    zusatz: dict = {}
    if fremdcode:
        zusatz = {"trust_remote_code": True, "code_revision": fremdcode}
    if revision:
        zusatz["revision"] = revision
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as fehler:  # pragma: no cover — hängt an der Umgebung
        raise MultiVectorFehler(
            "transformers/torch fehlen — `uv sync --extra reranker` ausführen") from fehler

    if geraet is None:
        geraet = "mps" if torch.backends.mps.is_available() else "cpu"
    try:
        tok = AutoTokenizer.from_pretrained(modell, **zusatz)
        netz = AutoModel.from_pretrained(modell, **zusatz).to(geraet).eval()
    except Exception as fehler:  # noqa: BLE001 — Modellname, Netz, Rechte: alles derselbe Abbruch
        raise MultiVectorFehler(f"Modell {modell!r} nicht ladbar: {fehler}") from fehler

    kopf = None
    if projektion is not None:
        gewichte = _kopfgewichte(projektion, revision)
        kopf = torch.nn.Linear(gewichte["weight"].shape[1], gewichte["weight"].shape[0],
                               bias="bias" in gewichte)
        kopf.load_state_dict(gewichte)
        kopf = kopf.to(geraet).eval()

    def kodiere(texte: Sequence[str]) -> list[torch.Tensor]:
        raus: list[torch.Tensor] = []
        for start in range(0, len(texte), 16):
            stapel = list(texte[start:start + 16])
            eingabe = tok(stapel, padding=True, truncation=True,
                          max_length=max_tokens, return_tensors="pt").to(geraet)
            with torch.no_grad():
                versteckt = netz(**eingabe).last_hidden_state
                if kopf is not None:
                    versteckt = kopf(versteckt)
            versteckt = torch.nn.functional.normalize(versteckt, p=2, dim=-1)
            for zeile, maske in zip(versteckt, eingabe["attention_mask"]):
                raus.append(zeile[maske.bool()].cpu())
        return raus

    return kodiere
