"""Constants for Common Crawl fsspec plugin."""

# URLs
DATA_BASE_URL = "https://data.commoncrawl.org"
INDEX_BASE_URL = "https://index.commoncrawl.org"
COLLINFO_URL = "https://index.commoncrawl.org/collinfo.json"

# S3
S3_INDEX_PREFIX = "cc-index/table/cc-main/warc/"

# Defaults
DEFAULT_MAX_SEARCH_RESULTS = 1000
DEFAULT_CACHE_TTL = 86400  # 24 hours in seconds
DEFAULT_REQUEST_TIMEOUT = 30  # seconds
DEFAULT_USER_AGENT = "commoncrawl-fsspec/0.1.0"

# Limits
MAX_SEARCH_RESULTS = 10000
MAX_RECORD_CACHE_SIZE = 10000
