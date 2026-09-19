"""
BƯỚC 2: EXTRACTION (Semantic HTML Extraction)
Cào nội dung từng bài trong url_queue.json,
trích xuất có cấu trúc và lưu vào bronze/

Chạy: python 02_scrape_articles.py
"""
import requests
from bs4 import BeautifulSoup, Tag
import json
import time
import random
from pathlib import Path
from datetime import datetime
import re
import hashlib

# ── Config ────────────────────────────────────────────────────────────────────
QUEUE_FILE   = Path("url_queue.json")
BRONZE_DIR   = Path("bronze")          # Raw JSON lưu tại đây
DELAY_RANGE  = (2.0, 5.0)
HEADERS = {
    "User-Agent": "MRAG-Medical-Research-Bot/1.0 (Academic Project - HUTECH CNTT)",
    "Accept-Language": "vi-VN,vi;q=0.9",
}
NOISE_TAGS = ["nav", "footer", "header", "aside", "script", "style",
              "form", ".share-buttons", ".print-btn", ".ad-block"]

BRONZE_DIR.mkdir(exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def url_to_filename(url: str) -> str:
    """Biến URL thành tên file an toàn"""
    slug = re.sub(r"[^\w\-]", "_", url.replace("https://www.msdmanuals.com", ""))
    return slug[:180] + ".json"

def fetch(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [FAIL] {url}: {e}")
        return None

def polite_sleep():
    time.sleep(random.uniform(*DELAY_RANGE))

# ── Metadata extraction ───────────────────────────────────────────────────────
def extract_metadata(soup: BeautifulSoup, url: str) -> dict:
    meta = {"url": url, "scraped_at": str(datetime.now())}

    # Title
    h1 = soup.find("h1")
    meta["title"] = h1.get_text(strip=True) if h1 else ""

    # Last updated
    updated = soup.find(attrs={"class": re.compile(r"last.?updated|date", re.I)})
    meta["last_updated"] = updated.get_text(strip=True) if updated else ""

    # Authors / Reviewers
    authors = soup.find_all(attrs={"class": re.compile(r"author|reviewer|contributor", re.I)})
    meta["authors"] = [a.get_text(strip=True) for a in authors]

    # Canonical URL
    canonical = soup.find("link", rel="canonical")
    meta["canonical_url"] = canonical["href"] if canonical else url

    return meta

# ── Table → Markdown ──────────────────────────────────────────────────────────
def table_to_markdown(table: Tag) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
        rows.append("| " + " | ".join(cells) + " |")
    if rows:
        # Thêm dòng separator sau header
        cols = len(rows[0].split("|")) - 2
        rows.insert(1, "|" + " --- |" * cols)
    return "\n".join(rows)

# ── Main content extraction (Context-Aware) ────────────────────────────────────
def extract_content(soup: BeautifulSoup) -> list[dict]:
    """
    Trích xuất nội dung dạng cây ngữ nghĩa.
    Trả về danh sách các block: {heading_path, type, content}
    heading_path: [H1, H2, H3] để biết ngữ cảnh của từng đoạn.
    """
    # Xóa noise
    for sel in NOISE_TAGS:
        for el in soup.select(sel):
            el.decompose()

    article = soup.find("article") or soup.find("main") or soup.find("body")
    if not article:
        return []

    blocks = []
    heading_stack = []  # [(level, text), ...]

    for el in article.descendants:
        if not isinstance(el, Tag):
            continue

        # Headings → cập nhật ngữ cảnh
        if el.name in ["h1", "h2", "h3", "h4"]:
            level = int(el.name[1])
            text = el.get_text(strip=True)
            # Pop các heading cùng hoặc thấp hơn
            heading_stack = [(l, t) for l, t in heading_stack if l < level]
            heading_stack.append((level, text))

        # Paragraph
        elif el.name == "p" and el.parent.name not in ["td", "th", "li"]:
            text = el.get_text(" ", strip=True)
            if len(text) > 30:  # bỏ qua đoạn quá ngắn
                blocks.append({
                    "heading_path": [t for _, t in heading_stack],
                    "type": "paragraph",
                    "content": text
                })

        # Table → Markdown (ĐÂY LÀ VÀNG)
        elif el.name == "table":
            md = table_to_markdown(el)
            if md:
                blocks.append({
                    "heading_path": [t for _, t in heading_stack],
                    "type": "table_markdown",
                    "content": md,
                    "table_html": str(el)  # Lưu HTML gốc để render ảnh sau
                })

        # List items
        elif el.name == "li" and el.parent.name in ["ul", "ol"]:
            text = el.get_text(" ", strip=True)
            if len(text) > 20:
                blocks.append({
                    "heading_path": [t for _, t in heading_stack],
                    "type": "list_item",
                    "content": text
                })

        # Images
        elif el.name == "img":
            blocks.append({
                "heading_path": [t for _, t in heading_stack],
                "type": "image",
                "content": el.get("alt", ""),
                "src": el.get("src", "")
            })

    return blocks

# ── Context-Aware Chunking (Silver prep) ─────────────────────────────────────
def create_chunks(blocks: list[dict], title: str, url: str, max_tokens: int = 800) -> list[dict]:
    """
    Ghép các block thành chunk văn bản có ngữ cảnh heading đầy đủ.
    Mỗi chunk: {chunk_id, context_path, content, type, source_url}
    """
    chunks = []
    current_text = ""
    current_path = []

    def flush(path, text, chunk_type="text"):
        if text.strip():
            chunk_id = hashlib.md5((url + text[:50]).encode()).hexdigest()[:12]
            chunks.append({
                "chunk_id": chunk_id,
                "source_url": url,
                "source_title": title,
                "context_path": " > ".join(path),  # VD: "Tăng huyết áp > Chống chỉ định"
                "content": text.strip(),
                "type": chunk_type,
                "word_count": len(text.split())
            })

    for b in blocks:
        # Table: luôn là chunk riêng (giữ nguyên cấu trúc)
        if b["type"] == "table_markdown":
            flush(current_path, current_text)  # flush đoạn trước
            current_text = ""
            flush(b["heading_path"], b["content"], chunk_type="table")
            continue

        # Image: chunk riêng
        if b["type"] == "image" and b["content"]:
            flush(b["heading_path"], f"[Hình ảnh] {b['content']}", chunk_type="image")
            continue

        # Đổi ngữ cảnh heading: flush đoạn cũ
        if b["heading_path"] != current_path and current_text:
            flush(current_path, current_text)
            current_text = ""

        current_path = b["heading_path"]
        current_text += " " + b["content"]

        # Quá dài: flush và bắt đầu chunk mới
        if len(current_text.split()) > max_tokens:
            flush(current_path, current_text)
            current_text = ""

    flush(current_path, current_text)
    return chunks

# ── Main Scraping Loop ────────────────────────────────────────────────────────
def main():
    q = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    total = len(q["pending"])
    print(f"[START] {total} URL cần xử lý")

    while q["pending"]:
        url = q["pending"].pop(0)
        fname = BRONZE_DIR / url_to_filename(url)

        # Skip nếu đã có file bronze
        if fname.exists():
            print(f"  [SKIP] đã có: {fname.name}")
            q["done"].append(url)
            continue

        print(f"  [SCRAPE] {url}")
        soup = fetch(url)
        if not soup:
            q["failed"].append(url)
            json.dump(q, open(QUEUE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            polite_sleep()
            continue

        # Trích xuất
        meta    = extract_metadata(soup, url)
        blocks  = extract_content(soup)
        chunks  = create_chunks(blocks, meta["title"], url)

        # Lưu Bronze (raw + structured)
        output = {
            "metadata": meta,
            "raw_blocks": blocks,
            "chunks": chunks,      # Sẵn sàng cho Silver layer
        }
        fname.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    -> {len(chunks)} chunks, {len(blocks)} blocks | lưu: {fname.name}")

        q["done"].append(url)
        remaining = len(q["pending"])
        print(f"    -> Còn lại: {remaining}/{total}")

        # Lưu queue (resume-safe)
        QUEUE_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
        polite_sleep()

    print(f"\n[DONE] Hoàn thành! done={len(q['done'])}, failed={len(q['failed'])}")

if __name__ == "__main__":
    main()
