# Lessons from past runs (Koray Gübür 2026-11-03, Nathan Gotch 2026-11-03, ad-creation 2026-11-05)

Read the section for the step you are on. Add a dated line when a run teaches something new.

## YouTube
- **Transcripts come only from the browser.** Use `tools/yt_transcript.mjs` (the "Show transcript" panel in ego-browser).
  - yt-dlp subtitles return 429.
  - `youtube-transcript-api` does not run on Python 3.15.
  - Calling innertube directly counts as bot-check circumvention, so it is forbidden.
- **The transcript panel has two DOM variants**, and the script handles both:
  - classic: `ytd-transcript-segment-renderer`
  - modern: `transcript-segment-view-model`
  
  If many videos fail with "no segments", look for a third variant before retrying.
- **Videos without a transcript** are often short trailers. Leave them in `_transcript_fail.txt` with the reason.
- **Flat channel listings only give approximate dates.** Nathan's run pulled in 55 videos older than the window this way.
  - Exact dates come only from `meta`.
  - `build_md.py` filters by the exact date.
  - Move any extra transcripts you already fetched to `raw/youtube/transcripts_out_of_window/`; don't delete them.
- **Re-uploads:** the same interview appears on several channels (James Dooley / FatRank / PromoSEO). Keep one copy and put the others in `_exclude.txt`.
- **Multi-speaker videos:** record the subject's time range in config `segments`, e.g. Koray's 1:15:30–1:45:56 inside a 3-hour charity stream.
- **yt-dlp:** use concurrency ≤2 and `--js-runtimes node`. On 429, wait and rerun; `meta` resumes.
- **One IP means one yt-dlp at a time.** On 2026-11-05, four subagents each ran `meta` in parallel. YouTube then answered every metadata call with 429 / "Sign in to confirm you're not a bot". Only the lead runs `meta`, serially.

## LinkedIn (`tools/linkedin.mjs`)
- **Post time comes from the activity id:** `Number(BigInt(id) >> 22n)` ms, accurate to the minute (UTC).
  - The classic UI exposes `data-urn`.
  - The new UI needs the post menu, read from the "Embed this post" link `targetUrn=`.
- **Lazy loading:** it only fires on real `page.mouse.wheel`; `scrollBy` does nothing.
- **Posts without an id** (new UI, no menu) get the date of the previous post plus a `date_estimated` note. Nathan had 17 of these.
- **Filenames** need a uid suffix: same day plus same first line collided for 26 of Koray's 494 posts.
- **Pace:** about 80 posts per run. Stop when the user says the value is low, and record the gap in README.

## Facebook (only if the user asks; low value for Koray: short cross-posts)
- The timestamp text is obfuscated. Hover the timestamp link to get a tooltip with the full date and the real permalink.
- Anchor on `[data-ad-rendering-role="story_message"]`; `role=article` elements are comments.
- The scraper lives in `~/projects/seo/research/koray-gubur/tools/fb_profile.mjs` (not generalised).

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
- **Cloudflare-blocked sites** (Search Engine Land, adogy): fetch them in ego-browser at a human pace, one page at a time. Never bypass the block.
- **Dead or redirected blogs** (gotchseo.com → rankability.com): use Wayback snapshots and say so in the note.
- **Re-dated posts:** if an old post shows a new date, note "có dấu hiệu bị đổi ngày".
- **Short links in social posts** (lnkd.in, ktg.digital): resolve them. Following those links found new talks, articles and hidden LinkedIn Articles.

## Process
- **Lead vs subagents.** The lead owns ego-browser and Whisper. Subagents do discovery, RSS feeds and articles, following `references/worker-brief.md`, with 1–2 subjects each.
- **Waiting:** `pgrep -f "<pattern>"` inside a Bash loop matches its own shell, so the loop never ends. Wait on the task notification instead.
- **zsh:** never name a shell variable `path`, because it overwrites `PATH`.
- **Deleting:** `pkill` and `rm -rf` may be denied. Stop background work with TaskStop, and clean generated files inside the script (`clean_generated()`).
