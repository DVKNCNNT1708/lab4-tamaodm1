# Lab 04 - HOÀN TẤT ✅

## Tóm Tắt Vấn Đề & Cách Sửa

### Vấn Đề Ban Đầu
2 test auth bị FAIL trên Docker/Local:
```
❌ POST reading without token returns 401 → Got 500
❌ POST reading with wrong token returns 401 → Got 500
Error: Unexpected token 'I' at 1:1 Internal Server Error
```

### Nguyên Nhân Sâu
1. **HTTPException serialization** - FastAPI không thể serialize complex dict detail trong dependencies
2. **Missing status.HTTP_STATUS_CODES** - Starlette mới không có dictionary này

### Cách Sửa

#### Fix 1: Đơn Giản Hóa HTTPException Details
```python
# ❌ TRƯỚC (lỗi)
raise HTTPException(
    detail=build_problem(status_code=401, title="Unauthorized", ...)
)

# ✅ SAU (đúng)
raise HTTPException(
    detail="Missing Authorization header",
    headers={"WWW-Authenticate": "Bearer"}
)
```

#### Fix 2: Thay HTTP Status Code Mapping
```python
# ❌ TRƯỚC (không tồn tại)
title=status.HTTP_STATUS_CODES.get(exc.status_code, "HTTP Error")

# ✅ SAU (chuẩn)
import http
def get_status_text(status_code: int) -> str:
    try:
        return http.HTTPStatus(status_code).phrase
    except ValueError:
        return "Unknown Error"

title=get_status_text(exc.status_code)
```

#### Fix 3: Exception Handler Enhancements
- Proper header handling cho WWW-Authenticate
- Consistent Content-Type: application/problem+json
- Fallback to string detail → ProblemDetails conversion

## Kết Quả

### ✅ Tất Cả 11 Tests PASS

```
┌─────────────────────────┬──────┬────────┐
│                         │  Run │ Failed │
├─────────────────────────┼──────┼────────┤
│ Iterations              │  1   │  0 ✓   │
│ Requests                │ 11   │  0 ✓   │
│ Test Scripts            │ 11   │  0 ✓   │
│ Assertions              │ 19   │  0 ✓   │
└─────────────────────────┴──────┴────────┘
```

### Chi Tiết Tests

**01_Functional (4 tests)** ✅
- ✓ GET /health → 200 OK
- ✓ POST /readings → 201 Created
- ✓ GET /readings/latest → 200 OK with items
- ✓ GET /readings/{reading_id} → 200 OK

**02_Auth (2 tests)** ✅ **← FIXED!**
- ✓ POST without token → 401 Unauthorized
- ✓ POST with wrong token → 401 Unauthorized

**03_Negative (2 tests)** ✅
- ✓ Missing required field → 422 Unprocessable
- ✓ Wrong data type → 422 Unprocessable

**04_Boundary_Reliability (3 tests)** ✅
- ✓ Boundary temp 80°C → 201 with X-Warning header
- ✓ Boundary temp 81°C → 422 (out of range)
- ✓ Health endpoint < 1000ms

## Reports Generated

```
reports/
├── newman-lab04-local.xml        ✓ Generated
├── newman-lab04-local.html       ✓ Generated
└── .gitkeep

Average Response Time: 6ms
Total Run Duration: 1052ms
Total Data Received: 1.68kB
```

## Files Changed

```
✏️ src/iot_app/main.py
   - Line ~1: Add import http
   - Line ~108-135: New get_status_text() function
   - Line ~137-160: Fixed http_exception_handler()
   - Line ~162-172: Simplified verify_bearer_token()
   - Line ~255-257: Simplified get_reading() HTTPException
```

## Git Commits

```
1f49016 Fix: Auth tests - simplify HTTPException details
0eb955f docs: Add fix documentation and quick reference guide
0129a7e Fix: Replace unavailable status.HTTP_STATUS_CODES
         with http.HTTPStatus for proper status text mapping
```

## Trạng Thái Submission

✅ **Ready for Lab 04 Submission**

- [x] Dockerfile (multi-stage, non-root user, HEALTHCHECK)
- [x] .dockerignore
- [x] .env.example
- [x] RUN_LOCAL.md
- [x] OpenAPI Contract (iot-ingestion.openapi.yaml)
- [x] Postman Collection (FIT4110_lab04_iot_docker.postman_collection.json)
- [x] Postman Environment (FIT4110_lab04_local.postman_environment.json)
- [x] Newman Report XML (reports/newman-lab04-local.xml)
- [x] Newman Report HTML (reports/newman-lab04-local.html)
- [x] All 11 Tests Passing
  - ✓ Functional tests
  - ✓ Auth tests (FIXED)
  - ✓ Negative tests
  - ✓ Boundary tests

## Local Testing Command

```bash
# Terminal 1: Start service
cd src
python -m uvicorn iot_app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Run tests
npm run test:local

# View reports
reports/newman-lab04-local.html  # Open in browser
```

## Docker Deployment (When Available)

```bash
docker build -t fit4110/iot-ingestion:lab04 .
docker run --rm --name fit4110-iot-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/iot-ingestion:lab04

# In another terminal
npm run test:local
```

---

**Status**: ✅ **COMPLETE - Ready for Submission**
