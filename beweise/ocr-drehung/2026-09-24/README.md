# Drehung: PaddleOCR gegen sich selbst, die drei Vorstufen einzeln (24.09.2026)

## Anlass

Der Auftraggeber hat die Sachlage klargestellt: Die Quellbilder liegen **gedreht** vor (quer oder auf
dem Kopf). Keine Engine richtet sie vorher aus, deshalb steht die Schrift bei der Erkennung seitwärts.
Das ist kein Schrift- und kein Modellproblem, sondern ein **fehlender Vorverarbeitungsschritt**.
Betroffen sind laut Urteilen und Notizen des Gegenlesens die Seiten **1, 2 und 7** des Pakets
`beweise/ocr-scans/2026-09-24/`.

In allen bisherigen Messungen liefen PaddleOCRs drei Vorstufen **abgeschaltet** — für die
Vergleichbarkeit mit Tesseract, das nichts Entsprechendes hat.

## Messstand

Dieselben 10 PNGs wie im Gegenlese-Paket, dieselbe Engine (PaddleOCR 3.7.0, `lang="german"`, CPU),
kein Ollama. **Fünf Varianten**, damit nicht nur der Sammelschalter, sondern der Anteil jeder
einzelnen Stufe sichtbar wird:

| Variante | `use_doc_orientation_classify` | `use_doc_unwarping` | `use_textline_orientation` |
|---|---|---|---|
| `aus` | – | – | – |
| `alle_an` | ✔ | ✔ | ✔ |
| `nur_seitenorientierung` | ✔ | – | – |
| `nur_entzerrung` | – | ✔ | – |
| `nur_zeilenorientierung` | – | – | ✔ |

Alle drei Optionen lassen sich in 3.7.0 einzeln schalten; **keine Variante ist ausgefallen**, 50 von
50 Messungen liegen vor, 0 Fehler. Der fremde Lasttest lief während der Messung **nicht**
(`pgrep -f dokumentenassistent.lasttest` je Zeile geprüft, `dauer_unter_fremdlast: false` überall);
loadavg 5–7. Die Variante `aus` reproduziert die Zahlen aus
`beweise/ocr-scans/2026-09-24/laeufe.jsonl` in jeder Zelle.

## Ergebnis

### Die drei gedrehten Seiten — hier entscheidet sich alles

| Seite | Variante | Zeichen | Zahlen | Daten | Konfidenz |
|---|---|---|---|---|---|
| 1 | `aus` | 122 | 3 | 0 | 0.774 |
| 1 | `alle_an` | 495 | 1 | 2 | 0.993 |
| 1 | **`nur_seitenorientierung`** | **495** | **3** | **2** | 0.966 |
| 1 | `nur_entzerrung` | 134 | 3 | 0 | 0.828 |
| 1 | `nur_zeilenorientierung` | 424 | 3 | 0 | 0.931 |
| 2 | `aus` | 97 | 4 | 0 | 0.697 |
| 2 | `alle_an` | 574 | 2 | 2 | 0.995 |
| 2 | **`nur_seitenorientierung`** | **564** | 2 | **2** | 0.987 |
| 2 | `nur_entzerrung` | 171 | 4 | 0 | 0.783 |
| 2 | `nur_zeilenorientierung` | 454 | 4 | 0 | 0.902 |
| 7 | `aus` | 91 | 3 | 0 | 0.681 |
| 7 | `alle_an` | 366 | 8 | 1 | 0.945 |
| 7 | **`nur_seitenorientierung`** | **413** | **8** | **1** | 0.947 |
| 7 | `nur_entzerrung` | 50 | 2 | 0 | 0.572 |
| 7 | `nur_zeilenorientierung` | 393 | 8 | 1 | 0.912 |

Die **Seitenorientierung** ist der wirksame Schritt. Sie vervier- bis versechsfacht die Textmenge auf
genau den drei Seiten, die der Auftraggeber benannt hat, und findet dort erstmals überhaupt
Datumsangaben. Die **Entzerrung** bringt auf diesen Seiten so gut wie nichts (Seite 7 wird sogar
schlechter: 91 → 50 Zeichen).

### Die sieben übrigen Seiten — macht eine Stufe eine gute Seite schlechter?

Das ist die entscheidende Gegenprobe, und sie trennt die Stufen sauber:

| Variante | verschlechterte Seiten (von 7) | wo |
|---|---|---|
| `alle_an` | **4** | S4 (2315→2018 Zeichen, **13→7 Zahlen**), S5, S8, S10 (61→56 Zahlen) |
| **`nur_seitenorientierung`** | **0** | — alle sieben Seiten Zeichen für Zeichen identisch zu `aus` |
| `nur_entzerrung` | **4** | S4 (13→7 Zahlen), S5, S8, S10 (61→55 Zahlen) |
| `nur_zeilenorientierung` | 1 | S10 (1889→1845 Zeichen, Zahlen unverändert) |

