# geo-draw

Trợ giảng Toán tiếng Việt (THCS–THPT). Ứng dụng nhận đề bằng văn bản hoặc ảnh chụp, **gợi ý từng bước để học sinh tự giải** (hoặc trình bày lời giải chi tiết khi học sinh yêu cầu), và **tự vẽ hình** cho bài hình học phẳng. Phần gợi ý theo bậc lấy từ dự án MathLovers. Hình được vẽ bằng DeepSeek (tạo scene Manim rồi render thành ảnh hoặc video) hoặc bằng parser cục bộ cho các hình cơ bản.

Ứng dụng gồm ba phần:

- `geo_draw/`: lõi xử lý (hình học, AI, render, tài khoản, cuộc trò chuyện).
- `api/`: máy chủ FastAPI.
- `web/`: giao diện React.

Bản giao diện Streamlit cũ (`streamlit_app/`) vẫn chạy được trong thời gian chuyển đổi.

## Cài đặt

Cần Python 3.12, Node 22 (dự án có `.nvmrc`), FFmpeg nếu muốn xuất video.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
nvm use              # chọn Node 22
npm --prefix web install
```

Trên Windows dùng `.venv\Scripts\pip` và `.venv\Scripts\python` thay cho `.venv/bin/...`.

## Chạy ứng dụng

Cách nhanh nhất là dùng script, script tự cài những gì còn thiếu (môi trường Python, thư viện, Node 22 qua nvm):

```bash
./start.sh          # chạy thật: tự build giao diện khi có thay đổi, mở http://localhost:8000
./start.sh dev      # phát triển: API tự nạp lại + giao diện http://localhost:5173
```

Đổi cổng bằng `PORT=9000 ./start.sh`; cho máy khác trong mạng truy cập bằng `HOST=0.0.0.0 ./start.sh`.

Hoặc chạy từng lệnh:

**Khi phát triển** (hai terminal, sửa code là trang tự cập nhật):

```bash
.venv/bin/uvicorn api.main:app --reload     # API: http://localhost:8000 (tài liệu API ở /docs)
npm --prefix web run dev                    # giao diện: http://localhost:5173
```

**Khi chạy thật** (một lệnh; FastAPI phục vụ luôn giao diện đã build):

```bash
npm --prefix web run build
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Mở `http://localhost:8000`. Nếu chạy sau HTTPS, đặt `GEO_DRAW_COOKIE_SECURE=1`.

**Bản Streamlit cũ:**

```bash
.venv/bin/streamlit run app.py
```

## Chạy production bằng Docker

Image gồm máy chủ API và giao diện đã build sẵn, kèm Cairo, Pango, FFmpeg để Manim vẽ hình và làm video. Tài khoản, cuộc trò chuyện và lượt dùng nằm trong **PostgreSQL**; ảnh đề bài và hình vẽ là tệp trong volume `mathmate-data`.

1. Tạo database riêng trên PostgreSQL có sẵn:
   ```sql
   CREATE USER mathmate WITH PASSWORD 'mật-khẩu-mạnh';
   CREATE DATABASE mathmate OWNER mathmate;
   ```
   Bảng được tạo tự động khi ứng dụng khởi động.
2. Trong `.env`, điền `DEEPSEEK_API_KEY` và `DATABASE_URL`:
   - PostgreSQL chạy thẳng trên máy chủ: `postgresql://mathmate:mật-khẩu@host.docker.internal:5432/mathmate`. PostgreSQL phải nghe trên địa chỉ mà container thấy được (`listen_addresses`), và `pg_hba.conf` phải cho phép dải mạng Docker (thường là `172.16.0.0/12`).
   - PostgreSQL chạy trong Docker: dùng tên container của nó làm tên máy, và cho container `app` vào cùng mạng Docker đó.
   - Mật khẩu có ký tự đặc biệt (`@`, `:`, `/`…) thì phải mã hóa URL, ví dụ `@` thành `%40`.
3. Chạy:
   ```bash
   cp .env.example .env                 # rồi điền như bước 2
   docker compose up -d --build         # mở http://<máy chủ>:8000 (đổi cổng bằng PORT trong .env)
   ```

**Chuyển dữ liệu cũ (SQLite) sang PostgreSQL** (không bắt buộc; chạy lại nhiều lần cũng không nhân đôi dữ liệu). Chép thư mục `generated/` cũ vào volume, rồi chạy lệnh chuyển bên trong container:

```bash
docker compose run --rm -v "$PWD/generated":/import:ro app sh -c "cp -a /import/. /data/ && python -m api.migrate_sqlite /data"
```

Lệnh này chép tài khoản (giữ nguyên mật khẩu và phiên đăng nhập), mọi cuộc trò chuyện của người dùng và khách, cùng lượt dùng trong ngày.

**Chạy sau Traefik** (HTTPS theo tên miền, không mở cổng 8000 ra ngoài). Trong `.env`, điền `DOMAIN`, đặt `GEO_DRAW_COOKIE_SECURE=1`, và nếu Traefik trên máy chủ dùng tên khác mặc định thì sửa `TRAEFIK_NETWORK` (mạng Docker của Traefik), `TRAEFIK_ENTRYPOINT` (`websecure`) và `TRAEFIK_CERTRESOLVER` (`letsencrypt`). Sau đó:

```bash
docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d --build
```

