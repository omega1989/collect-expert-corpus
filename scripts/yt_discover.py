"""Discover YouTube videos for one subject and fetch exact metadata.

Usage:
  .venv/bin/python tools/yt_discover.py <subject> channel   # own channels (approx. dates) -> raw/youtube/_channel_videos.txt
  .venv/bin/python tools/yt_discover.py <subject> search    # cfg yt_queries -> raw/youtube/_candidates.txt
  .venv/bin/python tools/yt_discover.py <subject> meta      # exact metadata for channel + candidates + _extra.txt
  .venv/bin/python tools/yt_discover.py <subject> queue     # in-window videos without transcript -> raw/youtube/_queue.txt
raw/youtube/_extra.txt adds ids by hand (verified guest appearances); _exclude.txt drops false positives.
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import BASE, SINCE, UNTIL, load

CFG = load()
YT = CFG["root"] / "raw" / "youtube"
META = YT / "meta"
TRANSCRIPTS = YT / "transcripts"
YTDLP = str(BASE / ".venv" / "bin" / "yt-dlp")
SINCE_D, UNTIL_D = SINCE.replace("-", ""), UNTIL.replace("-", "")
# Flat channel listings only give approximate dates ("3 months ago"); keep a margin, exact dates come from meta.
APPROX_SINCE = str(int(SINCE_D) - 300)  # ≈3 months earlier (yyyymmdd arithmetic)
MIN_SECONDS = 75  # shorter = Shorts / teasers, skipped


def run(args, timeout=300):
    try:
        return subprocess.run([YTDLP, "--js-runtimes", "node", *args],
                              capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ""


def channel():
    YT.mkdir(parents=True, exist_ok=True)
    rows = []
    for cid in CFG.get("own_channels", []):
        for tab in ("videos", "streams"):
            out = run(["--flat-playlist", "--extractor-args", "youtubetab:approximate_date",
                       "--print", "%(id)s|%(upload_date)s|%(duration)s|%(title)s",
                       f"https://www.youtube.com/channel/{cid}/{tab}"], timeout=900)
            for line in out.splitlines():
                vid, date, dur, title = (line.split("|", 3) + ["", "", ""])[:4]
                if len(vid) == 11 and (date in ("NA", "") or date >= APPROX_SINCE):
                    rows.append(f"{vid}|{cid}|{date}|{dur}|{title}")
            print(f"{cid}/{tab}: {len(rows)} in approx window", flush=True)
    (YT / "_channel_videos.txt").write_text("\n".join(dict.fromkeys(rows)) + "\n")


def search():
    YT.mkdir(parents=True, exist_ok=True)
    seen = {}
    for q in CFG.get("yt_queries", []):
        out = run(["--flat-playlist", "--print", "%(id)s|%(channel)s|%(title)s", f"ytsearch30:{q}"])
        for line in out.splitlines():
            vid, _, rest = line.partition("|")
            if len(vid) == 11:
                seen.setdefault(vid, rest)
        print(f"{q!r}: total {len(seen)}", flush=True)
    (YT / "_candidates.txt").write_text("\n".join(f"{k}|{v}" for k, v in seen.items()) + "\n")


def ids_from(path):
    if not path.exists():
        return []
    return [re.split(r"[|\s#]", l.strip())[0] for l in path.read_text().splitlines() if l.strip() and not l.startswith("#")]


def fetch_meta(vid):
    dest = META / f"{vid}.json"
    if dest.exists():
        return vid, "cached"
    out = run(["-j", "--skip-download", "--no-warnings", f"https://www.youtube.com/watch?v={vid}"], timeout=120)
    if not out.strip():
        return vid, "failed"
    d = json.loads(out)
    keep = {k: d.get(k) for k in ("id", "title", "channel", "channel_id", "channel_url", "uploader",
                                   "upload_date", "duration", "description", "chapters", "tags",
                                   "view_count", "webpage_url", "language", "was_live")}
    dest.write_text(json.dumps(keep, ensure_ascii=False, indent=1))
    return vid, "ok"


def meta():
    META.mkdir(parents=True, exist_ok=True)
    ids = []
    for f in ["_channel_videos.txt", "_candidates.txt", "_extra.txt"]:
        ids += ids_from(YT / f)
    ids = list(dict.fromkeys(ids))
    print(f"{len(ids)} ids", flush=True)
    with ThreadPoolExecutor(2) as ex:
        for i, (vid, status) in enumerate(ex.map(fetch_meta, ids), 1):
            if status != "cached":
                print(f"[{i}/{len(ids)}] {vid} {status}", flush=True)


def wanted(d, extra):
    """-> (keep?, reason)."""
    date = d.get("upload_date") or "0"
    if not SINCE_D <= date <= UNTIL_D:
        return False, "out of window"
    if (d.get("duration") or 0) < MIN_SECONDS:
        return False, "short (<75s)"
    text = f"{d.get('channel', '')} {d.get('title', '')} {d.get('description', '')}"
    if d.get("channel_id") in CFG.get("own_channels", []):
        f = CFG.get("own_filter")
        return (True, "own") if not f or re.search(f, text, re.I) else (False, "own channel, off-topic (own_filter)")
    if d["id"] in extra or CFG["match_re"].search(text):
        return True, "guest/featured"
    return False, "subject not mentioned"


def queue():
    extra = set(ids_from(YT / "_extra.txt"))
    exclude = set(ids_from(YT / "_exclude.txt"))
    rows, skipped = [], []
    for f in sorted(META.glob("*.json")):
        d = json.loads(f.read_text())
        keep, why = (False, "excluded (_exclude.txt)") if d["id"] in exclude else wanted(d, extra)
        if not keep:
            if why not in ("out of window", "subject not mentioned"):
                skipped.append(f"| {d.get('upload_date')} | {d['id']} | {d.get('channel')} | {d['title'].replace('|', '/')} | {why} |")
            continue
        if not (TRANSCRIPTS / f"{d['id']}.json").exists():
            rows.append((d["upload_date"], d["id"], d.get("duration") or 0))
    rows.sort(reverse=True)
    (YT / "_queue.txt").write_text("\n".join(r[1] for r in rows) + ("\n" if rows else ""))
    (YT / "_skipped.md").write_text("# Video trong kỳ nhưng không lấy transcript\n\n| upload | id | kênh | tiêu đề | lý do |\n|---|---|---|---|---|\n"
                                    + "\n".join(sorted(skipped, reverse=True)) + "\n")
    print(f"queue: {len(rows)} videos, {sum(r[2] for r in rows) / 3600:.1f}h; skipped {len(skipped)}")


if __name__ == "__main__":
    {"channel": channel, "search": search, "meta": meta, "queue": queue}[sys.argv[2]]()
