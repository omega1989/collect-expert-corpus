"""Add one subject (person or organisation) to a project and write its config.json skeleton.

Usage:
  python3 new_subject.py <project_dir> <path> --name "Nathan Gotch" --kind person \
      --match "nathan gotch" "gotch seo" [--speaker "^(nathan|gotch)\\b"]
<path> is <slug> or <group>/<slug> (e.g. source/savannah-sanchez). Fill the remaining config fields
(own_channels, yt_queries, pod_terms, hosted_shows, linkedin_feed…) during source discovery.
"""
import argparse
import json
import re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("path")
    ap.add_argument("--name", required=True)
    ap.add_argument("--kind", choices=["person", "org"], required=True)
    ap.add_argument("--match", nargs="+", required=True, help="regexes naming the subject in titles/descriptions")
    ap.add_argument("--speaker", default="^$", help="regex for transcript speaker labels")
    a = ap.parse_args()
    project = Path(a.project).expanduser().resolve()
    pj = project / "project.json"
    meta = json.loads(pj.read_text())
    assert re.fullmatch(r"[a-z0-9-]+(/[a-z0-9-]+)?", a.path), "path must be slug or group/slug (lowercase, hyphens)"
    assert a.path not in meta["subjects"], f"{a.path} already in project.json"
    for r in a.match + [a.speaker]:
        re.compile(r)
    d = project / a.path
    (d / "raw").mkdir(parents=True, exist_ok=True)
    cfg = {"name": a.name, "kind": a.kind, "match": a.match, "speaker_label": a.speaker,
           "own_channels": [], "own_filter": None, "yt_queries": [], "pod_terms": [], "hosted_shows": [],
           "linkedin_feed": None, "segments": {}, "pod_overrides": {}, "pod_notes": {}}
    (d / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
    meta["subjects"].append(a.path)
    pj.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"added {a.path}; subjects now: {meta['subjects']}")


if __name__ == "__main__":
    main()
