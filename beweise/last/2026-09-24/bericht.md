# Belastungstest

## gemma4:12b-it-q4_K_M · qwen3-embedding:0.6b

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 25 | 330.2 | 13.2 | 60 | 4 | 33 | 2/64 | 2/2 | 11/12 | 7.7 |
| 200 | 200 | 3246.8 | 16.2 | 80 | 3 | 89 | 11/640 | 8/8 | 18/20 | 10.6 |

## qwen3.5:9b-q8_0 · qwen3-embedding:0.6b

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 200 | 200 | 3624.5 | 18.1 | 63 | 21 | 82 | 19/621 | 7/8 | 14/20 | 8.0 |

## qwen3.5:9b · qwen3-embedding:0.6b

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 200 | 200 | 2819.9 | 14.1 | 64 | 19 | 83 | 17/621 | 8/8 | 14/20 | 5.7 |

## Wo es bricht

| Frage | gemma4:12b-it-q4_K_M · qwen3-embedding:0.6b @25 | gemma4:12b-it-q4_K_M · qwen3-embedding:0.6b @200 | qwen3.5:9b · qwen3-embedding:0.6b @200 | qwen3.5:9b-q8_0 · qwen3-embedding:0.6b @200 |
|---|---|---|---|---|
| Wie hoch war die Telefonrechnung für März 2025? | grün | grün | grün | grün |
| Welchen Betrag hat die Rechnung an die Kita Sonnenschein? | grün | grün | grün | grün |
| Was hat das Rollgerüst für die Bahnhofstraße 3 gekostet? | rot | grün | rot | rot |
| Was kostet die Fassadenfarbe für die Ringstraße 8 laut korrigierter Rechnung von Farben Meister? | grün | grün | grün | grün |
| Welcher Betrag gilt für das Gerüst Ringstraße 8 nach der Korrekturrechnung von Vogel? | grün | grün | grün | grün |
| Wie viele Wochen Standzeit sind im Rahmenvertrag mit dem Gerüstbauer im Grundpreis enthalten? | grün | grün | rot | rot |
| Mit welcher Frist kann der Rahmenvertrag Gerüstbau gekündigt werden? | grün | grün | rot | rot |
| Wann ist der Betriebsurlaub 2025? | grün | rot | rot | rot |
| Wie oft wird Tiefengrund bei stark saugendem Untergrund aufgetragen? | grün | grün | rot | rot |
| Was steht im Kaufvertrag für den Bagger? | grün | grün | grün | grün |
| Wie hoch war die Rechnung des Dachdeckers? | grün | grün | grün | grün |
| Was kostet die Alarmanlage laut Angebot der Sicherheitsfirma? | grün | grün | grün | grün |
| Wie hoch war die Farben-Meister-Rechnung vom 14. August? | – | grün | grün | grün |
| Welchen Betrag hat die Rechnung an die Kita Regenbogen für den Turnraum? | – | grün | grün | grün |
| Wie hoch war die Telefonrechnung für Oktober 2025? | – | grün | grün | grün |
| Wie viel haben wir 2025 insgesamt an Farben Meister gezahlt? | – | rot | rot | rot |
| Wie viel haben wir der WEG Ahornstraße 3-5 im Jahr 2025 insgesamt in Rechnung gestellt? | – | grün | grün | grün |
| Welche Rechnungsnummer mahnt Farben Meister in der Zahlungserinnerung an? | – | grün | grün | grün |
| Welcher Restbetrag ist auf der Schlussrechnung an die WEG Ahornstraße 3-5 noch zu zahlen? | – | grün | grün | grün |
| Was kostet die Photovoltaikanlage laut Angebot des Elektrikers? | – | grün | grün | grün |


## Nachtrag: der Bestätigungslauf vom 24.09., 12:45–13:51 (ruhige Maschine)

Zwei Stufen in einem Lauf, Endkonfiguration (`gemma4:12b-it-q4_K_M` · `qwen3-embedding:0.6b` · Reranker k=20 ·
`top_n` 5 · `kontext` 16384), loadavg 2–3, Netzteil.

**Stufe 25** (bytegleich der Demo-Stapel): Profil 16,9 s · Einordnen 330 s = 13,2 s/Datei · 12 Fragen in 93 s ·
Status 15 sicher / 4 Konflikt / 3 OCR unsicher / 2 Duplikat / 1 unklar · **Status zu 100 % richtig** ·
Belege 2/64 · Konflikte 2/2 · Fragen 11/12. Der 30-Seiten-Rahmenvertrag ist hier erstmals „sicher".
Kategorie-Treffer 33 % — der Profilvorschlag weicht bei fünf Stichproben-Dateien von den Sollkategorien ab
(er bildet Themen wie „Baumarkt & Material" statt Dokumentarten und lässt „Ausgangsrechnungen" aus).

**Stufe 200**: Einordnen 3.247 s = **16,2 s/Datei** · Lauf gesamt 59 min · 20 Fragen in 213 s = 10,6 s/Frage ·
Kategorie 89,4 % · Status 98,5 % · Belege 11/640 · Konflikte 8/8 · **Fragen 18/20** · Speicher 8,4 GB.

### Der Lauf belegt die Messregel

Dieselbe Konfiguration lief in der Nacht unter Fremdlast (Videorender, loadavg bis 40) und jetzt ruhig:

| | nachts | ruhig |
|---|---|---|
| Einordnen je Datei | 19,8 s | 16,2 s |
| Lauf gesamt | 75 min | 59 min |
| Kategorie · Status · Belege · Konflikte · Fragen | 89,4 % · 98,5 % · 11/640 · 8/8 · 18/20 | **identisch** |

Jede Qualitätszahl gleich, nur die Zeiten unterscheiden sich. Fremdlast macht langsamer, nicht ungenauer —
Zeiten gehören auf eine leere Maschine, Qualitätszahlen überstehen auch eine volle.

### Vorgeschichte dieses Laufs

Ein erster Versuch um 12:14 brach mit `HTTP 500` ab: Die Modelle liegen auf einer externen SSD, die zu dem
Zeitpunkt nur USB 2.0 aushandelte (`Device Speed 2`, 38 MB/s). Das Laden der 6,9-GB-Modelldatei überschritt
Ollamas Ladegrenze von 5 Minuten. Nach dem Umstecken: `Device Speed 4`, 982 MB/s, Modell geladen und
geantwortet in 17 Sekunden. Die Ursache des schlechten Links blieb unbestimmt.
