# Nathan Gotch — Raw corpus (SEO / AI SEO / GEO)

Mục tiêu: gom **mọi thứ Nathan Gotch nói/viết** trong 2 năm (**2024-11-03 → 2026-11-03**). Đây là **raw data**, chưa phân tích.
Thu thập ngày 2026-11-03. Bảng tổng theo ngày: [`INDEX.md`](INDEX.md).

Nathan: founder Gotch SEO / Gotch SEO Academy, co-founder & CEO **Rankability** (SaaS). gotchseo.com hiện đã 301 sang rankability.com.

## Tổng quan

| Nguồn | Số lượng | Khoảng thời gian | Ghi chú |
|---|---|---|---|
| YouTube (transcript) | **119 video** (95 kênh @nathangotch + 24 lần làm khách) | 2024-11-11 → 2026-10-28 | Transcript từ nút "Show transcript" của YouTube |
| Podcast | **45 tập**, Nathan nói ở ≥25 tập | 2024-11-13 → 2026-10-19 | Gồm show Nathan dẫn: **The AI Search Report** (Rankability, 8 tập). Tập chỉ có audio → Whisper |
| Bài viết | **17 bài** | 2024-11-14 → 2026-10-12 | gotchseo.com 9 (qua Wayback), rankability 2, nathangotch.com 2, dummies.com 2, phỏng vấn/bài về Nathan 2 |
| LinkedIn post | **327** (318 gốc + 9 repost) | 2024-11-03 → 2026-11-02 | Đủ 2 năm. 17 post ngày **ước lượng** (xem dưới) |

## Cấu trúc thư mục

```
INDEX.md                          bảng tổng theo ngày (mới → cũ)
raw/youtube/md/                   <YYYY-MM-DD>_<videoId>_<slug>.md  (description + chapters + transcript có timestamp)
raw/youtube/meta/, transcripts/   JSON gốc
raw/youtube/transcripts_out_of_window/   55 transcript video CŨ HƠN 2024-11-03 (lấy dư do ngày ước lượng của YouTube lệch; giữ lại tham khảo, không có trong INDEX)
raw/youtube/_skipped.md           video trong kỳ nhưng không lấy (Shorts, re-upload trùng, review của người khác…)
raw/podcasts/<show>/              <YYYY-MM-DD>_<slug>.md   + _needs_transcription.md, _other_appearances.md
raw/articles/<source>/            toàn văn  + _INDEX.md (gồm danh sách không lấy được)
raw/social/linkedin/md/<YYYY-MM>/ mỗi post 1 file; posts.jsonl = dữ liệu gốc
tools/                            script thu thập (giống bộ của Koray, đã đổi cấu hình)
```

Front matter mỗi file có `date` + `url`, cộng các trường lọc: `nathan_role` (YouTube: `own channel`/`guest/featured`; bài viết: `author`/`interviewee`/`quoted`/`about`), `nathan_speaks` (podcast: yes/no/unknown), `is_repost`, `date_estimated` (LinkedIn).

## Ngày tháng

- YouTube: `upload_date` chính xác từ metadata.
- Podcast: `pubDate` RSS.
- LinkedIn: từ activity ID (chính xác tới phút, UTC). **17 post** LinkedIn hiển thị giao diện mới không lộ ID → ngày **ước lượng** bằng post liền trước trong feed (trường `date_estimated`), sai số vài ngày.
- Bài gotchseo.com: lấy qua Wayback Machine vì site đã redirect. 2 bài (301-redirects-seo, google-biased) có dấu hiệu **bị đổi ngày** (snapshot cũ ghi 2024-01-17, nay ghi 2025) — đã note trong file.

## Lưu ý chất lượng

1. Transcript YouTube phần lớn là auto-caption (một số video Nathan upload phụ đề English US — chính xác hơn). Không có nhãn người nói.
2. Trùng lặp: chuỗi phỏng vấn **James Dooley** (AI visibility trackers, agentic website builders, AI employees, multi-agent, search everywhere optimization…) có ở cả YouTube lẫn podcast FatRank / James Dooley Podcast / AI SEO & Business Automation; YouTube đã chỉ giữ 1 bản mỗi buổi.
3. Phần lớn video kênh Nathan là nội dung hướng dẫn + quảng bá Rankability/Search OS; khi phân tích nên tách phần pitch sản phẩm.

## Chỗ còn thiếu

| Thiếu | Lý do |
|---|---|
| X / Twitter (@nathangotch), Facebook | Chưa thu thập (với Koray, Facebook giá trị thấp) |
| Newsletter "The Search Plays" (Kit) | Không có archive công khai |
| ~20 bài cũ gotchseo.com | Wayback không có snapshot |
| Blog rankability.com (186 bài byline "Rankability") | Không ghi tác giả Nathan → không lấy |
| Webinar 2026-09-22 | Không tìm thấy bản ghi |
| YouTube Shorts | Bỏ qua (danh sách trong `_skipped.md`) |

## Tools

Giống `../koray-gubur/tools/` (xem README bên đó). `build_md.py` gộp JSON → markdown + INDEX; `transcribe.py` chạy Whisper local; `.mjs` chạy qua `ego-browser nodejs < tools/<file>.mjs`.
