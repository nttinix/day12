## Họ và tên: Nguyễn Trọng Tín
## MSSV: 2A202600229

## Part 1: Localhost vs Production
## Exercise 1.1 - Anti-patterns

1. Hardcoded API key
    - Tại dòng 17 OPENAI_API_KEY được viết thẳng trong source code, thay vì đọc từ biến môi trường
    - Tại dòng 34 log ra OPENAI_API_KEY
2. Port cố định
    - Tại dòng 52 đang setting port cố định
3. Debug mode bật sẵn
    - Tại dòng 21 có `DEBUG = True`, tức là debug được bật sẵn trong cấu hình
    - Tại dòng 53 có `reload=True`, tức server chạy theo chế độ dev và tự reload code
4. Không có health check endpoint
    - File chỉ khai báo endpoint `/` và `/ask`, không có endpoint như `/health` hoặc `/ready`
    - Vì vậy cloud platform không có cách kiểm tra app còn sống hay đã sẵn sàng nhận request chưa
5. Không xử lý graceful shutdown
    - File `develop/app.py` không có lifecycle management như `lifespan`, không bắt signal `SIGTERM`, và không có cleanup logic trước khi tắt
    - Khi app bị dừng đột ngột, request đang chạy hoặc kết nối đang mở có thể bị ngắt giữa chừng

## Exercise 1.2 - Chạy basic version

Đã chạy `python app.py` trong thư mục `01-localhost-vs-production/develop` và test thành công endpoint `/ask`.
Kết luận: app chạy được trên local nhưng chưa production-ready vì còn nhiều anti-patterns.

###  Exercise 1.3: So sánh với advanced version

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode trực tiếp trong code | Đọc từ environment variables qua `settings` | Giúp đổi cấu hình theo môi trường và tránh lộ secrets |
| Health check | Không có `/health` hay `/ready` | Có `/health` và `/ready` | Cloud platform và load balancer biết app còn sống và sẵn sàng nhận request |
| Logging | Dùng `print()` thủ công | Dùng structured JSON logging với `logging` | Dễ theo dõi, tìm lỗi và gom log trên production |
| Shutdown | Không có xử lý shutdown | Có `lifespan` và bắt `SIGTERM` | Giúp tắt app an toàn, tránh ngắt request hoặc mất kết nối đột ngột |
| Host binding | `localhost` | `0.0.0.0` | Cho phép app nhận kết nối từ ngoài container hoặc cloud |
| Port | Cố định `8000` | Đọc từ `PORT` env var | Phù hợp với Railway, Render, Cloud Run |
| Debug | `DEBUG = True`, `reload=True` | Chỉ bật reload khi `debug=true` | Tránh chạy chế độ dev trên production |
| Secrets | API key và DB URL hardcode | Secrets lấy từ env vars | An toàn hơn và đúng chuẩn 12-factor |
| Request handling | Nhận `question` đơn giản, ít validate | Có kiểm tra body request và lỗi `422` | Giúp API chặt chẽ hơn, giảm lỗi đầu vào |
| CORS | Không cấu hình | Có `CORSMiddleware` | Cho phép kiểm soát domain nào được gọi API |

## Part 2: Docker Containerization

###  Exercise 2.1: Dockerfile cơ bản

1. Base image là gì?
    - Base image là image gốc dùng làm nền để build container.
    - Trong bài này, base image là `python:3.11` ở bản basic và `python:3.11-slim` ở bản advanced.
    - Nó cung cấp sẵn môi trường Python để app có thể chạy.

2. Working directory là gì?
    - Working directory là thư mục làm việc mặc định bên trong container.
    - Trong Dockerfile này, `WORKDIR /app` nghĩa là các lệnh như `COPY`, `RUN`, `CMD` sẽ làm việc trong thư mục `/app`.

