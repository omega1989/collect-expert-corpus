"""articles_common.py — shared helpers (HTML->Markdown, writer) for article / web-guide / talk collectors.

The subject comes from the SUBJECT env var (e.g. SUBJECT=experts/jane-doe).
write(item, body_md, kind=...) puts files in <subject>/raw/<kind>/<source_slug>/<date>_<slug>.md,
kind = "articles" (default), "web" (official guides / help pages) or "talks" (webinars, conference talks).
"""
import json, os, re, time, unicodedata, datetime as dt
from pathlib import Path
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent / os.environ["SUBJECT"]
OUT = ROOT / "raw" / "articles"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
S = requests.Session(); S.headers["User-Agent"] = UA
FETCHED = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
from common import SINCE as WIN_START, UNTIL as WIN_END  # noqa: E402

def get(url, **kw):
    time.sleep(1.0)
    r = S.get(url, timeout=60, **kw); r.raise_for_status(); return r

# ---------------- HTML -> Markdown ----------------
def _inline(node):
    out = []
    for c in node.children:
        if isinstance(c, NavigableString):
            out.append(re.sub(r"\s+", " ", str(c)))
            continue
        if not isinstance(c, Tag): continue
        n = c.name
        if n in ("script", "style", "noscript", "svg", "button", "form"): continue
        if n == "br": out.append("\u2028"); continue
        if n in ("strong", "b", "em", "i"):
            raw = _inline(c); t = raw.strip(); mk = "**" if n in ("strong", "b") else "*"
            if not t: out.append(" " if raw else ""); continue
            if t.startswith(mk) and t.endswith(mk) and len(t) > 2 * len(mk): mk = ""
            lead = " " if raw[:1].isspace() else ""; trail = " " if raw[-1:].isspace() else ""
            out.append(f"{lead}{mk}{t}{mk}{trail}"); continue
        if n == "code": out.append(f"`{c.get_text()}`"); continue
        if n == "a":
            t = _inline(c).strip(); h = c.get("href") or ""
            if h and t and not h.startswith(("javascript:", "#")): out.append(f"[{t}]({h})")
            else: out.append(t)
            continue
        if n == "img":
            src = c.get("src") or c.get("data-src") or ""
            if src and "/_/stat?" not in src: out.append(f"![{(c.get('alt') or '').strip()}]({src})")
            continue
        out.append(_inline(c))
    return "".join(out)

BLOCKS = {"p","div","section","article","figure","figcaption","blockquote","ul","ol","li","pre","table",
          "h1","h2","h3","h4","h5","h6","hr","iframe","header","footer","main","aside","picture","center"}

def _has_block(tag):
    return any(isinstance(c, Tag) and c.name in BLOCKS for c in tag.children)

def _list(tag, depth):
    lines = []; ordered = tag.name == "ol"; i = 1
    for li in tag.find_all("li", recursive=False):
        sub = [c for c in li.children if isinstance(c, Tag) and c.name in ("ul", "ol")]
        for s in sub: s.extract()
        if _has_block(li):
            text = " ".join(b.strip() for b in _blocks(li, depth + 1) if b.strip())
        else:
            text = _inline(li).strip()
        bullet = f"{i}." if ordered else "-"
        lines.append("  " * depth + f"{bullet} {text}")
        for s in sub: lines.append(_list(s, depth + 1))
        i += 1
    return "\n".join(lines)

def _table(tag):
    rows = []
    for tr in tag.find_all("tr"):
        cells = [_inline(td).strip().replace("|", "\\|").replace("\n", " ") for td in tr.find_all(["td", "th"])]
        if cells: rows.append(cells)
    if not rows: return ""
    w = max(len(r) for r in rows); rows = [r + [""] * (w - len(r)) for r in rows]
    md = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w]
    md += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(md)

