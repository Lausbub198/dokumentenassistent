# Belastungstest

## qwen3.5:9b

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 10 | 93.5 | 9.3 | 40 | 20 | 100 | 0/24 | 1/1 | 7/8 | 3.7 |
| 25 | 25 | 251.8 | 10.1 | 52 | 12 | 77 | 3/58 | 2/2 | 12/12 | 5.7 |
| 50 | 50 | 534.8 | 10.7 | 44 | 24 | 86 | 7/129 | 4/4 | 8/12 | 5.7 |
| 100 | 100 | 1198.6 | 12.0 | 58 | 22 | 84 | 10/291 | 4/4 | 8/12 | 5.6 |
| 200 | 200 | 2614.9 | 13.1 | 64 | 19 | 83 | 17/621 | 8/8 | 14/20 | 6.9 |

## qwen3:4b

| Stufe | Dateien | Einordnen s | s/Datei | sicher % | unklar % | Kategorie-Treffer % | Belege ungültig | Konflikte ist/soll | Fragen-Treffer | Fragen-Dauer Ø s |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 10 | 58.2 | 5.8 | 40 | 20 | 75 | 6/32 | 1/1 | 4/8 | 14.1 |
| 25 | 25 | 145.8 | 5.8 | 32 | 32 | 38 | 16/73 | 2/2 | 5/12 | 17.6 |

## Wo es bricht

| Frage | qwen3.5:9b @10 | qwen3.5:9b @25 | qwen3.5:9b @50 | qwen3.5:9b @100 | qwen3.5:9b @200 | qwen3:4b @10 | qwen3:4b @25 |
|---|---|---|---|---|---|---|---|
| Wie hoch war die Telefonrechnung für März 2025? | grün | grün | grün | grün | grün | grün | grün |
| Welchen Betrag hat die Rechnung an die Kita Sonnenschein? | grün | grün | grün | grün | grün | grün | grün |
| Was hat das Rollgerüst für die Bahnhofstraße 3 gekostet? | grün | grün | grün | grün | grün | grün | grün |
| Was kostet die Fassadenfarbe für die Ringstraße 8 laut korrigierter Rechnung von Farben Meister? | grün | grün | grün | grün | grün | grün | grün |
| Wann ist der Betriebsurlaub 2025? | rot | grün | rot | rot | rot | rot | rot |
| Was steht im Kaufvertrag für den Bagger? | grün | grün | grün | grün | grün | rot | rot |
| Wie hoch war die Rechnung des Dachdeckers? | grün | grün | grün | grün | grün | rot | rot |
| Was kostet die Alarmanlage laut Angebot der Sicherheitsfirma? | grün | grün | grün | grün | grün | rot | rot |
| Welcher Betrag gilt für das Gerüst Ringstraße 8 nach der Korrekturrechnung von Vogel? | – | grün | grün | grün | grün | – | grün |
| Wie viele Wochen Standzeit sind im Rahmenvertrag mit dem Gerüstbauer im Grundpreis enthalten? | – | grün | rot | rot | rot | – | rot |
| Mit welcher Frist kann der Rahmenvertrag Gerüstbau gekündigt werden? | – | grün | rot | rot | rot | – | rot |
| Wie oft wird Tiefengrund bei stark saugendem Untergrund aufgetragen? | – | grün | rot | rot | rot | – | rot |
| Wie hoch war die Farben-Meister-Rechnung vom 14. August? | – | – | – | – | rot | – | – |
| Welchen Betrag hat die Rechnung an die Kita Regenbogen für den Turnraum? | – | – | – | – | grün | – | – |
| Wie hoch war die Telefonrechnung für Oktober 2025? | – | – | – | – | grün | – | – |
| Wie viel haben wir 2025 insgesamt an Farben Meister gezahlt? | – | – | – | – | rot | – | – |
| Wie viel haben wir der WEG Ahornstraße 3-5 im Jahr 2025 insgesamt in Rechnung gestellt? | – | – | – | – | grün | – | – |
| Welche Rechnungsnummer mahnt Farben Meister in der Zahlungserinnerung an? | – | – | – | – | grün | – | – |
| Welcher Restbetrag ist auf der Schlussrechnung an die WEG Ahornstraße 3-5 noch zu zahlen? | – | – | – | – | grün | – | – |
| Was kostet die Photovoltaikanlage laut Angebot des Elektrikers? | – | – | – | – | grün | – | – |

