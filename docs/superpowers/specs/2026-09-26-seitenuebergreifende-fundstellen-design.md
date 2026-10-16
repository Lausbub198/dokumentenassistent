# Seitenübergreifende Fundstellen mit PDF-Provenienz

Stand: 26.09.2026. Nutzerziel: PDF-Seitengrenzen dürfen zusammenhängenden
Dokumenttext nicht künstlich in Such-Chunks trennen. Die Herkunft jeder Passage
muss für zitierbare PDF-Seiten erhalten bleiben. Danach folgt ein isolierter
Retrieval-Vergleich ohne Antwortgenerierung. Nicht Teil dieser Änderung sind
PDF→Markdown-Konvertierung, automatische Überschriftenerkennung, ein neues
Embeddingmodell oder eine neue Antwortstrategie.

## Ausgangslage und Entscheidung

`lies_seiten` liefert geordneten Text mit PDF-Seitennummern. `zerlege` trennt an
Leerzeilen, teilt überlange Absätze bei 380 Wörtern mit 30 Wörtern Überlappung
und verbindet kurze Teile bis etwa 120 Wörter. Die Verbindung endet derzeit
an jeder Seite, weil `Fundstelle.seite` nur eine Zahl trägt. Index, MCP und
Web zeigen dieselbe Einzelseite an. Dieser Datenvertrag, nicht ein gemessener
Suchvorteil, ist die Seitenbarriere.

Gewählt wird ein fortlaufender Textstrom **je Dokument** mit expliziter
Seiten-Provenienz pro Chunk. Absätze und die bestehenden 120/380/30-Regeln
bleiben für die erste Ablation unverändert. Weder Dateigrenzen noch die
Reihenfolge der ausgelesenen PDF-Seiten dürfen überschritten werden. Ein
Seitenwechsel allein löst keinen Chunk-Abschluss aus.

Verworfene Alternativen für diesen Schritt:

- PDF zunächst in Markdown umwandeln: ändert Extraktion, Layoutinterpretation
  und Chunking zugleich; der Effekt einer aufgehobenen Seitenbarriere wäre
  nicht mehr isolierbar.
- Nur Parent-Document-Retrieval ändern: erweitert den Antwortkontext, behebt
  aber die Seitenbarriere in den indexierten Chunks nicht.

## Daten- und Zitiervertrag

Eine `Fundstelle` behält für bestehende Aufrufer `seite` als **erste** PDF-Seite
und bekommt zusätzlich eine geordnete, unveränderliche Folge von Spannen
`(seite, start, ende)`. `start`/`ende` sind halb-offene Zeichenpositionen im
genau gespeicherten `Fundstelle.text`. Eingefügte Trenner zwischen Textteilen
gehören keiner PDF-Seite an. Jede Spanne muss innerhalb des Chunktexts liegen;
die Seitennummern müssen in der Reihenfolge der beitragenden Seiten monoton
sein. Leere PDF-Seiten können zwischen Beiträgen liegen. Eine Seite darf
mehrere Spannen beitragen, wenn ihre Textteile durch eingefügte Trenner
getrennt sind. Aus der geordneten Spannenfolge ergibt sich der Seitenbereich.

Die SQLite-Tabelle `fundstellen` erhält eine nullable JSON-Spalte für diese
Spannen. Alte Zeilen ohne Spannen werden beim Lesen als einseitiger Beleg
interpretiert, ohne bestehende IDs oder Embeddings als neue Provenienz
auszugeben. Neue Zeilen speichern Spannen und Text gemeinsam in der
vorhandenen Transaktion. Bei geändertem Text ersetzt der Kopielauf die
Fundstelle und invalidiert ihren Vektor nach den bestehenden
Text-/Modell-Provenienzregeln. Bei lediglich korrigierter Seiten-Provenienz
bleibt derselbe Textvektor gültig, aber die Beleganzeige muss die neuen
Spannen verwenden. Quellenindex und Originale werden nicht in-place umgebaut.