3. Tại sao COPY requirements.txt trước?
    - Để tận dụng Docker layer cache.
    - Nếu `requirements.txt` không đổi thì Docker không cần cài lại dependencies mỗi lần build, nên build nhanh hơn.
    - Sau đó mới `COPY` source code để khi code thay đổi, chỉ các layer phía sau bị build lại.

4. CMD vs ENTRYPOINT khác nhau thế nào?
    - `CMD` là lệnh mặc định khi container khởi động, có thể bị ghi đè dễ dàng khi chạy `docker run`.
    - `ENTRYPOINT` dùng để cố định executable chính của container, còn tham số truyền thêm thường được nối vào sau.
    - Trong bài này Dockerfile dùng `CMD ["python", "app.py"]` hoặc `CMD ["uvicorn", ...]` để chỉ lệnh mặc định chạy app.

###  Exercise 2.2: Build và run
Image size là 424MB

###  Exercise 2.3: Multi-stage build

- Stage 1 làm gì?
    - Stage 1 là `builder`, dùng để cài dependencies và các build tools cần thiết như `gcc`, `libpq-dev`.
    - Stage này chạy `pip install --user -r requirements.txt` để chuẩn bị sẵn các package Python.
    - Image của stage này không dùng để deploy trực tiếp.

- Stage 2 làm gì?
    - Stage 2 là `runtime`, chỉ chứa những gì cần để chạy app.
    - Stage này copy packages đã cài từ stage 1 sang, copy source code, tạo `appuser`, cấu hình `ENV`, `HEALTHCHECK`, rồi chạy `uvicorn`.
    - Đây là image cuối cùng được dùng để deploy.

- Tại sao image nhỏ hơn?
    - Vì image cuối chỉ giữ runtime cần thiết, không giữ lại build tools và các file tạm của quá trình cài đặt.
    - Multi-stage giúp tách phần build và phần chạy, nên final image sạch hơn và nhẹ hơn.
    - Ngoài ra Dockerfile advanced dùng `python:3.11-slim`, vốn nhỏ hơn `python:3.11` của bản basic.

- Image `advanced`  nhỏ hơn(56.6MB), sạch hơn và phù hợp để deploy production hơn bản `basic`.

###  Exercise 2.4: Docker Compose stack

Architecture diagram:

```text
User
  |
  v
Nginx (port 80/443)
  |
  v
Agent (FastAPI, port 8000)
  | \
  |  \
  v   v
Redis  Qdrant
```

Services được start:
- `agent`
- `redis`
- `qdrant`
- `nginx`

Chúng communicate thế nào:
- User gửi request vào `nginx` qua cổng `80` hoặc `443`.
- `nginx` đóng vai trò reverse proxy và chuyển request vào `agent`.
- `agent` giao tiếp với `redis` qua `REDIS_URL=redis://redis:6379/0` để lưu cache, session hoặc rate limiting data.
- `agent` giao tiếp với `qdrant` qua `QDRANT_URL=http://qdrant:6333` để truy cập vector database cho RAG.
- Các service nằm chung trong network `internal`, nên chúng gọi nhau bằng tên service như `redis`, `qdrant`, `agent`.

## Part 3: Cloud Deployment
###  Exercise 3.1: Deploy Railway

- Các bước đã làm:
    - Đăng nhập Railway bằng `railway login`
    - Khởi tạo project bằng `railway init`
    - Deploy code bằng `railway up`

- Sau khi deploy:
    - Dùng `railway status` để kiểm tra trạng thái service
    - Dùng `railway logs` để xem log nếu build hoặc run bị lỗi
    - Dùng `railway domain` để lấy URL public của service
    - Public URL: `https://trongtin20k-production.up.railway.app/`

- Cách kiểm tra:
    - Test health endpoint bằng `curl.exe https://<railway-domain>/health`
    - Nếu app có endpoint `/ask` thì có thể test thêm bằng request phù hợp
    - Test root endpoint thành công:
      - `{"message":"AI Agent running on Railway!","docs":"/docs","health":"/health"}`

