# MSD Manuals Scraper — Chiến Lược Thu Thập Dữ Liệu (Đã Cải Tiến)

> Tài liệu mô tả chiến lược cào dữ liệu từ MSD Manuals phục vụ hệ thống Data Lakehouse — Multimodal RAG Dược phẩm.
> Phiên bản này khắc phục 3 điểm yếu: **MinIO Storage**, **NER chất lượng**, **Data Quality Validation**.

---

## Cấu Trúc Thư Mục (Cập Nhật)

```
msd_scraper/
├── 01_discover_urls.py        # Lập bản đồ URL từ Sitemap XML (2,607 URLs)
├── 02_scrape_articles.py      # Cào nội dung → Bronze Layer
├── 03_silver_processing.py    # NER + Graph Edge Detection + Table→PNG
├── 04_data_quality.py         # ⭐ MỚI: Kiểm tra chất lượng dữ liệu Silver
├── 05_gold_export.py          # Export chunks.jsonl + graph_edges.json
├── 06_upload_to_minio.py      # ⭐ MỚI: Đẩy Bronze/Silver/Gold lên MinIO
├── requirements.txt
├── url_queue.json             # Trạng thái cào (resume-safe)
├── bronze/                    # Raw JSON nguyên bản (local cache)
├── silver/                    # Đã làm sạch + NER + graph edges
│   └── table_images/          # Ảnh PNG các bảng HTML
└── gold/
    ├── chunks.jsonl            # → Qdrant (text vector)
    ├── graph_edges.json        # → Neo4j Knowledge Graph
    └── colpali_table_pairs.jsonl  # → Train ColPali (query, image)
```

---

## Luồng Dữ Liệu Trong Lakehouse (Cập Nhật)

```
MSD Manuals (VI - /vi/professional/)
     │  Sitemap XML: 2,607 bài viết chuyên gia
     ▼
01_discover_urls.py → url_queue.json (pending / done / failed)
     │  Polite Scraping: delay 2-5s, User-Agent minh bạch, robots.txt OK
     ▼
02_scrape_articles.py
     │  • Metadata: title, last_updated, url, scraped_at
     │  • Context-Aware Blocks: heading_path + content (giữ ngữ cảnh cha)
     │  • Bảng: Markdown table + HTML gốc
     ▼
bronze/*.json  (BRONZE LAYER — Local Cache)
     │  file_hash gán sẵn để phát hiện trùng lặp
     ▼
03_silver_processing.py
     │  • NER 3 tầng (xem chi tiết bên dưới)
     │  • Table → PNG (html2image)
     │  • Graph Edge Detection từ heading context
     ▼
silver/*.json  (SILVER LAYER — Local Cache)
     │
     ▼
04_data_quality.py  ⭐ MỚI
     │  • Kiểm tra 100% chunk có source_url, trust_score
     │  • Kiểm tra chunk_length > 50 ký tự
     │  • Báo cáo tỷ lệ lỗi, dừng nếu vượt ngưỡng
     ▼
05_gold_export.py
     │  • chunks.jsonl           → Qdrant.upsert()
     │  • graph_edges.json       → Neo4j / NetworkX
     │  • colpali_table_pairs.jsonl → Train ColPali
     ▼
06_upload_to_minio.py  ⭐ MỚI
     │  • bronze/ → s3://medallion/bronze/msd/{date}/
     │  • silver/ → s3://medallion/silver/msd/{date}/
     │  • gold/   → s3://medallion/gold/msd/{date}/
     ▼
MinIO Object Storage  (LAKEHOUSE THẬT)
```

---

## Cách Chạy

