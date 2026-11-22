#!/usr/bin/env python3
"""Stellen aus dem Karriere-Feed von ERPNext nach content/jobs/ (verbindungen.md MKT-20).

Gegenstelle zu recruiting_extension.api.career_feed.get_career_feed (Vertrag Version 1, ADR-recruiting-0034).
Der Feed ist signiert: HMAC-SHA256 ueber die kanonische JSON-Form von {version, generated_at, jobs}. Ohne
gueltige Signatur schreibt dieses Skript nichts.

    CAREER_FEED_URL=https://<erp>/api/method/recruiting_extension.api.career_feed.get_career_feed \
    CAREER_FEED_HMAC_SECRET=... python bin/karriere_feed.py            # Probelauf: zeigt nur, was sich aendern wuerde
    ... python bin/karriere_feed.py --schreiben                         # schreibt content/jobs/<slug>.md

Standard ist der Probelauf. Geloescht wird nie: Stellen, die nicht mehr im Feed stehen, setzt --schreiben auf
draft: true. Dateien ohne den Kopf "quelle: erpnext-feed" (von Hand gepflegt) bleiben unberuehrt.
Nur Standardbibliothek. Das Secret kommt aus Keeper (gleicher Wert wie recruiting_career_feed_hmac_secret).
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import json
import os
import re
import sys
import urllib.request
from collections.abc import Mapping
from pathlib import Path

FEED_VERSION = 1
MARKE = 'quelle: "erpnext-feed"'
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
JOBS = Path(__file__).resolve().parents[1] / "content" / "jobs"


class FeedFehler(Exception):
    pass


def canonical_bytes(feed: Mapping) -> bytes:
    body = {k: feed[k] for k in ("version", "generated_at", "jobs")}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def pruefen(feed: Mapping, secret: str) -> None:
    if not secret:
        raise FeedFehler("CAREER_FEED_HMAC_SECRET fehlt")
    if not isinstance(feed, Mapping) or feed.get("version") != FEED_VERSION:
        raise FeedFehler(f"Feed-Version {feed.get('version') if isinstance(feed, Mapping) else '?'} statt {FEED_VERSION}")
    if not all(k in feed for k in ("generated_at", "jobs")) or not isinstance(feed["jobs"], list):
        raise FeedFehler("Feed unvollstaendig")
    erwartet = "sha256=" + hmac.new(secret.encode("utf-8"), canonical_bytes(feed), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(erwartet, str(feed.get("signature") or "")):
        raise FeedFehler("Signatur fehlt oder passt nicht")


def _q(v) -> str:
    return json.dumps("" if v is None else str(v), ensure_ascii=False)


def _text_aus_html(fragment: str) -> str:
    """Hugo rendert Markdown; einfaches HTML aus ERPNext geht als Absatztext, Tags fallen weg."""
    t = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h[1-6]>", "\n", fragment or "")
    t = re.sub(r"(?i)<li[^>]*>", "- ", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    return "\n".join(line.rstrip() for line in t.splitlines()).strip()


def datei(job: Mapping) -> str:
    """Front Matter wie recruiting/career_feed.front_matter, dazu die Herkunftsmarke und der Text."""
    kopf = [
        "---",
        f"title: {_q(job.get('title'))}",
        f"date: {_q(str(job.get('published_at') or '')[:10])}",
        f"slug: {_q(job.get('slug'))}",
        f"department: {_q(job.get('department'))}",
        f"location: {_q(job.get('location'))}",
        f"employment_type: {_q(job.get('employment_type'))}",
        'status: "Active"',
        MARKE,
    ]
    if job.get("valid_until"):
        kopf.append(f"expiryDate: {_q(str(job['valid_until'])[:10])}")
    kopf += ["draft: false", "---", ""]
    teile = [str(job.get("summary") or "").strip(), _text_aus_html(str(job.get("description_html") or ""))]
    rumpf = "\n\n".join(t for t in teile if t)
    return "\n".join(kopf) + (rumpf + "\n" if rumpf else "")


def plan(feed: Mapping, ordner: Path) -> list[tuple[str, Path, str | None]]:
    """(aktion, pfad, inhalt): neu, aendern, gleich, entwurf (nicht mehr im Feed), fremd (von Hand, Slug kollidiert)."""
    aus: list[tuple[str, Path, str | None]] = []
    im_feed: set[str] = set()
    for job in feed["jobs"]:
        slug = str(job.get("slug") or "")
        if not SLUG_RE.match(slug):
            raise FeedFehler(f"ungueltiger Slug: {slug!r}")
        im_feed.add(slug)
        pfad = ordner / f"{slug}.md"
        inhalt = datei(job)
        if not pfad.exists():
            aus.append(("neu", pfad, inhalt))
            continue
        alt = pfad.read_text(encoding="utf-8")
        if MARKE not in alt:
            aus.append(("fremd", pfad, None))
        elif alt == inhalt:
            aus.append(("gleich", pfad, None))
        else:
            aus.append(("aendern", pfad, inhalt))
    for pfad in sorted(ordner.glob("*.md")):
        if pfad.stem in im_feed or pfad.name == "_index.md":
            continue
        alt = pfad.read_text(encoding="utf-8")
        if MARKE in alt and "draft: false" in alt:
            aus.append(("entwurf", pfad, alt.replace("draft: false", "draft: true", 1)))
    return aus


def holen(url: str, timeout: int = 30) -> dict:
    if not url.startswith("https://"):
        raise FeedFehler("CAREER_FEED_URL muss mit https:// beginnen")
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "seraph-karriere-feed/1"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body.get("message", body) if isinstance(body, dict) else body


def main(argv: list[str] | None = None, feed: Mapping | None = None, ordner: Path = JOBS) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--schreiben", action="store_true", help="Dateien schreiben (sonst nur Probelauf)")
    args = ap.parse_args(argv)
    try:
        if feed is None:
            feed = holen(os.environ.get("CAREER_FEED_URL", "").strip())
        pruefen(feed, os.environ.get("CAREER_FEED_HMAC_SECRET", "").strip())
        schritte = plan(feed, ordner)
    except (FeedFehler, OSError, ValueError) as e:
        print(f"karriere_feed: {e}", file=sys.stderr)
        return 2
    for aktion, pfad, inhalt in schritte:
        print(f"{aktion:8} {pfad.name}")
        if args.schreiben and inhalt is not None and aktion in ("neu", "aendern", "entwurf"):
            pfad.write_text(inhalt, encoding="utf-8", newline="\n")
    if not args.schreiben:
        print("Probelauf: nichts geschrieben (--schreiben schreibt).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
