"""Create (or refresh the tools of) an expert-corpus project.

Usage:
  python3 init_project.py <project_dir> --title "Jane Doe" [--years 2 | --since 2024-11-05 --until 2026-11-05]
  python3 init_project.py <project_dir> --update-tools     # recopy scripts, keep data and project.json
Creates project.json, tools/ (copies of this folder with __PROJECT_DIR__ filled in) and .venv with yt-dlp etc.
Prints warnings for missing external tools (ffmpeg, whisper-cli + model, ego-browser).
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGES = ["yt-dlp", "requests", "beautifulsoup4", "lxml"]
NOT_COPIED = {"init_project.py", "new_subject.py"}
MODEL = Path.home() / ".cache" / "whisper" / "ggml-large-v3-turbo-q5_0.bin"


def copy_tools(project):
    tools = project / "tools"
    tools.mkdir(exist_ok=True)
    n = 0
    for f in sorted(HERE.iterdir()):
        if f.suffix not in (".py", ".mjs") or f.name in NOT_COPIED:
            continue
        text = f.read_text().replace("__PROJECT_DIR__", str(project))
        (tools / f.name).write_text(text)
        n += 1
    leftover = [f.name for f in tools.iterdir() if f.suffix in (".py", ".mjs") and "__PROJECT_DIR__" in f.read_text()]
    assert not leftover, f"placeholder left in {leftover}"
    return n


def iso(s):
    try:
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        raise SystemExit(f"date must be YYYY-MM-DD, got {s!r}")


def main():
    if sys.version_info < (3, 11):
        raise SystemExit(f"Python {sys.version.split()[0]} is too old: yt-dlp needs 3.11+. "
                         "Install a newer one (brew install python@3.12) and run this script with python3.12.")
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--title")
    ap.add_argument("--years", type=int, default=2)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--update-tools", action="store_true")
    a = ap.parse_args()
    project = Path(a.project).expanduser().resolve()
    pj = project / "project.json"

    if a.update_tools:
        assert pj.exists(), f"{pj} missing: run without --update-tools first"
    else:
        assert a.title, "--title is required for a new project"
        assert not pj.exists(), f"{pj} exists: use --update-tools to refresh tools only"
        today = dt.date.today()
        until = iso(a.until) if a.until else today.isoformat()
        since = iso(a.since) if a.since else (today - dt.timedelta(days=round(365.25 * a.years))).isoformat()
        assert since < until, "since must be before until"
        project.mkdir(parents=True, exist_ok=True)
        pj.write_text(json.dumps({"title": a.title, "since": since, "until": until, "subjects": [],
                                  "created": today.isoformat()}, ensure_ascii=False, indent=1))

    n = copy_tools(project)
    venv = project / ".venv"
    if not (venv / "bin" / "yt-dlp").exists():
        subprocess.run([sys.executable, "-m", "venv", venv], check=True)
        subprocess.run([venv / "bin" / "pip", "install", "-q", *PACKAGES], check=True)
    else:
        subprocess.run([venv / "bin" / "pip", "install", "-q", "-U", "yt-dlp"], check=True)
    assert (venv / "bin" / "yt-dlp").exists(), "yt-dlp not installed in .venv"

    warnings = [w for w, ok in [
        ("ffmpeg missing (needed by Whisper step)", shutil.which("ffmpeg")),
        ("whisper-cli missing (brew install whisper-cpp)", shutil.which("whisper-cli")),
        (f"Whisper model missing: {MODEL}", MODEL.exists()),
        ("ego-browser missing (needed for YouTube transcripts / LinkedIn)", shutil.which("ego-browser")),
        ("node missing (yt-dlp --js-runtimes node)", shutil.which("node")),
    ] if not ok]
    print(json.dumps({"project": str(project), "tools_copied": n, "project_json": json.loads(pj.read_text()),
                      "warnings": warnings}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
