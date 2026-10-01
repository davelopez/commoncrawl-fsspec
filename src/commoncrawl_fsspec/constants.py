"""Constants for Common Crawl fsspec plugin."""

# URLs
DATA_BASE_URL = "https://data.commoncrawl.org"
INDEX_BASE_URL = "https://index.commoncrawl.org"
COLLINFO_URL = "https://index.commoncrawl.org/collinfo.json"

# Defaults
DEFAULT_CACHE_TTL = 86400  # 24 hours in seconds
DEFAULT_REQUEST_TIMEOUT = 30  # seconds
DEFAULT_USER_AGENT = "commoncrawl-fsspec/0.1.0"

# Legacy ARC-format crawls listed in collinfo.json but without browsable data
# (no *.paths.gz manifests) on data.commoncrawl.org. See issue #4.
# Common Crawl says it is improving access to these: remove an ID once
# https://data.commoncrawl.org/crawl-data/<ID>/warc.paths.gz returns 200.
LEGACY_CRAWL_IDS = frozenset({"CC-MAIN-2008-2009", "CC-MAIN-2009-2010", "CC-MAIN-2012"})
