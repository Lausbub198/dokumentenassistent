# Skript-Baustein: Wie die Suche wirklich funktioniert 

> **Historisch, Stand 25.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


Notiz für das TelePro-Skript (Format nach `TelePro/SKRIPT-FORMAT.md`). Ergänzt `skript-baustein-kontext-4k.md`:
dort steht, *wie viel* Kontext das RAG braucht — hier steht, *wer* die richtigen Absätze in diesen Kontext legt.
Stand 2026-09-20; die Zahlen aus dem Retrieval-Eval (`beweise/retrieval/`) folgen, sobald gemessen. Alles hier
beschreibt den Code in `src/dokumentenassistent/suche.py`, `fundstellen.py`, `zitatpruefung.py` — nichts ist erfunden.

Zum Systembild: dieser Baustein gehört zum Knoten **suche (M11)** und greift auf **fundstellen (M4)** zurück.

---

# Das Missverständnis: „Die KI durchsucht meine Dokumente" 

Wenn ich sage, mein Assistent beantwortet Fragen zu meinen Dokumenten, denken die meisten:
Das Sprachmodell liest die Dokumente und sucht die Antwort.

Stimmt nicht. Das Sprachmodell sucht **gar nichts**.

[PAUSE]

Der Fachbegriff für das, was hier passiert, heißt **RAG** — Retrieval-Augmented Generation.
Drei Wörter, drei Schritte: **Retrieval** — das Heraussuchen. **Augmented** — das Anreichern des Prompts mit dem Gefundenen.
**Generation** — das Formulieren der Antwort.

Nur der dritte Schritt ist das Sprachmodell.

[PAUSE]

Das Retrieval — das Heraussuchen — ist ein Stück klassischer Informatik. Mathematik aus den Neunzigern, deterministisch, in Millisekunden.
Das Sprachmodell kommt erst ganz am Ende dran, und es bekommt genau **acht Absätze** und eine Frage.
Mehr sieht es nicht.

Das ist kein Kompromiss. Das ist der Grund, warum das Ding funktioniert.