```bash
# 0. Cài thư viện
pip install -r requirements.txt

# 1. Khám phá URL từ Sitemap (nhanh, ~30 giây)
python 01_discover_urls.py
# → Tạo url_queue.json với 2,607 URLs

# 2. Cào nội dung (Resume-safe: dừng/chạy lại bất kỳ lúc nào)
python 02_scrape_articles.py --batch 500
# → Mỗi lần chạy cào thêm 500 bài, tự động bỏ qua bài đã cào

# 3. Silver Processing (NER + Graph + Table→PNG)
python 03_silver_processing.py

# 4. Kiểm tra chất lượng dữ liệu ⭐ MỚI
python 04_data_quality.py
# → In báo cáo chất lượng, fail nếu chunk rỗng > 1%

# 5. Xuất Gold Layer
python 05_gold_export.py

# 6. Upload lên MinIO ⭐ MỚI
python 06_upload_to_minio.py
# → Yêu cầu MinIO đang chạy (docker-compose up minio)
```

---

## Khắc Phục Chi Tiết 4 Điểm Yếu

### ⭐ Khắc Phục 1: Lưu Trữ MinIO (Thay Local Folder)

**Vấn đề cũ:** Bronze/Silver/Gold chỉ lưu ở thư mục local → Không phải Lakehouse thật.

**Giải pháp:** Script `06_upload_to_minio.py` đẩy toàn bộ file lên MinIO sau khi pipeline chạy xong. Cấu trúc bucket:

```
s3://medallion/
├── bronze/
│   └── msd/2026-09-05/
│       └── _vi_professional_tim-mach_...json
├── silver/
│   └── msd/2026-09-05/
│       └── _vi_professional_tim-mach_...json
└── gold/
    └── msd/2026-09-05/
        ├── chunks.jsonl
        ├── graph_edges.json
        └── colpali_table_pairs.jsonl
```

Metadata MinIO object:
```json
{
  "x-amz-meta-source": "msd_manuals",
  "x-amz-meta-trust-score": "0.95",
  "x-amz-meta-ingestion-date": "2026-09-05",
  "x-amz-meta-file-hash": "sha256:abc123..."
}
```

---

### ⭐ Khắc Phục 2: NER 3 Tầng (Thay Regex Cứng)

**Vấn đề cũ:** `DRUG_RE = re.compile(r"\b(Warfarin|Aspirin...)\b")` → Danh sách cứng, bỏ sót hàng nghìn thuốc, gây lỗi `source: "UNKNOWN"`.

**Giải pháp mới — NER 3 tầng theo thứ tự ưu tiên:**

```
Tầng 1: Regex Whitelist (nhanh, chính xác cao)
  → Khớp các tên thuốc đã biết trong từ điển (Warfarin, Aspirin, ...)
  → Ưu tiên cao nhất vì độ chính xác tuyệt đối

Tầng 2: Title-as-Source Fallback (mới thêm)
  → Nếu Tầng 1 không tìm thấy drug trong Title bài viết
  → Lấy LUÔN Title bài làm source (VD: "Rau đắng biển" → source = "Rau đắng biển")
  → Giải quyết hoàn toàn lỗi UNKNOWN

Tầng 3: DrugBank Dictionary Lookup (bổ sung sau)
  → Load danh sách ~13,000 tên thuốc từ DrugBank API
  → Fuzzy match để bắt các biến thể tên thuốc
```

**So sánh kết quả:**

| Trường hợp | NER cũ | NER mới (3 tầng) |
|-----------|--------|-----------------|
| Bài "Tetracyclines" | `source: "UNKNOWN"` | `source: "Tetracyclines"` |
| Bài "Rau đắng biển" | `source: "UNKNOWN"` | `source: "Rau đắng biển"` |
| Bài "Warfarin" | `source: "Warfarin"` ✅ | `source: "Warfarin"` ✅ |

---

### ⭐ Khắc Phục 3: Data Quality Validation (Script Mới)

**Vấn đề cũ:** Không có bước kiểm tra → Dữ liệu xấu lọt vào Qdrant/Neo4j.

**Script `04_data_quality.py` kiểm tra:**

