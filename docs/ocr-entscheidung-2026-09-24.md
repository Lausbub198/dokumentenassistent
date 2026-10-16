# OCR im Produkt: Tesseract wird abgelöst (24.09.2026)

> **Historisch, Stand 24.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


> Diese Seite erzählt die ganze Kette: welche Engines geprüft wurden, mit welchen zwei Messarten,
> warum die beste Engine der Rohwerte trotzdem ausscheidet, was die Drehung bringt, wie die neue
> Schwelle abgeleitet ist — und was danach immer noch ungemessen bleibt.
> Vorgänger: `docs/ocr-befund-2026-09-23.md`, `docs/ocr-portabel-2026-09-23.md`,
> `docs/ocr-scans-2026-09-23.md`. Belege: `beweise/ocr-portabel/2026-09-23/`,
> `beweise/ocr-scans/2026-09-24/`, `beweise/ocr-drehung/2026-09-24/`.

## Was entschieden wurde

In `modelle.yaml` stehen seit heute vier neue Schlüssel:

```yaml
ocr: paddleocr        # statt tesseract
ocr_drehung: true     # NUR die Seitenorientierung; die anderen zwei Vorstufen schaden gemessen
ocr_schwelle: 0.80    # statt der Tesseract-Schwelle 0,6 — und sie weist faktisch nichts ab, s. u.
# ocr_sprache: german # optional; ohne den Schlüssel gilt die Kennung der gewählten Engine
```

Tesseract bleibt vollständig benutzbar (`ocr: tesseract`) und behält seine eigenen Standardwerte
(`deu`, Schwelle 0,6). Der Code-Default von `auslesen.lies_seiten` ist weiterhin Tesseract — was das
Produkt tut, entscheidet ausschließlich `modelle.yaml`.

## Warum Tesseract abgelöst wird

Nicht wegen einer Kennzahl, sondern weil **zwei voneinander unabhängige Messarten** in dieselbe
Richtung zeigen. Jede für sich hat eine Lücke, die die andere schließt.

### Messart 1 — 96 gerenderte Seiten mit maschineller Wahrheit

Seiten, die eine vom Erzeuger gesetzte Textebene tragen, werden zu Bildern gerendert und durch die
OCR geschickt; die Textebene ist die Wahrheit, die Differenz die Fehlerrate. Vollständig in
`docs/ocr-portabel-2026-09-23.md`, hier nur das Ergebnis:

| Engine | portabel | F1 Wort | Zahlentreue | s/Seite |
|---|---|---|---|---|
| `tesseract` (bisheriges Produkt) | ja | 0.9642 | 84.3 % | 0.98 |
| `tesseract_vorverarbeitet` | ja | 0.9600 | 82.6 % | 1.48 |
| **`paddleocr`** | **ja** | **0.9808** | **94.7 %** | 29.35 |
| `easyocr` | ja | 0.9087 | 84.6 % | 10.38 |
| `vision` *(Messlatte, macOS-only)* | nein | 0.9647 | 91.4 % | 0.22 |

Seite gegen Seite liest `paddleocr` auf **81 von 96** Seiten mehr richtige Wörter als Tesseract und
verfehlt **110 statt 320** Zahlen und Fristen. Die Messlatte Vision schafft 65 von 96 — die portable
Engine schlägt hier die macOS-Engine.

**Die Lücke dieser Messart:** sie misst auf den falschen Seiten. Eine Wahrheit gibt es nur, wo eine
Textebene liegt — also auf sauber gerenderten PDF-Seiten. Im Betrieb hängt die OCR an den **134
Seiten ohne** Textebene: Scans und Handyfotos, schief, verrauscht, wechselnd belichtet.

### Messart 2 — 10 echte Scan-/Fotoseiten, von Hand gegengelesen

Genau diese Lücke schließt das Gegenlese-Paket (`docs/ocr-scans-2026-09-23.md`, Urteile in
`beweise/ocr-scans/2026-09-24/urteile.json`). Zehn Seiten aus zehn verschiedenen Dateien des echten
Bestands, deterministisch gezogen, vier Engines nebeneinander, **ein Mensch urteilt** — ohne Wahrheit
gibt es nichts automatisch zu bewerten.

