# Lab 04 - Authentication Tests Fix Summary

## Problem Identified
Newman test report showed **2 failing tests** out of 11:

1. **Auth Test Failed**: "POST reading without token returns 401"
   - Expected: HTTP 401
   - Got: HTTP 500 Internal Server Error
   
2. **Auth Test Failed**: "POST reading with wrong token returns 401"  
   - Expected: HTTP 401
   - Got: HTTP 500 Internal Server Error

**Error Message**: `Unexpected token 'I' at 1:1 Internal Server Error`

This indicated that FastAPI was returning plain text error responses instead of proper ProblemDetails JSON responses.

---

## Root Cause Analysis

The issue was in how `HTTPException` was being raised in the `verify_bearer_token` dependency function:

**Original Code (❌ BROKEN):**
```python
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail=build_problem(  # ← Passing a dict as detail!
        status_code=status.HTTP_401_UNAUTHORIZED,
        title="Unauthorized",
        detail="Missing Authorization header",
        problem_type="https://smart-campus.local/problems/unauthorized",
    ),
)
```

When `HTTPException` is raised in a dependency with a complex dict as the `detail` parameter, FastAPI's serialization can fail, causing it to fall back to a generic "Internal Server Error" response instead of properly handling the exception.

---

## Solution Implemented

### 1. Simplified `verify_bearer_token` Function
Changed to pass simple string details with proper HTTP headers:

```python
def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},  # ← Proper auth header
        )

    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### 2. Enhanced Exception Handler
Updated the `http_exception_handler` to properly convert string details to ProblemDetails format:

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # Build ProblemDetails from string detail
    problem = build_problem(
        status_code=exc.status_code,
        title=status.HTTP_STATUS_CODES.get(exc.status_code, "HTTP Error"),
        detail=str(exc.detail),  # ← Now handles string details
        instance=str(request.url.path),
        problem_type="https://smart-campus.local/problems/request-error",
    )
    
    # Ensure all required fields
    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", status.HTTP_STATUS_CODES.get(exc.status_code))
    problem.setdefault("type", "about:blank")
    problem.setdefault("instance", str(request.url.path))
    
    # Properly handle headers and content type
    headers = dict(getattr(exc, "headers", None) or {})
    headers["Content-Type"] = "application/problem+json"
    
    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        headers=headers,
    )
```

### 3. Fixed Other HTTPException Raises
Updated the `get_reading` endpoint which also had the same issue:

```python
# Changed from passing build_problem dict to simple string detail
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"Reading {reading_id} does not exist",
)
```

---

## Expected Test Results After Fix

### Before Fix ❌
```
Tests: 11 total
- Passed: 9
- Failed: 2
  - Auth without token: ✗ (500 error)
  - Auth with wrong token: ✗ (500 error)
```

### After Fix ✅
```
Tests: 11 total (Expected)
- Passed: 11
- Failed: 0
  - Auth without token: ✓ (401 with ProblemDetails)
  - Auth with wrong token: ✓ (401 with ProblemDetails)
```

---

## Response Format

The fix ensures that all auth failures now return proper RFC 7807 Problem Details responses:

```json
{
  "type": "about:blank",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Missing Authorization header",
  "instance": "/readings"
}
```

With proper HTTP headers:
- `Content-Type: application/problem+json`
- `WWW-Authenticate: Bearer` (for 401 responses)

---

## Files Modified

1. **src/iot_app/main.py**
   - `verify_bearer_token()` function
   - `http_exception_handler()` function
   - `get_reading()` endpoint

---

## Next Steps

1. Rebuild Docker image: `docker build -t fit4110/iot-ingestion:lab04 .`
2. Run container: `docker run --rm --name fit4110-iot-lab04 -p 8000:8000 --env-file .env.example fit4110/iot-ingestion:lab04`
3. Execute tests: `npm run test:local`
4. Verify Newman report in `reports/newman-lab04-local.html`