- Kết luận:
    - Railway giúp deploy app lên cloud nhanh mà không cần tự cấu hình server
    - Sau khi deploy thành công, agent có thể được truy cập qua public URL thay vì chỉ chạy ở localhost

## Part 4: API Security

###  Exercise 4.1: API Key authentication

- API key được check ở đâu?
    - API key được lấy từ biến môi trường `AGENT_API_KEY`.
    - Header được đọc bằng `APIKeyHeader(name="X-API-Key", auto_error=False)`.
    - Việc kiểm tra nằm trong hàm `verify_api_key()`.
    - Endpoint `/ask` dùng `Depends(verify_api_key)` nên chỉ truy cập được khi có key hợp lệ.

- Điều gì xảy ra nếu sai key?
    - Nếu không gửi key, API trả `401` với thông báo thiếu `X-API-Key`.
    - Nếu gửi key sai, API trả `403` với thông báo `Invalid API key`.

- Làm sao rotate key?
    - Đổi giá trị của biến môi trường `AGENT_API_KEY` sang key mới.
    - Restart hoặc redeploy service để app đọc key mới.
    - Không nên hardcode key trong source code, nên lưu trong env vars hoặc secret manager.

- Test:
    - Chạy app:
      - `cd 04-api-gateway/develop`
      - `$env:AGENT_API_KEY="my-secret-key"`
      - `python app.py`
    - Test không có key:
      - `curl.exe -X POST "http://localhost:8000/ask?question=Hello"`
      - Kết quả: `401 Unauthorized`
    - Test có key đúng:
      - `curl.exe -X POST "http://localhost:8000/ask?question=Hello" -H "X-API-Key: my-secret-key"`
      - Kết quả: `200 OK` và trả về câu trả lời của agent

###  Exercise 4.2: JWT authentication

- JWT flow:
    - Client gửi `username` và `password` tới endpoint `POST /auth/token`.
    - Server gọi `authenticate_user()` để kiểm tra thông tin đăng nhập.
    - Nếu hợp lệ, server tạo JWT bằng `create_token()` với các thông tin như `sub`, `role`, `iat`, `exp`.
    - Client nhận token và gửi lại trong header `Authorization: Bearer <token>` khi gọi `/ask`.
    - Server dùng `verify_token()` để kiểm tra chữ ký, hạn dùng và lấy ra thông tin user.

- JWT chứa gì?
    - `sub`: username
    - `role`: vai trò người dùng
    - `iat`: thời điểm cấp token
    - `exp`: thời điểm hết hạn token

- Nếu token sai hoặc hết hạn thì sao?
    - Không gửi token: trả `401`
    - Token hết hạn: trả `401`
    - Token không hợp lệ: trả `403`

- Test:
    - Chạy app:
      - `cd 04-api-gateway/production`
      - `python app.py`
    - Lấy token:
      - `curl.exe -X POST "http://localhost:8000/auth/token" -H "Content-Type: application/json" -d "{\"username\":\"student\",\"password\":\"demo123\"}"`
    - Dùng token gọi API:
      - `curl.exe -X POST "http://localhost:8000/ask" -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"question\":\"Explain JWT\"}"`

- Kết luận:
    - JWT giúp xác thực kiểu stateless, không cần lưu session trên server cho mỗi request.
    - Cách này phù hợp hơn API Key khi cần phân quyền và mở rộng hệ thống.

###  Exercise 4.3: Rate limiting

- Algorithm nào được dùng?
    - Thuật toán được dùng là `Sliding Window Counter`.
    - Mỗi user có một danh sách timestamp request trong cửa sổ thời gian 60 giây.
    - Khi có request mới, hệ thống xóa các timestamp cũ ngoài window rồi kiểm tra số request còn lại.

- Limit là bao nhiêu requests/minute?
    - User thường: `10 requests/phút`
    - Admin: `100 requests/phút`

