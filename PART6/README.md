# PART6 Production Agent

Production-ready chat agent cho bài lab Part 6.

## Public deployment

Railway URL:

`https://mainservice-production-6da5.up.railway.app/`

## Tinh nang

- `POST /ask` de hoi dap qua REST API
- Conversation history luu trong Redis
- API key authentication
- Rate limit `10 req/min/user`
- Cost guard `10 USD/thang/user`
- Ho tro OpenAI real LLM qua `LLM_PROVIDER=openai`
- `GET /health` va `GET /ready`
- Structured JSON logging
- Docker multi-stage + Nginx + Redis

## Test tren Railway

Health:

```powershell
curl https://mainservice-production-6da5.up.railway.app/health
```

Ready:

```powershell
curl https://mainservice-production-6da5.up.railway.app/ready
```

Ask:

```powershell
curl -Method POST "https://mainservice-production-6da5.up.railway.app/ask" `
  -Headers @{ "Content-Type" = "application/json"; "X-API-Key" = "super-secret-key" } `
  -Body '{"question":"Hello","user_id":"student-01"}'
```

Ask voi cau hoi dai hon de test real LLM:

```powershell
curl -Method POST "https://mainservice-production-6da5.up.railway.app/ask" `
  -Headers @{ "Content-Type" = "application/json"; "X-API-Key" = "super-secret-key" } `
  -Body '{"question":"Explain briefly the differences between Docker, Docker Compose, and Kubernetes, then give one real-world use case for each.","user_id":"student-01"}'
```

History:

```powershell
curl -Headers @{ "X-API-Key" = "super-secret-key" } `
  "https://mainservice-production-6da5.up.railway.app/history/student-01/<session_id>"
```

## Trang thai hien tai

- Public deployment dang hoat dong tren Railway
- `/health`, `/ready`, `/ask` da test thanh cong
- `/ask` dang su dung OpenAI real LLM, khong con la mock
- Redis dang duoc dung de luu state va conversation history

## Chay local

```bash
cp .env.example .env
docker compose up --build --scale agent=3
```

Test:

```bash
curl http://localhost:8080/health

curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: super-secret-key" \
  -d "{\"question\":\"Hello\",\"user_id\":\"student-01\"}"
```

## Xem history

```bash
curl -H "X-API-Key: super-secret-key" \
  http://localhost:8080/history/student-01/<session_id>
```
