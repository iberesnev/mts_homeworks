LOG_LEVEL = "DEBUG"

BOT_NAME = "wiki"
SPIDER_MODULES = ["wiki.spiders"]
NEWSPIDER_MODULE = "wiki.spiders"

ROBOTSTXT_OBEY = False

DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3.0
AUTOTHROTTLE_MAX_DELAY = 8.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5

RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [403, 408, 429, 500, 502, 503, 504]

# скрываюсь как могу... (если бы меня забанили, я бы точно купил бы проксей побольше, но всё работает и так:) )
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
}

DOWNLOADER_MIDDLEWARES = {
    "wiki.middlewares.SlotPolicyAndBackoffMiddleware": 560,
}