- Làm sao bypass limit cho admin?
    - Không bypass hoàn toàn, nhưng admin được dùng limiter riêng là `rate_limiter_admin`.
    - Trong `app.py`, nếu `role == "admin"` thì hệ thống dùng `rate_limiter_admin` thay vì `rate_limiter_user`.
    - Vì vậy admin có limit cao hơn rất nhiều so với user thường.

- Nếu vượt limit thì sao?
    - API trả `429 Too Many Requests`.
    - Response có thêm các header như `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`.

- Test:
    - Dùng token của `student` rồi gọi `/ask` nhiều lần liên tiếp.
    - Sau khi vượt quá `10` request trong `60` giây, API sẽ trả `429`.
    - Nếu dùng token của `teacher` thì có thể gọi nhiều hơn vì limit là `100` request/phút.

###  Exercise 4.4: Cost guard

- Cost guard dùng để làm gì?
    - Cost guard dùng để theo dõi chi phí sử dụng LLM và chặn request khi vượt budget.
    - Mục tiêu là tránh phát sinh hóa đơn quá lớn do gọi model quá nhiều.

- Logic trong `cost_guard.py`:
    - Mỗi user có budget mặc định là `$1/ngày`.
    - Toàn hệ thống có global budget là `$10/ngày`.
    - Khi user dùng đến `80%` budget thì hệ thống ghi warning log.
    - Nếu user vượt budget cá nhân, API trả `402`.
    - Nếu vượt global budget, API trả `503`.

- Hệ thống track gì?
    - `input_tokens`
    - `output_tokens`
    - `request_count`
    - `total_cost_usd`

- Cost được tính như thế nào?
    - Dựa trên số input tokens và output tokens của mỗi request.
    - `record_usage()` sẽ cộng dồn usage và cập nhật tổng chi phí cho user cũng như toàn hệ thống.

- Trong production nên làm thế nào?
    - Phiên bản hiện tại lưu dữ liệu in-memory nên chỉ phù hợp để demo.
    - Trong production nên lưu usage vào Redis hoặc database để không bị mất khi restart app.

- Test:
    - Gọi `/ask` nhiều lần với token hợp lệ để làm tăng usage.
    - Dùng endpoint `/me/usage` để xem số request, số token và chi phí đã dùng.
    - Khi vượt budget cá nhân, API sẽ trả lỗi `402 Payment Required`.

- Kết luận:
    - Cost guard là lớp bảo vệ tài chính cho hệ thống AI.
    - Nó rất quan trọng khi deploy production vì giúp kiểm soát ngân sách và tránh lạm dụng API.

## Part 5: Scaling & Reliability

###  Exercise 5.1: Health checks

- Làm trong file `05-scaling-reliability/develop/app.py`
- `/health`: kiểm tra app còn sống không
- `/ready`: kiểm tra app đã sẵn sàng nhận request chưa
- Nếu chưa ready thì trả `503`

###  Exercise 5.2: Graceful shutdown

- Làm trong file `05-scaling-reliability/develop/app.py`
- Bắt signal `SIGTERM` và `SIGINT`
- Khi shutdown thì dừng nhận request mới, chờ request đang chạy hoàn thành
- Sau đó app tắt an toàn

###  Exercise 5.3: Stateless design

- Làm trong `05-scaling-reliability/production`
- Không lưu state trong memory của app
- Chuyển conversation history sang Redis
- Khi scale nhiều instance, dữ liệu vẫn dùng chung được

###  Exercise 5.4: Load balancing

- Chạy stack với `docker compose up --scale agent=3`
- Dùng Nginx để phân phối request tới nhiều agent instances
- Nếu 1 instance chết thì request được chuyển sang instance khác

###  Exercise 5.5: Test stateless

- Chạy `python test_stateless.py`
- Script tạo conversation, kill một instance, rồi gọi tiếp
- Nếu conversation vẫn còn thì chứng tỏ app đã stateless đúng
