# Belastungstest

## ministral-3:8b-instruct-2512-q4_K_M

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 25 | 242.5 | 9.7 | 36 | 28 | 11 | 10/67 | 2/2 | 7/12 | 5.1 |

## olmo-3:7b-instruct-q4_K_M

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 25 | 174.2 | 7.0 | 20 | 60 | 0 | 24/68 | 0/2 | 3/12 | 3.4 |

## qwen3.5:4b-q4_K_M

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 25 | 163.2 | 6.5 | 64 | 8 | 60 | 3/62 | 1/2 | 10/12 | 3.1 |
| 100 | 100 | 780.2 | 7.8 | 68 | 16 | 68 | 24/306 | 2/4 | 10/12 | 3.7 |
| 200 | 200 | 1566.1 | 7.8 | 66 | 22 | 73 | 39/641 | 3/8 | 16/20 | 4.1 |

## gemma4:12b-it-q4_K_M

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 25 | 321.2 | 12.8 | 56 | 8 | 29 | 3/63 | 2/2 | 10/12 | 8.4 |
| 100 | 100 | 1535.7 | 15.4 | 74 | 6 | 89 | 11/307 | 4/4 | 10/12 | 8.6 |
| 200 | 200 | 3215.4 | 16.1 | 80 | 4 | 90 | 12/638 | 8/8 | 16/20 | 9.8 |

## qwen3.5:9b

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 100 | 1173.9 | 11.7 | 58 | 22 | 84 | 10/291 | 4/4 | 8/12 | 5.5 |
| 200 | 200 | 2528.4 | 12.6 | 64 | 19 | 83 | 17/621 | 8/8 | 14/20 | 6.6 |

## gemma4:e4b

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 100 | 737.3 | 7.4 | 58 | 24 | 17 | 30/321 | 3/4 | 8/12 | 3.3 |
| 200 | 200 | 1569.6 | 7.8 | 62 | 22 | 11 | 49/677 | 6/8 | 13/20 | 4.7 |

## Wo es bricht

| Frage | gemma4:12b-it-q4_K_M @25 | gemma4:12b-it-q4_K_M @100 | gemma4:12b-it-q4_K_M @200 | gemma4:e4b @100 | gemma4:e4b @200 | ministral-3:8b-instruct-2512-q4_K_M @25 | olmo-3:7b-instruct-q4_K_M @25 | qwen3.5:4b-q4_K_M @25 | qwen3.5:4b-q4_K_M @100 | qwen3.5:4b-q4_K_M @200 | qwen3.5:9b @100 | qwen3.5:9b @200 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wie hoch war die Telefonrechnung für März 2025? | grün | grün | grün | grün | grün | grün | rot | grün | grün | grün | grün | grün |
| Welchen Betrag hat die Rechnung an die Kita Sonnenschein? | grün | grün | grün | grün | grün | grün | rot | grün | grün | grün | grün | grün |
| Was hat das Rollgerüst für die Bahnhofstraße 3 gekostet? | grün | grün | grün | grün | rot | rot | rot | grün | grün | grün | grün | grün |
| Was kostet die Fassadenfarbe für die Ringstraße 8 laut korrigierter Rechnung von Farben Meister? | grün | grün | grün | grün | grün | grün | rot | grün | grün | grün | grün | grün |
| Welcher Betrag gilt für das Gerüst Ringstraße 8 nach der Korrekturrechnung von Vogel? | grün | grün | grün | rot | grün | grün | rot | grün | grün | grün | grün | grün |
| Wie viele Wochen Standzeit sind im Rahmenvertrag mit dem Gerüstbauer im Grundpreis enthalten? | rot | rot | rot | rot | rot | rot | rot | rot | rot | grün | rot | rot |
| Mit welcher Frist kann der Rahmenvertrag Gerüstbau gekündigt werden? | rot | rot | rot | rot | rot | rot | rot | rot | rot | grün | rot | rot |
| Wann ist der Betriebsurlaub 2025? | grün | grün | grün | grün | rot | rot | rot | grün | grün | rot | rot | rot |
| Wie oft wird Tiefengrund bei stark saugendem Untergrund aufgetragen? | grün | grün | grün | rot | rot | rot | rot | grün | grün | rot | rot | rot |
| Was steht im Kaufvertrag für den Bagger? | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün |
| Wie hoch war die Rechnung des Dachdeckers? | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün |
| Was kostet die Alarmanlage laut Angebot der Sicherheitsfirma? | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün | grün |
| Wie hoch war die Farben-Meister-Rechnung vom 14. August? | – | – | rot | – | rot | – | – | – | – | rot | – | rot |
| Welchen Betrag hat die Rechnung an die Kita Regenbogen für den Turnraum? | – | – | grün | – | grün | – | – | – | – | grün | – | grün |
| Wie hoch war die Telefonrechnung für Oktober 2025? | – | – | grün | – | grün | – | – | – | – | grün | – | grün |
| Wie viel haben wir 2025 insgesamt an Farben Meister gezahlt? | – | – | rot | – | grün | – | – | – | – | rot | – | rot |
| Wie viel haben wir der WEG Ahornstraße 3-5 im Jahr 2025 insgesamt in Rechnung gestellt? | – | – | grün | – | grün | – | – | – | – | grün | – | grün |
| Welche Rechnungsnummer mahnt Farben Meister in der Zahlungserinnerung an? | – | – | grün | – | rot | – | – | – | – | grün | – | grün |
| Welcher Restbetrag ist auf der Schlussrechnung an die WEG Ahornstraße 3-5 noch zu zahlen? | – | – | grün | – | grün | – | – | – | – | grün | – | grün |
| Was kostet die Photovoltaikanlage laut Angebot des Elektrikers? | – | – | grün | – | grün | – | – | – | – | grün | – | grün |
