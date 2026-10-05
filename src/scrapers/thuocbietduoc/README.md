# Thuốc Biệt Dược Scraper — Tầng Bronze (Data Lakehouse)

Module cào và đóng gói dữ liệu thô (Raw Data Ingestion) từ website **Thuốc Biệt Dược** (`thuocbietduoc.com.vn`), lưu trữ tại Tầng Bronze với **độ tin cậy cao nhất (`trust_score = 1.0`)**.

## Cấu trúc thư mục

```
Project/
├── thuocbietduoc_scraper_pipeline.ipynb # [RECOMMENDED] Notebook cào Thuốc Biệt Dược
├── bronze/
│   └── thuocbietduoc/             # [OUTPUT] Chứa các file Bronze raw JSON cào được
└── thuocbietduoc_scraper/
    ├── config.py                  # Cấu hình URLs, Delays, User-Agents
    ├── url_queue_thuocbietduoc.json # Hàng đợi quản lý trạng thái (Resume-Safe)
    ├── requirements.txt           # Thư viện phụ thuộc Python
    └── README.md                  # Hướng dẫn sử dụng
```

## Hướng dẫn sử dụng

### 1. Cài đặt phụ thuộc
```bash
pip install -r thuocbietduoc_scraper/requirements.txt
```

### 2. Chạy Notebook Pipeline (`thuocbietduoc_scraper_pipeline.ipynb`)
Mở file `thuocbietduoc_scraper_pipeline.ipynb` và chạy từng cell:
1. **Cell 1 & 2**: Khởi tạo cấu hình và thiết lập môi trường.
2. **Cell 3 & 4**: Quét danh mục sản phẩm Thuốc Biệt Dược (`discover_urls()`) và lưu vào `url_queue_thuocbietduoc.json`.
3. **Cell 5 & 6**: Cào dữ liệu chi tiết sản phẩm (`scrape_bronze()`), băm SHA-256 (`file_hash`) và đóng gói 5 trường metadata Tầng Bronze vào `bronze/thuocbietduoc/`.
4. **Cell 7**: Đọc & kiểm tra chất lượng file JSON Tầng Bronze.

## Chuẩn Dữ Liệu Đầu Ra (Bronze Layer Standard)

Mỗi file tại `bronze/thuocbietduoc/<id>_<slug>_<hash>.json` chứa:
- `source_name`: `"Thuốc Biệt Dược"`
- `trust_score`: `1.0`
- `source_url`: URL gốc bài viết thuốc
- `ingestion_timestamp`: Thời gian cào (ISO 8601 UTC)
- `file_hash`: Mã băm SHA-256 nội dung dữ liệu thô
- `lineage_hash`: Mã băm truy vết lineage
- `raw_data`: Chi tiết tên thuốc, thành phần hoạt chất, chỉ định, chống chỉ định, liều dùng, tác dụng phụ, thận trọng, nhà sản xuất, số đăng ký và HTML nguyên bản.
