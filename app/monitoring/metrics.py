from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Metrics Definitions
TELEGRAM_REQUESTS = Counter(
    'telegram_requests_total',
    'Total Telegram requests received',
    ['update_type']
)

JOIN_REQUESTS = Counter(
    'join_requests_total',
    'Total join requests processed',
    ['chat_id', 'status']
)

APPROVALS = Counter(
    'approvals_total',
    'Total join requests approved',
    ['chat_id', 'result']
)

WELCOME_MESSAGES = Counter(
    'welcome_messages_total',
    'Total welcome messages sent',
    ['result']
)

BROADCAST_MESSAGES = Counter(
    'broadcast_messages_total',
    'Total broadcast messages processed',
    ['result']
)

BROADCAST_QUEUE_DEPTH = Gauge(
    'broadcast_queue_depth',
    'Current number of pending broadcasts'
)

HANDLER_PROCESSING_SECONDS = Histogram(
    'handler_processing_seconds',
    'Time spent processing updates',
    ['handler']
)

APPROVAL_DELAY_SECONDS = Histogram(
    'approval_delay_seconds',
    'Time taken from request to approval'
)

class MetricsCollector:
    @staticmethod
    def inc_telegram_request(update_type: str):
        TELEGRAM_REQUESTS.labels(update_type=update_type).inc()
        
    @staticmethod
    def inc_join_request(chat_id: int, status: str):
        JOIN_REQUESTS.labels(chat_id=str(chat_id), status=status).inc()
        
    @staticmethod
    def inc_approval(chat_id: int, result: str):
        APPROVALS.labels(chat_id=str(chat_id), result=result).inc()
        
    @staticmethod
    def inc_welcome_message(result: str):
        WELCOME_MESSAGES.labels(result=result).inc()
        
    @staticmethod
    def inc_broadcast_message(result: str):
        BROADCAST_MESSAGES.labels(result=result).inc()
        
    @staticmethod
    def set_broadcast_queue_depth(depth: int):
        BROADCAST_QUEUE_DEPTH.set(depth)

def start_metrics_server(port: int = 9090):
    start_http_server(port)
