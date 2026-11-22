"""Tests fuer bin/karriere_feed.py (MKT-20). Ohne Netz: der Feed wird direkt uebergeben."""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("karriere_feed", Path(__file__).resolve().parents[1] / "bin" / "karriere_feed.py")
kf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kf)

SECRET = "feed-test-secret"


def signiert(jobs, secret=SECRET):
    """Wie recruiting_extension/recruiting/career_feed.sign in 420."""
    feed = {"version": 1, "generated_at": "2026-11-22T10:00:00", "jobs": jobs}
    body = json.dumps(feed, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    feed["signature"] = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return feed


JOB = {
    "slug": "soc-analyst-umschulung", "title": "SOC-Analyst (Umschulung)", "department": "SOC", "location": "Köln",
    "location_type": "Hybrid", "employment_type": "Vollzeit", "summary": "Kurz und knapp.",
    "description_html": "<p>Du arbeitest im SOC.</p><ul><li>Wazuh</li><li>Zeek</li></ul>",
    "published_at": "2026-11-20T08:00:00", "valid_until": "2027-01-31", "salary_range": "", "apply_url_path": "/career/x/apply",
}


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    monkeypatch.setenv("CAREER_FEED_HMAC_SECRET", SECRET)
    (tmp_path / "_index.md").write_text("---\ntitle: Jobs\n---\n", encoding="utf-8")
    return tmp_path


def test_probelauf_schreibt_nichts(ordner, capsys):
    assert kf.main([], feed=signiert([JOB]), ordner=ordner) == 0
    assert not (ordner / "soc-analyst-umschulung.md").exists()
    assert "neu" in capsys.readouterr().out


def test_schreiben_legt_datei_mit_front_matter_an(ordner):
    assert kf.main(["--schreiben"], feed=signiert([JOB]), ordner=ordner) == 0
    text = (ordner / "soc-analyst-umschulung.md").read_text(encoding="utf-8")
    assert text.startswith('---\ntitle: "SOC-Analyst (Umschulung)"\ndate: "2026-11-20"\nslug: "soc-analyst-umschulung"\n')
    assert 'location: "Köln"' in text and 'quelle: "erpnext-feed"' in text and 'expiryDate: "2027-01-31"' in text
    assert "Du arbeitest im SOC." in text and "- Wazuh" in text and "<p>" not in text
    # zweiter Lauf: nichts zu tun
    assert [a for a, _, _ in kf.plan(signiert([JOB]), ordner) if a != "gleich"] == []


def test_falsche_oder_fehlende_signatur_schreibt_nichts(ordner, monkeypatch):
    assert kf.main(["--schreiben"], feed=signiert([JOB], secret="anderes"), ordner=ordner) == 2
    feed = signiert([JOB])
    feed["jobs"][0]["title"] = "manipuliert"
    assert kf.main(["--schreiben"], feed=feed, ordner=ordner) == 2
    monkeypatch.setenv("CAREER_FEED_HMAC_SECRET", "")
    assert kf.main(["--schreiben"], feed=signiert([JOB]), ordner=ordner) == 2
    assert not (ordner / "soc-analyst-umschulung.md").exists()


def test_handgepflegte_datei_bleibt_und_abgelaufene_wird_entwurf(ordner):
    hand = ordner / "soc-analyst-umschulung.md"
    hand.write_text('---\ntitle: "Hand"\ndraft: false\n---\n', encoding="utf-8")
    alt = ordner / "alte-stelle.md"
    alt.write_text('---\ntitle: "Alt"\nquelle: "erpnext-feed"\ndraft: false\n---\n', encoding="utf-8")
    assert kf.main(["--schreiben"], feed=signiert([JOB]), ordner=ordner) == 0
    assert hand.read_text(encoding="utf-8").startswith('---\ntitle: "Hand"')
    assert "draft: true" in alt.read_text(encoding="utf-8")
    assert alt.exists(), "es wird nie geloescht"


def test_ungueltiger_slug_und_falsche_version(ordner):
    assert kf.main([], feed=signiert([{**JOB, "slug": "../boese"}]), ordner=ordner) == 2
    feed = signiert([JOB])
    feed["version"] = 2
    assert kf.main([], feed=feed, ordner=ordner) == 2


def test_nur_https():
    with pytest.raises(kf.FeedFehler):
        kf.holen("http://erp.test/feed")
