"""
BƯỚC 1: Quét tự động tất cả các file PDF trong thư mục data/ -> PNG images (Tối ưu siêu tốc & Bổ sung PDF mới)
Chạy: python step1_pdf_to_images.py
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import fitz  # pymupdf
import re
import json
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# ── Cấu hình ──────────────────────────────────────────────
DATA_DIR        = Path("data")
OUTPUT_DIR      = Path("data/page_images")
DPI             = 150
MIN_WHITE_RATIO = 0.98
SKIP_PAGES_FILE = Path("data/skip_pages.txt")
META_PATH       = Path("data/pages_metadata.json")
# ──────────────────────────────────────────────────────────


def sanitize_prefix(filename: str) -> str:
    name = Path(filename).stem
    clean = re.sub(r'[^a-zA-Z0-9]', '_', name)
    clean = re.sub(r'_+', '_', clean).strip('_').lower()
    return clean


def load_existing_meta() -> dict:
    """Tải metadata cũ để tái sử dụng thông tin trang đã render."""
    if META_PATH.exists():
        try:
            with open(META_PATH, encoding="utf-8") as f:
                data = json.load(f)
                return {item["image_name"]: item for item in data if "image_name" in item}
        except Exception:
            pass
    return {}


def load_skipped_pages() -> set:
    """Tải danh sách trang đã xác nhận là trang trắng/bỏ qua."""
    if SKIP_PAGES_FILE.exists():
        with open(SKIP_PAGES_FILE, encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def pdf_to_images(pdf_path: Path, prefix: str, output_dir: Path, skipped_set: set, existing_meta: dict, dpi: int = 150):
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    metadata = []
    new_skipped = []

    print(f"\n[PDF] Quét: {pdf_path.name} ({len(doc)} trang)")
    for page_num in range(len(doc)):
        img_name = f"{prefix}_page_{page_num+1:04d}.png"
        img_path = output_dir / img_name

        # 1. Đã nằm trong skip_pages.txt -> Bỏ qua (0ms)
        if img_name in skipped_set:
            continue

        # 2. File ảnh đã tồn tại trên đĩa -> Bỏ qua render, giữ metadata
        if img_path.exists():
            if img_name in existing_meta:
                metadata.append(existing_meta[img_name])
            else:
                with Image.open(img_path) as im:
                    w, h = im.size
                metadata.append({
                    "image_name": img_name,
                    "image_path": str(img_path),
                    "source_pdf": str(pdf_path),
                    "prefix": prefix,
                    "page_num": page_num + 1,
                    "width": w,
                    "height": h,
                })
            continue

        # 3. Render trang MỚI
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(str(img_path))

        with Image.open(img_path).convert("L") as img:
            hist = img.histogram()
            white_ratio = sum(hist[241:]) / (img.width * img.height)

        if white_ratio > MIN_WHITE_RATIO:
            new_skipped.append(img_name)
            skipped_set.add(img_name)
            if img_path.exists():
                img_path.unlink()
            continue

        item = {
            "image_name": img_name,
            "image_path": str(img_path),
            "source_pdf": str(pdf_path),
            "prefix": prefix,
            "page_num": page_num + 1,
            "width": pix.width,
            "height": pix.height,
        }
        metadata.append(item)
        existing_meta[img_name] = item

    doc.close()
    return metadata, new_skipped


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing_meta = load_existing_meta()
    skipped_set = load_skipped_pages()

    pdf_files = sorted(DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        print("[WARN] Không tìm thấy file PDF nào trong thư mục data/")
        return

    print(f"[INFO] Tìm thấy {len(pdf_files)} file PDF")
    all_metadata = []
    all_skipped = []

    for pdf_path in pdf_files:
        prefix = sanitize_prefix(pdf_path.name)
        metadata, skipped = pdf_to_images(pdf_path, prefix, OUTPUT_DIR, skipped_set, existing_meta, DPI)
        all_metadata.extend(metadata)
        all_skipped.extend(skipped)
        print(f"    OK: {len(metadata)} trang hợp lệ")

    # Ghi metadata và skipped pages
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, ensure_ascii=False, indent=2)

    with open(SKIP_PAGES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(skipped_set)))

    print(f"\n[DONE] Xong! Tổng ảnh hợp lệ: {len(all_metadata)}")


if __name__ == "__main__":
    main()

