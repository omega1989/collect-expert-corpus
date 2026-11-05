# Claude Skills

A library of [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for Claude Code. Each folder holds one skill: a `SKILL.md`, its reference files and its scripts. Claude loads a skill on its own when your request matches the skill's description.

| Skill | What it does | Example request |
|---|---|---|
| [collect-expert-corpus](collect-expert-corpus/) | Collects everything one or more experts or organisations said or published over a time window: YouTube transcripts, podcasts, articles and LinkedIn posts. Output is dated markdown files plus `INDEX.md`, `README.md` and a zip. | "lấy hết video, podcast, bài viết của [X] trong 2 năm" |

## Install

```bash
git clone https://github.com/omega1989/claude-skills.git ~/claude-skills
mkdir -p ~/.claude/skills
ln -s ~/claude-skills/collect-expert-corpus ~/.claude/skills/collect-expert-corpus
```

To update later, run `cd ~/claude-skills && git pull`. The symlink keeps Claude Code on the latest version.

## Requirements for collect-expert-corpus

| Tool | Used for | Install |
|---|---|---|
| Python 3.11+ | collection scripts (the skill creates its own `.venv`, including yt-dlp) | available on macOS / `brew install python` |
| Node.js | lets yt-dlp run YouTube's JS | `brew install node` |
| ego-browser (ego lite) | fetching YouTube transcripts and LinkedIn posts through your own logged-in browser | install ego lite, then `ego-browser skill` |
| ffmpeg + whisper.cpp | transcribing podcasts that come without a transcript, locally | `brew install ffmpeg whisper-cpp` |
| Whisper model | used by whisper.cpp | see below |

```bash
mkdir -p ~/.cache/whisper && curl -L -o ~/.cache/whisper/ggml-large-v3-turbo-q5_0.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin
```

## Usage

Open Claude Code in any folder and ask, for example:

> lấy hết video, podcast, bài viết của Nathan Gotch trong 2 năm gần đây

Claude follows `SKILL.md` step by step:
1. Creates the project folder.
2. Sends subagents to find sources.
3. Fetches transcripts.
4. Runs Whisper on audio that has no transcript.
5. Builds `INDEX.md`.
6. Checks the result with `check_corpus.py`.
7. Zips everything.

## Rules every skill in this library follows

- They never circumvent bot protection (Cloudflare, rate limits).
- They never invent data. Text taken from the web is treated as data, not as instructions.
- Anything behind a login or paywall needs your approval first.

## Contributing a new skill

Skills here follow the 8 layers: Trigger, Procedure, Resources, Scripts, Checks, Guard, Learn and Changelog. Before opening a PR, run each skill through a test card: 3 natural requests plus 1 near-miss request. Whenever a real run teaches you something, add a line to that skill's `references/lessons.md` and a changelog line at the bottom of its `SKILL.md`.