[NOTE: Systembild einblenden, Knoten „suche M11" hervorheben. Einblendung: RAG = Retrieval · Augmented · Generation = Heraussuchen · Anreichern · Formulieren]

# Schritt 0: Chunking — Absätze statt Dokumente 

Bevor irgendetwas gesucht wird, passiert etwas, das in der Fachsprache **Chunking** heißt. Chunk — ein Brocken, ein Stück.
Auf Deutsch: Die Datei wird **zerlegt**.

Warum? Weil eine Rechnung von Krause GmbH nicht „über Heizung" ist. Ein bestimmter Absatz darin nennt den Betrag.
Wer ganze Dokumente sucht, findet das Dokument. Wer Absätze sucht, findet die **Stelle**.

Und die Stelle ist das, was ich später zitieren will.

[PAUSE]

Bei mir heißen die Chunks **Fundstellen**, und sie entstehen so:

Erstens: Die Datei wird zu **Seiten**. Hat das PDF eine Textebene, wird sie gelesen. Hat es keine — ein Scan, ein Handyfoto — läuft eine Texterkennung, OCR, mit Tesseract. Kein Sprachmodell, ein Programm aus den Achtzigern.

Zweitens: Jede Seite wird an den **Leerzeilen** geschnitten. Ein Textblock zwischen zwei Leerzeilen ist ein Absatz — so, wie ein Mensch einen Absatz auch erkennen würde.
Hat eine Seite keine Leerzeilen, ist die ganze Seite ein Absatz.

Drittens: Ist ein Absatz zu lang — mehr als **380 Wörter** — wird er in **Fenster** geteilt. Jedes Fenster überlappt das vorige um **30 Wörter**, damit an der Schnittkante kein Satz halbiert wird, den nachher niemand findet.
In der Fachsprache: *Sliding Window mit Overlap*. Auf Deutsch: verschobenes Fenster mit Überlappung.

Viertens: Jeder Chunk bekommt eine **Adresse** — Dateiname, Seitennummer, Absatznummer. Fortlaufend, ohne Lücke.

[NOTE: Einblendung einer Fundstellen-ID im Format `Rechnung (3).pdf#S1#A4` — „Datei, Seite 1, Absatz 4"]

Diese Adresse ist später das Zitat. Und weil sie fortlaufend vergeben wird, kann ich sie aufklappen und den Absatz nachlesen.

[PAUSE]

Jetzt der Punkt, auf den ich hinaus will: **Das ist deterministisch.**
Dieselbe Datei, dieselbe Zerlegung. Immer. Kein Modell entscheidet, wo geschnitten wird — eine Leerzeile entscheidet, und eine Wortzahl.

Es gibt Verfahren, bei denen ein Sprachmodell die Schnittstellen wählt — „semantisches Chunking". Klingt schlauer.
Aber dann ist die Fundstelle Nummer 4 heute eine andere als morgen, und mein Zitat zeigt ins Leere.
!!Ein Zitat, das ich nicht reproduzieren kann, ist kein Beleg!!.

Deshalb: Leerzeilen und Wortzahl. Langweilig, nachprüfbar, jeden Tag gleich.

# Schritt 1: Sparse Retrieval — die Wortsuche, BM25 

Die erste Suche heißt in der Fachsprache **Sparse Retrieval** — spärlich, weil jeder Absatz nur die paar Wörter enthält, die tatsächlich drinstehen. Auf Deutsch: **Wortsuche**. Der Algorithmus dahinter heißt **BM25**. Best Match 25 — die Nummer ist historisch, der Algorithmus ist von 1994 und steckt bis heute in jeder Volltextsuche, von Lucene bis Elasticsearch.

Die Idee in einem Satz:
Ein Absatz passt zur Frage, wenn er die **seltenen** Wörter der Frage enthält — oft, aber nicht nur, weil er lang ist.

[PAUSE]

Drei Zutaten:

Erstens: **Wie oft** kommt das Wort im Absatz vor.
Zweitens: **Wie selten** ist das Wort im ganzen Bestand. „Rechnung" steht in hundert Absätzen — sagt nichts. „Krause" steht in dreien — sagt alles.
Drittens: **Wie lang** ist der Absatz. Ein langer Absatz enthält jedes Wort irgendwann — dafür wird er bestraft.

Das ist BM25. Keine Magie, keine Trainingsdaten, kein Zufall.
Dieselbe Frage, derselbe Bestand — **immer dasselbe Ergebnis**.

!!Und es ist unschlagbar, wenn die Frage den Wortlaut des Dokuments trifft!!: „Tiefengrund", „Rahmenvertrag Gerüstbau",
eine Rechnungsnummer, die man kennt. Das findet BM25 sofort, auf Platz 1. Ein Sprachmodell würde raten.

Aber — und das habe ich erst durch Messen gelernt — es hat eine deutsche Schwäche.
Ich frage nach der „Telefonrechnung". In der Rechnung steht „Telefon" und „Rechnung". Zwei Wörter, nicht eins.
Für BM25 sind das Fremdwörter. Platz 45 von 694.
Und wer *nach* einer Rechnungsnummer fragt, statt sie zu kennen, gibt BM25 nichts zum Suchen.

[NOTE: Einblendung „Wo es bricht", Zeile Telefonrechnung: BM25 45 · Embedding 1. Zahlen aus `docs/retrieval-befund-2026-09-21.md`]

[NOTE: Falls Zeit: die Anekdote aus dem Code — die Standard-Bibliothek liefert bei kleinen Beständen 0 für alles, sobald ein Wort in mehr als der Hälfte der Absätze steht. Bei drei Dokumenten fand die Suche deshalb nichts. Wir rechnen die IDF selbst, Lucene-Variante, immer positiv.]

# Schritt 2: Dense Retrieval — die Bedeutungssuche, Embeddings 

BM25 hat eine Schwäche: Es kennt nur Buchstaben.
Frage ich nach der **Heizungsreparatur**, und in der Rechnung steht **Instandsetzung Gastherme** — null Treffer. Kein gemeinsames Wort.

Dafür gibt es die zweite Suche: **Dense Retrieval** — dicht, weil hier jeder Absatz durch eine lange, lückenlose Zahlenreihe beschrieben wird. Auf Deutsch: **Bedeutungssuche**. Das Werkzeug dafür heißt **Embedding** — wörtlich Einbettung: ein Text wird in einen Zahlenraum eingebettet.

Ein Embedding-Modell verwandelt einen Text in eine Zahlenreihe — bei bge-m3 sind es 1 024 Zahlen.
Texte mit ähnlicher **Bedeutung** bekommen ähnliche Zahlenreihen.
„Heizungsreparatur" und „Instandsetzung Gastherme" liegen nah beieinander.
„Heizungsreparatur" und „Speisekarte" liegen weit auseinander.

[PAUSE]

Beim Einlesen bekommt jede Fundstelle einmal ihre Zahlenreihe — das dauert, passiert aber nur einmal.
Bei einer Frage wird nur die Frage in Zahlen verwandelt, und dann rechnet der Assistent den Winkel zwischen der Frage und jedem Absatz.
Kleiner Winkel, hohe Ähnlichkeit.

Wichtig: **Auch das ist deterministisch.** Dasselbe Modell, derselbe Text, dieselbe Zahlenreihe.
Das Embedding-Modell ist ein neuronales Netz, aber es erzeugt nichts — es misst.

[NOTE: Einblendung: zwei Pfeile im Raum, Winkel dazwischen; „Kosinus-Ähnlichkeit"]

Und hier wird es spannend: Embedding-Modelle sind **nicht gleich**.
bge-m3, nomic-embed-text, qwen3-embedding — die verstehen Deutsch unterschiedlich gut, Fachbegriffe unterschiedlich gut, kurze Absätze unterschiedlich gut.

Gemessen, 200 Dateien, 694 Absätze, 14 Fragen: Wie oft steht die richtige Datei auf Platz 1?
qwen3-embedding: **79 Prozent**. bge-m3: 71. nomic-embed-text: **29**.
Dasselbe Verfahren, derselbe Bestand — und das kleinste Modell findet zwei Drittel der Antworten nicht auf Anhieb.
Bei 25 Dateien hätte man den Unterschied nie gesehen: da treffen alle drei.

!!Welches Embedding auf deinen Dokumenten trifft, kann man nicht wissen. Man muss es messen — und zwar auf der Größe, die dein Bestand wirklich hat!!.

# Schritt 3: Hybrid Search — zwei Listen, eine Antwort 

Jetzt habe ich zwei Ranglisten. BM25 sagt: Absatz 17, dann 4, dann 9.
Die Embeddings sagen: Absatz 4, dann 22, dann 17.

Wer hat recht?

Beide. Deshalb heißt der Ansatz **Hybrid Search** — Hybridsuche, Wortsuche und Bedeutungssuche zusammen. Das ist der Standard, den auch die großen Suchmaschinen fahren.

Zusammengeführt wird mit **Reciprocal Rank Fusion**, RRF — wörtlich: Verschmelzung über die Kehrwerte der Ränge.
Klingt kompliziert, ist eine Zeile: Jeder Absatz bekommt Punkte für seinen **Platz** in jeder Liste — Platz 1 gibt mehr als Platz 2, Platz 2 mehr als Platz 3.
Wer in beiden Listen vorne steht, gewinnt.

[PAUSE]

Warum Plätze und nicht Punktzahlen? Weil BM25-Punkte und Kosinus-Winkel nichts miteinander zu tun haben.
Man kann sie nicht addieren. Plätze kann man addieren.

Absatz 4 steht in beiden Listen oben — der gewinnt.
Absatz 17 in beiden weiter oben — zweiter.
Und Absatz 22, den nur die Embeddings kannten, kommt trotzdem rein.

!!Das ist der Trick!!: Die Wortsuche findet den Wortlaut, die Bedeutungssuche findet die Umschreibung — und keine von beiden kann die andere überstimmen.

Und genau da liegt auch die Falle, die ich gemessen habe: Wenn eine der beiden Listen schlecht ist, zieht sie die andere mit runter.
Mit BM25 auf Platz 45 fällt die richtige Datei im Hybrid von Platz 1 auf Platz 3 oder 4 — bei acht Absätzen im Prompt ist sie noch drin, aber sie steht nicht mehr oben.
Hybrid ist nur so gut wie die schwächere Hälfte. Deshalb: erst BM25 deutschfähig machen — Komposita zerlegen —, dann darf es gleichberechtigt mitstimmen.

[NOTE: Zahlen: bge-m3 dense 71 % Rang 1 → hybrid 57 %; Recall@8 in beiden 93 %. `docs/retrieval-befund-2026-09-21.md`]

Die besten **acht** kommen in den Prompt. Nicht mehr.
Und wenn selbst der beste Absatz einen zu schlechten Wert hat, wird das Modell **gar nicht gefragt** — die Antwort ist dann „nicht gefunden", ohne dass eine KI Gelegenheit hatte, etwas zu erfinden.

[NOTE: Einblendung: zwei Ranglisten, Pfeile zu einer dritten, „RRF"]

# Schritt 4: Augmented Generation — jetzt erst das Sprachmodell 

Erst jetzt kommt das Sprachmodell ins Spiel — das ist das A und das G in RAG: der Prompt wird mit den acht Absätzen **angereichert**, und das Modell **formuliert**. Es bekommt eine kurze, harte Anweisung:

Beantworte die Frage **ausschließlich** aus diesen acht Absätzen.
Belege **jede** Aussage mit der Absatz-ID in eckigen Klammern.
Wenn ein Absatz einen anderen korrigiert — Korrekturrechnung — gilt der korrigierte Wert, und du nennst beide.

[PAUSE]

Das Modell formuliert. Es sucht nicht, es erinnert sich an nichts, es weiß nichts über meine Firma.
Es hat acht Absätze und eine Frage. Das ist die ganze Welt, die es sieht.

Und genau deshalb reicht ein kleines Modell. Ein 4-Milliarden-Modell auf einem Notebook muss nicht alles wissen.
Es muss acht Absätze lesen und einen sauberen deutschen Satz daraus machen.

Und deshalb braucht es auch **kein Denkmodell**. Denken — dieses lange Überlegen vor der Antwort — hilft bei Rätseln.
Hier gibt es kein Rätsel. Gemessen: Die reine Instruct-Version von Qwen3-4B schlägt das Denkmodell mit abgeschaltetem
Denken 21 zu 0 beim Verdichten und ist viermal schneller.
!!Ein RAG braucht kein Modell, das denkt. Es braucht eines, das lesen kann!!.

[NOTE: Zahlen aus `lokalki-lab/docs/messungen/2026-09-20-screening-ohne-denken.md`; Herleitung in `skript-baustein-journey.md`, Station 5]

# Schritt 5: Grounding Check — Vertrauen ist gut, Zitatprüfung 

Und weil ich einem Sprachmodell trotzdem nicht traue, kommt danach noch eine Kontrolle. In der Fachsprache **Grounding** — ist die Antwort im Text verankert? Auf Deutsch: **Zitatprüfung**. Wieder ohne KI.

Jedes Zitat, das das Modell in eckige Klammern gesetzt hat, wird geprüft:
Gehört die ID zu einem der acht Absätze, die es bekommen hat? Wenn nicht — **weg**.
Steht der zitierte Wortlaut wirklich in dem Absatz? Wenn nicht — **ungültig**.

Eine Antwort ohne ein einziges gültiges Zitat gilt als „nicht gefunden".

[PAUSE]

Das heißt: Das Modell kann halluzinieren, so viel es will. Es kommt nicht durch.
Jede Zahl, die der Assistent nennt, hat eine Adresse — Datei, Seite, Absatz — und die kann ich aufklappen und nachlesen.

[NOTE: Demo: Antwort mit Belegkarte aufklappen, Original-Absatz zeigen]

# Warum das auf einem Notebook funktioniert 

Zusammengefasst, damit man's mitschreiben kann:

Erstens: Chunking — Absätze, nicht Dokumente. Deterministisch.
Zweitens: Sparse Retrieval, BM25 — Wortsuche, exakt, deterministisch.
Drittens: Dense Retrieval, Embeddings — Bedeutungssuche, deterministisch, austauschbar.
Viertens: Hybrid Search, RRF — beide Listen zusammen, keine überstimmt die andere.
Fünftens: Augmented Generation — acht Absätze ins Modell, Zitatpflicht.
Sechstens: Grounding — Zitatprüfung ohne KI.

[NOTE: Einblendung als Tabelle: Fachbegriff | Deutsch | deterministisch? — sechs Zeilen, fünfmal „ja", einmal „nein (das Modell)"]

[PAUSE]

Von diesen sechs Schritten ist **genau einer** ein Sprachmodell.
Die anderen fünf sind Mathematik, die auf jedem Rechner in Millisekunden läuft.

Das ist die Antwort auf die Frage, warum das lokal geht.
!!Nicht, weil das Modell so schlau ist — sondern weil es so wenig tun muss!!.

# Und welches Embedding? Messen. 

Bleibt die eine Stelle, an der man raten könnte: welches Embedding-Modell.

Ich rate nicht. Ich habe zwanzig Fragen zu meinem Bestand, bei denen ich weiß, in welcher Datei die Antwort steht.
Dann lasse ich die Suche laufen — nur BM25, nur Embeddings, beides zusammen — für jedes Embedding-Modell.
Und zähle: Wie oft steht die richtige Datei auf Platz 1? Unter den ersten fünf? Unter den ersten acht?

Das dauert Minuten, braucht kein Sprachmodell, und danach weiß ich es.

Ergebnis bei 200 Dateien: Die richtige Datei ist unter den ersten acht — bei **93 Prozent** der Fragen, mit bge-m3 wie mit qwen3-embedding.
Eine von vierzehn Fragen findet kein Verfahren: die Rechnung vom 14. August, bester Platz 7.
Die kann das beste Sprachmodell der Welt nicht beantworten. Das ist kein Modellfehler — das ist ein Retriever-Fehler, und den sehe ich nur, weil ich ihn getrennt messe.

[NOTE: Einblendung Tabelle Retrieval-Eval Stufe 200: Variante × Embedding, Recall@1/5/8/MRR — `beweise/retrieval/2026-09-21/bericht.md`]

[NOTE: Die Erwartung von gestern („Hybrid > jede Einzelsuche") ist GEMESSEN FALSCH für Rang 1 — Hybrid gleichgewichtet verliert gegen dense allein, weil BM25 auf Deutsch schwach ist. Das ehrlich sagen; es ist die bessere Geschichte.]

Und das ist auch die Brücke zum Kontext-Thema: Wenn die richtige Datei in neun von zehn Fällen unter den ersten fünf ist,
dann reichen fünf Absätze im Prompt. Dann reicht 4k. Dann reicht das Notebook.
Gemessen: 93 Prozent unter den ersten fünf mit bge-m3 hybrid oder qwen3-embedding dense — fünf Absätze reichen.

---

## Quellen (nicht sprechen)

- Ablauf: `src/dokumentenassistent/suche.py::suche` — `bm25_rang` → `provider.embed([frage])` → `dense_rang` →
  `rrf(k=60)` → Schwelle 0.02 → `top_n=8` → `generate_text(_prompt)` → `_karten` (Zitate nur aus Top-8).
- BM25: eigene Implementierung, Lucene-IDF `log(1 + (N-n+0.5)/(n+0.5))`, k1 = 1.5, b = 0.75. Grund im Docstring:
  `rank_bm25.BM25Okapi` liefert bei kleinen Beständen 0 (negative IDF gekappt).
- Chunking: `fundstellen.py::zerlege`, Absatz = Leerzeilen-getrennt (`_LEERZEILE`), Fenster 380 Wörter, Überlappung 30,
  Absatznummer je Seite fortlaufend, ID-Format `<datei>#S<seite>#A<absatz>` (`_ZITAT` in suche.py). Seiten aus
  `auslesen.py`: pypdf-Textebene, sonst Tesseract-OCR (`lang=deu`). Tesseract: HP Labs 1985, offen seit 2005.
- Embedding: `modelle.yaml` → bge-m3 (1 024 Dimensionen), Alternative qwen3-embedding:0.6b; Kosinus in `dense_rang`.
- Anweisung an das Modell: `_ANWEISUNG` in suche.py (ausschließlich aus Absätzen, jede Aussage belegen,
  Korrekturregel).
- Zitatprüfung: `zitatpruefung.py::pruefe_beleg` (Wortlaut normalisiert im Absatz enthalten), `pruefe_wert`.
- Retrieval-Eval: `src/dokumentenassistent/retrieval_eval.py`, gemessen 2026-09-21 00:01, Ausgabe
  `beweise/retrieval/2026-09-21/` (laeufe.jsonl, bericht.md); Befund `docs/retrieval-befund-2026-09-21.md`.
  Stufe 200: bm25 R@1/5/8 21/36/43; dense bge-m3 71/86/93, nomic 29/64/79, qwen3-emb 79/93/93; hybrid bge-m3
  57/93/93, nomic 36/79/93, qwen3-emb 50/86/93. Stufe 25: hybrid alle 100/100/100.
  Goldstandard `beispiele/malerbetrieb/golden.json` (Fragen mit `datei`).
- RRF: Cormack, Clarke, Buettcher 2009, „Reciprocal Rank Fusion outperforms Condorcet and individual rank learning
  methods", k = 60 wie im Paper. BM25: Robertson & Walker 1994 (Okapi at TREC-3).
