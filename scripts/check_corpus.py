"""Verify the "Done means" list of an expert corpus. Prints PASS/FAIL per check + counts; exit 1 on any FAIL.

Usage: .venv/bin/python tools/check_corpus.py            (run from the project dir)
Checks:
  1 dates     every corpus .md has a front-matter date inside [since, until] (undated web guides must say date_type)
  2 transcripts  no "(no transcript in feed)" placeholder left, except files tagged subject_speaks: no
  3 youtube   every id in each _queue.txt has a transcript or a permanent line in _transcript_fail.txt
              (fail reasons are counted so the reader can judge them)
  4 linkedin  every linkedin_feed has raw/social/linkedin/_done (window start or feed end reached)
              or a non-empty raw/social/linkedin/_gap.md saying why it stopped
  5 docs      README.md + INDEX.md at root, INDEX.md per subject, all rebuilt after the newest data file
  6 zip       ../<project>-corpus-*.zip exists, is newer than INDEX.md, passes testzip, has no .venv/
"""
import json
import re
import sys
import zipfile
from collections import Counter

from common import BASE, SINCE, UNTIL, ids_from, subjects

PLACEHOLDER = "(no transcript in feed)"
results, counts = [], Counter()


def front(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip().strip('"')
    return out


def corpus_files(root):
    for f in sorted((root / "raw").rglob("*.md")):
        if not any(p.startswith("_") for p in f.relative_to(root / "raw").parts):
            yield f


def check(name, ok, detail):
    results.append((name, ok, detail))


bad_dates, placeholders, unasked, yt_pending, li_open, newest = [], [], 0, [], [], 0.0
fail_reasons = Counter()
for root in subjects():
    rel = root.relative_to(BASE)
    for f in corpus_files(root):
        newest = max(newest, f.stat().st_mtime)
        text = f.read_text()
        fm = front(text)
        counts[f"{rel}:{f.relative_to(root / 'raw').parts[0]}"] += 1
        d = fm.get("date", "")[:10]
        if not (SINCE <= d <= UNTIL) and "undated" not in fm.get("date_type", ""):
            bad_dates.append(f"{f.relative_to(BASE)} date={d or 'MISSING'}")
        if PLACEHOLDER in text:
            if fm.get("subject_speaks") == "no":
                unasked += 1
            else:
                placeholders.append(str(f.relative_to(BASE)))
    yt = root / "raw" / "youtube"
    done = {p.stem for p in (yt / "transcripts").glob("*.json")}
    failed = set(ids_from(yt / "_transcript_fail.txt"))
    if (yt / "_transcript_fail.txt").exists():
        fail_reasons.update(l.split("|", 1)[-1].strip() for l in (yt / "_transcript_fail.txt").read_text().splitlines() if "|" in l)
    yt_pending += [f"{rel}:{i}" for i in ids_from(yt / "_queue.txt") if i not in done | failed]
    cfg = json.loads((root / "config.json").read_text())
    li = root / "raw" / "social" / "linkedin"
    gap = li / "_gap.md"
    if cfg.get("linkedin_feed") and not (li / "_done").exists() and not (gap.exists() and gap.read_text().strip()):
        li_open.append(str(rel))
    if not (root / "INDEX.md").exists() or (root / "INDEX.md").stat().st_mtime < newest:
        check("5 docs", False, f"{rel}/INDEX.md missing or older than data: run build_md.py all")

readme = BASE / "README.md"
check("1 dates", not bad_dates, f"{len(bad_dates)} out of window/missing: {bad_dates[:5]}")
check("2 transcripts", not placeholders, f"{len(placeholders)} placeholders left (+{unasked} skipped, subject not speaking): {placeholders[:5]}")
check("3 youtube", not yt_pending, f"{len(yt_pending)} queued without transcript/fail line: {yt_pending[:5]}; "
      f"failed by reason: {dict(fail_reasons.most_common(6))}")
check("4 linkedin", not li_open, f"feeds with neither _done nor _gap.md: {li_open}")
index = BASE / "INDEX.md"
docs_ok = readme.exists() and index.exists() and index.stat().st_mtime >= newest
if not any(n == "5 docs" for n, _, _ in results):
    check("5 docs", docs_ok, "README.md + INDEX.md present and fresh" if docs_ok else "root README.md/INDEX.md missing or stale")
zips = sorted(BASE.parent.glob(f"{BASE.name}-corpus-*.zip"), key=lambda p: p.stat().st_mtime)
zip_ok, zip_detail = False, "no zip"
if zips:
    z = zips[-1]
    with zipfile.ZipFile(z) as zf:
        bad = zf.testzip()
        venv = [n for n in zf.namelist() if "/.venv/" in n]
        zip_ok = bad is None and not venv and index.exists() and z.stat().st_mtime >= index.stat().st_mtime
        zip_detail = f"{z.name}: {len(zf.namelist())} files, testzip={'ok' if bad is None else bad}, .venv files={len(venv)}"
check("6 zip", zip_ok, zip_detail)

for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name:14s} {detail}")
print(json.dumps(dict(sorted(counts.items())), ensure_ascii=False, indent=1))
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
