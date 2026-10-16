# OCR-Vergleich 2026-09-23

Seitenmessungen: 731 | Engines: tesseract, vision, vision_korrektur, tesseract_vorverarbeitet, paddleocr, easyocr
Ausgewertet werden die **96 Seiten, die jede Engine gemessen hat** (Schnittmenge) — sonst staenden Mediane ueber verschiedene Seitenmengen nebeneinander.

## Messbedingungen

| Beginn | Modus | Engines | Seiten geplant | dpi | Seed | min. Zeichen |
|---|---|---|---|---|---|---|
| 2026-09-23T19:39:35 | wahrheit | tesseract_vorverarbeitet, paddleocr, easyocr | 150 | 300 | 42 | 200 |

* Uebernommen aus `beweise/ocr-reihenfolge/2026-09-23/laeufe.jsonl`: 432 Seitenzeile(n) fuer tesseract, vision, vision_korrektur — nicht neu gemessen, damit die Stichprobe dieselbe bleibt.

## Kennzahlen je Engine

| Engine | Seiten | CER Median | CER P90 | WER Median | Zahlentreue | Datumstreue | Zahlen erfunden | OCR s/Seite | Render s/Seite |
|---|---|---|---|---|---|---|---|---|---|
| tesseract | 96 | 0.0664 | 0.6777 | 0.1146 | 84.3 % (1690/2004) | 95.7 % (133/139) | 140 | 0.98 | 0.46 |
| vision | 96 | 0.1166 | 0.6762 | 0.1507 | 91.4 % (1831/2004) | 97.8 % (136/139) | 148 | 0.22 | 0.46 |
| vision_korrektur | 96 | 0.1133 | 0.6762 | 0.1504 | 91.0 % (1823/2004) | 97.8 % (136/139) | 142 | 0.35 | 0.46 |
| tesseract_vorverarbeitet | 96 | 0.0558 | 0.6758 | 0.1056 | 82.6 % (1656/2004) | 97.1 % (135/139) | 168 | 1.51 | 1.25 |
| paddleocr | 96 | 0.0513 | 0.7119 | 0.0886 | 94.7 % (1897/2004) | 97.8 % (136/139) | 222 | 31.12 | 1.25 |
| easyocr | 96 | 0.0722 | 0.7100 | 0.1427 | 84.6 % (1695/2004) | 89.9 % (125/139) | 413 | 11.86 | 1.25 |

## Reihenfolge-unabhaengige Kennzahlen (Leitkennzahl)

F1 ueber Wort- und Zeichen-Trigramm-Multimengen — Median ueber die Seiten. Anders als
CER/WER zaehlen sie eine abweichende Lesereihenfolge nicht als Fehler. CER steht zum
Vergleich daneben, ist hier aber Nebenkennzahl (siehe Modul-Docstring).

### Alle Seiten

| Engine | Seiten | F1 Wort | F1 Trigramm | CER Median | Zahlentreue | Zahlen erfunden | OCR s/Seite |
|---|---|---|---|---|---|---|---|
| tesseract | 96 | 0.9642 | 0.9803 | 0.0664 | 84.3 % (1690/2004) | 140 | 0.98 |
| vision | 96 | 0.9647 | 0.9786 | 0.1166 | 91.4 % (1831/2004) | 148 | 0.22 |
| vision_korrektur | 96 | 0.9718 | 0.9791 | 0.1133 | 91.0 % (1823/2004) | 142 | 0.35 |
| tesseract_vorverarbeitet | 96 | 0.9600 | 0.9784 | 0.0558 | 82.6 % (1656/2004) | 168 | 1.51 |
| paddleocr | 96 | 0.9808 | 0.9831 | 0.0513 | 94.7 % (1897/2004) | 222 | 31.12 |
| easyocr | 96 | 0.9087 | 0.9615 | 0.0722 | 84.6 % (1695/2004) | 413 | 11.86 |

### Tragfaehige Teilmenge (alle Engines CER <= 0,3)