```python
RULES = {
    "source_url_not_null":    "100% chunk phải có source_url",
    "trust_score_not_null":   "100% chunk phải có trust_score",
    "content_length_min_50":  "< 1% chunk có content < 50 ký tự",
    "chunk_id_unique":        "Không được có chunk_id trùng lặp",
    "context_path_not_empty": "> 90% chunk phải có context_path",
}
```

**Báo cáo mẫu:**
```
=== DATA QUALITY REPORT — Silver Layer ===
Total chunks: 5,505
✅ source_url_not_null:    5505/5505 (100.0%) — PASS
✅ trust_score_not_null:   5505/5505 (100.0%) — PASS
✅ content_length_min_50:  5450/5505 (99.0%)  — PASS (threshold: 99%)
✅ chunk_id_unique:        5505/5505 (100.0%) — PASS
⚠️ context_path_not_empty: 4954/5505 (90.0%) — WARN
Pipeline: PASS — Tiến hành Gold Export
```

---

### ⭐ Khắc Phục 4: ColPali Training Data Thực Tế

**Vấn đề cũ:** `colpali_table_pairs.jsonl` sinh từ HTML table → Ít, không đại diện.

**Chiến lược mới — 2 nguồn ColPali data:**

| Nguồn | Loại ảnh | Chất lượng | Script xử lý |
|-------|---------|------------|-------------|
| **Dược Thư PDF (ưu tiên)** | Ảnh trang sách scan thật | ⭐⭐⭐ Cao nhất | `pdf_to_png.py` (riêng biệt) |
| **MSD HTML tables** | Ảnh render từ HTML | ⭐⭐ Trung bình | Script hiện tại |
| **PubChem** | Ảnh cấu trúc hóa học | ⭐⭐ Trung bình | `pubchem_images.py` (kế hoạch) |

> **Lưu ý:** Script `pdf_to_png.py` xử lý Dược Thư Quốc Gia sẽ được phát triển riêng trong nhánh `pdf_pipeline/`.

---

## Điểm Đặc Biệt Của Chiến Lược (Tóm Tắt)

| Tính năng | Mô tả | Trạng thái |
|-----------|-------|-----------|
| **Sitemap-based Discovery** | Lấy 2,607 URLs từ Sitemap XML chính thức | ✅ Hoàn thành |
| **Context-Aware Chunking** | Mỗi chunk biết heading cha: `"Tăng HA > Chống chỉ định"` | ✅ Hoàn thành |
| **Resume-Safe** | Dừng bất kỳ lúc nào, chạy lại tiếp tục từ chỗ dừng | ✅ Hoàn thành |
| **Polite Scraping** | Delay 2-5s ngẫu nhiên, robots.txt OK, UA minh bạch | ✅ Hoàn thành |
| **NER 3 tầng** | Regex → Title Fallback → DrugBank Dict | ✅ Tầng 1+2 / ⏳ Tầng 3 |
| **Auto Graph Edges** | Tự phát hiện quan hệ thuốc từ heading "Tương tác thuốc" | ✅ Hoàn thành |
| **Data Quality Validation** | Kiểm tra 5 quy tắc chất lượng trước khi export Gold | ⏳ Cần implement |
| **MinIO Upload** | Đẩy toàn bộ Bronze/Silver/Gold lên Object Storage | ⏳ Cần implement |
| **Incremental Update** | Chỉ cào lại bài có `last_updated` mới hơn | ⏳ Kế hoạch |

---

## Kết Quả Hiện Tại (550 bài đầu tiên)

```
Bronze files:   550 JSON files (~45MB)
Silver files:   550 JSON files (đã NER + Graph)
Gold:
  chunks.jsonl:              5,505 text chunks
  graph_edges.json:          82 quan hệ thuốc (DDI)
  colpali_table_pairs.jsonl: 12 cặp (từ HTML table)

Pending còn lại: 2,052 bài
```

> Chạy thêm `python 02_scrape_articles.py --batch 2052` để cào hết toàn bộ 2,607 bài.
