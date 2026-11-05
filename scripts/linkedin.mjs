// Scrape LinkedIn posts through ego-browser (user's logged-in session), page "p2".
// Works on the first subject (project.json order, config.json with linkedin_feed) whose
// raw/social/linkedin/_done marker is missing; the marker is written once the feed reaches SINCE or
// stops loading (feed end). A subject whose feed loads nothing gets _gap.md (check login / URL) and is skipped;
// write _gap.md yourself to stop a feed early (the reason is reported by check_corpus).
// Exact post time comes from the activity id in the "Embed this post" menu link
// (LinkedIn ids carry a millisecond timestamp in their top 41 bits).
// Resumable: the tab stays scrolled between runs; posts are deduped by URN.
// Usage: ego-browser nodejs < tools/linkedin.mjs
const BASE = "__PROJECT_DIR__"; // filled in by init_project.py

const MAX_POSTS_PER_RUN = 80;

const fs = await import("node:fs/promises");
const PROJECT = JSON.parse(await fs.readFile(`${BASE}/project.json`, "utf8"));
const SINCE = Date.parse(`${PROJECT.since}T00:00:00Z`);
let ROOT = null, FEED = null;
for (const subject of PROJECT.subjects) {
  const cfg = JSON.parse(await fs.readFile(`${BASE}/${subject}/config.json`, "utf8").catch(() => "{}"));
  const dir = `${BASE}/${subject}`;
  const li = `${dir}/raw/social/linkedin`;
  const finished = (await fs.stat(`${li}/_done`).catch(() => null)) || (await fs.stat(`${li}/_gap.md`).catch(() => null));
  if (!ROOT && cfg.linkedin_feed && !finished) {
    ROOT = dir;
    FEED = cfg.linkedin_feed;
  }
}
if (!ROOT) {
  console.log("all LinkedIn feeds done");
  process.exit(0);
}
console.log(`subject: ${ROOT.slice(BASE.length + 1)}  feed: ${FEED}`);
const OUT_DIR = `${ROOT}/raw/social/linkedin`;
const OUT = `${OUT_DIR}/posts.jsonl`;
await fs.mkdir(OUT_DIR, { recursive: true });
const seen = new Set(
  (await fs.readFile(OUT, "utf8").catch(() => "")).split("\n").filter(Boolean).map((l) => JSON.parse(l).urn),
);

const task = await taskSpace("expert-corpus");
const page = (await task.pages()).find((p) => p.label === "p2") || (await task.newPage());
if (!(await page.url()).startsWith(FEED)) {
  await page.goto(FEED);
  await page.waitForTimeout(5000);
}

const tagUnits = () =>
  page.evaluate(() => {
    window.__kgNext ??= 0;
    const ids = [];
    // Classic UI exposes the activity urn directly; the newer UI needs the menu lookup.
    for (const u of document.querySelectorAll('[data-urn^="urn:li:activity:"]')) {
      if (u.dataset.kgLi || u.parentElement.closest('[data-urn^="urn:li:activity:"]')) continue;
      const id = String(window.__kgNext++);
      u.dataset.kgLi = id;
      u.dataset.kgUrn = u.getAttribute("data-urn");
      ids.push(id);
    }
    for (const u of document.querySelectorAll('[role="listitem"]')) {
      if (u.dataset.kgLi || !/^Feed post/.test(u.innerText)) continue;
      const id = String(window.__kgNext++);
      u.dataset.kgLi = id;
      const menu = [...u.querySelectorAll("button")].find((b) => /control menu|more actions/i.test(b.getAttribute("aria-label") || ""));
      if (menu) menu.dataset.kgMenu = id;
      ids.push(id);
    }
    return ids;
  });

const tsFromId = (id) => Number(BigInt(id) >> 22n);

// Real wheel input near the last post; LinkedIn ignores programmatic scrollBy for lazy loading.
const scrollFeed = async () => {
  await page.evaluate(() => {
    const all = document.querySelectorAll("[data-kg-li]");
    all[all.length - 1]?.scrollIntoView({ block: "end" });
    window.scrollBy(0, -400);
  });
  await page.mouse.move(600, 500);
  await page.mouse.wheel(0, 1200, { label: "scroll activity feed" });
  await page.waitForTimeout(4000);
};

