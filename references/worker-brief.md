# Worker brief: collect raw data for one or two subjects

Project: <PROJECT_DIR>. Research topic: <TOPIC>. The lead fills in both placeholders when spawning you.

Goal: collect everything the subject said or published in the window given by `since` → `until` in `<PROJECT_DIR>/project.json`. This is RAW data; do not analyse it. Each file's front matter must carry an accurate `date`.

Before starting, read the YouTube, Podcasts and Articles sections of `<SKILL_DIR>/references/lessons.md`.

## Tools (read them first; all live in tools/, Python is .venv/bin/python)
- `common.py`: date window from `project.json`, plus `<subject>/config.json`. Its docstring describes the config fields.
- `yt_discover.py <subject> channel|search|meta|queue`
  - Run **only `channel` and `search`**. **Never run `meta`**: parallel workers on one IP get YouTube to answer 429 / "Sign in to confirm you're not a bot". The lead runs `meta` + `queue` for all subjects serially afterwards.
  - Put extra video ids (guest appearances you verified, talks re-hosted on YouTube) into `raw/youtube/_extra.txt`, one id per line; `# comments` are OK.
  - To judge candidates without `meta`, read titles and channels in `_candidates.txt` / `_channel_videos.txt`.
  - **Do NOT fetch YouTube transcripts and do NOT use ego-browser/playwriter.** The lead agent fetches transcripts in the user's browser afterwards.
- `podcasts.py <subject> discover|collect`
  - discover searches iTunes.
  - Save each relevant RSS feed as `raw/podcasts/feeds/<show-slug>.xml` (curl is fine), then run collect.
- `pod_tag.py <subject>` tags whether the subject speaks.
- `transcribe.py`: Whisper. **Do not run it.** The lead runs it centrally because it is CPU heavy. Just leave the placeholder `(no transcript in feed)` and the `audio:` URL.
- `articles_common.py` (env `SUBJECT=<subject path from project.json>`): `html_to_md`, `write(item, body_md, kind=...)`.
  - kind is `"articles"` (blog posts, newsletters, interviews), `"web"` (official guides/reports/help pages) or `"talks"` (webinars/conference talks not on YouTube).
  - For a talk whose video is only on another host (Wistia, Vimeo, the vendor's site), write the description/notes plus the placeholder `(no transcript in feed)` and set `item["audio"]` to a URL that yt-dlp or direct download can fetch. If the page already shows a transcript, include it instead.
  - Write your collector as `tools/articles_<slug>.py` (or several), so it can be rerun.
- `build_md.py <subject>` builds `INDEX.md` for the subject. Run it at the end.

## Steps per subject
1. **Identify sources.** Find:
   - own YouTube channel id(s)
   - LinkedIn profile URL, as `https://www.linkedin.com/in/<handle>/recent-activity/all/` (company page for orgs only if no person)
   - own podcast/show, blog, newsletter archive (Substack/beehiiv/Kit), course/free resources
   - talks on industry libraries (e.g. Motion library, Foreplay), conference talks, guest podcasts, guest YouTube interviews
   - X/TikTok/Instagram handles (only note them)
   
   Use WebSearch/WebFetch, the iTunes API, and yt-dlp.
2. **Fill config.json:** own_channels, own_filter (only if the own channel is mostly off-topic), yt_queries (~8–15), pod_terms, hosted_shows, linkedin_feed.
3. **YouTube:** run channel → search only. From the titles/channels, add verified guest appearances to `_extra.txt`; the subject must actually appear or speak. Add obvious false positives to `raw/youtube/_exclude.txt`, one id per line with a reason. The lead runs meta → queue later.
4. **Podcasts:** discover, save feeds, collect, pod_tag. Prefer feeds with `<podcast:transcript>`. If a show page has a published transcript, put it in the episode file.
5. **Articles / web / talks:** collect full text. Dates must come from the page (meta/JSON-LD/visible date); if a date is approximate, add `date_type: approximate` and a note.
6. **Write `<subject>/NOTES.md`** in Vietnamese with English terms. Include:
   - every source found, as a table with counts per source
   - what was collected
   - gaps and why
   - a section **"Cần lead làm (browser)"** listing URLs that are blocked for scripts (Cloudflare/403/login) or that need the browser, with what is there.

## Rules
- Never circumvent bot protection (no Cloudflare bypass, no rotating UAs to dodge blocks, no innertube tricks). If blocked, list it in NOTES.md.
- Nothing behind a login or paywall. Free lead-magnet PDFs that need an email: just list them.
- Be polite to servers (≈1 req/s).
- Stay inside your subject folders (plus your own `tools/articles_<slug>*.py`). Don't edit the shared tools; if one has a bug, describe it in your final report.
- Final report (short): counts per source type, the number of YouTube candidates plus `_extra` ids, the podcasts needing Whisper, and the "Cần lead làm" list.
