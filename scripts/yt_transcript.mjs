// Fetch YouTube transcripts through ego-browser (the user's real browser), using the
// "Show transcript" panel. Walks every subject's raw/youtube/_queue.txt (project.json subjects),
// skips ids already done or failed. Resumable; run repeatedly until "remaining 0".
// Usage: ego-browser nodejs < tools/yt_transcript.mjs
const BASE = "__PROJECT_DIR__"; // filled in by init_project.py
const BATCH = 40;

const fs = await import("node:fs/promises");
const PROJECT = JSON.parse(await fs.readFile(`${BASE}/project.json`, "utf8"));
const lines = async (f) => (await fs.readFile(f, "utf8").catch(() => "")).split("\n").filter(Boolean);

const jobs = [];
let remaining = 0;
for (const subject of PROJECT.subjects) {
  const yt = `${BASE}/${subject}/raw/youtube`;
  const out = `${yt}/transcripts`;
  const queue = await lines(`${yt}/_queue.txt`);
  if (!queue.length) continue;
  await fs.mkdir(out, { recursive: true });
  const done = new Set((await fs.readdir(out)).map((f) => f.replace(".json", "")));
  const failed = new Set((await lines(`${yt}/_transcript_fail.txt`)).map((l) => l.split("|")[0]));
  for (const id of queue) {
    if (done.has(id) || failed.has(id)) continue;
    if (jobs.length < BATCH) jobs.push({ id, OUT: out, FAIL: `${yt}/_transcript_fail.txt` });
    else remaining++;
  }
}

const task = await taskSpace("expert-corpus");
const page = task.page("p1");
let ok = 0;

for (const { id, OUT, FAIL } of jobs) {
  try {
    await page.goto(`https://www.youtube.com/watch?v=${id}`, { timeout: 45000 }).catch(() => {});
    await page.waitForSelector("ytd-watch-metadata", { timeout: 20000 });
    // Pause playback so audio does not run while we read.
    await page.evaluate(() => document.querySelector("video")?.pause());
    const hasBtn = await page
      .waitForSelector("ytd-video-description-transcript-section-renderer button", { state: "attached", timeout: 8000 })
      .then(() => true, () => false);
    if (!hasBtn) throw new Error("no transcript button");
    await page.evaluate(() => document.querySelector("ytd-video-description-transcript-section-renderer button").click());
    // Classic panel uses ytd-transcript-segment-renderer; the newer "modern transcript view"
    // uses transcript-segment-view-model.
    const SEG = "ytd-transcript-segment-renderer, transcript-segment-view-model";
    await page.waitForSelector(SEG, { state: "attached", timeout: 60000 });
    // Wait until the segment count stops growing.
    let prev = -1;
    for (let i = 0; i < 10; i++) {
      const n = await page.evaluate((SEG) => document.querySelectorAll(SEG).length, SEG);
      if (n === prev) break;
      prev = n;
      await page.waitForTimeout(700);
    }
    const data = await page.evaluate(() => {
      const classic = [...document.querySelectorAll("ytd-transcript-segment-renderer")];
      if (classic.length)
        return {
          language: document.querySelector("ytd-transcript-footer-renderer")?.innerText.trim() || null,
          segments: classic.map((s) => ({
            t: s.querySelector(".segment-timestamp")?.innerText.trim(),
            text: s.querySelector(".segment-text")?.innerText.trim(),
          })),
        };
      const panel = document.querySelector('[target-id="PAmodern_transcript_view"]');
      return {
        language: panel?.innerText.match(/^.*(English|auto-generated).*$/m)?.[0].trim() || "unknown (modern transcript view)",
        segments: [...document.querySelectorAll("transcript-segment-view-model")].map((s) => ({
          t: s.querySelector(".ytwTranscriptSegmentViewModelTimestamp")?.innerText.trim(),
          text: s.querySelector("span[role='text']")?.innerText.trim(),
        })),
      };
    });
    if (!data.segments.length) throw new Error("empty transcript");
    await fs.writeFile(`${OUT}/${id}.json`, JSON.stringify({ id, fetched_at: new Date().toISOString(), ...data }));
    ok++;
    console.log(`ok ${id} ${data.segments.length} segs ${data.language}`);
  } catch (e) {
    await fs.appendFile(FAIL, `${id}|${String(e.message).split("\n")[0]}\n`);
    console.log(`FAIL ${id} ${e.message.split("\n")[0]}`);
  }
}

console.log(`batch done: ${ok}/${jobs.length} ok, remaining ${remaining}`);