Cập nhật phiên bản mới: `git pull` rồi chạy lại lệnh trên. Sao lưu: dùng `pg_dump` cho database, và với tệp hình vẽ: `docker run --rm -v geo-draw_mathmate-data:/data -v "$PWD":/backup alpine tar czf /backup/mathmate-data.tgz -C /data .` (tên volume có tiền tố là tên thư mục dự án; xem bằng `docker volume ls`).

Máy chủ chỉ chạy **một** tiến trình uvicorn: các lượt đang chạy và luồng cập nhật trực tiếp nằm trong bộ nhớ của tiến trình đó, nên đừng tăng `--workers` hay chạy nhiều bản sao.

## Thiết lập DeepSeek

Sao chép `.env.example` thành `.env` rồi điền:

```env
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_VISION_MODEL=deepseek-v4-flash-vision-exp
DEEPSEEK_BASE_URL=https://api.deepseek.com
# Số lượt dùng AI mỗi ngày: mỗi lượt trợ giảng trả lời và mỗi lần vẽ bằng AI tính 1 lượt; vẽ bằng Parser không tính
GEO_DRAW_DAILY_LIMIT_USER=100
GEO_DRAW_DAILY_LIMIT_GUEST=10
```

Máy chủ dùng chung một key cho mọi người dùng; người dùng không cần nhập key. Không commit tệp `.env`. Ứng dụng không ghi API key vào scene, log hoặc mã nguồn.

Hai lựa chọn model (chọn trong **Cài đặt**):

- `deepseek-v4-flash`: nhanh, phù hợp đa số đề.
- `deepseek-v4-pro`: ưu tiên chất lượng cho đề phức tạp.

## Cách dùng

- **Tài khoản**: đăng ký hoặc đăng nhập bằng tên và mật khẩu; hoặc bấm **Dùng thử không cần tài khoản**. Lịch sử của người dùng thử chỉ lưu trên trình duyệt đó.
- **Giải toán**: tin nhắn đầu tiên là đề bài (mọi dạng: phương trình, hàm số, bất đẳng thức, hình học…). Trợ giảng gợi ý theo 5 bậc: *Hiểu đề → Nhớ kiến thức → Chiến lược → Bước đầu tiên → Sâu hơn nữa*. Mỗi lượt kết thúc bằng một câu hỏi dẫn dắt. Học sinh trả lời trong khung chat. Bấm **Gợi ý sâu hơn** khi bí.
  - Ở chế độ **Gợi ý**, trợ giảng không bao giờ đưa lời giải hay đáp số, kể cả khi bị yêu cầu.
  - Chuyển sang **Lời giải chi tiết** (có hỏi xác nhận) để xem lời giải đầy đủ từng bước. Bấm **Gợi ý** để quay lại.
  - Công thức toán hiển thị bằng KaTeX.
- **Vẽ hình**: bài hình học phẳng (có điểm được đặt tên như ABC, tâm O) được **tự vẽ** ở khung bên phải. Bài khác thì bấm **Vẽ hình** nếu cần. Muốn chỉnh hình, nhập vào ô **Yêu cầu chỉnh hình** trong khung hình, ví dụ *"vẽ thêm đường cao AH"*; ứng dụng vẽ lại và giữ bố cục của hình trước.
- **Ảnh đề bài**: dán ảnh bằng **Ctrl+V**, kéo thả vào khung chat, hoặc bấm nút đính kèm. DeepSeek đọc đề trong ảnh; đề đọc được hiện trong khung chat để bạn kiểm tra.
- **Khung hình**: zoom và kéo ảnh, chọn lại các phiên bản trước, xem mã Manim và log.
- **Chỉnh hình thủ công**: dịch hoặc ẩn tên điểm, ẩn chấm điểm, thêm, ẩn hoặc làm đậm đoạn thẳng. Tab **Dựng hình** hạ đường vuông góc, dựng tia phân giác, đường trung trực hoặc trung tuyến. Mọi thao tác chỉ render lại trên máy chủ, không gọi DeepSeek. Chỉ áp dụng cho hình do DeepSeek tạo.

## Cách hoạt động

- **DeepSeek AI**: gửi đề đến `/chat/completions`, nhận mã `GeoScene`, kiểm tra cú pháp và chặn import hoặc lệnh nguy hiểm trước khi render. Nếu render lỗi, ứng dụng gửi log cho DeepSeek tự sửa, tối đa 3 lần.
- **Parser nhanh**: chạy hoàn toàn cục bộ, phù hợp tam giác, tứ giác, đường tròn, trung điểm, đường cao và trung tuyến cơ bản.
- Việc vẽ chạy nền trên máy chủ; tiến độ được gửi về trình duyệt theo thời gian thực. Đóng tab giữa chừng thì hình vẫn được lưu.
- Nhãn dùng `Text` nên ảnh tĩnh không cần cài LaTeX. Video cần FFmpeg.

## Kiểm thử

```bash
.venv/bin/python -m unittest discover -s tests -v
npx --prefix web tsc -b web && npm --prefix web run lint
```

Lưu ý: kiểm tra tĩnh làm giảm rủi ro khi chạy mã do AI tạo, nhưng không phải sandbox bảo mật tuyệt đối. Chỉ sử dụng API hoặc model đáng tin cậy, và khi cần thì xem tab **Mã Manim** để kiểm tra.
