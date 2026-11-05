# collect-expert-corpus

An [Agent Skill](https://docs.claude.com/en/docs/claude-code/skills) for Claude Code. Give it one or more experts or organisations and a time window. It collects everything they said or published in that window and saves it as dated raw files:

- YouTube transcripts
- podcasts, with transcripts
- articles
- LinkedIn posts (optional)

Each item becomes a markdown file with its exact publish date. The skill then writes `INDEX.md` (all items sorted by date) and `README.md`, and zips everything. It does not analyse the content; that is a separate step.

To use it, just ask Claude Code, for example:

- "lấy hết video, podcast, bài viết của Ali Abdaal trong 2 năm qua"
- "gom data chuyên gia Brian Dean"
- "collect everything Lenny Rachitsky said about pricing"

**Runs on macOS only.**

## Install (about 15 minutes, once)

1. **Homebrew.** Skip if you already have it. Open Terminal and paste:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. **Tools.** The Python that ships with macOS (3.9) is too old; you need 3.11 or newer.
   ```bash
   brew install python@3.12 node ffmpeg whisper-cpp
   ```
3. **Whisper model.** About 574 MB; used to transcribe podcasts that come without a transcript.
   ```bash
   mkdir -p ~/.cache/whisper && curl -L -o ~/.cache/whisper/ggml-large-v3-turbo-q5_0.bin \
     https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin
   ```
4. **ego lite (the `ego-browser` command).** Install the ego lite app and finish its first-run onboarding. Onboarding adds the `ego-browser` command. This step is only needed for YouTube transcripts and LinkedIn.
5. **The skill.**
   ```bash
   git clone https://github.com/omega1989/collect-expert-corpus.git ~/.claude/skills/collect-expert-corpus
   ```
6. **Check.** Run:
   ```bash
   python3.12 --version && which node ffmpeg whisper-cli ego-browser && ls ~/.cache/whisper/
   ```
   It should print 4 paths and the model file name. Then restart Claude Code.

To update: `cd ~/.claude/skills/collect-expert-corpus && git pull`

## Risks: read before using

- **LinkedIn.** LinkedIn's terms forbid automated collection, and the skill runs on **your personal LinkedIn account**. LinkedIn may warn or restrict that account. The skill always asks before touching LinkedIn and only collects the subjects you approve. If you're unsure, answer "no LinkedIn".
- **YouTube transcripts.** These are read in your own browser at a human pace, 3–8 seconds per video. The skill asks before starting. If YouTube starts asking "confirm you're not a bot", the skill stops and waits; it never tries to get around it.
- **Websites.** The skill reads public pages only. It never logs in, never opens paid content, and never tries to get around blocks such as Cloudflare. Pages it cannot read are listed as gaps in the README.
- **Disk and time.** Whisper runs on your Mac: about 2–4 minutes of processing per hour of audio. A large expert can take several hours and a few GB.

## How it works

Claude follows [`SKILL.md`](SKILL.md):

1. Creates the project and adds each expert (`scripts/init_project.py`, `scripts/new_subject.py`).
2. Asks you about LinkedIn and YouTube-in-browser.
3. Sends subagents to find sources: podcasts, articles, talks. The brief they get is [`references/worker-brief.md`](references/worker-brief.md).
4. Discovers YouTube videos, one expert at a time.
5. Fetches transcripts and, if you approved it, LinkedIn posts.
6. Runs Whisper on audio that has no transcript.
7. Builds `INDEX.md` and `README.md`, then zips everything.
8. Checks 6 "done" conditions with `scripts/check_corpus.py`. Anything still missing is listed as a gap.

Lessons from past runs are in [`references/lessons.md`](references/lessons.md). The tests to run before changing the skill are in [`references/test-card.md`](references/test-card.md).

## Contributing

If a real run teaches you something new:
1. Add a line to `references/lessons.md`.
2. Add a line to the changelog at the bottom of `SKILL.md`.
3. Run `references/test-card.md`.
4. Open a PR.
