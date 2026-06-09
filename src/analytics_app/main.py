import os
from datetime import datetime, timezone
from typing import Annotated, List, Optional, Union, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


SERVICE_NAME = os.getenv("SERVICE_NAME", "analytics")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")


app = FastAPI(
    title="FIT4110 Lab 04 - Analytics Service",
    version=SERVICE_VERSION,
    description="Simple Analytics service implementing a subset of analytics.openapi.yaml for Lab 4.",
)


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: Optional[str] = None


class HealthStatus(BaseModel):
    status: str
    service: str
    time: str


class IngestAccepted(BaseModel):
    status: Literal["ACCEPTED"]
    acceptedAt: str


class AnalyticsSummary(BaseModel):
    totalEvents: int
    totalAlerts: int
    denyRate: Optional[float] = None
    averageConfidence: Optional[float] = None
    topCamera: Optional[str] = None
    generatedAt: str


class DashboardCard(BaseModel):
    key: str
    label: str
    value: int
    unit: Optional[str] = None


class DashboardResponse(BaseModel):
    generatedAt: str
    cards: List[DashboardCard]


class AccessIngestEvent(BaseModel):
    sourceType: Literal["access"]
    eventId: str
    gateId: str
    cardId: Optional[str] = None
    direction: Optional[Literal["IN", "OUT"]]
    decision: Literal["ALLOW", "DENY"]
    occurredAt: str


class CameraIngestEvent(BaseModel):
    sourceType: Literal["camera"]
    detectionId: str
    detectionType: Literal["PERSON", "VEHICLE", "UNKNOWN_OBJECT"]
    confidence: float = Field(..., ge=0, le=1)
    cameraId: str
    trackingId: Optional[str] = None
    occurredAt: str


class CoreBusinessIngestEvent(BaseModel):
    sourceType: Literal["core-business"]
    businessEventId: str
    eventType: Literal[
        "VISION_DETECTION",
        "ACCESS_DENIED",
        "UNAUTHORIZED_ACCESS",
        "SECURITY_INTRUSION",
        "NOTIFICATION_FAILURE",
    ]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: Literal["OPEN", "RESOLVED", "FAILED", "IGNORED"]
    gateId: Optional[str] = None
    cameraId: Optional[str] = None
    occurredAt: str


class IotIngestEvent(BaseModel):
    sourceType: Literal["iot"]
    deviceId: str
    metric: Literal["temperature", "humidity", "occupancy", "power"]
    value: float
    unit: Optional[str] = None
    occurredAt: str


IngestEvent = Annotated[
    Union[AccessIngestEvent, CameraIngestEvent, CoreBusinessIngestEvent, IotIngestEvent],
    Field(discriminator="sourceType"),
]


_EVENT_STORE: List[dict] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Problem(title="Unauthorized", status=401, detail="Missing Authorization header").dict(),
        )
    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Problem(title="Unauthorized", status=401, detail="Invalid bearer token").dict(),
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        content = exc.detail
    else:
        content = Problem(title=status.HTTP_STATUS_CODES.get(exc.status_code, "HTTP Error"), status=exc.status_code, detail=str(exc.detail)).dict()

    return JSONResponse(status_code=exc.status_code, content=content, media_type="application/problem+json")


@app.get("/health", response_model=HealthStatus)
def health():
    return HealthStatus(status="ok", service=SERVICE_NAME, time=now_iso())


@app.post("/ingest", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_event(payload: IngestEvent, _: None = Depends(verify_bearer_token)):
    item = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    item["received_at"] = now_iso()
    _EVENT_STORE.append(item)

    return IngestAccepted(status="ACCEPTED", acceptedAt=now_iso())


@app.get("/analytics/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    fromDate: str = Query(...),
    toDate: str = Query(...),
    sourceType: Optional[str] = Query(default=None),
    _: None = Depends(verify_bearer_token),
):
    try:
        dt_from = datetime.fromisoformat(fromDate)
        dt_to = datetime.fromisoformat(toDate)
        # convert to epoch timestamps (UTC) for safe comparison
        if dt_from.tzinfo is None:
            dt_from = dt_from.replace(tzinfo=timezone.utc)
        else:
            dt_from = dt_from.astimezone(timezone.utc)
        if dt_to.tzinfo is None:
            dt_to = dt_to.replace(tzinfo=timezone.utc)
        else:
            dt_to = dt_to.astimezone(timezone.utc)
        dt_from_ts = dt_from.timestamp()
        dt_to_ts = dt_to.timestamp()
    except Exception:
        raise HTTPException(status_code=400, detail=Problem(title="Bad Request", status=400, detail="Invalid date format").dict())

    filtered = []
    confidences = []
    deny_count = 0
    for e in _EVENT_STORE:
        try:
            occurred = datetime.fromisoformat(e.get("occurredAt") or e.get("occurred_at") or e.get("received_at"))
            if occurred.tzinfo is None:
                occurred = occurred.replace(tzinfo=timezone.utc)
            else:
                occurred = occurred.astimezone(timezone.utc)
            occurred_ts = occurred.timestamp()
        except Exception:
            continue
        # compare using epoch timestamps
        if occurred_ts < dt_from_ts or occurred_ts > dt_to_ts:
            continue
        if sourceType and e.get("sourceType") != sourceType:
            continue
        filtered.append(e)
        if e.get("sourceType") == "camera" and isinstance(e.get("confidence"), (int, float)):
            confidences.append(float(e.get("confidence")))
        if e.get("sourceType") == "access" and e.get("decision") == "DENY":
            deny_count += 1
        if e.get("sourceType") == "core-business" and e.get("severity") in ("HIGH", "CRITICAL"):
            deny_count += 1

    total = len(filtered)
    avg_conf = sum(confidences) / len(confidences) if confidences else None
    deny_rate = (deny_count / total) if total else None

    top_camera = None
    camera_counts = {}
    for e in filtered:
        if e.get("sourceType") == "camera":
            cam = e.get("cameraId")
            if cam:
                camera_counts[cam] = camera_counts.get(cam, 0) + 1
    if camera_counts:
        top_camera = max(camera_counts, key=camera_counts.get)

    return AnalyticsSummary(
        totalEvents=total,
        totalAlerts=deny_count,
        denyRate=deny_rate,
        averageConfidence=avg_conf,
        topCamera=top_camera,
        generatedAt=now_iso(),
    )


@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(_: None = Depends(verify_bearer_token)):
    total = len(_EVENT_STORE)
    alerts = sum(1 for e in _EVENT_STORE if (e.get("sourceType") == "access" and e.get("decision") == "DENY") or (e.get("sourceType") == "core-business" and e.get("severity") in ("HIGH", "CRITICAL")))
    cards = [
        DashboardCard(key="totalEvents", label="Total Events", value=total, unit=None),
        DashboardCard(key="totalAlerts", label="Total Alerts", value=alerts, unit=None),
    ]
    return DashboardResponse(generatedAt=now_iso(), cards=cards)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.analytics_app.main:app", host="0.0.0.0", port=4010, reload=False)
