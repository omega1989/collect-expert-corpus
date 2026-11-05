"""Turn raw JSON (YouTube meta+transcripts, LinkedIn posts) into dated markdown + indexes.

Usage: .venv/bin/python tools/build_md.py <subject|all>
Outputs per subject:
  raw/youtube/md/<YYYY-MM-DD>_<id>_<slug>.md
  raw/social/linkedin/md/<YYYY-MM>/<YYYY-MM-DD>_<slug>_<uid>.md
  INDEX.md (every item of the subject, sorted by date; podcasts/articles/talks/web read from front matter)
With "all", also writes the master INDEX.md at the project root.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from common import BASE, PROJECT, SINCE, UNTIL, ids_from, load, subjects

CFG = ROOT = RAW = None  # set per subject in build()


def slug(s, n=60):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:n] or "untitled"


def iso(yyyymmdd):
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}" if yyyymmdd else None


def fmt_dur(sec):
    sec = int(sec or 0)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def front(d):
    return "---\n" + "".join(f"{k}: {json.dumps(v, ensure_ascii=False)}\n" for k, v in d.items()) + "---\n\n"


def build_youtube(index):
    meta_dir, tr_dir = RAW / "youtube" / "meta", RAW / "youtube" / "transcripts"
    out = RAW / "youtube" / "md"
    out.mkdir(parents=True, exist_ok=True)
    exclude = set(ids_from(RAW / "youtube" / "_exclude.txt"))
    for f in tr_dir.glob("*.json"):
        if f.stem in exclude:
            continue
        tr = json.loads(f.read_text())
        mf = meta_dir / f.name
        if not mf.exists():
            continue
        m = json.loads(mf.read_text())
        date = iso(m.get("upload_date"))
        if not date or not SINCE <= date <= UNTIL:
            continue
        own = m.get("channel_id") in CFG.get("own_channels", [])
        fm = {
            "type": "youtube", "title": m["title"], "date": date, "channel": m.get("channel"),
            "subject_role": "own channel" if own else "guest/featured",
            "url": m.get("webpage_url"), "duration": fmt_dur(m.get("duration")),
            "transcript_language": tr.get("language"), "transcript_source": "YouTube transcript panel",
            "fetched_at": tr.get("fetched_at"),
        }
        if m["id"] in CFG.get("segments", {}):
            fm["subject_segment"] = CFG["segments"][m["id"]]
        chapters = "".join(f"- {fmt_dur(c['start_time'])} {c['title']}\n" for c in (m.get("chapters") or []))
        body = "\n".join(f"[{s['t']}] {s['text']}" for s in tr["segments"])
        name = f"{date}_{m['id']}_{slug(m['title'])}.md"
        (out / name).write_text(
            front(fm) + f"# {m['title']}\n\n**Ngày đăng:** {date} · **Kênh:** {m.get('channel')} · "
            f"**Thời lượng:** {fm['duration']} · {m.get('webpage_url')}\n\n"
            f"## Description\n\n{m.get('description') or ''}\n\n"
            + (f"## Chapters\n\n{chapters}\n" if chapters else "")
            + f"## Transcript\n\n{body}\n"
        )
        index.append((date, "YouTube", m.get("channel"), m["title"], f"raw/youtube/md/{name}"))


LI_HEADER_END = re.compile(r"^.*(Visible to anyone on or off LinkedIn|ago •).*$", re.M)
LI_FOOTER = re.compile(r"\n(Like\nComment\nRepost\nSend|\d[\d,]* reactions?|Activate to view larger image).*", re.S)


def build_linkedin(index):
    src = RAW / "social" / "linkedin" / "posts.jsonl"
    if not src.exists():
        return
    out = RAW / "social" / "linkedin" / "md"
    links = defaultdict(list)
    prev_date = None
    for line in src.read_text().splitlines():
        p = json.loads(line)
        date = (p.get("date") or "")[:10] or None
        # Feed is newest-first: a post without an id-derived time sits between its neighbours.
        if not date and prev_date:
            date, p["date_estimated"] = prev_date, f"ước lượng từ post liền trước trong feed ({p.get('relative_time')})"
        prev_date = (p.get("date") or "")[:10] or prev_date
        if date and not SINCE <= date <= UNTIL:
            continue
        raw = p["text"]
        heads = list(LI_HEADER_END.finditer(raw))
        body = raw[heads[0].end():] if heads else raw
        body = LI_FOOTER.sub("", body).strip()
        body = re.sub(r"(\n\s*([\d,.]+K?|[\d,]+ (comments?|reposts?)|…see more|… more|​)\s*)+$", "", body)
        body = re.sub(r"\n{3,}", "\n\n", body)
        ext = sorted({u for u in p["links"] if not re.search(r"linkedin\.com/(services|feed/update)", u)})
        for u in ext:
            links[u].append(date)
        first = next((l for l in body.splitlines() if l.strip()), "")
        d = out / ((date or "unknown")[:7])
        d.mkdir(parents=True, exist_ok=True)
        uid = re.sub(r"\D", "", p["urn"])[-6:] or "x"
        name = f"{date or 'unknown'}_{slug(first, 50)}_{uid}.md"
        fm = {"type": "linkedin_post", "date": date, "datetime_utc": p.get("date"), "date_estimated": p.get("date_estimated"), "url": p.get("permalink"),
              "is_repost": p.get("is_repost"), "has_video": p.get("has_video"), "images": p.get("images"),
              "outbound_links": ext}
        (d / name).write_text(
            front(fm) + f"# LinkedIn post — {date}{' (repost)' if p.get('is_repost') else ''}\n\n"
            f"**Ngày đăng:** {p.get('date')} (UTC, tính từ activity ID) · {p.get('permalink')}\n\n{body}\n"
            + ("\n## Links\n\n" + "".join(f"- {u}\n" for u in ext) if ext else "")
        )
        index.append((date, "LinkedIn" + (" (repost)" if p.get("is_repost") else ""), "LinkedIn",
                      first[:100], f"raw/social/linkedin/md/{(date or 'unknown')[:7]}/{name}"))
    (RAW / "social" / "linkedin" / "_outbound_links.md").write_text(
        "# Link ngoài trích từ LinkedIn posts\n\n| domain | url | ngày post |\n|---|---|---|\n"
        + "".join(f"| {urlparse(u).netloc} | {u} | {', '.join(sorted(set(filter(None, ds))))} |\n"
                  for u, ds in sorted(links.items(), key=lambda kv: (urlparse(kv[0]).netloc, kv[0])))
    )


def read_front(f):
    t = f.read_text()
    if not t.startswith("---"):
        return {}
    fm = {}
    for line in t.split("---", 2)[1].splitlines():
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"')
    return fm


def collect_md(index, base, kind):
    for f in sorted((RAW / base).rglob("*.md")):
        if any(part.startswith("_") for part in f.relative_to(RAW).parts):
            continue
        fm = read_front(f)
        if fm.get("date"):
            index.append((fm["date"], kind, fm.get("show") or fm.get("source") or "", fm.get("title", f.stem),
                          str(f.relative_to(ROOT))))


def clean_generated():
    """Remove previously generated .md files so renamed outputs don't leave stale copies."""
    for d in [RAW / "youtube" / "md", RAW / "social" / "linkedin" / "md"]:
        for f in d.rglob("*.md") if d.exists() else []:
            f.unlink()


