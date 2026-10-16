"""Original-Dokument aus dem Werkzeug öffnen (10.10.2026).

Belegkarten und Detailansicht verlinken auf /dokument/<hash>; PDFs springen mit #page=N auf die
Fundstelle. Ausgeliefert wird nur, was im Index steht UND unterhalb des Quellordners liegt —
kein freier Pfad in der URL, damit über diese Route keine anderen Dateien lesbar sind.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()


def pfad_im_bestand(werkstatt, datei_hash: str) -> Path | None:
    datei = werkstatt.index.datei(datei_hash)
    if datei is None:
        return None
    pfad = Path(datei.pfad).resolve()
    quelle = Path(werkstatt.quelle).resolve()
    if not pfad.is_relative_to(quelle) or not pfad.is_file():
        return None
    return pfad


@router.get("/dokument/{datei_hash}")
def dokument(request: Request, datei_hash: str) -> FileResponse:
    werkstatt = request.app.state.werkstatt
    pfad = pfad_im_bestand(werkstatt, datei_hash) if werkstatt else None
    if pfad is None:
        raise HTTPException(status_code=404, detail="Dokument nicht im Bestand")
    art = mimetypes.guess_type(pfad.name)[0] or "application/octet-stream"
    return FileResponse(pfad, media_type=art, filename=pfad.name, content_disposition_type="inline")
