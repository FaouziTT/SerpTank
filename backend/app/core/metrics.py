
from prometheus_client import Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path

        start_time = time.time()
        response = await call_next(request)
        end_time = time.time()

        # Observe metrics
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=response.status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(end_time - start_time)

        return response

async def metrics_endpoint(request: Request):
    return Response(generate_latest(), media_type="text/plain")