let saved = 0, oldStreak = 0, idleScrolls = 0, oldest = null;
while (saved < MAX_POSTS_PER_RUN && oldStreak < 4 && idleScrolls < 6) {
  const ids = await tagUnits();
  if (!ids.length) {
    await scrollFeed();
    idleScrolls++;
    continue;
  }
  idleScrolls = 0;
  for (const id of ids) {
    let urn = await page.evaluate((id) => document.querySelector(`[data-kg-li="${id}"]`)?.dataset.kgUrn || null, id);
    const hasMenu = !urn && await page.evaluate((id) => !!document.querySelector(`[data-kg-menu="${id}"]`), id);
    if (hasMenu) {
      await page.click(`[data-kg-menu="${id}"]`, { label: "open post menu" }).catch(() => {});
      await page.waitForFunction(() => [...document.querySelectorAll("a")].some((a) => /embed-modal\/\?targetUrn=/.test(a.href)), undefined, { timeout: 4000 }).catch(() => {});
      urn = await page.evaluate(() => {
        const a = [...document.querySelectorAll("a")].find((a) => /embed-modal\/\?targetUrn=/.test(a.href));
        return a ? decodeURIComponent(a.href.split("targetUrn=")[1]).split("&")[0] : null;
      });
      await page.keyboard.press("Escape");
      await page.waitForTimeout(300);
    }
    const data = await page.evaluate(async (id) => {
      const u = document.querySelector(`[data-kg-li="${id}"]`);
      if (!u) return null;
      for (const b of u.querySelectorAll("button")) if (/^…\s*(see\s+)?more$/i.test(b.innerText.trim())) b.click();
      await new Promise((r) => setTimeout(r, 500));
      const links = [...new Set([...u.querySelectorAll("a[href]")].map((a) => a.href)
        .filter((h) => !/linkedin\.com\/(in\/|company\/|feed\/hashtag|search\/)|embed-modal|^javascript/.test(h)))];
      return {
        relative_time: [...u.querySelectorAll("span")].map((s) => s.textContent.trim()).find((t) => /^\d+(m|h|d|w|mo|yr)\b/.test(t)) || null,
        is_repost: /reposted this/i.test(u.innerText.slice(0, 300)),
        has_video: !!u.querySelector("video"),
        has_document: /document|pages\b/i.test(u.querySelector("iframe")?.title || ""),
        images: u.querySelectorAll("img[src*='media.licdn.com/dms/image']").length,
        links,
        text: u.innerText.slice(0, 30000),
      };
    }, id);
    if (!data) continue;
    const key = urn || `unit-${id}-${data.text.slice(150, 220)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const postId = urn?.match(/\d{19}/)?.[0];
    const ts = postId ? tsFromId(postId) : NaN;
    const iso = Number.isNaN(ts) ? null : new Date(ts).toISOString().slice(0, 16) + "Z";
    await fs.appendFile(OUT, JSON.stringify({
      urn: key, permalink: urn ? `https://www.linkedin.com/feed/update/${urn}/` : null, date: iso, ...data,
      scraped_at: new Date().toISOString(),
    }) + "\n");
    saved++;
    if (iso) oldest = iso;
    oldStreak = !Number.isNaN(ts) && ts < SINCE ? oldStreak + 1 : 0;
    const preview = data.text.split("\n").filter((l) => l.trim()).slice(6, 7).join(" ");
    console.log(`${iso ?? "??"} ${data.relative_time}  ${preview.slice(0, 80)}  links=${data.links.length}`);
  }
  await scrollFeed();
}
const total = (await fs.readFile(OUT, "utf8").catch(() => "")).split("\n").filter(Boolean).length;
if (oldStreak >= 4) await fs.writeFile(`${OUT_DIR}/_done`, `reached ${oldest} at ${new Date().toISOString()}\n`);
else if (idleScrolls >= 6 && total === 0)
  await fs.writeFile(`${OUT_DIR}/_gap.md`, `No posts loaded from ${FEED} (${new Date().toISOString()}): check that the user is logged in and the URL is right, then delete this file and rerun.\n`);
else if (idleScrolls >= 6 && (await fs.stat(`${OUT_DIR}/_idle_once`).catch(() => null)))
  await fs.writeFile(`${OUT_DIR}/_done`, `feed ended at ${oldest} (no more posts loaded in 2 runs) at ${new Date().toISOString()}\n`);
else if (idleScrolls >= 6) await fs.writeFile(`${OUT_DIR}/_idle_once`, `${new Date().toISOString()}\n`); // maybe just slow
else await fs.rm(`${OUT_DIR}/_idle_once`, { force: true });
console.log({ subject: ROOT.slice(BASE.length + 1), saved, oldest, reachedCutoff: oldStreak >= 4, idle: idleScrolls >= 6 });
