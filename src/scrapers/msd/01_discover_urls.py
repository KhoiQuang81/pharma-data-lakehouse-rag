"""
BƯỚC 1: DISCOVERY & MAPPING
Duyệt cây URL của MSD Manuals (phiên bản tiếng Việt / chuyên gia)
và lưu vào url_queue.json để các bước sau xử lý.

Chạy: python 01_discover_urls.py
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from pathlib import Path
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL   = "https://www.msdmanuals.com"
START_URLS = [
    "/vi/chuyen-gia",   # Trang chủ chuyên gia tiếng Việt
]
QUEUE_FILE = Path("url_queue.json")
DELAY_RANGE = (2.0, 5.0)  # Polite: đợi 2-5 giây
HEADERS = {
    "User-Agent": "MRAG-Medical-Research-Bot/1.0 (Academic Project - HUTECH CNTT - contact: research@edu.vn)",
    "Accept-Language": "vi-VN,vi;q=0.9",
}

# ── Load / Init queue ─────────────────────────────────────────────────────────
def load_queue() -> dict:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return {"pending": [], "done": [], "failed": [], "discovered_at": str(datetime.now())}

def save_queue(q: dict):
    QUEUE_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [queue] pending={len(q['pending'])}  done={len(q['done'])}  failed={len(q['failed'])}")

# ── Fetch helpers ─────────────────────────────────────────────────────────────
def fetch(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [FAIL] {url} -> {e}")
        return None

def polite_sleep():
    t = random.uniform(*DELAY_RANGE)
    time.sleep(t)

# ── Extract all article links from a category page ────────────────────────────
def extract_article_links(soup: BeautifulSoup, base: str) -> list[str]:
    links = set()
    # MSD dùng các link dạng /vi/chuyen-gia/<chuyen-khoa>/<chu-de>
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Chỉ lấy link nội bộ tiếng Việt chuyên gia
        if href.startswith("/vi/chuyen-gia/") and href.count("/") >= 4:
            links.add(BASE_URL + href.split("#")[0])  # bỏ anchor
    return list(links)

# ── Extract category links (Level 1 & 2) ─────────────────────────────────────
def extract_category_links(soup: BeautifulSoup) -> list[str]:
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/vi/chuyen-gia/") and href.count("/") == 3:
            links.add(BASE_URL + href)
    return list(links)

# ── Main Discovery ────────────────────────────────────────────────────────────
def main():
    q = load_queue()
    visited_cats = set(q["done"] + q["failed"])

    # Seed
    for path in START_URLS:
        url = BASE_URL + path
        if url not in visited_cats:
            print(f"\n[L1] Khám phá chuyên khoa từ: {url}")
            soup = fetch(url)
            if soup:
                cat_links = extract_category_links(soup)
                print(f"     -> Tìm thấy {len(cat_links)} chuyên khoa")

                for cat_url in cat_links:
                    if cat_url not in visited_cats:
                        polite_sleep()
                        print(f"  [L2] Duyệt chuyên khoa: {cat_url}")
                        cat_soup = fetch(cat_url)
                        if cat_soup:
                            article_links = extract_article_links(cat_soup, BASE_URL)
                            new_links = [l for l in article_links
                                         if l not in q["pending"] and l not in q["done"]]
                            q["pending"].extend(new_links)
                            print(f"       -> +{len(new_links)} bài mới (tổng pending: {len(q['pending'])})")
                            save_queue(q)
                        else:
                            q["failed"].append(cat_url)
                            save_queue(q)

    print(f"\n[DONE] Tổng URL đã phát hiện: {len(q['pending'])} bài cần cào")
    save_queue(q)

if __name__ == "__main__":
    main()