**Der Schaden kommt vollständig aus der Entzerrung.** `alle_an` und `nur_entzerrung` verschlechtern
exakt dieselben vier Seiten in derselben Größenordnung; `nur_seitenorientierung` lässt alle sieben
unberührt. Auf Seite 4 verschwinden unter Entzerrung **6 von 13 Zahlen ersatzlos** (Zahlenmengen
verglichen, `zahlenmengen.json`: 7 gemeinsam, 6 nur ohne Entzerrung, 0 neue) — die Stufe liest sie
nicht anders, sie liest sie gar nicht.

### Summen über alle zehn Seiten

| Variante | Zeichen | Zahlen | Daten | Dauer s |
|---|---|---|---|---|
| `aus` | 9248 | 179 | 21 | 247.8 |
| `alle_an` | 9807 | 168 | 25 | 260.2 |
| **`nur_seitenorientierung`** | **10410** | **182** | **26** | **247.0** |
| `nur_entzerrung` | 8871 | 166 | 21 | 241.8 |
| `nur_zeilenorientierung` | 10165 | 184 | 22 | 252.0 |

`nur_seitenorientierung` ist in jeder Spalte mindestens so gut wie `aus` — mehr Zeichen, mehr Zahlen,
mehr Datumsangaben — und **kostet keine messbare Laufzeit** (247,0 gegen 247,8 s; der Unterschied
liegt unter der Streuung der Maschine). `alle_an` ist dagegen in der Spalte „Zahlen" *schlechter* als
gar keine Drehung.

## Befund

Die Empfehlung des Sammelschalters wäre falsch gewesen. Gemessen gewinnt **nur die
Seitenorientierung**:

* sie repariert alle drei gedrehten Seiten mindestens so gut wie `alle_an`, auf Seite 1 und 7 besser,
* sie verschlechtert **keine** der sieben übrigen Seiten,
* sie kostet keine zusätzliche Zeit,
* die Entzerrung (`use_doc_unwarping`) ist auf diesem Material ausschließlich schädlich,
* die Zeilenorientierung hilft ebenfalls, aber schwächer, und berührt eine gute Seite.

## Was diese Zahlen NICHT sind

Indikatoren, keine Qualität. Mehr Zeichen kann mehr gelesener Text oder mehr Rauschen sein; ein hoher
Zeilen-Score kann eine sicher falsch gelesene Zahl begleiten. **Ob der aufgerichtete Text richtig
ist, weiß keine dieser Spalten** — die Urteile im Paket vom 24.09. hängen an der Variante `aus`.
Dafür liegt `gegenlesen.html` daneben.

Weitere Grenzen: zehn Seiten (eine Seite wiegt 10 Prozentpunkte), drei davon in der Gruppe, um die
es geht; ein Gegenleser; nur dieses Material und diese Hardware; die Stufen wurden einzeln und
gemeinsam gemessen, aber nicht in den drei Paarungen.

## Gegenlese-Paket

`gegenlesen.html` — Doppelklick genügt, Safari reicht. Links das Bild, rechts dieselbe Seite durch
alle fünf Varianten untereinander, je mit Zeichen-, Zahlen- und Datumszähler, Konfidenz und Dauer.
Die drei gedrehten Seiten sind als solche markiert; zu jeder Seite steht das frühere Urteil zu
`paddleocr` (Variante `aus`) aus `beweise/ocr-scans/2026-09-24/urteile.json` dabei.

Die Seite lädt **nichts** nach: die einzigen Verweise sind die zehn eigenen PNGs (geprüft auf
`src`/`href`/`url()`/`@import`; die zehn `https://` im HTML stehen als Dokumenttext in den
`<pre>`-Blöcken, weil auf Rechnungen Web-Adressen gedruckt sind — inerter Text, kein Verweis).

## Dateien und Datenschutz

| Datei | Inhalt | versioniert |
|---|---|---|
| `laeufe.jsonl` | je Seite und Variante eine Zeile, sofort geschrieben; nur Kennzahlen | ja |
| `zahlenmengen.json` | Zahlen- und Datumsmengen je Variante gegen `aus`, **nur Anzahlen** | ja |
| `README.md` | dieses Dokument | ja |
| `gegenlesen.html`, `seite-*.png` | **Dokumentinhalt** (Bilder und OCR-Volltext) | **nein** — `.gitignore` im Ordner darüber |
