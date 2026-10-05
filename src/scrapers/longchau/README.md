# Nhà Thuốc Long Châu Scraper Notebooks — Tầng Bronze (Data Lakehouse)

Bộ công cụ cào và đóng gói dữ liệu thô (Raw Data Ingestion) từ **Nhà Thuốc Long Châu** (`nhathuoclongchau.com.vn`) bằng **Jupyter Notebook (`.ipynb`)**, lưu trữ tại Tầng Bronze của hệ thống Data Lakehouse.

## Cấu trúc thư mục

```
Project/
├── longchau_scraper_pipeline.ipynb # [RECOMMENDED] Notebook trọn vẹn 3 bước (End-to-End)
├── bronze/
│   └── longchau/                  # [OUTPUT] Chứa các file Bronze raw JSON cào được
└── longchau_scraper/
    ├── 01_discover_urls.ipynb     # Notebook Bước 1: Khám phá URL A-Z
    ├── 02_scrape_bronze.ipynb     # Notebook Bước 2: Cào chi tiết & lưu Bronze JSON
    ├── config.py                  # Cấu hình URLs, Delays, User-Agents
    ├── url_queue_longchau.json    # Hàng đợi quản lý trạng thái (Resume-Safe)
    ├── requirements.txt           # Thư viện phụ thuộc Python
    └── README.md                  # Hướng dẫn sử dụng
```

## Hướng dẫn sử dụng

### 1. Cài đặt phụ thuộc
```bash
pip install -r longchau_scraper/requirements.txt
```

### 2. Chạy Notebook Pipeline Tổng Hợp (`longchau_scraper_pipeline.ipynb`)
Mở file `longchau_scraper_pipeline.ipynb` và chạy từng cell:
1. **Cell 1 & 2**: Khởi tạo cấu hình và thiết lập thư mục.
2. **Cell 3 & 4**: Chạy `discover_urls()` để quét toàn bộ danh mục sản phẩm tra cứu A-Z (`/thuoc/tra-cuu-thuoc-a-z`).
3. **Cell 5 & 6**: Chạy `scrape_bronze()` cào dữ liệu chi tiết sản phẩm và đóng gói file JSON thô chuẩn Tầng Bronze vào `bronze/longchau/`.
4. **Cell 7 & 8**: Kiểm tra mẫu file Bronze JSON thu được.

## Chuẩn Dữ Liệu Đầu Ra (Bronze Layer Standard)

Mỗi file tại `bronze/longchau/<sku>_<slug>_<hash>.json` chứa:
- `source_name`: `"Nhà Thuốc Long Châu"`
- `trust_score`: `0.75`
- `source_url`: URL gốc sản phẩm
- `ingestion_timestamp`: Thời gian cào (ISO 8601 UTC)
- `file_hash`: Mã băm SHA-256 của nội dung raw JSON
- `lineage_hash`: Mã băm truy vết lineage
- `raw_data`: Toàn bộ `pageProps` nguyên bản từ Next.js SSR của Long Châu (`product`, `breadcrumbs`, `faq`, `content`...)