Die aktuelle ID-Form bleibt eine dokumentgebundene ID aus Dokumenthash,
Startseite, fortlaufender Chunknummer und Texthash. Sie ist **kein** Beweis,
dass nur die Startseite zitiert werden darf. Die Zitierprüfung akzeptiert
weiterhin nur bekannte IDs aus dem tatsächlichen Antwortkontext. In Web und
MCP wird ein einseitiger Chunk wie bisher mit einer Seite, ein mehrseitiger
Chunk als Seitenbereich angezeigt. Das bestehende MCP-Feld `seite` bleibt
als Startseite erhalten; ein additives `seiten`-Feld liefert alle betroffenen
Seiten. Ein bloßes Chunk-ID-Zitat beansprucht keinen exakteren Ort als diesen
Bereich. Ein genauerer Ort innerhalb des Bereichs wäre eine spätere,
gesondert geprüfte Wortlaut-Zuordnung.

## Verarbeitung und Fehlergrenzen

Der Chunker baut aus den `Seite`-Objekten in PDF-Lesereihenfolge logische
Absätze. Ein Absatz, der am Seitenende ohne Leerzeile weiterläuft, wird
nicht durch den Seitenwechsel beendet. Eine vorhandene Leerzeile bleibt
eine Absatzgrenze, auch wenn sie an einer Seitengrenze liegt. Kurze
benachbarte Absätze dürfen bis zur bestehenden Mindestgröße zusammenlaufen.
Der finale Chunktext und seine Spannen werden aus denselben Teilstücken
erzeugt; nachträgliches Rekonstruieren der Seiten aus dem fertigen Text ist
ausgeschlossen. Für Tabellen, mehrspaltige PDFs und wiederholte Kopf-/Fußzeilen
ist eine korrekte Lesereihenfolge Voraussetzung; diese Änderung behauptet
keine neue Layoutanalyse. Solche Fälle werden im Test als Risiken separat
ausgewiesen.

Die optionale `eltern_seiten`-Suche setzt bisher einseitige Fundstellen
voraus. Sie muss bei mehrseitigen Chunks entweder die gespeicherten Spannen
korrekt benutzen oder ausdrücklich mit einem Fehler abbrechen; eine
stillschweigend falsche Seite ist unzulässig. Standardmäßig ist sie aus.
Nicht lesbare PDFs lassen den bisherigen Index unverändert; vollständiger
Dokumentersatz und Beleg-/Vektorinvalidierung behalten ihre Transaktionsgrenze.

## Prüfnachweise und Übernahme

Vor Produktcode stehen fehlschlagende Regressionen für: Satzfortsetzung über
zwei PDF-Seiten, eine echte Absatzgrenze am Seitenwechsel, lange Absätze mit
Fenster/Überlappung, Seiten-Spannen nach Zusammenführen und Teilen,
Index-Roundtrip, alte einseitige Indexzeilen, Web-/MCP-Seitenbereich,
fehlgeschlagenen Ersatz sowie eine mehrdeutige/ungültige Quellen-ID.
Die vollständige Produktsuite muss danach bestehen; bestehende
einseitige Zitate dürfen sich nicht ändern.

Der Bestandsversuch verwendet dieselben ausgelesenen Seitentexte und zwei
getrennte private Indexkopien: A mit bisheriger Seitenbarriere, B ohne sie.
Vor Embeddings: Anzahl/Größe der Chunks, Grenzfälle und exakte wie
Whitespace-normalisierte Gold-Wortlautverfügbarkeit auf 85 positiven
Fragen. Danach – nur mit gesondert freigegebenen lokalen Embeddings – ein
gepaarter Retrieval-Lauf auf 85 positiven und 15 negativen Fragen mit
identischem Modell, Reranker, Schwelle und Kontextbudget. Berichtet werden
Zielchunk-Rang, Kontexttreffer, Gewinne, Verluste, Negativkontrollen und
Laufzeit. Wortlauttreffer bleiben getrennt von semantischer Antwortstützung;
ohne Antwort-LLM gibt es keine Behauptung über richtige Endantworten.

Kein Produkt-Default-Wechsel allein aufgrund synthetischer Tests oder
Gold-Wortlautverfügbarkeit. Original-PDFs, Quellindex, menschliche Freigaben
und alte Messartefakte bleiben unverändert. Private Dokumenttexte und Fragen
bleiben außerhalb von Git und Berichtsausgaben.
