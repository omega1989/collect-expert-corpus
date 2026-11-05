"""Transcribe media without a transcript (podcast audio, talk videos) with local whisper.cpp.

Any raw/**/*.md (outside _-prefixed dirs) containing the placeholder "(no transcript in feed)" and an
`audio:` front-matter URL is processed; files tagged `subject_speaks: no` are skipped.
Usage:
  .venv/bin/python tools/transcribe.py <subject|all> list
  .venv/bin/python tools/transcribe.py <subject|all> run
Transcripts are cached in raw/_whisper/<parent>/<stem>.txt, then replace the placeholder.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

from common import BASE, load, subjects

MODEL = Path.home() / ".cache" / "whisper" / "ggml-large-v3-turbo-q5_0.bin"
YTDLP = str(BASE / ".venv" / "bin" / "yt-dlp")
PLACEHOLDER = "(no transcript in feed)"


def pending(root):
    for f in sorted((root / "raw").rglob("*.md")):
        if any(p.startswith("_") for p in f.relative_to(root / "raw").parts[:-1]) or f.name.startswith("_"):
            continue
        text = f.read_text()
        if PLACEHOLDER not in text or re.search(r"^subject_speaks: no\b", text, re.M):
            continue
        audio = re.search(r"^audio: (\S+)", text, re.M)
        if audio:
            yield root, f, audio.group(1)


def download(url, dest):
    if re.search(r"\.(mp3|m4a|mp4|wav|aac|ogg)(\?|$)", url, re.I):
        with requests.get(url, stream=True, timeout=120, headers={"User-Agent": "Mozilla/5.0"}) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
    else:  # page URL (Vimeo, Wistia, …): let yt-dlp find the audio
        subprocess.run([YTDLP, "-q", "-f", "bestaudio/best", "-o", str(dest), url], check=True)


def transcribe(root, f, url):
    out = root / "raw" / "_whisper" / f.parent.name / f"{f.stem}.txt"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src, wav = Path(tmp) / "media", Path(tmp) / "audio.wav"
        download(url, src)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ar", "16000", "-ac", "1", wav], check=True)
        subprocess.run(["whisper-cli", "-m", MODEL, "-f", wav, "-l", "auto", "-otxt", "-of", Path(tmp) / "out",
                        "--no-prints"], check=True)
        out.write_text((Path(tmp) / "out.txt").read_text())
    return out


def merge(f, txt):
    body = "*(Transcript tự chép bằng Whisper large-v3-turbo, chạy local — không có nhãn người nói)*\n\n" + txt.read_text()
    f.write_text(f.read_text().replace(PLACEHOLDER, body).replace("transcript_available: false", "transcript_available: true"))


def preflight():
    missing = [t for t in ("ffmpeg", "whisper-cli") if not shutil.which(t)]
    missing += [str(MODEL)] if not MODEL.exists() else []
    if missing:
        raise SystemExit(f"missing: {', '.join(missing)} — see README (brew install ffmpeg whisper-cpp + model download)")


if __name__ == "__main__":
    roots = subjects() if sys.argv[1] == "all" else [load()["root"]]
    items = [it for r in roots for it in pending(r)]
    for root, f, url in items:
        print(f.relative_to(BASE), url[:80])
    if sys.argv[2] == "run":
        preflight()
        for i, (root, f, url) in enumerate(items, 1):
            try:
                merge(f, transcribe(root, f, url))
                print(f"[{i}/{len(items)}] ok {f.relative_to(BASE)}", flush=True)
            except Exception as e:
                print(f"[{i}/{len(items)}] FAIL {f.relative_to(BASE)}: {e}", flush=True)