| Engine | brauchbar | Fehler in Zahlen | unbrauchbar |
|---|---|---|---|
| `tesseract` | 3 | 1 | 5 |
| `tesseract_vorverarbeitet` | 5 | 0 | 5 |
| **`paddleocr`** | **7** | **0** | 3 |
| `vision` *(Messlatte, macOS-only)* | 8 | 2 | 0 |

*(`tesseract` hat auf einer Seite kein Urteil bekommen; die Zeile zählt deshalb 9 statt 10.)*

Die Auswertungsregel stand **vor** dem Gegenlesen fest (`docs/ocr-scans-2026-09-23.md`, Abschnitt
„Auswertungslogik"). Angewandt:

1. **Ausschluss zuerst:** mehr `Fehler in Zahlen` als Tesseract → ausgeschlossen. `paddleocr` hat
   null, Tesseract eins. Kein Ausschluss. ✔
2. **Leitgröße:** `paddleocr` bleibt empfohlen, wenn es mindestens so viele brauchbare Seiten hat.
   7 gegen 3. ✔
3. **Abstand unter 3 Seiten entscheidet nichts.** Der Abstand ist 4. Die Regel nennt „8 gegen 3" als
   Beispiel eines echten Befunds; 7 gegen 3 liegt knapp darüber. ✔

Beide Messarten zeigen dasselbe: **`paddleocr`**.

## Welche Engines geprüft wurden — und warum die anderen ausscheiden

| Engine | Ergebnis |
|---|---|
| `tesseract` | bisheriges Produkt, Messlatte nach unten. Auf echten Scans 3 von 10 brauchbar. |
| `tesseract_vorverarbeitet` | dieselbe Engine mit `ocr_vorverarbeitung.vorverarbeite`. Auf Renderings paarweise **25:51** schlechter, auf Scans 5 von 10 — besser als rohes Tesseract, schlechter als `paddleocr`. Bemerkenswert: die **CER sinkt** (0.0558 gegen 0.0664). Hätte man nach CER entschieden, wäre das die Empfehlung gewesen — die Kennzahl misst aber Lesereihenfolge mit (Befund vom 23.09.). |
| **`paddleocr`** | **gewählt.** Beide Messarten vorn. |
| `easyocr` | deutlich schwächer (paarweise 16:79 bei F1 Wort), erfindet am meisten (413 Nennungen). |
| `surya` | **nicht gemessen.** Dependency-Konflikt, nicht auflösbar: `surya-ocr` fordert in *jeder* geprüften Version (0.14.7–0.22.1) `pillow<11`, das Produkt fordert `pillow>=11.0` und hat 12.3.0 installiert. Surya aufzunehmen hieße, Pillow im **Produkt** zurückzustufen, um eine Engine zu *messen* — die Reihenfolge verkehrt herum. Ersetzt durch `easyocr`. Wortlaut des Resolvers in `docs/ocr-portabel-2026-09-23.md`. |
| `python-doctr` | nicht gemessen (Begrenzung auf drei neue Engines). Löst gegen `pillow>=11` sauber auf und wäre der nächste Kandidat, falls `paddleocr` am Abhängigkeitsgewicht scheitert. |
| `vision` / `vision_korrektur` | **Messlatte, kein Kandidat** — siehe nächster Abschnitt. |

## Warum Vision trotz der besten Rohwerte ausscheidet

Zwei Gründe, jeder für sich ausreichend:

1. **Zwei Seiten mit falsch gelesenen Zahlen.** Auf den 10 gegengelesenen Scan-Seiten liefert Vision
   das beste Rohergebnis — 8 brauchbar, 0 unbrauchbar — aber auf zwei Seiten stimmen die Zahlen
   nicht. Die vorab festgelegte Regel schließt das aus, und zwar bewusst als **erstes**
   Kriterium: Dieser Assistent antwortet mit Zitatpflicht und wird nach Beträgen und Fristen
   gefragt. Eine falsch gelesene Zahl erzeugt ein Zitat, das **richtig aussieht und falsch ist**.
   Fehlender Text fällt dem Nutzer auf, eine falsche Ziffer nicht. `paddleocr` hat auf denselben
   Seiten null solcher Fälle.
2. **macOS-only.** Gefordert ist eine Lösung für alle Rechner. Das allein hätte Vision schon am
   23.09. aus der Kandidatenrolle genommen; es bleibt in allen Tabellen als **Messlatte** stehen —
   „was auf dieser Hardware erreichbar wäre".

Bemerkenswert bleibt, dass die portable Engine die Messlatte auf den Renderings **schlägt** (81:14
gegen 65:30 paarweise). Der Verzicht auf Vision kostet also nicht die Lesequalität, sondern die
Geschwindigkeit: 0,22 gegen 29 s je Seite.

## Die Drehung: der größte einzelne Hebel — aber nur eine der drei Vorstufen

In **allen** Messungen bis heute liefen PaddleOCRs drei Vorstufen — Seitenorientierung
(`use_doc_orientation_classify`), Entzerrung (`use_doc_unwarping`), Zeilenorientierung
(`use_textline_orientation`) — **abgeschaltet**. Das war richtig: sie geben der Engine eine
Vorverarbeitung, die Tesseract nicht hat, und der Vergleich sollte die *Erkennung* messen.

Für das Produkt gilt das nicht mehr. Drei der zehn Scan-Seiten hat der Auftraggeber genau deshalb als
unbrauchbar markiert („grundsätzlich alles, weil das Bild einfach verdreht ist"; „müsste erst rotiert
werden"). Gemessen am 24.09.2026, dieselben 10 PNGs, PaddleOCR gegen sich selbst, CPU, ohne Ollama —
und diesmal **jede Stufe einzeln**, nicht nur als Sammelschalter
(`beweise/ocr-drehung/2026-09-24/laeufe.jsonl`).

### Die vier Varianten über alle zehn Seiten

| Variante | Zeichen | Zahlen | Datumsangaben | Laufzeit |
|---|---|---|---|---|
| keine Vorstufe (`aus`) | 9248 | 179 | 21 | 248 s |
| **nur Seitenorientierung** | **10410** | **182** | **26** | **247 s** |
| nur Zeilenorientierung | 10165 | 184 | 22 | 252 s |
| nur Entzerrung | 8871 | 166 | 21 | 242 s |
| alle drei zusammen | 9807 | 168 | 25 | 260 s |

**Der Sammelschalter ist die schlechteste Wahl, die nach Fortschritt aussieht.** „Alle drei an" liest
über alle Seiten **168** Zahlen und damit *weniger* als gar keine Vorstufe (179) — der Gewinn der
Seitenorientierung wird von der Entzerrung wieder aufgefressen. Hätte diese Runde die drei Stufen
weiter nur gemeinsam geschaltet, wäre genau dieser Rückschritt als „Preis der Drehung" eingebaut und
in `modelle.yaml` als unvermeidbarer Tausch beschrieben worden. Er ist vermeidbar.

### Die Seitenorientierung kostet nichts

| Seite | Urteil (ohne Drehung) | Zeichen ohne → mit | Zahlen | Daten | Konfidenz |
|---|---|---|---|---|---|
| 1 | **unbrauchbar** | 122 → **495** | 3 → 3 | 0 → **2** | 0.774 → **0.966** |
| 2 | **unbrauchbar** | 97 → **564** | 4 → 2 | 0 → **2** | 0.697 → **0.987** |
| 7 | **unbrauchbar** | 91 → **413** | 3 → **8** | 0 → **1** | 0.681 → **0.947** |
| 3, 4, 5, 6, 8, 9, 10 | brauchbar | *unverändert* | *unverändert* | *unverändert* | *unverändert* |

Die sieben bereits brauchbaren Seiten sind **zeichenweise identisch** zum Lauf ohne Vorstufe: gleiche
Zeichenzahl, gleiche Zahlen- und Datumszähler, gleiche Konfidenz, und der Vergleich der
**Zahlenmengen** (`zahlenmengen.json`) verzeichnet auf keiner dieser Seiten auch nur eine Zahl, die
nur in der einen oder nur in der anderen Variante vorkommt. Die Laufzeit ist unverändert (247 gegen
248 s). Die Seitenorientierung tut also genau eine Sache: sie richtet Seiten auf, die schief liegen,
und lässt alles andere in Ruhe.

Auf den drei verdrehten Seiten vervier- bis versechsfacht sich die Textmenge, die Konfidenz springt
von 0,68–0,77 auf 0,95–0,99, und auf allen dreien werden erstmals überhaupt Datumsangaben erkannt
(0 → 5 in der Summe). Auf Seite 7 kommen sieben Zahlen dazu, die es vorher nicht gab.

### Warum die anderen beiden Stufen aus bleiben

**Entzerrung (`use_doc_unwarping`) schadet.** Sie verschlechtert 4 der 7 guten Seiten. Eine Zählung
allein könnte das nicht von „anders gelesen" trennen, deshalb der Mengenvergleich
(`zahlenmengen.json`, nur Anzahlen, kein Inhalt):

| Seite | gemeinsam | nur ohne Entzerrung | nur mit Entzerrung | Befund |
|---|---|---|---|---|
| 4 | 7 | **6** | **0** | **reiner Verlust** |
| 10 | 52 | 9 | 3 | überwiegend Verlust |
| 5 | 15 | 1 | 1 | Tausch |

Auf **Seite 4 verschwinden sechs von dreizehn Zahlen ersatzlos** — die Entzerrung liest sie nicht
anders, sie liest sie gar nicht. Und sie repariert die verdrehten Seiten nicht: dort bleiben die
Datumsangaben bei 0.

**Zeilenorientierung (`use_textline_orientation`) bringt fast nichts und kostet.** Sie liest über
alle Seiten zwei Zahlen mehr als die Seitenorientierung (184 gegen 182), aber **vier Datumsangaben
weniger** (22 gegen 26), weil sie auf den drei verdrehten Seiten nur eine statt fünf findet. Auf
Seite 10 verschlechtert sie eine brauchbare Seite leicht (1889 → 1845 Zeichen, Konfidenz 0,975 →
0,968).

### Entscheidung: `ocr_drehung: true` schaltet nur `use_doc_orientation_classify`

Der Schlüssel heißt weiterhin `ocr_drehung`, Standard `true`. Er schaltet genau die Vorstufe ein, die
gemessen hilft. Die beiden anderen sind **nicht** einzeln schaltbar gemacht worden: ein Schlüssel für
eine Einstellung, die auf jeder gemessenen Seite entweder schadet oder nichts bringt, wäre
Konfiguration für einen Fall, den es nicht gibt. Dass sie existieren und warum sie aus sind, steht im
Docstring von `auslesen.OcrEinstellungen` und im Kommentar in `modelle.yaml` — wer sie doch probieren
will, findet dort die Zahlen, gegen die er antritt.

Anders als in der ersten Fassung dieser Seite ist die Entscheidung damit **nicht mehr knapp**. Sie
war es nur, solange „Drehung" hieß: drei Seiten gewinnen, drei Seiten verlieren. Einzeln gemessen
gewinnen drei Seiten und keine verliert.

**Was diese Messung ausdrücklich NICHT zeigt:** ob der aufgerichtete Text **richtig** ist.
Zeichenzahl, Zahl- und Datumszähler und Konfidenz sind Indikatoren, keine Qualität — mehr Zeichen
kann mehr gelesener Text oder mehr Rauschen sein, und eine hohe Konfidenz kann eine sicher falsch
gelesene Zahl begleiten. Die Urteile des Auftraggebers hängen an den **ungedrehten** Texten; für die
aufgerichteten gibt es keine. Fällig ist deshalb eine **zweite Gegenlese-Runde mit Drehung**, und
zwar auf den drei aufgerichteten Seiten, deren Text es vorher schlicht nicht gab.

## Die Schwelle: warum 0,6 nicht stehen bleiben durfte

`werkstatt.ocr_schwelle = 0.6` entscheidet, ob eine Seite als `ocr_unsicher` gilt — und eine
`ocr_unsicher`-Datei geht **gar nicht erst ans Sprachmodell** und landet nicht im Index. Die Schwelle
ist damit kein Feinregler, sondern ein Tor.

Die 0,6 stammen aus **Tesseract-Wortkasten-Konfidenzen** (`pytesseract.image_to_data`, `conf/100`,
gemittelt über die erkannten Wortkästen). PaddleOCR liefert `rec_scores` — einen Wert je erkannter
**Textzeile**. Das ist nicht dieselbe Größe, und sie liegt sichtbar höher: auf denselben zehn
Scan-Seiten Median **0,994** (paddleocr) gegen **0,799** (tesseract). Mit 0,6 hätte `ocr_unsicher`
unter PaddleOCR bei **keiner einzigen** der zehn Seiten ausgelöst (Minimum 0,681) — der Schutz wäre
stillschweigend abgeschaltet gewesen, ohne dass irgendwo ein Fehler erschienen wäre.

### Ableitung — zweimal, weil die erste auf der falschen Variante stand

Die menschlichen Urteile sind die einzige Wahrheit, die es für echte Scans gibt. Gezählt wird so:

* **„unbrauchbar" = hätte als unsicher erkannt werden sollen** (positive Klasse). Drei Seiten.
* **„brauchbar" = hätte nicht** (negative Klasse). Sieben Seiten.
* **„Fehler in Zahlen" zählt zur positiven Klasse** — eine falsch gelesene Zahl ist nach der Regel
  dieses Projekts der *schlimmere* Fall als fehlender Text, also genau das, was das Tor abfangen
  soll. Für `paddleocr` ist die Klasse auf diesen zehn Seiten **leer**; die Zählregel ändert hier
  also nichts, sie ist für die nächste Runde festgehalten. (Für Tesseract wäre sie relevant: dessen
  eine Seite mit falschen Zahlen trägt Konfidenz 0,871 und läge weit über jeder sinnvollen Schwelle.)

#### Erster Anlauf: ohne Drehung — und genau darum unbrauchbar

Ein erster Durchgang leitete die Schwelle aus den Zeilen-Scores **ohne** Vorstufe ab, mit dem
Argument, nur diese Texte seien beurteilt:

| Klasse | Werte ohne Drehung |
|---|---|
| **unbrauchbar** (3) | 0.681, 0.697, 0.774 |
| **brauchbar** (7) | *kein Text erkannt* → 0.0, 0.975, 0.994, 0.994, 0.996, 0.997, 1.000 |

Dort trennen die Klassen vollständig, jeder Wert in (0,7735 … 0,9752] tut dasselbe, und die Mitte
liegt bei **0,87**. Diese Zahl stand in der ersten Fassung von `modelle.yaml`.

Sie ist trotzdem falsch, und zwar aus einem einzigen, harten Grund: **im Produkt läuft
`ocr_drehung: true`.** Eine Schwelle, die auf einer Variante abgeleitet ist, die niemand ausführt,
misst nichts. Also neu, auf der Variante, die wirklich läuft.

#### Zweiter Anlauf: PaddleOCR + Seitenorientierung — die Klassen trennen nicht mehr

Dieselben zehn Seiten, dieselben Urteile, Spalte `nur_seitenorientierung` aus
`beweise/ocr-drehung/2026-09-24/laeufe.jsonl`:

| Klasse | Werte mit Seitenorientierung |
|---|---|
| **unbrauchbar** (3) | 0.9468, 0.9656, **0.9872** |
| **brauchbar** (7) | *kein Text erkannt* → 0.0, **0.9752**, 0.9937, 0.9946, 0.9964, 0.9969, 1.0000 |

**Die Klassen überlappen.** 0,9752 (brauchbar) liegt unter 0,9872 (unbrauchbar). Es gibt keinen
Trennwert mehr, der beide Gruppen sauber scheidet — das ist der Befund, und er wird hier nicht
weggerechnet.

Alle Arbeitspunkte, die überhaupt in Frage kommen:

| Schwelle | Sensitivität | Spezifität | brauchbare Seiten fälschlich unsicher |
|---|---|---|---|
| 0,9937 (bester Youden-Index, J = 0,71) | 3/3 | 5/7 | **2** — darunter eine Seite mit 61 Zahlen |
| 0,9872 … 0,9752 | 2/3 | 6/7 | 1 (die Seite ohne Text) |
| **0,80 (eingestellt)** | **0/3** | **6/7** | **1 (die Seite ohne Text)** |

**Warum nicht 0,9937, obwohl es der rechnerisch beste Wert ist.** Er weist genau die drei Seiten ab,
die die Seitenorientierung gerade repariert hat — 122/97/91 → 495/564/413 Zeichen, 0 → 5
Datumsangaben —, plus eine brauchbare Seite mit 61 Zahlen. Der Gewinn der Drehung würde an der
nächsten Stelle wieder weggeworfen. Der Grund für die Überlappung ist nämlich kein Messrauschen,
sondern ein **Etikettenproblem**: die Urteile „unbrauchbar" hängen an den ungedrehten Texten. Für die
Produktvariante sind sie veraltet. Eine Schwelle gegen veraltete Etiketten zu optimieren heißt, die
Kennzahl zu bedienen statt das Problem.

**Gewählt: 0,80 — und dieser Wert weist auf den gemessenen Seiten faktisch nichts ab.** Das gehört
genau so gesagt, und es ist keine Notlösung, die sich als Lösung ausgibt:

* 0,80 liegt **unter allen zehn** gemessenen Seitenwerten der Produktvariante (Minimum 0,9468).
* 0,80 liegt **über** den Werten, die dieselben drei Seiten **ohne** Orientierungskorrektur hatten
  (0,681 / 0,697 / 0,774). Eine Seite, bei der die Korrektur versagt und die Engine wirklich Rauschen
  liest, fällt also weiterhin durch. Das ist der einzige Fall, für den die Schwelle unter
  `ocr_drehung: true` noch nachweislich etwas leistet.
* Abgewiesen wird auf dieser Stichprobe genau eine Seite: die **reine Bildseite ohne Text**. Sie
  bekommt nach der Regel „kein Text erkannt → Sicherheit 0.0" eine 0,0 und fällt unter *jede*
  Schwelle. Diese Regel bleibt absichtlich erhalten (Test
  `test_M3_B10_paddleocr_ohne_erkennung_hat_sicherheit_null`): eine Seite, von der die OCR nichts
  liefert, darf nicht als sicher gelesen gelten. Dass ausgerechnet diese Seite auch nichts *enthält*,
  was das Modell einordnen könnte, macht den Preis hier theoretisch.

Mit anderen Worten: **unter PaddleOCR mit Seitenorientierung ist `ocr_unsicher` praktisch auf die
Regel „kein Text erkannt" zusammengeschrumpft.** Wer glaubt, die Schwelle fange schlecht gelesene
Seiten ab, irrt — sie tut es auf den Daten, die es gibt, nicht. Der Schutz gegen falsch gelesene
Zahlen liegt woanders (Zitatprüfung, Konfliktprüfung), nicht hier.

### Geprüftes Alternativsignal: Textmenge je Seitenfläche

Der Auftrag nennt die Möglichkeit, ein anderes Signal zu nehmen. Naheliegend ist die Textdichte. Sie
wurde nachgerechnet (Zeichen je Megapixel der Seite, Variante `nur_seitenorientierung`):

| Klasse | Zeichen/Megapixel |
|---|---|
| **unbrauchbar** (3) | 34, 41, 47 |
| **brauchbar** (7) | 0 *(Seite ohne Text)*, 67, 77, 194, 224, 276, 302 |

Auf den Etiketten, die es gibt, **trennt die Dichte sauber**: jeder Wert zwischen 47 und 67 erreicht
Sensitivität 3/3 und Spezifität 6/7. Das ist besser als alles, was die Konfidenz noch leistet.

**Eingebaut wird sie trotzdem nicht**, aus zwei Gründen:

1. Sie hängt an **denselben veralteten Etiketten**. Die drei „unbrauchbaren" Seiten sind nach der
   Aufrichtung mit 413–564 Zeichen gerade dünn, nicht leer — und dass sie dünn sind, ist eine
   Eigenschaft der abgebildeten Dokumente (Personalausweis, Handyfoto), nicht ein Fehler der
   Erkennung. Ein Dichte-Tor würde also nicht „schlecht gelesen" abweisen, sondern „wenig Text
   drauf". Die brauchbare Seite mit **13 Zeichen** (Dichte 77) zeigt, wie schmal der Grat ist: eine
   Seite tiefer in der Sortierung, und das Tor schlüge bei einem korrekt gelesenen Dokument an.
2. Es wäre ein neues Signal, ein neuer Konfigurationsschlüssel und eine neue Codepfad-Verzweigung —
   gebaut auf einer Stichprobe von zehn Seiten mit **einer** Fehlerursache. Das ist genau die
   Spekulation, die dieses Projekt sonst vermeidet.

Festgehalten ist sie hier, weil sie der aussichtsreichste Kandidat für die Runde **nach** der zweiten
Gegenlese ist — dann mit Etiketten, die zu den aufgerichteten Texten passen.

### Vorbehalt — und das ist kein Formelsatz

**Zehn Seiten sind eine winzige Stichprobe.** Konkret:

* Die positive Klasse besteht aus **drei Seiten**. Eine einzige Seite wiegt 33 Prozentpunkte
  Sensitivität.
* **Alle drei scheitern an derselben Ursache** — Verdrehung. Genau der Ursache, die mit
  `ocr_drehung: true` jetzt behoben ist. Über andere Fehlerursachen (Unschärfe, Überbelichtung,
  Durchscheinen, Handschrift, schlechte Kopien) sagt diese Ableitung **nichts**. Es ist gut möglich,
  dass eine unscharfe Seite hohe Zeilen-Scores auf falsch gelesenem Text liefert und das Tor
  ungehindert passiert — 0,80 lässt sie mit Sicherheit durch.
* Ein Gegenleser, ein Durchgang — keine Angabe, wie reproduzierbar das Urteil selbst ist.
* **Die Urteile gelten für Texte, die es im Produkt nicht mehr gibt.** Die drei aufgerichteten Seiten
  sind heute andere Texte als die, über die geurteilt wurde. Ob sie brauchbar sind, ist
  **ungemessen** — und davon hängt ab, ob die Überlappung ein Etikettenproblem ist (dann ist 0,80
  richtig) oder ein echtes Signalproblem (dann braucht es das andere Signal).

**Was eine belastbare Ableitung bräuchte:** rund 100 gegengelesene Seiten aus dem echten Bestand,
gezogen über **mehrere Fehlerursachen** (nicht nur Verdrehung) und **mit der Drehung, die im Produkt
läuft**, mit mindestens 20–30 Seiten in der Klasse „unbrauchbar". Dann ließen sich Sensitivität und
Spezifität über den Schwellenbereich auftragen und der Arbeitspunkt bewusst wählen — und dann ließe
sich auch entscheiden, ob die Konfidenz überhaupt das richtige Signal ist oder die Textdichte. Bis
dahin ist 0,80 eine **begründete Setzung ohne nachgewiesene Schutzwirkung**, und sie steht in
`modelle.yaml`, damit sie ohne Code-Änderung korrigiert werden kann.

## Was der Wechsel im Betrieb kostet

| | Tesseract | PaddleOCR |
|---|---|---|
| Abhängigkeit | `tesseract`-Binary (brew) | `uv sync --extra ocr-paddle`: `paddleocr` + `paddlepaddle` (vollständiges Inferenz-Framework, u. a. `opencv-contrib-python`, `shapely`, `pandas`, `protobuf`) |
| Modelle | im Paket | einmaliger Download nach `~/.paddlex` beim ersten Lauf, danach offline |
| Erstaufruf | – | rund 5 s Modell-Ladezeit je Einstellung, einmalig je Prozess |
| Laufzeit je Seite | ~1 s | ~29 s; die Seitenorientierung kostet nichts (247 gegen 248 s über 10 Seiten) |
| Voller Einlesevorgang (134 OCR-pflichtige Seiten) | ~2,2 min | ~66 min |

Eine Stunde einmalig beim Einlesen ist vertretbar — das Einordnen mit dem Sprachmodell dauert auf
demselben Bestand ohnehin länger (16,2 s je Datei über 200 Dokumente, `beweise/last/2026-09-24/`). Das Abhängigkeitsgewicht ist
die eigentliche Frage an diesen Wechsel, und sie ist eine **Betriebsentscheidung, keine Messfrage**:
Wer sie anders beantwortet, setzt `ocr: tesseract` und weiß aus der Tabelle oben, was das kostet.

**Kein stiller Rückfall.** Ist `ocr: paddleocr` eingestellt und das Extra fehlt, bricht der Start mit
Installationsbefehl ab (`provider.lade_ocr_einstellungen` → `auslesen.fordere_ocr`). Würde das
Produkt stattdessen leise Tesseract nehmen, liefe es mit 3 statt 7 brauchbaren von 10 Seiten — eine
andere Messlage als die eingestellte, und niemand hätte es bemerkt. Dasselbe Prinzip wie beim
Reranker.

## Was ungemessen bleibt

Vollständig, ohne Beschönigung:

1. **Ob der aufgerichtete Text richtig ist.** Die einzige menschliche Wahrheit, die es gibt, hängt an
   den ungedrehten Texten. Fällig: zweite Gegenlese-Runde mit `ocr_drehung: true`, zuerst auf den
   drei aufgerichteten Seiten.
2. **Ob `ocr_unsicher` unter Drehung überhaupt noch etwas leistet.** Nein, nach dieser Messung — die
   Klassen trennen nicht mehr, 0,80 weist außer leeren Ergebnissen nichts ab. Ob das richtig ist
   (weil die Seiten wirklich repariert sind) oder ein blinder Fleck, hängt an derselben zweiten
   Gegenlese-Runde. Der Kandidat für ein besseres Signal — Textmenge je Seitenfläche — ist oben
   gerechnet und begründet zurückgestellt.
3. **Andere Fehlerursachen als Verdrehung.** Unschärfe, Überbelichtung, Durchscheinen, Handschrift
   sind in der Stichprobe nicht oder nicht als Misserfolg vertreten.
4. **Absatz- und Tabellenstruktur.** `fundstellen.zerlege` trennt an Leerzeilen. PaddleOCR liefert
   Zeilen, die hier mit `\n` verbunden werden — ob daraus dieselbe Absatztrennung entsteht wie bei
   Tesseract, hat **keine** dieser Messungen betrachtet. Sie haben Zeichen, Wörter und Zahlen
   verglichen, und die Leitkennzahl ignoriert Reihenfolge ausdrücklich. Das ist die nächstgrößte
   offene Stelle nach der Gegenlese-Runde.
5. **`return_word_box`.** PaddleOCR kennt eine Option, die Wortkästen statt Zeilen liefern könnte —
   dann wären die Konfidenzen beider Engines dieselbe Größe und die Schwelle übertragbar. Ob sie mit
   dem deutschen Modell funktioniert: ungeprüft.
6. **Die Laufzeitprobe auf PDFs ohne Textebene** (10 Seiten) aus `docs/ocr-portabel-2026-09-23.md`
   ist weiterhin nicht nachgeholt; die Laufzeiten stammen aus dem Renderinglauf.
7. **Die 50 fehlenden Seiten** des Wahrheitslaufs (96 von 150 ausgewertet).
8. **`python-doctr`** als Alternative mit leichterem Abhängigkeitsbaum: ungemessen.
9. **Andere Hardware.** Alles gemessen auf einem MacBook Pro M4 Pro (24 GB), CPU-Pfad von PaddleOCR.
   Die 29 s je Seite sind kein allgemeiner Wert.

## Belege

| Ordner | Inhalt |
|---|---|
| `beweise/ocr-portabel/2026-09-23/` | Wahrheitslauf, 96 Seiten, 6 Engines (`laeufe.jsonl`, `bericht.md`) |
| `beweise/ocr-scans/2026-09-24/` | Gegenlese-Paket und `urteile.json`. **Nicht versioniert** (`.gitignore`) — enthält als einziger Beweisordner absichtlich Dokumentinhalt |
| `beweise/ocr-drehung/2026-09-24/` | Drehungsmessung (`laeufe.jsonl`, `zahlenmengen.json`), nur Kennzahlen, kein Inhalt |
