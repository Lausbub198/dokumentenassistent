# Abnahme — Urteile des Auftraggebers

## Zweck

Der zweite unabhängige Prüfstein neben GermanQuAD (`beweise/germanquad/README.md`). Der
bisherige Goldstandard `beispiele/malerbetrieb` ist synthetisch: Dokumente *und* Fragen
stammen aus derselben Quelle. Hier ist beides fremd — **eigene Dokumente** (30–50 Stück in
einem Ordner) und **eigene Fragen**, und geurteilt wird von Hand. Was dabei entsteht, ist ein
Goldstandard, den niemand aus diesem Projekt geschrieben hat.

## Bedienung

```bash
uv run dokumentenassistent --quelle ~/Pfad/zu/meinen/Dokumenten --ziel ~/Pfad/zur/Ablage
# Browser: http://127.0.0.1:8765/abnahme
```

Vorher gehört der übliche Weg: Profil bestätigen, Stapel einordnen, Kopien freigeben —
gefragt wird nur der **bestätigte** Bestand. `--abnahme <ordner>` verlegt die Ablage der
Urteile (Standard: `beweise/abnahme`, relativ zum Arbeitsverzeichnis).

Kein Login, kein Löschen, kein Bearbeiten. Ein Urteil ist ein Messwert, kein Zustand:
ein späteres Urteil zur selben Frage hängt eine neue Zeile an und löscht die alte nicht.

## Zwei Protokoll-Modi: `knapp` (Standard) und `voll`

Anlass (23.09.2026): der Auftraggeber will diese Ansicht mit ECHTEN, teils vertraulichen
Dokumenten benutzen. Das Protokoll liegt im Projektordner unter Git — ein unbedachtes
`git add` hätte damit fremden Dokumentinhalt im Repository. Deshalb ist das Protokoll
**standardmäßig inhaltsfrei**: es belegt das Urteil, nicht den Wortlaut. Welcher Modus gilt,
steht in `modelle.yaml` unter `abnahme_protokoll: knapp | voll` (Standard `knapp`).

Der Modus entscheidet auch den Dateinamen — **mechanischer** statt disziplinarischer Schutz:
wer versehentlich `voll` mit echten Dokumenten fährt, committet nicht automatisch, weil
`urteile-voll.jsonl` in `.gitignore` steht, egal ob das beim Schreiben jemand bedacht hat.

### `beweise/abnahme/<YYYY-MM-DD>/urteile.jsonl` — Modus `knapp` (Standard, **nicht** ignoriert)

Eine JSON-Zeile je Urteil, **append-only**, ohne Dokumentinhalt.

| Feld | Bedeutung |
|---|---|
| `zeit` | Zeitstempel mit Zeitzone (ISO 8601) |
| `frage_hash` / `frage_zeichen` | sha256 der Frage (erste 16 Hex-Zeichen) / ihre Länge |
| `antwort_hash` / `antwort_zeichen` | sha256 des Antworttexts / seine Länge |
| `status` | `gefunden`, `nicht_gefunden` oder `widersprüchlich` |
| `karten_ids_hash` | je Belegkarte die gehashte Fundstellen-ID — **nicht** die ID im Klartext, denn `datei#S..#A..` trägt den Dateinamen und damit selbst schon Inhalt |
| `karten_anzahl` | Zahl der Belegkarten |
| `urteil` | `richtig` oder `falsch` — nichts anderes wird geschrieben |
| `bemerkung_zeichen` | nur die Länge der Bemerkung, nicht der Text |
| `llm` | Modell, das eingeordnet hat (aus `modelle.yaml`) |
| `llm_suche` | Modell, das geantwortet hat; `null`, wenn es dasselbe ist |
| `embedding` | Embedding-Modell des Bestands |
| `reranker` | Reranker-Modell, `null`, wenn keiner eingestellt ist |
| `top_n` | Zahl der Absätze, die in den Prompt gingen |
| `absaetze_durchsucht` | Zahl der bestätigten Fundstellen mit Vektor zum Zeitpunkt des Urteils |

### `beweise/abnahme/<YYYY-MM-DD>/urteile-voll.jsonl` — Modus `voll` (in `.gitignore`)

Dieselben Kennzahlfelder wie oben, **zusätzlich** im Klartext:

| Feld | Bedeutung |
|---|---|
| `frage` | die gestellte Frage, wörtlich |
| `antwort` | der Antworttext des Modells, wörtlich (mit Zitatklammern) |
| `belegkarten` | Liste je Beleg: `id` (Fundstellen-ID), `datei`, `wortlaut` |
| `bemerkung` | freiwillig: die richtige Antwort oder warum das Urteil so ausfällt |

Gedacht für den synthetischen Korpus (`beispiele/malerbetrieb`), wo Inhalt unkritisch und zur
Fehlersuche nützlich ist — dort schadet ein Klartext-Protokoll niemandem.

Die Modellfelder (`llm`, `llm_suche`, `embedding`) stehen in **jeder** Zeile, in beiden Modi,
weil ein Urteil ohne sie wertlos ist: ein „falsch" gilt für genau dieses Modell-, Embedding-
und Bestandsdreieck, nicht allgemein.
