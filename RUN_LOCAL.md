# RUN_LOCAL.md – Hướng dẫn chạy Lab 04

Tài liệu này giúp người khác clone repo sạch và chạy lại service trong Docker.

---

## 1. Clone repo

```bash
git clone <repo-url>
cd FIT4110_lab04_docker_packaging
```

---

## 2. Cài dependencies cho Newman/Prism/Spectral

```bash
npm install
```

---

## 3. Build Docker image

```bash
docker build -t fit4110/iot-ingestion:lab04 .
```

---

## 4. Run container

```bash
docker run --rm \
  --name fit4110-iot-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/iot-ingestion:lab04
```

Mở terminal khác, kiểm tra:

```bash
curl http://localhost:8000/health
```

Kết quả mong đợi:

```json
{
  "status": "ok",
  "service": "iot-ingestion",
  "version": "0.4.0"
}
```

---

## 5. Chạy Newman test trên container

```bash
npm run test:local
```

Report sinh tại:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

---

## 6. Dừng container

Nếu không dùng `--rm` hoặc container còn chạy:

```bash
docker stop fit4110-iot-lab04
```

---

## Run Analytics example

Build image for analytics example:

```bash
docker build -f Dockerfile.analytics -t fit4110/analytics:lab04 .
```

Run container:

```bash
docker run --rm \
  --name fit4110-analytics-lab04 \
  -p 4010:4010 \
  --env-file .env.example \
  fit4110/analytics:lab04
```

Check health and endpoints:

```bash
curl http://localhost:4010/health
curl -X POST http://localhost:4010/ingest -H "Authorization: Bearer local-dev-token" -H "Content-Type: application/json" -d '{"sourceType":"camera","detectionId":"d-1","detectionType":"PERSON","confidence":0.95,"cameraId":"CAM-01","occurredAt":"2026-06-01T10:00:00+00:00"}'
curl "http://localhost:4010/analytics/summary?fromDate=2026-06-01T00:00:00&toDate=2026-06-30T23:59:59" -H "Authorization: Bearer local-dev-token"
```


---

## 7. Lệnh nhanh

```bash
make build
make run
make test-docker
make stop
```
