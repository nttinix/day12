# Deployment Report - Part 6

## Muc tieu

Deploy production-ready AI agent cua Part 6 len Railway voi:

- FastAPI web service
- Redis de luu conversation history, rate limit, va cost usage
- Public URL co the truy cap tu Internet

## Nen tang deploy

- Platform: Railway
- App service: FastAPI agent
- Redis service: Railway Redis
- Public URL: `https://mainservice-production-6da5.up.railway.app/`

## Cau hinh da dung

### App service variables

```env
AGENT_API_KEY=super-secret-key
ENVIRONMENT=production
PORT=8000
REDIS_URL=${{Redis.REDIS_URL}}
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=<your-valid-openai-key>
```

### Luu y quan trong

- `AGENT_API_KEY` la key de goi API cua app, khong phai OpenAI API key.
- `REDIS_URL` phai dung Railway reference variable, khong duoc hardcode `redis://redis:6379/0`.
- App listen tren port `8000`.
- De dung real LLM, can set `LLM_PROVIDER=openai` va `OPENAI_API_KEY` hop le.

## Cac buoc deploy da thuc hien

### 1. Di chuyen vao thu muc project

```powershell
cd c:\Users\TRONG_TIN\Desktop\AI20K\LAB\day12_ha-tang-cloud_va_deployment\PART6
```

### 2. Dang nhap Railway

```powershell
railway login
railway whoami
```

### 3. Tao project Railway moi

```powershell
railway init
```

### 4. Tao Redis service tren Railway

```powershell
railway deploy -t redis
```

Sau buoc nay, project Railway co 1 Redis service.

### 5. Tao web service cho app

Trong Railway dashboard:

- Chon `New`
- Tao `Empty Service` hoac `Blank Service`

Sau do link terminal vao dung service app:

```powershell
railway service
```

Chon service web moi tao, khong chon Redis.

### 6. Deploy code len Railway

```powershell
railway up
```

Railway build app tu `Dockerfile` trong thu muc `PART6`.

### 7. Cau hinh variables cho service app

Trong dashboard, vao tab `Variables` cua service app va them:

```env
AGENT_API_KEY=super-secret-key
ENVIRONMENT=production
PORT=8000
REDIS_URL=${{Redis.REDIS_URL}}
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=<your-valid-openai-key>
```

### 8. Redeploy service

Sau khi cap nhat variables:

```powershell
railway up
```

hoac bam `Redeploy` trong Railway dashboard.

### 9. Bat public domain

Trong Railway dashboard:

- Vao `Settings`
- Chon `Networking`
- Bam `Generate Domain`

Ket qua nhan duoc:

```text
https://mainservice-production-6da5.up.railway.app/
```

## Loi gap phai va cach sua

### Loi 1: `'$PORT' is not a valid integer`

Nguyen nhan:

- `railway.toml` dung `--port $PORT`, nhung Railway khong expand bien o `startCommand`.

Cach sua:

- Doi thanh port co dinh:

```toml
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

### Loi 2: `startup_error` voi `Authentication required.`

Nguyen nhan:

- App ket noi Redis sai URL.
- Dang dung hardcoded Redis URL hoac service variable sai.

Cach sua:

- Dung Railway reference variable:

```env
REDIS_URL=${{Redis.REDIS_URL}}
```

### Loi 3: Healthcheck fail

Nguyen nhan:

- Redis chua noi dung
- `PORT` chua dung
- App chua san sang tai `/health`

Cach sua:

- Dat `PORT=8000`
- Dat `REDIS_URL` dung
- Redeploy lai service

### Loi 4: `/ask` bi `500 Internal Server Error` khi bat OpenAI

Nguyen nhan:

- Xung dot version giua `openai` va `httpx`
- Container dang cai `httpx` khong tuong thich voi `openai==1.51.0`

Cach sua:

- Pin `httpx==0.27.2` trong `requirements.txt`
- Bọc loi provider trong `app/llm.py` de log ro hon khi OpenAI fail

## Ket qua test sau deploy

### Health endpoint

```powershell
curl https://mainservice-production-6da5.up.railway.app/health
```

### Ready endpoint

```powershell
curl https://mainservice-production-6da5.up.railway.app/ready
```

### Ask endpoint

```powershell
curl -Method POST "https://mainservice-production-6da5.up.railway.app/ask" `
  -Headers @{ "Content-Type" = "application/json"; "X-API-Key" = "super-secret-key" } `
  -Body '{"question":"Hello","user_id":"student-01"}'
```

### Ask endpoint de test real LLM

```powershell
curl -Method POST "https://mainservice-production-6da5.up.railway.app/ask" `
  -Headers @{ "Content-Type" = "application/json"; "X-API-Key" = "super-secret-key" } `
  -Body '{"question":"Explain briefly the differences between Docker, Docker Compose, and Kubernetes, then give one real-world use case for each.","user_id":"student-01"}'
```

### Ket qua thuc te

- HTTP status: `200 OK`
- Agent tra ve JSON hop le
- Co `session_id`
- Co `answer`
- `model` tra ve la model OpenAI that
- App da hoat dong cong khai tren Railway
- Agent dang su dung real LLM, khong con la mock

Mot response mau:

```json
{
  "session_id": "48e83689bd28426f965a691174272afb",
  "user_id": "student-01",
  "answer": "**Docker** is a platform that allows developers to package applications into containers. **Docker Compose** helps define and run multi-container applications. **Kubernetes** is an orchestration platform for managing containers at scale...",
  "history_length": 2,
  "model": "gpt-4o-mini"
}
```

## Tong ket

Part 6 da duoc deploy thanh cong len Railway. He thong hien tai da dat duoc:

- Public API hoat dong
- Xac thuc bang API key
- Redis-backed state
- Conversation history
- OpenAI real LLM hoat dong
- Health va readiness endpoints
- Production deployment URL

Public deployment:

`https://mainservice-production-6da5.up.railway.app/`