## Befunde (Auswertung 19.09., 23:00)

Lauf auf leerer Maschine, Netzteil, `caffeinate`; `qwen3.5:9b` über alle fünf Stufen, `qwen3:4b` bis 25 (Abbruch auf Wunsch). Drei Vorläufe vom Nachmittag liegen als `laeufe_abgebrochen_*.jsonl` daneben (Profil-Prompt-Fehler, siehe Commit `fix(profil)`).

1. **Zeit ist linear.** 9–13 s je Datei Einordnung mit 9B, 6 s mit 4B. 200 Dateien = 44 min. Kein Einbruch, kein Speicherproblem (5,5 GB VRAM konstant, Kontext 4096).
2. **Qualität fällt zwischen 25 und 50 auf ein Plateau und bleibt dort bis 200.** Status-Treffer 81–83 %, Kategorie 83–86 %, verworfene Belege konstant < 3 %, alle 8 Konflikte gefunden, Suche 5–7 s auch bei 694 Absätzen. Verwechslungsproben (20 Farben-Meister-Rechnungen, Teil-/Schlussrechnung, Mahnung) alle richtig.
3. **Es bricht an der Dokumentart, nicht an der Menge.** Die 38 „unklar" bei 200 sind fast vollständig: Verträge, Notizen, Wiki, Bescheide, Aufmaße — alles ohne Rechnungsfelder. Der 30-Seiten-Rahmenvertrag war bei Stufe 25 freigegeben (Modell ließ Betrag weg) und ab 50 unklar (Modell behauptete einen Betrag, Zitatprüfung verwarf ihn). Kein Kontextfenster-Problem, sondern: vier Rechnungsfelder passen nicht auf einen Vertrag. Folge: unklar → nie freigegeben → für die Suche unsichtbar, bis ein Mensch klickt. Designvorschlag: Felder je Dokumenttyp.
4. **4B erfindet mit echtem Beleg.** Bei allen drei Fangfragen („Bagger", „Dachdecker", „Alarmanlage") antwortet `qwen3:4b` „gefunden" und zitiert eine existierende, aber unpassende Fundstelle. 9B sagt fünfmal sauber „nicht gefunden". Dazu 6/32 bzw. 16/73 verworfene Belege (9B: 0/24, 3/58) und Kategorie 75 → 38 %. Die Zitatprüfung prüft Existenz, nicht Passung — beim kleinen Modell ist sie Dauerbetrieb statt Sicherheitsnetz. Abhilfe teilweise: Allerweltswörter (Rechnung, Angebot, Betrag) nicht als BM25-Signal zählen, dann erreicht die Fangfrage das Modell gar nicht.
5. **Offen:** Frage „Farben-Meister-Rechnung vom 14. August" bei 200 nicht gefunden (Datum als Suchbegriff trägt nicht); 4B braucht je Frage 14–18 s statt 6 (Ursache ungeprüft); Notiz/Wiki werden vom Modell als „unbekannt" verworfen, obwohl Kategorie „Interne Unterlagen" existiert.

**Minimum-Aussage für das Skript:** 16 GB und 4B: läuft, aber jeder vierte Beleg hält nicht und Fangfragen werden beantwortet. 24 GB und 9B: 8 von 10 Dokumenten richtig, Belege zu 97 % haltbar, Fangfragen verweigert, 13 s je Dokument.

## Nachtrag 20.09., 00:08 bis 00:53: GGUF gegen MLX (Stufe 25, leere Maschine, Netzteil)

| Stufe 25 | qwen3.5:9b (GGUF, llama.cpp/Metal) | qwen3.5:9b-mlx (8,9 GB Tag) |
|---|---|---|
| Einordnen | 326 s | 1.207 s |
| Profil | 20 s | 32 s |
| Fragen (12) | 92 s | 84 s |
| Speicher (ollama ps) | 5,5 GB | 14 GB |
| Status-Treffer | 92 % | 84 % |
| Belege verworfen | 3/58 | 6/58 |
| Fragen-Treffer | 12/12 | 9/12 |

MLX-Tag ist keine 4-Bit-Variante (14 GB im Speicher). JSON-Aufrufe mit Schema fast 4x langsamer, freie Textantworten gleichauf. Ein Lauf, eine Stufe: ob der MLX-Engine bei format-Schema leidet oder die Quantisierung schlicht zu gross ist, nicht getrennt. Entscheidung: GGUF bleibt, modelle.yaml unveraendert.
