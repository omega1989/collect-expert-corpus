"""Tag podcast episode files with whether the subject actually speaks in them.

Adds/refreshes in raw/podcasts/<show>/*.md (idempotent):
  subject_speaks: yes|no|unknown   subject_lines: <speaker turns labelled as the subject>
  transcript_available: true|false  subject_speaks_note (from cfg pod_overrides / pod_notes)
Speaker labels are matched with cfg speaker_label (regex, e.g. "^(savannah|sanchez)\\b").
Usage: .venv/bin/python tools/pod_tag.py <subject> [--dry]
"""
import re
import sys
from collections import Counter

from common import load

CFG = load()
POD = CFG["root"] / "raw" / "podcasts"
FIELDS = ("subject_speaks", "subject_lines", "transcript_available", "subject_speaks_note")
SUBJECT_LABEL = re.compile(CFG.get("speaker_label", "^$"), re.I)
OVERRIDES = CFG.get("pod_overrides", {})  # filename -> [speaks, note]
NOTES = CFG.get("pod_notes", {})          # filename -> note

UP = "A-ZÇĞİÖŞÜ"
NAME = rf"[{UP}][\w.'’-]*(?:\s+[{UP}][\w.'’-]*){{0,3}}"
# "Name:", "**Name:**", "Name says:", "<v Name>", "Name 2:", "**James (to audience):**"
LABEL = re.compile(
    rf"^\s*(?:\*\*)?(?:<v\s+)?(?P<name>{NAME})(?:\s+\d)?(?:\s*\([^)]*\))?"
    rf"(?:\*\*)?\s*(?::|>|\s+says\b)"
)
NO_TRANSCRIPT = re.compile(r"^\s*\((no transcript|transcript fetch failed)", re.I)
NOT_SPEAKERS = {"Speaker", "Mistake", "Could", "When", "Note", "Transcript"}


def split(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("no front matter")
    return m.group(1), text[m.end():]


def tag(f):
    fm, body = split(f.read_text())
    tr = body.split("## Transcript", 1)[1] if "## Transcript" in body else ""
    available = bool(tr.strip()) and not NO_TRANSCRIPT.match(tr.strip())
    names = Counter()
    for line in tr.splitlines():
        m = LABEL.match(line)
        if m and m.group("name") not in NOT_SPEAKERS:
            names[m.group("name")] += 1
    n_lines = sum(c for n, c in names.items() if SUBJECT_LABEL.match(n))
    labelled = n_lines > 0 or sum(1 for c in names.values() if c >= 2) >= 2
    note = NOTES.get(f.name)
    if f.name in OVERRIDES:
        speaks, note = OVERRIDES[f.name]
    elif not available:
        speaks = "unknown"
    elif n_lines:
        speaks = "yes"
    elif labelled:
        speaks = "no"
    else:
        speaks = "unknown"
    keep = [ln for ln in fm.splitlines() if ln.split(":", 1)[0] not in FIELDS]
    keep += [f"subject_speaks: {speaks}", f"subject_lines: {n_lines}",
             f"transcript_available: {'true' if available else 'false'}"]
    if note:
        keep.append(f'subject_speaks_note: "{note}"')
    return "---\n" + "\n".join(keep) + "\n---\n" + body, speaks, n_lines, available, names


def main():
    dry = "--dry" in sys.argv
    tally = Counter()
    for f in sorted(POD.glob("*/*.md")):
        if f.parent.name.startswith("_"):
            continue
        new, speaks, k, avail, names = tag(f)
        tally[speaks] += 1
        print(f"{speaks:7s} {k:3d} {'T' if avail else '-'}  {f.relative_to(POD)}  {dict(names.most_common(4))}")
        if not dry:
            f.write_text(new)
    print(dict(tally), "total", sum(tally.values()))


if __name__ == "__main__":
    main()
