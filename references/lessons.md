# Lessons from past runs (two SEO-expert corpora 2026-11-03, an ad-creative research set 2026-11-05)

Read the section for the step you are on. Add a dated line when a run teaches something new.

## YouTube
- **Transcripts are read the way a person reads them.** Open the video in the user's browser (ego-browser) and read the "Show transcript" panel at a human pace, with 3–8 s between videos. The user must approve this first (SKILL step 3).
  - When yt-dlp subtitle downloads return 429, wait. Never work around it with tricks.
  - `youtube-transcript-api` does not run on Python 3.15.
  - Direct innertube calls count as bot-check circumvention and are forbidden.
- **The transcript panel has two DOM variants**, and the script handles both:
  - classic: `ytd-transcript-segment-renderer`
  - modern: `transcript-segment-view-model`
  
  If many videos fail with "no segments", look for a third variant before retrying.
- **Videos without a transcript** are often short trailers. Leave them in `_transcript_fail.txt` with the reason.
- **Flat channel listings only give approximate dates.** One run pulled in 55 videos older than the window this way.
  - Exact dates come only from `meta`.
  - `build_md.py` filters by the exact date.
  - Move any extra transcripts you already fetched to `raw/youtube/transcripts_out_of_window/`; don't delete them.
- **Re-uploads:** the same interview often appears on several channels. Keep one copy and put the others in `_exclude.txt`.
- **Multi-speaker videos:** record the subject's time range in config `segments`, e.g. `1:15:30–1:45:56` of a 3-hour charity stream.
- **yt-dlp:** use concurrency ≤2 and `--js-runtimes node`. On 429, wait and rerun; `meta` resumes.
- **One IP means one yt-dlp at a time.** On 2026-11-05, four subagents each ran `meta` in parallel. YouTube then answered every metadata call with 429 / "Sign in to confirm you're not a bot". Only the lead runs `meta`, serially.

## LinkedIn (`tools/linkedin.mjs`)
- **Post time comes from the activity id:** `Number(BigInt(id) >> 22n)` ms, accurate to the minute (UTC).
  - The classic UI exposes `data-urn`.
  - The new UI needs the post menu, read from the "Embed this post" link `targetUrn=`.
- **Lazy loading:** it only fires on real `page.mouse.wheel`; `scrollBy` does nothing.
- **Posts without an id** (new UI, no menu) get the date of the previous post plus a `date_estimated` note; about 5% of posts in one run.
- **Filenames** need a uid suffix: same day plus same first line collided for 26 of 494 posts in one run.
- **Pace:** about 80 posts per run. Stop when the user says the value is low, and record the gap in README.

## Facebook (not included; only if the user asks, after the same approval as LinkedIn)
- Value was low in the one run that tried it: mostly short cross-posts of LinkedIn content.
- The timestamp text is obfuscated. Hover the timestamp link to get a tooltip with the full date and the real permalink.
- Anchor on `[data-ad-rendering-role="story_message"]`; `role=article` elements are comments.

## Podcasts
- **Discovery:** use the iTunes Search API with `entity=podcastEpisode`, then save each show's RSS feed.
  - Transistor feeds carry `<podcast:transcript>`.
  - Run `pod_tag.py` after collection to tag `subject_speaks`.
  - A show the subject hosts goes in `hosted_shows`, so every episode is kept.
- **"Mentions only" episodes** (`subject_speaks: no`) stay in the corpus but are skipped by Whisper.
- **Whisper:** use whisper.cpp `whisper-cli` with `~/.cache/whisper/ggml-large-v3-turbo-q5_0.bin`.
  - It takes about 2–4 minutes per hour of audio.
  - Run one process at a time.

## Articles / web
- **Sites that block scripts** (e.g. Search Engine Land): with the user's approval, read them in ego-browser at a human pace, one page at a time. Never use bypass tools.
- **Dead or redirected blogs:** use Wayback snapshots and say so in the note.
- **Re-dated posts:** if an old post shows a new date, note "có dấu hiệu bị đổi ngày".
- **Short links in social posts** (lnkd.in and custom shorteners): resolve them. Following those links found new talks, articles and hidden LinkedIn Articles.
- **Undated pages:** `articles_common.write` refuses an empty date. Use the fetch date with `date_type: "undated (fetched …)"`.

## Process
- **Lead vs subagents.** The lead owns every YouTube call, ego-browser and Whisper. Subagents do discovery, RSS feeds and articles, following `references/worker-brief.md`, with 1–2 subjects each.
- **Waiting:** `pgrep -f "<pattern>"` inside a Bash loop matches its own shell, so the loop never ends. Wait on the task notification instead.
- **zsh:** never name a shell variable `path`, because it overwrites `PATH`.
- **Deleting:** `pkill` and `rm -rf` may be denied. Stop background work with TaskStop, and clean generated files inside the script (`clean_generated()`).