def _blocks(node, depth=0):
    out, buf = [], []
    def flush():
        t = "".join(buf).strip()
        if t: out.append(t)
        buf.clear()
    for c in node.children:
        if isinstance(c, NavigableString):
            buf.append(re.sub(r"\s+", " ", str(c))); continue
        if not isinstance(c, Tag): continue
        n = c.name
        if n in ("script", "style", "noscript", "svg", "button", "form", "nav"): continue
        if n not in BLOCKS:
            # inline element
            tmp = BeautifulSoup("<x></x>", "lxml").x; tmp.append(c.__copy__())
            buf.append(_inline(tmp)); continue
        flush()
        if n in ("h1","h2","h3","h4","h5","h6"):
            t = _inline(c).strip()
            if t: out.append("#" * int(n[1]) + " " + t)
        elif n in ("ul", "ol"): out.append(_list(c, depth))
        elif n == "pre": out.append("```\n" + c.get_text().rstrip() + "\n```")
        elif n == "table": out.append(_table(c))
        elif n == "hr": out.append("---")
        elif n == "iframe":
            src = c.get("src") or c.get("data-src")
            if src: out.append(f"[Embedded: {src}]({src})")
        elif n == "blockquote":
            inner = "\n\n".join(_blocks(c, depth)) if _has_block(c) else _inline(c).strip()
            out.append("\n".join("> " + l if l else ">" for l in inner.split("\n")))
        elif n == "p" or not _has_block(c):
            t = _inline(c).strip()
            if t: out.append(t)
        else:
            out.extend(_blocks(c, depth))
    flush()
    return [b for b in out if b.strip()]

def html_to_md(html_or_tag):
    soup = html_or_tag if isinstance(html_or_tag, Tag) else BeautifulSoup(html_or_tag, "lxml")
    if soup.name == "[document]": soup = soup.body or soup
    md = "\n\n".join(_blocks(soup))
    md = re.sub(r"[ \t]+\n", "\n", md); md = re.sub(r"[ \t]*\u2028[ \t]*", "  \n", md); md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"

# ---------------- writing ----------------
def slugify(s, n=70):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:n].rstrip("-") or "untitled"

def yq(v):
    return json.dumps(v, ensure_ascii=False)

INDEX_FILE = ROOT / "raw" / "articles" / "_index.json"

def load_index():
    return json.loads(INDEX_FILE.read_text()) if INDEX_FILE.exists() else []

def save_index(items):
    seen = {}
    for x in items: seen[x["file"]] = x
    INDEX_FILE.write_text(json.dumps(list(seen.values()), ensure_ascii=False, indent=1), encoding="utf-8")

def write(item, body_md, index=None, kind="articles"):
    """item: source, source_slug, title, date, url, author, role; optional updated, date_type, note, audio.
    A talk without transcript: body_md containing "(no transcript in feed)" + item["audio"] = video page URL,
    then tools/transcribe.py fills it with Whisper."""
    d = item["date"]
    path = ROOT / "raw" / kind / item["source_slug"] / f"{d}_{slugify(item['title'])}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = ["---", f"type: {kind.rstrip('s')}", f"source: {yq(item['source'])}", f"title: {yq(item['title'])}", f"date: {yq(d)}"]
    if item.get("date_type"): fm.append(f"date_type: {item['date_type']}")
    if item.get("published"): fm.append(f"published: {yq(item['published'])}")
    if item.get("updated"): fm.append(f"updated: {yq(item['updated'])}")
    fm += [f"url: {yq(item['url'])}", f"author: {yq(item['author'])}", f"subject_role: {item['role']}",
           f"fetched_at: {yq(FETCHED)}"]
    if item.get("note"): fm.append(f"note: {yq(item['note'])}")
    if item.get("audio"): fm.append(f"audio: {item['audio']}")
    fm.append("---")
    head = f"# {item['title']}\n\n**Ngày đăng:** {d} · **Nguồn:** {item['source']}\n\n"
    path.write_text("\n".join(fm) + "\n\n" + head + body_md, encoding="utf-8")
    rec = {k: item.get(k) for k in ("source", "title", "date", "date_type", "published", "updated", "url", "role")}
    rec["file"] = str(path.relative_to(ROOT / "raw"))
    if index is not None: index.append(rec)
    print("wrote", path.relative_to(ROOT), len(body_md), "chars", flush=True)
    return path

def in_window(d): return bool(d) and WIN_START <= d[:10] <= WIN_END
