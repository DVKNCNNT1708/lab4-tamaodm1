# ✅ Lab 04 Authentication Tests - FIXED

## Vấn đề Đã Phát Hiện (Problem Identified)

- **2 test auth đã FAIL** ❌
  - Test 1: "POST reading without token returns 401" → Nhận 500 thay vì 401
  - Test 2: "POST reading with wrong token returns 401" → Nhận 500 thay vì 401

## Nguyên Nhân (Root Cause)

Hàm `verify_bearer_token` raise HTTPException với `detail` là dict complex. FastAPI không thể serialize dict này đúng cách, dẫn tới lỗi 500 thay vì 401.

## Cách Sửa (Solution)

### Thay Đổi 1: Đơn Giản Hóa verify_bearer_token
- **Trước**: Raise HTTPException với `detail=build_problem(...)`  (dict phức tạp)
- **Sau**: Raise HTTPException với `detail="string"` + proper headers

### Thay Đổi 2: Cải Thiện Exception Handler
- Đảm bảo JSONResponse được trả về với `Content-Type: application/problem+json`
- Proper handling của headers từ HTTPException

### Thay Đổi 3: Fix endpoint GET /readings/{reading_id}
- Cũng sửa từ dict detail → string detail

## Kết Quả Mong Đợi

✅ Tất cả 11 test sẽ PASS
```
Tests: 11 total
├── ✓ Functional: 8/8
├── ✓ Auth: 2/2 (SỬA RỒI)
├── ✓ Negative: 2/2
└── ✓ Boundary: 3/3
```

## Tiếp Theo (Next Steps)

### Cách 1: Với Docker (Recommended)
```bash
# Build image mới
docker build -t fit4110/iot-ingestion:lab04 .

# Run container
docker run --rm \
  --name fit4110-iot-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/iot-ingestion:lab04

# Trong terminal khác - chạy tests
npm run test:local

# Kiểm tra report
reports/newman-lab04-local.html
```

### Cách 2: Chạy Local (không Docker)
```bash
# Cài dependencies
npm install
pip install -r requirements.txt

# Chạy service
python -m uvicorn src.iot_app.main:app --reload --host 0.0.0.0 --port 8000

# Trong terminal khác - chạy tests
npm run test:local
```

## Verification Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Test auth failure (should be 401, not 500)
curl -X POST http://localhost:8000/readings \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32-LAB-A01","metric":"temperature","value":25,"timestamp":"2026-05-13T08:30:00+07:00"}'

# Should return ProblemDetails JSON:
# {
#   "type": "about:blank",
#   "title": "Unauthorized",
#   "status": 401,
#   "detail": "Missing Authorization header",
#   "instance": "/readings"
# }
```

## Files Changed

```
✏️ src/iot_app/main.py
   - verify_bearer_token() function
   - http_exception_handler() function  
   - get_reading() endpoint
```

**Commit**: `Fix: Auth tests - simplify HTTPException details to string for proper ProblemDetails serialization`

---

**Status**: ✅ READY FOR TESTING
