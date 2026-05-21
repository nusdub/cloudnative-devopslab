from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
ORDER_CREATED = Counter(
    "orders_created_total",
    "Total number of created demo orders",
    ["region"],
)
APP_INFO = Gauge(
    "app_info",
    "Application metadata exposed as labels",
    ["name", "version", "env"],
)
APP_BUILD_INFO = Gauge(
    "app_build_info",
    "Build provenance metadata exposed as labels",
    ["git_sha", "image_digest"],
)
FAULT_MODE = Gauge(
    "fault_mode_enabled",
    "Whether fault mode is enabled",
)