| Engine | Seiten | F1 Wort | F1 Trigramm | CER Median | Zahlentreue | Zahlen erfunden | OCR s/Seite |
|---|---|---|---|---|---|---|---|
| tesseract | 58 | 0.9747 | 0.9877 | 0.0144 | 91.8 % (961/1047) | 58 | 1.29 |
| vision | 58 | 0.9776 | 0.9881 | 0.0161 | 91.2 % (955/1047) | 29 | 0.27 |
| vision_korrektur | 58 | 0.9774 | 0.9876 | 0.0161 | 90.7 % (950/1047) | 28 | 0.41 |
| tesseract_vorverarbeitet | 58 | 0.9739 | 0.9872 | 0.0166 | 91.9 % (962/1047) | 51 | 1.78 |
| paddleocr | 58 | 0.9823 | 0.9920 | 0.0123 | 93.8 % (982/1047) | 39 | 33.58 |
| easyocr | 58 | 0.9192 | 0.9654 | 0.0222 | 86.1 % (901/1047) | 147 | 11.89 |


## Paarweise je Seite gegen `tesseract`

Alle Engines lesen dieselben Seiten, also wird auch je Seite verglichen. Delta ist
immer als Gewinn der neuen Engine orientiert (bei CER/WER umgedreht, dort ist
weniger besser). Median gegen Median steht in der Tabelle darueber.

| Engine | Kennzahl | Seiten | Δ Median | Δ Mittel | besser | gleich | schlechter |
|---|---|---|---|---|---|---|---|
| vision | wort_f1 | 96 | 0.0046 | 0.0200 | 65 | 1 | 30 |
| vision | ngramm_f1 | 96 | 0.0010 | 0.0165 | 53 | 1 | 42 |
| vision | cer | 96 | -0.0000 | -0.0210 | 47 | 2 | 47 |
| vision_korrektur | wort_f1 | 96 | 0.0081 | 0.0230 | 68 | 1 | 27 |
| vision_korrektur | ngramm_f1 | 96 | 0.0010 | 0.0179 | 61 | 1 | 34 |
| vision_korrektur | cer | 96 | -0.0000 | -0.0208 | 46 | 4 | 46 |
| tesseract_vorverarbeitet | wort_f1 | 96 | -0.0013 | -0.0060 | 25 | 20 | 51 |
| tesseract_vorverarbeitet | ngramm_f1 | 96 | -0.0004 | -0.0037 | 36 | 8 | 52 |
| tesseract_vorverarbeitet | cer | 96 | -0.0003 | 0.0022 | 32 | 13 | 51 |
| paddleocr | wort_f1 | 96 | 0.0120 | 0.0382 | 81 | 1 | 14 |
| paddleocr | ngramm_f1 | 96 | 0.0043 | 0.0271 | 82 | 0 | 14 |
| paddleocr | cer | 96 | 0.0019 | 0.0220 | 63 | 3 | 30 |
| easyocr | wort_f1 | 96 | -0.0453 | -0.0321 | 16 | 1 | 79 |
| easyocr | ngramm_f1 | 96 | -0.0194 | -0.0025 | 20 | 0 | 76 |
| easyocr | cer | 96 | -0.0074 | 0.0178 | 26 | 1 | 69 |


## Wo es bricht

Die 10 Seiten mit der hoechsten CER je Engine (kein Textinhalt).

### tesseract

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-024.pdf | 4 | 0.9179 | 1.0267 | 7 | 6 |
| datei-047.pdf | 1 | 0.8836 | 1.2500 | 0 | 12 |
| datei-023.pdf | 7 | 0.8669 | 1.0149 | 5 | 2 |
| datei-001.pdf | 23 | 0.8299 | 1.3378 | 6 | 11 |
| datei-006.pdf | 5 | 0.8138 | 0.9667 | 81 | 12 |
| datei-044.pdf | 1 | 0.7651 | 0.7642 | 1 | 1 |
| datei-021.pdf | 43 | 0.7613 | 0.9010 | 38 | 2 |
| datei-045.pdf | 1 | 0.7347 | 0.7642 | 4 | 1 |
| datei-023.pdf | 2 | 0.7270 | 0.9114 | 6 | 1 |
| datei-008.pdf | 33 | 0.6777 | 0.8657 | 0 | 1 |

