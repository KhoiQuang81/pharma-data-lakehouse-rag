import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPPER_DIR = PROJECT_ROOT / "thuocbietduoc_scraper"
BRONZE_DIR = PROJECT_ROOT / "bronze" / "thuocbietduoc"

# Ensure output directories exist
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

# Queue file path
QUEUE_FILE = SCRAPPER_DIR / "url_queue_thuocbietduoc.json"

# Thuoc Biet Duoc URLs
BASE_URL = "https://thuocbietduoc.com.vn"

# Scraping settings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

# Request delays & retries
REQUEST_DELAY_MIN = 0.5  # seconds
REQUEST_DELAY_MAX = 1.2  # seconds
MAX_RETRIES = 3
TIMEOUT_SECONDS = 15

# Metadata defaults (Data Lakehouse Standards)
SOURCE_NAME = "Thuốc Biệt Dược"
TRUST_SCORE = 1.0
