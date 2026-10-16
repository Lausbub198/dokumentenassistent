# OCR-Vergleich 2026-09-23

Seitenmessungen: 450 | Engines: tesseract, vision, vision_korrektur

## Kennzahlen je Engine

| Engine | Seiten | CER Median | CER P90 | WER Median | Zahlentreue | Datumstreue | Zahlen erfunden | OCR s/Seite | Render s/Seite |
|---|---|---|---|---|---|---|---|---|---|
| tesseract | 150 | 0.0599 | 0.6758 | 0.1080 | 83.6 % (2729/3265) | 96.1 % (196/204) | 230 | 1.07 | 0.47 |
| vision | 150 | 0.1013 | 0.6762 | 0.1438 | 91.7 % (2995/3265) | 97.1 % (198/204) | 196 | 0.23 | 0.47 |
| vision_korrektur | 150 | 0.0998 | 0.6762 | 0.1424 | 91.1 % (2976/3265) | 97.1 % (198/204) | 187 | 0.38 | 0.47 |

## Wo es bricht

Die 10 Seiten mit der hoechsten CER je Engine (kein Textinhalt).

### tesseract

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-023.pdf | 3 | 0.9453 | 0.9717 | 6 | 2 |
| datei-024.pdf | 4 | 0.9179 | 1.0267 | 7 | 6 |
| datei-023.pdf | 4 | 0.9003 | 1.0053 | 7 | 1 |
| datei-047.pdf | 1 | 0.8836 | 1.2500 | 0 | 12 |
| datei-023.pdf | 7 | 0.8669 | 1.0149 | 5 | 2 |
| datei-023.pdf | 7 | 0.8669 | 1.0149 | 5 | 2 |
| datei-001.pdf | 23 | 0.8299 | 1.3378 | 6 | 11 |
| datei-006.pdf | 5 | 0.8138 | 0.9667 | 81 | 12 |
| datei-006.pdf | 3 | 0.7869 | 0.9200 | 88 | 7 |
| datei-021.pdf | 66 | 0.7668 | 0.9574 | 17 | 5 |

### vision

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-001.pdf | 23 | 1.0357 | 1.5676 | 1 | 35 |
| datei-006.pdf | 5 | 0.9780 | 0.9733 | 12 | 6 |
| datei-047.pdf | 1 | 0.9229 | 1.2333 | 0 | 12 |
| datei-006.pdf | 3 | 0.9036 | 0.9067 | 7 | 6 |
| datei-006.pdf | 1 | 0.8360 | 0.8618 | 3 | 8 |
| datei-023.pdf | 2 | 0.7821 | 0.9430 | 0 | 0 |
| datei-024.pdf | 4 | 0.7673 | 1.0214 | 3 | 15 |
| datei-021.pdf | 43 | 0.7651 | 0.9538 | 31 | 32 |
| datei-023.pdf | 3 | 0.7490 | 0.9811 | 4 | 1 |
| datei-023.pdf | 4 | 0.7456 | 1.0000 | 3 | 10 |

### vision_korrektur

| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |
|---|---|---|---|---|---|
| datei-001.pdf | 23 | 0.9949 | 1.5676 | 1 | 34 |
| datei-006.pdf | 5 | 0.9795 | 0.9800 | 14 | 6 |
| datei-047.pdf | 1 | 0.9247 | 1.2500 | 0 | 12 |
| datei-006.pdf | 3 | 0.8949 | 0.9667 | 7 | 5 |
| datei-006.pdf | 1 | 0.8374 | 0.8780 | 3 | 8 |
| datei-023.pdf | 2 | 0.7899 | 0.9684 | 0 | 0 |
| datei-024.pdf | 4 | 0.7795 | 1.0481 | 3 | 15 |
| datei-023.pdf | 3 | 0.7585 | 0.9906 | 4 | 1 |
| datei-021.pdf | 43 | 0.7584 | 0.9439 | 32 | 32 |
| datei-023.pdf | 4 | 0.7537 | 1.0214 | 3 | 10 |


## Laufzeitprobe (PDFs ohne Textebene, keine Wahrheit)

| Engine | Seiten | OCR s/Seite Median | Seiten ohne Text | Zeichen Median |
|---|---|---|---|---|
| tesseract | 10 | 1.22 | 1 | 1782 |
| vision | 10 | 0.26 | 2 | 1790 |
| vision_korrektur | 10 | 0.42 | 2 | 1787 |
