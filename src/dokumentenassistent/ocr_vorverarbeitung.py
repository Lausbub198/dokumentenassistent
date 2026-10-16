"""Bild-Vorverarbeitung vor der OCR — vier Stufen, jede einzeln abschaltbar, nur Pillow/numpy.

Warum ueberhaupt
----------------
`tesseract` bekommt heute das gerenderte Seitenbild unveraendert. Tesseract binarisiert
intern (Otsu) und findet Zeilen ueber waagerechte Projektionen; beides arbeitet schlechter,
wenn die Seite schief liegt oder der Kontrast flau ist. Ob das auf *diesem* Korpus etwas
bringt, ist eine Messfrage — deshalb steht die Vorverarbeitung als **eigene Engine**
(`tesseract_vorverarbeitet`) neben `tesseract` und wird gegen dieselbe Wahrheit gemessen.

Keine externen Programme: `unpaper` und `ocrmypdf` sind auf dieser Maschine nicht vorhanden
und sollen es auch nicht werden. Alles hier laeuft mit Pillow und numpy, die das Produkt
ohnehin mitbringt — die Vorverarbeitung kostet also keine zusaetzliche Abhaengigkeit.

Reihenfolge der Stufen, und warum genau diese
---------------------------------------------
1. **Graustufen** — Farbe traegt in Scans keine Leseinformation, und alle folgenden Stufen
   (Histogramm, Median, Projektionsprofil) sind auf einem Kanal definiert statt auf dreien.
2. **Kontrastnormalisierung** — vor der Entrauschung, weil ein flaues Bild (Graustufen 110
   bis 150 statt 0 bis 255) den Medianfilter schwache Striche wegmitteln laesst. Gespreizt
   wird per Perzentilschnitt (`autocontrast(cutoff=...)`), nicht auf Min/Max: ein einzelner
   schwarzer Staubpunkt wuerde sonst die ganze Spreizung bestimmen.
3. **Entrauschung** — leichter 3x3-Medianfilter. Median statt Weichzeichner, weil er
   Einzelpunkte (Scanstaub, JPEG-Rauschen) entfernt, ohne Kanten zu verwischen; Buchstaben
   leben von Kanten. 3x3 ist die kleinste sinnvolle Groesse — 5x5 frisst duenne Serifen.
4. **Entzerren (deskew)** — zuletzt, weil die Drehung interpoliert und damit neue
   Zwischenwerte erzeugt; eine Kontrastspreizung *nach* der Drehung wuerde diese
   Interpolationskanten mitverstaerken.

Die Neigung wird ueber das **waagerechte Projektionsprofil** geschaetzt: liegt die Seite
gerade, fallen die Textzeilen in wenige Zeilen mit viel Tinte und viele mit gar keiner —
die Varianz des Profils ist maximal. Der Winkel, der diese Varianz maximiert, ist die
Neigung. Das braucht keine Kantenerkennung und keine Hough-Transformation, also kein
OpenCV.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter, ImageOps

GRENZWINKEL = 5.0  # Scans liegen selten schiefer; mehr zu suchen kostet nur Zeit
GROB_SCHRITT = 1.0
FEIN_SCHRITT = 0.25
SCHAETZ_BREITE = 800  # Messbild fuer die Neigung; darueber wird nur langsamer, nicht genauer
MINDEST_WINKEL = 0.2  # darunter lohnt die Drehung nicht — Interpolation ohne Gegenwert
KONTRAST_SCHNITT = 2  # Prozent je Seite des Histogramms


def schaetze_neigung(bild: Image.Image) -> float:
    """Neigung in Grad, gleiches Vorzeichen wie `Image.rotate` (positiv = gegen den Uhrzeiger).

    Zwei Durchgaenge: erst 1°-Raster ueber ±`GRENZWINKEL`, dann 0,25° um den Sieger. Das
    Profilkriterium ist glatt genug, dass der grobe Durchgang das richtige Tal findet, und
    spart gegenueber einem vollen 0,25°-Raster gut die Haelfte der Drehungen.

    Gemessen wird auf einem auf `SCHAETZ_BREITE` verkleinerten Bild: die Zeilenlage einer
    Seite bleibt beim Verkleinern erhalten, die Rechenzeit nicht.
    """
    klein = _messbild(bild)
    grob = _bester_winkel(klein, np.arange(-GRENZWINKEL, GRENZWINKEL + GROB_SCHRITT, GROB_SCHRITT))
    fein = np.arange(grob - GROB_SCHRITT, grob + GROB_SCHRITT + FEIN_SCHRITT, FEIN_SCHRITT)
    return float(_bester_winkel(klein, fein))


def _messbild(bild: Image.Image) -> np.ndarray:
    """Verkleinertes Graustufenbild als Tintenmenge je Bildpunkt (0 = Papier)."""
    grau = bild.convert("L")
    if grau.width > SCHAETZ_BREITE:
        hoehe = max(1, round(grau.height * SCHAETZ_BREITE / grau.width))
        grau = grau.resize((SCHAETZ_BREITE, hoehe), Image.BILINEAR)
    werte = np.asarray(grau, dtype=np.float32)
    return np.maximum(werte.mean() - werte, 0.0)


def _bester_winkel(tinte: np.ndarray, winkel: np.ndarray) -> float:
    """Der Winkel aus `winkel`, bei dem das Zeilenprofil die groesste Varianz hat."""
    return float(max(winkel, key=lambda w: _profilvarianz(tinte, float(w))))


def _profilvarianz(tinte: np.ndarray, winkel: float) -> float:
    """Varianz der zeilenweisen Tintensumme, nachdem die Neigung `winkel` herausgedreht wurde.

    Die Drehung laeuft ueber Pillow (bikubisch, Rand mit 0 = kein Papier, keine Tinte), damit
    der leere Rand die Summe nicht faelscht.
    """
    if winkel:
        bild = Image.fromarray(tinte).rotate(-winkel, resample=Image.BICUBIC, fillcolor=0.0)
        tinte = np.asarray(bild, dtype=np.float32)
    return float(np.var(tinte.sum(axis=1)))


def vorverarbeite(
    bild: Image.Image,
    *,
    graustufen: bool = True,
    kontrast: bool = True,
    entrauschen: bool = True,
    entzerren: bool = True,
) -> Image.Image:
    """Aufbereitetes Bild fuer die OCR. Reine Funktion: die Eingabe bleibt unveraendert.

    Jede Stufe ist einzeln abschaltbar, damit im Zweifel gemessen statt geglaubt werden kann,
    welche Stufe den Unterschied macht. Sind alle vier aus, kommt das Bild unveraendert
    zurueck (als Kopie).
    """
    ergebnis = bild.copy()
    if graustufen:
        ergebnis = ergebnis.convert("L")
    if kontrast:
        ergebnis = ImageOps.autocontrast(ergebnis, cutoff=KONTRAST_SCHNITT)
    if entrauschen:
        ergebnis = ergebnis.filter(ImageFilter.MedianFilter(size=3))
    if entzerren:
        ergebnis = _entzerre(ergebnis)
    return ergebnis


def _entzerre(bild: Image.Image) -> Image.Image:
    """Dreht die geschaetzte Neigung heraus; unter `MINDEST_WINKEL` bleibt das Bild wie es ist.

    Der Rand wird mit Papierweiss gefuellt, nicht mit Schwarz — ein schwarzer Keil am Rand
    ist fuer jede OCR ein Stoerobjekt.
    """
    winkel = schaetze_neigung(bild)
    if abs(winkel) < MINDEST_WINKEL:
        return bild
    weiss = 255 if bild.mode == "L" else (255, 255, 255)
    return bild.rotate(-winkel, resample=Image.BICUBIC, fillcolor=weiss, expand=False)
