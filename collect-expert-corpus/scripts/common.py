"""Shared settings for every collector: the date window and per-subject config.

<project>/project.json (from init_project.py) holds title, since, until and the subject list.
Each subject lives in <slug>/ or <group>/<slug>/ with a config.json:
  name, kind (person|org), match (regex list: how the subject is named in titles/descriptions),
  own_channels (YouTube channel ids), own_filter (optional regex: keep only matching own-channel videos),
  yt_queries, pod_terms, hosted_shows (feed slugs where the subject hosts), speaker_label (regex),
  linkedin_feed (recent-activity URL).
Tools take the subject folder as first argument: .venv/bin/python tools/<tool>.py <subject> ...
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PROJECT = json.loads((BASE / "project.json").read_text())
SINCE, UNTIL = PROJECT["since"], PROJECT["until"]


def subjects():
    return [BASE / s for s in PROJECT["subjects"]]


def load(arg=None):
    root = (BASE / (arg or sys.argv[1])).resolve()
    cfg = json.loads((root / "config.json").read_text())
    cfg["root"] = root
    cfg["match_re"] = re.compile("|".join(cfg["match"]), re.I)
    return cfg
