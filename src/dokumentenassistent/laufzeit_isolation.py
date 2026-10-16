"""Isolationstest v2: Prompt-Einlesen (Prefill) und Generieren je Laufzeit getrennt messen (09.10.2026).

Ersetzt die Aussagekraft von `laufzeit_vergleich.py` (06.10.), das zwei Fehler hatte: jede Wiederholung
schickte denselben Prompt (die Laufzeit cachte ihn, „1,5 s für 10 000 Wörter“ war der Cache), und in
LM Studio dachte qwen3.5 mit. Hier:
- jede Wiederholung bekommt einen anderen Textausschnitt (kein Prompt-Cache),
- gemessen werden die Zeiten, die der Server selbst meldet: Ollama `prompt_eval_duration`/`eval_duration`,
  LM Studio `stats.time_to_first_token`/`tokens_per_second` (REST v0). Die Zeit bis zum ersten Token
  zählt als Einlesezeit — auch wenn ein Modell danach denkt, bleibt der Prefill vergleichbar,
- direkt an der Schnittstelle, nicht über den Produkt-Adapter.
Prompts aus öffentlichen GermanQuAD-Absätzen, nie aus dem privaten Bestand.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time
import urllib.request
from dokumentenassistent.pfade_privat import GERMANQUAD, LAEUFE

SCHEMA = {"type": "object", "properties": {"thema": {"type": "string"}, "jahr": {"type": "string"}},
          "required": ["thema", "jahr"]}
AUFTRAG = "Nenne in einem Satz das Thema der folgenden Absätze und eine darin genannte Jahreszahl.\n\n"
LAENGEN = {"kurz": 150, "lang": 7000}


def woerter(bestand: Path) -> list[str]:
    texte = [p.read_text(encoding="utf-8") for p in sorted(bestand.glob("*.txt")) if not p.name.startswith("._")]
    return " ".join(texte).split()


def prompt(alle: list[str], laenge: int, wiederholung: int, art: str) -> str:
    """Jede (Länge, Wiederholung, Art) bekommt einen eigenen Ausschnitt — kein Prompt teilt einen Anfang."""
    schluessel = list(LAENGEN.values()).index(laenge) * 8 + wiederholung * 2 + (art == "json")
    start = (schluessel * 7300) % max(1, len(alle) - laenge)
    return AUFTRAG + " ".join(alle[start:start + laenge])


def _post(url: str, daten: dict, timeout: int = 900) -> dict:
    req = urllib.request.Request(url, data=json.dumps(daten).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ollama(host: str, modell: str, text: str, schema: dict | None) -> dict:
    t = time.monotonic()
    a = _post(f"{host}/api/generate", {"model": modell, "prompt": text, "stream": False, "think": False,
                                       "format": schema, "options": {"temperature": 0, "num_ctx": 32768,
                                                                     "num_predict": 256}})
    pe, ed = a.get("prompt_eval_duration", 0) / 1e9, a.get("eval_duration", 0) / 1e9
    return {"prompt_tokens": a.get("prompt_eval_count"), "prefill_s": round(pe, 2),
            "prefill_tps": round(a.get("prompt_eval_count", 0) / pe, 1) if pe else None,
            "gen_tokens": a.get("eval_count"), "gen_tps": round(a.get("eval_count", 0) / ed, 1) if ed else None,
            "gesamt_s": round(time.monotonic() - t, 2), "antwort": a.get("response", "")}


def lmstudio(host: str, modell: str, text: str, schema: dict | None) -> dict:
    t = time.monotonic()
    daten = {"model": modell, "messages": [{"role": "user", "content": text}], "temperature": 0,
             "max_tokens": 256, "stream": False}
    if schema is not None:
        daten["response_format"] = {"type": "json_schema", "json_schema": {"name": "a", "strict": True, "schema": schema}}
    a = _post(f"{host}/api/v0/chat/completions", daten)
    s, u = a.get("stats", {}), a.get("usage", {})
    ttft = s.get("time_to_first_token")
    return {"prompt_tokens": u.get("prompt_tokens"), "prefill_s": round(ttft, 2) if ttft else None,
            "prefill_tps": round(u.get("prompt_tokens", 0) / ttft, 1) if ttft else None,
            "gen_tokens": u.get("completion_tokens"), "gen_tps": s.get("tokens_per_second"),
            "gesamt_s": round(time.monotonic() - t, 2),
            "antwort": (a.get("choices") or [{}])[0].get("message", {}).get("content") or ""}


def json_gueltig(antwort: str) -> bool:
    try:
        return isinstance(json.loads(antwort), dict)
    except (json.JSONDecodeError, TypeError):
        return False


def miss(aufruf, alle: list[str], wiederholungen: int) -> dict:
    aufruf(prompt(alle, LAENGEN["kurz"], 99, "text"), None)  # Aufwärmen: Modell laden, eigener Ausschnitt
    raus = {}
    for name, laenge in LAENGEN.items():
        for art in ("text", "json"):
            werte = []
            for w in range(wiederholungen):
                try:
                    r = aufruf(prompt(alle, laenge, w, art), SCHEMA if art == "json" else None)
                    r["json_ok"] = json_gueltig(r.pop("antwort")) if art == "json" else None
                    werte.append(r)
                except Exception as fehler:  # ein Fehler je Aufruf ist ein Befund, kein Abbruch
                    werte.append({"fehler": f"{type(fehler).__name__}: {str(fehler)[:120]}"})
            ok = [x for x in werte if "fehler" not in x]
            def med(k):
                v = [x[k] for x in ok if x.get(k) is not None]
                return round(statistics.median(v), 2) if v else None
            raus[f"{name}_{art}"] = {"n_ok": len(ok), "fehler": [x["fehler"] for x in werte if "fehler" in x],
                                     **{k: med(k) for k in ("prompt_tokens", "prefill_s", "prefill_tps",
                                                             "gen_tokens", "gen_tps", "gesamt_s")},
                                     **({"json_ok": sum(bool(x.get("json_ok")) for x in ok)} if art == "json" else {})}
    return raus


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--ollama", nargs="*", default=[], help="Ollama-Modelle, nacheinander, je danach entladen")
    a.add_argument("--lmstudio", nargs="*", default=[], help="in LM Studio bereits geladene Modell-IDs")
    a.add_argument("--bestand", type=Path, default=GERMANQUAD / "bestand")
    a.add_argument("--wiederholungen", type=int, default=3)
    a.add_argument("--ausgabe", type=Path, default=LAEUFE / "laufzeit-isolation-v2.json")
    args = a.parse_args()
    alle = woerter(args.bestand)
    bericht = json.loads(args.ausgabe.read_text()) if args.ausgabe.exists() else {}
    ziele = [("ollama", m) for m in args.ollama] + [("lmstudio", m) for m in args.lmstudio]
    for laufzeit, modell in ziele:
        host = "http://localhost:11434" if laufzeit == "ollama" else "http://localhost:1234"
        fn = ollama if laufzeit == "ollama" else lmstudio
        bericht[f"{laufzeit}:{modell}"] = miss(lambda t, s: fn(host, modell, t, s), alle, args.wiederholungen)
        args.ausgabe.write_text(json.dumps(bericht, indent=1))
        print(laufzeit, modell, json.dumps({k: (v["prefill_tps"], v["gen_tps"]) for k, v in bericht[f"{laufzeit}:{modell}"].items()}), flush=True)
        if laufzeit == "ollama":  # entladen, damit das nächste Modell allein im Speicher misst
            _post(f"{host}/api/generate", {"model": modell, "keep_alive": 0})


if __name__ == "__main__":
    main()
