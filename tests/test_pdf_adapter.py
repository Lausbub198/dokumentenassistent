"""PDF native extraction is selectable and never silently falls back."""
import shutil
import subprocess

import pytest
from reportlab.pdfgen import canvas

from dokumentenassistent import auslesen
from dokumentenassistent.auslesen import NichtLesbar, OcrEinstellungen, lies_seiten
from tests.conftest import schreibe_text_pdf


def pdf_with_form(path):
    c = canvas.Canvas(str(path))
    c.drawString(50, 770, 'Formularwert:')
    c.acroForm.textfield(name='betrag', value='1250.99 EUR', x=160, y=760,
                         width=150, height=18, borderWidth=1)
    c.showPage()
    c.save()
    return path


@pytest.mark.skipif(not shutil.which('pdftotext'), reason='Poppler unavailable')
def test_pdftotext_reads_form_value_with_page_provenance(tmp_path):
    path = pdf_with_form(tmp_path/'form.pdf')
    old = lies_seiten(path)[0]
    new = lies_seiten(path, OcrEinstellungen(pdf_extraktion='pdftotext'))[0]
    assert '1250.99 EUR' not in old.text
    assert '1250.99 EUR' in new.text
    assert (new.nummer, new.per_ocr, new.extraktor) == (1, False, 'pdftotext')
    assert new.extraktor_version


@pytest.mark.skipif(not shutil.which('pdftotext'), reason='Poppler unavailable')
def test_pdftotext_retains_page_numbers_and_exact_numeric_signs(tmp_path):
    path = schreibe_text_pdf(tmp_path/'pages.pdf', ['Preis -12,50 EUR am 01.02.2026', 'Seite zwei +4,00 EUR'])
    pages = lies_seiten(path, OcrEinstellungen(pdf_extraktion='pdftotext'))
    assert [p.nummer for p in pages] == [1, 2]
    assert '-12,50 EUR' in pages[0].text
    assert '+4,00 EUR' in pages[1].text


def test_missing_selected_executable_is_explicit_error(tmp_path, monkeypatch):
    path = pdf_with_form(tmp_path/'form.pdf')
    monkeypatch.setattr(auslesen.shutil, 'which', lambda name: None if name=='pdftotext' else '/bin/x')
    with pytest.raises(NichtLesbar, match='pdftotext'):
        lies_seiten(path, OcrEinstellungen(pdf_extraktion='pdftotext'))


def test_selected_extractor_timeout_is_not_pypdf_fallback(tmp_path, monkeypatch):
    path = pdf_with_form(tmp_path/'form.pdf')
    monkeypatch.setattr(auslesen.shutil, 'which', lambda name: '/bin/pdftotext')
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)
    monkeypatch.setattr(auslesen.subprocess, 'run', timeout)
    with pytest.raises(NichtLesbar, match='Zeitlimit'):
        lies_seiten(path, OcrEinstellungen(pdf_extraktion='pdftotext'))


@pytest.mark.skipif(not shutil.which('pdftotext'), reason='Poppler unavailable')
def test_image_only_pdf_still_uses_ocr(bild_pdf):
    page = lies_seiten(bild_pdf, OcrEinstellungen(pdf_extraktion='pdftotext'))[0]
    assert page.per_ocr is True
    assert page.extraktor == 'ocr:tesseract'
    assert '2025-0815' in page.text


def test_poppler_text_page_does_not_require_pypdf_parser(tmp_path, monkeypatch):
    path = tmp_path/'hard.pdf'
    path.write_bytes(b'not parsed by pypdf')
    def fail_reader(*args):
        raise ValueError('synthetic pypdf parser failure')
    monkeypatch.setattr(auslesen, 'PdfReader', fail_reader)
    def poppler(args, **kwargs):
        if args[1] == '-v':
            return subprocess.CompletedProcess(args, 0, b'', b'pdftotext version 1')
        if args[0] == 'pdfinfo':
            return subprocess.CompletedProcess(args, 0, b'Pages: 1\n', b'')
        return subprocess.CompletedProcess(args, 0, b'Betrag 1250 EUR\n', b'')
    monkeypatch.setattr(auslesen.shutil, 'which', lambda name:'/bin/'+name)
    monkeypatch.setattr(auslesen.subprocess, 'run', poppler)
    page = lies_seiten(path, OcrEinstellungen(pdf_extraktion='pdftotext'))[0]
    assert page.text == 'Betrag 1250 EUR'


def test_layout_mode_is_explicit_and_passes_layout_flag(tmp_path, monkeypatch):
    path=pdf_with_form(tmp_path/'form.pdf')
    seen=[]
    real=auslesen.subprocess.run
    def track(args, **kwargs):
        seen.append(args)
        return real(args, **kwargs)
    monkeypatch.setattr(auslesen.subprocess, 'run', track)
    page=lies_seiten(path,OcrEinstellungen(pdf_extraktion='pdftotext_layout'))[0]
    assert '1250.99 EUR' in page.text
    assert any('-layout' in args for args in seen)


def test_multiple_pages_use_one_poppler_text_call(tmp_path, monkeypatch):
    path=schreibe_text_pdf(tmp_path/'pages.pdf',['Erste Seite','Zweite Seite'])
    seen=[]
    real=auslesen.subprocess.run
    def track(args,**kwargs):
        if args[0]=='pdftotext' and '-v' not in args:
            seen.append(args)
        return real(args,**kwargs)
    monkeypatch.setattr(auslesen.subprocess,'run',track)
    pages=lies_seiten(path,OcrEinstellungen(pdf_extraktion='pdftotext_layout'))
    assert [p.nummer for p in pages]==[1,2]
    assert len(seen)==1


def test_empty_version_response_is_explicit_error(tmp_path, monkeypatch):
    path=pdf_with_form(tmp_path/'form.pdf')
    monkeypatch.setattr(auslesen.shutil,'which',lambda name:'/bin/'+name)
    monkeypatch.setattr(auslesen.subprocess,'run',lambda args,**kw:subprocess.CompletedProcess(args,0,b'',b''))
    with pytest.raises(NichtLesbar,match='Versionsprüfung'):
        lies_seiten(path,OcrEinstellungen(pdf_extraktion='pdftotext'))
