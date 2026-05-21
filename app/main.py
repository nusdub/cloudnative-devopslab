import asyncio
import logging
import random
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from app.config import get_settings
from app.logging_config import configure_logging
from app.metrics import APP_BUILD_INFO, APP_INFO, FAULT_MODE, ORDER_CREATED, REQUEST_COUNT, REQUEST_LATENCY
from app.tracing import configure_tracing

configure_logging()
logger = logging.getLogger("cloudnative-devopslab")

LOW_CARDINALITY_ROUTES = {
    "/": "/",
    "/healthz": "/healthz",
    "/readyz": "/readyz",
    "/api/orders": "/api/orders",
    "/api/fault": "/api/fault",
    "/api/slo": "/api/slo",
    "/api/version": "/api/version",
    "/metrics": "/metrics",
}


class OrderRequest(BaseModel):
    item: Annotated[str, Field(min_length=1, max_length=64)]
    quantity: Annotated[int, Field(ge=1, le=100)] = 1
    region: Annotated[str, Field(min_length=2, max_length=32)] = "cn-north"


class FaultRequest(BaseModel):
    enabled: bool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    APP_INFO.labels(settings.app_name, settings.app_version, settings.app_env).set(1)
    APP_BUILD_INFO.labels(settings.git_sha, settings.image_digest).set(1)
    FAULT_MODE.set(1 if settings.fault_mode else 0)
    logger.info(
        "application_started",
        extra={
            "extra": {
                "env": settings.app_env,
                "version": settings.app_version,
                "git_sha": settings.git_sha,
                "image_digest": settings.image_digest,
            }
        },
    )
    yield
    logger.info("application_stopped")


app = FastAPI(
    title="CloudNative DevOpsLab",
    description="A production-style demo service for SRE CI/CD, observability, and rollback practice.",
    version=get_settings().app_version,
    lifespan=lifespan,
)

configure_tracing(app)

_runtime_fault_mode = get_settings().fault_mode


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str):
        return path
    return LOW_CARDINALITY_ROUTES.get(request.url.path, "unknown")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    started_at = time.perf_counter()
    path = _route_template(request)
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    try:
        response = await call_next(request)
    except Exception:
        REQUEST_COUNT.labels(request.method, path, "500").inc()
        REQUEST_LATENCY.labels(request.method, path).observe(time.perf_counter() - started_at)
        logger.exception(
            "request_failed",
            extra={"extra": {"path": path, "method": request.method, "request_id": request_id}},
        )
        raise

    latency_seconds = time.perf_counter() - started_at
    REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(latency_seconds)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        extra={
            "extra": {
                "path": path,
                "method": request.method,
                "status": response.status_code,
                "latency_ms": round(latency_seconds * 1000, 2),
                "request_id": request_id,
            }
        },
    )
    return response


@app.get("/")
async def root() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "purpose": "sre-cicd-observability-lab",
    }


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    settings = get_settings()
    if not settings.readiness_enabled or _runtime_fault_mode:
        raise HTTPException(status_code=503, detail="service is not ready")
    return {"status": "ready"}


@app.get("/api/version")
async def version() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "git_sha": settings.git_sha,
        "image_digest": settings.image_digest,
    }


@app.post("/api/orders", status_code=201)
async def create_order(order: OrderRequest) -> JSONResponse:
    settings = get_settings()
    if settings.slow_request_ms > 0:
        await asyncio.sleep(settings.slow_request_ms / 1000)
    if _runtime_fault_mode:
        raise HTTPException(status_code=500, detail="fault mode is enabled")

    order_id = f"ord-{int(time.time())}-{random.randint(1000, 9999)}"
    ORDER_CREATED.labels(order.region).inc()
    logger.info(
        "order_created",
        extra={"extra": {"order_id": order_id, "item": order.item, "region": order.region}},
    )
    return JSONResponse(
        status_code=201,
        content={"order_id": order_id, "item": order.item, "quantity": order.quantity, "region": order.region},
    )


@app.post("/api/fault")
async def set_fault_mode(payload: FaultRequest) -> dict[str, bool]:
    global _runtime_fault_mode
    _runtime_fault_mode = payload.enabled
    FAULT_MODE.set(1 if _runtime_fault_mode else 0)
    logger.warning("fault_mode_changed", extra={"extra": {"enabled": _runtime_fault_mode}})
    return {"fault_mode": _runtime_fault_mode}


@app.get("/api/slo")
async def slo() -> dict[str, float | int | str]:
    settings = get_settings()
    return {
        "availability_target_percent": settings.slo_availability_target,
        "latency_p95_target_ms": settings.slo_latency_p95_ms,
        "error_budget_monthly_percent": round(100 - settings.slo_availability_target, 3),
        "interpretation": "Use request success rate and p95 latency as service SLI examples.",
    }


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
