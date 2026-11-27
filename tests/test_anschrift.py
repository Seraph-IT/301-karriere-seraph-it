"""Ort und Firmenangaben wie im Impressum von seraph-it.de (Am Frankenturm 5, 50667 Koeln).

Anlass 27.11.2026: Die Karriereseite nannte Seraph IT "IT-Managed-Service-Provider aus Duesseldorf"
und als Arbeitsort "Duesseldorf / Remote". Ein Buero in Duesseldorf gibt es nicht. Georgij hat am
selben Tag angeordnet, dass Name und Anschrift ueberall so stehen wie im Impressum.
"""

from __future__ import annotations

import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUELLEN = ["hugo.toml", "content", "layouts", "archetypes"]


def _dateien():
    for q in QUELLEN:
        p = ROOT / q
        if p.is_file():
            yield p
        elif p.is_dir():
            yield from (f for f in p.rglob("*") if f.is_file() and f.suffix in {".md", ".html", ".toml"})


def test_kein_duesseldorf_als_firmenort():
    treffer = []
    for f in _dateien():
        for nr, zeile in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "düsseldorf" in zeile.lower() or "duesseldorf" in zeile.lower():
                treffer.append(f"{f.relative_to(ROOT)}:{nr}")
    assert treffer == []


def test_ort_und_firma_wie_im_impressum():
    params = tomllib.loads((ROOT / "hugo.toml").read_text(encoding="utf-8"))["params"]
    assert params["company"] == "Seraph IT GmbH"
    assert params["location"].startswith("Köln")
    assert "Köln" in params["description"]
