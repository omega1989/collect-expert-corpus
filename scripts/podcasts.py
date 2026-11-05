"""Collect podcast episodes featuring one subject from RSS feeds (+ transcripts when the feed has them).

Usage:
  .venv/bin/python tools/podcasts.py <subject> discover   # iTunes episode search (cfg pod_terms) -> raw/podcasts/_itunes.json
  .venv/bin/python tools/podcasts.py <subject> collect    # parse raw/podcasts/feeds/<show-slug>.xml, write episode .md files
Shows listed in cfg hosted_shows keep every in-window episode; other shows only episodes naming the subject.
"""
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

from common import SINCE, UNTIL, load

CFG = load()
POD = CFG["root"] / "raw" / "podcasts"
FEEDS = POD / "feeds"
HOSTED = set(CFG.get("hosted_shows", []))
NS = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd", "podcast": "https://podcastindex.org/namespace/1.0"}
UA = {"User-Agent": "Mozilla/5.0 (research script)"}


def slug(s, n=70):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n] or hashlib.sha1(s.encode()).hexdigest()[:10]


def discover():
    POD.mkdir(parents=True, exist_ok=True)
    out = {}
    for term in CFG.get("pod_terms", []):
        r = requests.get("https://itunes.apple.com/search",
                         params={"term": term, "entity": "podcastEpisode", "limit": 200}, headers=UA, timeout=60)
        for it in r.json().get("results", []):
            if CFG["match_re"].search(f"{it.get('trackName', '')} {it.get('description', '')}"):
                out[it["trackId"]] = {k: it.get(k) for k in ("collectionName", "trackName", "releaseDate",
                                                             "trackViewUrl", "episodeUrl", "feedUrl", "collectionViewUrl")}
    (POD / "_itunes.json").write_text(json.dumps(list(out.values()), ensure_ascii=False, indent=1))
    shows = {}
    for e in out.values():
        if SINCE <= (e["releaseDate"] or "")[:10] <= UNTIL:
            shows.setdefault(e["collectionName"], []).append(e)
    for name, eps in sorted(shows.items(), key=lambda x: -len(x[1])):
        print(f"{len(eps):3d}  {name}  feed={eps[0].get('feedUrl')}")


def collect():
    n, errors = 0, []
    for feed in sorted(FEEDS.glob("*.xml")):
        show_slug = feed.stem
        try:
            channel = ET.parse(feed).getroot().find("channel")
            show = channel.findtext("title")
        except (ET.ParseError, AttributeError) as e:  # e.g. a Cloudflare HTML page saved as .xml
            errors.append(f"{feed.name}: not an RSS feed ({e.__class__.__name__})")
            continue
        outdir = POD / show_slug
        for item in channel.findall("item"):
            title = item.findtext("title") or ""
            desc_html = item.findtext("description") or ""
            try:
                date = parsedate_to_datetime(item.findtext("pubDate")).date().isoformat()
            except (TypeError, ValueError):
                errors.append(f"{feed.name}: no/invalid pubDate for {title[:80]!r}")
                continue
            if not SINCE <= date <= UNTIL:
                continue
            if show_slug not in HOSTED and not CFG["match_re"].search(f"{title} {desc_html}"):
                continue
            outdir.mkdir(exist_ok=True)
            dest = outdir / f"{date}_{slug(title)}.md"
            if dest.exists():
                if f"title: {json.dumps(title, ensure_ascii=False)}\n" not in dest.read_text():  # same day, different episode
                    dest = outdir / f"{date}_{slug(title)}-{hashlib.sha1(title.encode()).hexdigest()[:6]}.md"
                if dest.exists():
                    continue
            tr = item.find("podcast:transcript", NS)
            transcript = "(no transcript in feed)"
            if tr is not None:
                resp = requests.get(tr.get("url"), headers=UA, timeout=60)
                transcript = resp.text if resp.ok else f"(transcript fetch failed: HTTP {resp.status_code})"
            enc = item.find("enclosure")
            desc = BeautifulSoup(desc_html, "html.parser").get_text("\n").strip()
            dest.write_text(
                "---\n"
                f"type: podcast\nshow: {json.dumps(show, ensure_ascii=False)}\n"
                f"title: {json.dumps(title, ensure_ascii=False)}\n"
                f"date: {date}\nurl: {item.findtext('link')}\n"
                f"audio: {enc.get('url') if enc is not None else ''}\n"
                f"duration: {item.findtext('itunes:duration', namespaces=NS)}\n"
                f"subject_role: {'host' if show_slug in HOSTED else 'guest'}\n"
                f"transcript_available: {'true' if tr is not None else 'false'}\n"
                "---\n\n"
                f"# {title}\n\n**Ngày phát hành:** {date} · **Show:** {show}\n\n"
                f"## Description\n\n{desc}\n\n## Transcript\n\n{transcript}\n"
            )
            n += 1
            print(f"{date}  {show}  {title[:80]}", flush=True)
    (POD / "_collect_errors.txt").unlink(missing_ok=True)
    if errors:
        (POD / "_collect_errors.txt").write_text("\n".join(errors) + "\n")
    print(f"wrote {n} episodes; {len(errors)} feed/item errors" + (" (see raw/podcasts/_collect_errors.txt)" if errors else ""))


if __name__ == "__main__":
    {"discover": discover, "collect": collect}[sys.argv[2]]()