### vision

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-001.pdf | 23 | 1.0357 | 1.5676 | 1 | 35 |
| datei-006.pdf | 5 | 0.9780 | 0.9733 | 12 | 6 |
| datei-047.pdf | 1 | 0.9229 | 1.2333 | 0 | 12 |
| datei-006.pdf | 1 | 0.8360 | 0.8618 | 3 | 8 |
| datei-023.pdf | 2 | 0.7821 | 0.9430 | 0 | 0 |
| datei-024.pdf | 4 | 0.7673 | 1.0214 | 3 | 15 |
| datei-021.pdf | 43 | 0.7651 | 0.9538 | 31 | 32 |
| datei-023.pdf | 7 | 0.7077 | 0.8856 | 6 | 0 |
| datei-053.pdf | 1 | 0.6768 | 0.6862 | 0 | 0 |
| datei-054.pdf | 1 | 0.6762 | 0.6862 | 0 | 0 |

### vision_korrektur

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-001.pdf | 23 | 0.9949 | 1.5676 | 1 | 34 |
| datei-006.pdf | 5 | 0.9795 | 0.9800 | 14 | 6 |
| datei-047.pdf | 1 | 0.9247 | 1.2500 | 0 | 12 |
| datei-006.pdf | 1 | 0.8374 | 0.8780 | 3 | 8 |
| datei-023.pdf | 2 | 0.7899 | 0.9684 | 0 | 0 |
| datei-024.pdf | 4 | 0.7795 | 1.0481 | 3 | 15 |
| datei-021.pdf | 43 | 0.7584 | 0.9439 | 32 | 32 |
| datei-023.pdf | 7 | 0.7083 | 0.8955 | 7 | 0 |
| datei-053.pdf | 1 | 0.6768 | 0.6778 | 0 | 0 |
| datei-054.pdf | 1 | 0.6762 | 0.6778 | 0 | 0 |

### tesseract_vorverarbeitet

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-023.pdf | 2 | 1.0354 | 0.9620 | 5 | 2 |
| datei-001.pdf | 23 | 1.0221 | 2.5946 | 6 | 20 |
| datei-023.pdf | 7 | 0.9692 | 1.0149 | 7 | 2 |
| datei-024.pdf | 4 | 0.8874 | 1.0214 | 7 | 6 |
| datei-048.pdf | 1 | 0.8212 | 0.9459 | 0 | 1 |
| datei-006.pdf | 5 | 0.8167 | 0.9667 | 82 | 13 |
| datei-021.pdf | 43 | 0.7770 | 0.9076 | 41 | 4 |
| datei-047.pdf | 1 | 0.7466 | 1.2667 | 2 | 9 |
| datei-045.pdf | 1 | 0.7334 | 0.7561 | 5 | 2 |
| datei-043.pdf | 2 | 0.6758 | 0.8116 | 2 | 2 |

### paddleocr

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-001.pdf | 23 | 1.3912 | 2.6081 | 4 | 82 |
| datei-021.pdf | 43 | 0.9249 | 0.9472 | 24 | 59 |
| datei-047.pdf | 1 | 0.8664 | 1.1500 | 0 | 12 |
| datei-024.pdf | 4 | 0.7626 | 0.9840 | 3 | 11 |
| datei-048.pdf | 1 | 0.7555 | 0.7027 | 0 | 1 |
| datei-023.pdf | 2 | 0.7506 | 0.9177 | 0 | 3 |
| datei-023.pdf | 7 | 0.7249 | 0.9403 | 1 | 0 |
| datei-053.pdf | 1 | 0.7127 | 0.7071 | 0 | 0 |
| datei-054.pdf | 1 | 0.7127 | 0.7071 | 0 | 0 |
| datei-055.pdf | 1 | 0.7119 | 0.7071 | 0 | 0 |

### easyocr

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-047.pdf | 1 | 0.8767 | 1.2333 | 0 | 12 |
| datei-001.pdf | 23 | 0.8435 | 2.4865 | 5 | 129 |
| datei-048.pdf | 1 | 0.7664 | 0.7838 | 0 | 1 |
| datei-021.pdf | 43 | 0.7613 | 0.9505 | 25 | 65 |
| datei-024.pdf | 4 | 0.7429 | 0.8984 | 7 | 4 |
| datei-023.pdf | 2 | 0.7388 | 0.9241 | 3 | 0 |
| datei-023.pdf | 7 | 0.7118 | 0.9055 | 7 | 0 |
| datei-053.pdf | 1 | 0.7105 | 0.7573 | 1 | 0 |
| datei-054.pdf | 1 | 0.7105 | 0.7573 | 1 | 0 |
| datei-051.pdf | 1 | 0.7100 | 0.7573 | 1 | 0 |

