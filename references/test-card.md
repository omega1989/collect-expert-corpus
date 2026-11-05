# Test card: collect-expert-corpus

Run the trigger tests and the replay set after every change to the description, the procedure or the scripts. Write the date and the result in the changelog of SKILL.md.

## Trigger tests
Use a fresh Claude Code session each time and run each ask 3 times. The skill must load for the first three asks and stay off for the near-miss.

| # | Ask | Expect |
|---|---|---|
| 1 | "lấy hết video, podcast, bài viết của Ali Abdaal trong 2 năm qua" | loads |
| 2 | "gom data chuyên gia Brian Dean, transcript YouTube với podcast" | loads |
| 3 | "collect everything Lenny Rachitsky said about pricing since 2024" | loads |
| 4 (near-miss) | "tóm tắt video YouTube này giúp anh: <one URL>" | stays off (single video, analysis) |

## Replay set (offline, no YouTube, no browser)
`scripts/` + fixtures should reproduce these results. The cases come from the independent review on 2026-11-05.

| Case | Input | Expect |
|---|---|---|
| Python too old | `init_project.py` run with Python 3.9 | exits with "needs 3.11+" |
| Bad date | `--since 2024-11-5` | exits with "date must be YYYY-MM-DD" |
| Update tools twice | `init_project.py --update-tools` after `tools/__pycache__` exists | succeeds |
| Exclude with reason | `_exclude.txt` line `ID | reupload`, transcript exists | id absent from queue AND from INDEX |
| Broken feed | a `.xml` that is an HTML page, plus an item without pubDate | collect continues; both listed in `_collect_errors.txt` |
| Same title, other URL | two `write()` calls, same day/title/source, different URL | two files |
| Empty date | `write()` with `date=""` | AssertionError naming the rule |
| LinkedIn gap | feed set, no `_done`, README mentions LinkedIn | check 4 FAIL; with `_gap.md` → PASS |
| Transcript fail reasons | `_transcript_fail.txt` with reasons | check 3 prints counts per reason |
| January window | `--since 2025-01-20` | yt_discover APPROX_SINCE = 20241020 |

Ship when all 4 trigger rows are correct in 3 of 3 runs and every replay case matches.
