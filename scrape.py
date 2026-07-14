# -*- coding: utf-8 -*-
"""
抓取「現在宅知道」官方頻道 (@cbotaku) 的影片,統計今年鐵牛、偷米、赤鬼伯伯
的出席次數,產生 data.js 給 index.html 使用。

使用 yt-dlp 抓取,不需要任何 API 金鑰。
由 GitHub Actions 每週四自動執行;也可本機手動執行:  python scrape.py

需求:  pip install yt-dlp
"""
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

CHANNEL_URL = "https://www.youtube.com/@cbotaku/videos"
YEAR = "2026"

GUESTS = {
    "鐵牛": ["鐵牛"],
    "偷米": ["偷米"],
    "赤鬼伯伯": ["赤鬼伯伯", "赤鬼"],
}
DATE_RE = re.compile(r"(20\d{2})(\d{2})(\d{2})")
PART_RE = re.compile(r"[｜|]\s*P(\d+)\s*$", re.IGNORECASE)


def fetch_entries():
    print("正在用 yt-dlp 抓取頻道影片清單(約一兩分鐘)...")
    # 只抓最新 800 部就足以涵蓋一整年,加快執行速度
    result = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--flat-playlist",
         "--playlist-items", "1:800", "-J", CHANNEL_URL],
        capture_output=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        sys.exit("yt-dlp 執行失敗")
    data = json.loads(result.stdout.decode("utf-8", "replace"))
    return data.get("entries") or []


def build(entries):
    by_date = {}
    for e in entries:
        title = (e.get("title") or "").strip()
        if "現在宅知道" not in title or "VOD" not in title.upper():
            continue
        m = DATE_RE.search(title)
        if not m or m.group(1) != YEAR:
            continue
        date = "".join(m.groups())
        vid = e.get("id")
        pm = PART_RE.search(title)
        part = int(pm.group(1)) if pm else 1
        by_date.setdefault(date, []).append({
            "part": part,
            "id": vid,
            "title": title,
            "url": "https://www.youtube.com/watch?v=" + vid,
            "thumb": "https://i.ytimg.com/vi/%s/hqdefault.jpg" % vid,
        })

    counts = {g: 0 for g in GUESTS}
    episodes = []
    for date in sorted(by_date, reverse=True):
        parts = sorted(by_date[date], key=lambda p: p["part"])
        all_titles = " ".join(p["title"] for p in parts)
        present = [g for g, aliases in GUESTS.items()
                   if any(a in all_titles for a in aliases)]
        for g in present:
            counts[g] += 1
        episodes.append({
            "date": date,
            "dateText": "%s/%s/%s" % (date[:4], date[4:6], date[6:]),
            "title": PART_RE.sub("", parts[0]["title"]).strip(),
            "guests": present,
            "parts": parts,
        })

    tw_now = datetime.now(timezone.utc) + timedelta(hours=8)
    return {
        "year": YEAR,
        "updated": tw_now.strftime("%Y-%m-%d %H:%M") + "(台灣時間)",
        "guests": list(GUESTS.keys()),
        "counts": counts,
        "episodes": episodes,
    }


def main():
    entries = fetch_entries()
    print("頻道影片總數:", len(entries))
    data = build(entries)
    print("%s 年集數(以日期去重):%d" % (YEAR, len(data["episodes"])))
    for g, c in data["counts"].items():
        print("  %s: %d 次" % (g, c))
    out = __file__.replace("scrape.py", "data.js")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("window.SHOW_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print("已寫入 data.js")


if __name__ == "__main__":
    main()