def table(rows):
    return ("| Ngày | Loại | Nguồn | Tiêu đề | File |\n|---|---|---|---|---|\n"
            + "".join(f"| {d} | {k} | {s} | {t.replace('|', '/')} | [{Path(p).name}]({p}) |\n" for d, k, s, t, p in rows))


def counts_line(rows):
    counts = defaultdict(int)
    for r in rows:
        counts[r[1]] += 1
    return " · ".join(f"**{k}:** {v}" for k, v in sorted(counts.items())), dict(counts)


def build(root):
    global CFG, ROOT, RAW
    CFG = load(str(root.relative_to(BASE)))
    ROOT, RAW = CFG["root"], CFG["root"] / "raw"
    clean_generated()
    index = []
    build_youtube(index)
    build_linkedin(index)
    collect_md(index, "podcasts", "Podcast")
    collect_md(index, "articles", "Article")
    collect_md(index, "talks", "Talk")
    collect_md(index, "web", "Web/Guide")
    index = [r for r in index if r[0] and SINCE <= r[0][:10] <= UNTIL]
    index.sort(key=lambda r: r[0] or "", reverse=True)
    line, counts = counts_line(index)
    (ROOT / "INDEX.md").write_text(f"# {CFG['name']} — raw corpus ({SINCE} → {UNTIL})\n\n{line}\n\n" + table(index))
    print(root.relative_to(BASE), counts)
    return index


def main():
    roots = subjects() if sys.argv[1] == "all" else [load()["root"]]
    rows = []
    for root in roots:
        rel = root.relative_to(BASE)
        name = json.loads((root / "config.json").read_text())["name"]
        rows += [(d, k, f"{name} · {s}" if s else name, t, f"{rel}/{p}") for d, k, s, t, p in build(root)]
    if sys.argv[1] == "all":
        rows.sort(key=lambda r: r[0] or "", reverse=True)
        (BASE / "INDEX.md").write_text(f"# {PROJECT['title']} — raw corpus ({SINCE} → {UNTIL})\n\n"
                                       f"{counts_line(rows)[0]}\n\n" + table(rows))


if __name__ == "__main__":
    main()
