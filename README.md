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

### Trên VPS dùng chung (Traefik + Postgres chung + Jenkins)

Giống cách deploy Wordime: ứng dụng không mở cổng nào, Traefik (chạy ở chế độ host network) phục vụ HTTPS qua mạng `mathmate-web`, và ứng dụng nối vào Postgres chung qua mạng Docker của container Postgres. Các tệp: `docker-compose.prod.yml`, `deploy.sh`, `Jenkinsfile`, `scripts/backup.sh`.

Làm theo thứ tự (bước sau phụ thuộc bước trước):

1. **Database và role** trên Postgres chung (một lần):
   ```bash
   docker exec -it <pg-container> psql -U postgres -d postgres -c "CREATE DATABASE mathmate;"
   docker exec -it <pg-container> psql -U postgres -d postgres -c "CREATE USER mathmate WITH PASSWORD '<mật-khẩu-mạnh>';"
   docker exec -it <pg-container> psql -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE mathmate TO mathmate;"
   # Postgres 15+: thiếu dòng này thì ứng dụng kết nối được nhưng không tạo được bảng.
   docker exec -it <pg-container> psql -U postgres -d mathmate -c "GRANT ALL ON SCHEMA public TO mathmate;"
   ```
   Thử quyền ghi từ mạng của Postgres: `docker run --rm --network <DB_NETWORK> postgres:17-alpine psql "postgresql://mathmate:<mật-khẩu>@<pg-container>:5432/mathmate" -c "CREATE TABLE _probe(x int); DROP TABLE _probe;"`. Bảng của ứng dụng được tạo tự động khi khởi động.
2. **DNS**: bản ghi A cho tên miền (ví dụ `mathmate.tonyvibecode.com`) trỏ về VPS, trước lần deploy đầu.
3. **Cấu hình**: managed config `mathmate.tonyvibecode.com` trong Jenkins (và một `.env` trong thư mục checkout nếu deploy tay) gồm `DEEPSEEK_API_KEY`, `DATABASE_URL` (tên container Postgres làm tên máy), `DB_NETWORK`, `APP_DOMAIN`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, và các hạn mức nếu muốn đổi. Xem phần "Docker" trong `.env.example`.
4. **Deploy**: chạy job Jenkins, hoặc `./deploy.sh` trên VPS. Pipeline chạy toàn bộ test trong image (`docker build --target test`), build, khởi động lại, rồi kiểm tra health, database và địa chỉ công khai.
5. **Sao lưu** ngay trong ngày: tạo `/opt/mathmate/backup.env` (xem `.env.example`), chạy thử một lần, rồi đặt cron mỗi giờ:
   ```cron
   0 * * * * BACKUP_ENV_FILE=/opt/mathmate/backup.env /đường/dẫn/geo-draw/scripts/backup.sh >> /var/log/mathmate-backup.log 2>&1
   ```
   Mỗi lần sao lưu tạo `mathmate-db-….sql.gz` (pg_dump) và `mathmate-files-….tar.gz` (ảnh và hình vẽ); cách khôi phục ghi ở cuối script. Đừng khôi phục bằng `pg_dumpall --clean`: nó xóa database của mọi ứng dụng trên Postgres chung.

Quay lại bản trước: `IMAGE=mathmate:previous docker compose -f docker-compose.prod.yml --env-file .env up -d`.

### Ở máy khác (mở cổng, không Traefik)

```bash
cp .env.example .env                 # điền DEEPSEEK_API_KEY; DATABASE_URL tùy chọn
docker compose up -d --build         # mở http://<máy>:8000 (đổi cổng bằng PORT trong .env)
```

### Chuyển dữ liệu cũ (SQLite) sang PostgreSQL

Không bắt buộc; chạy lại nhiều lần cũng không nhân đôi dữ liệu. Chép thư mục `generated/` cũ vào volume, rồi chạy lệnh chuyển bên trong container:

```bash
docker compose -f docker-compose.prod.yml --env-file .env run --rm -v "$PWD/generated":/import:ro app \
  sh -c "cp -a /import/. /data/ && python -m api.migrate_sqlite /data"
```

Lệnh này chép tài khoản (giữ nguyên mật khẩu và phiên đăng nhập), mọi cuộc trò chuyện của người dùng và khách, cùng lượt dùng trong ngày.

**Giới hạn chi phí AI.** Mỗi tài khoản và mỗi khách có hạn mức lượt AI mỗi ngày. Vì khách chỉ được nhận diện bằng cookie, khách còn bị giới hạn chung theo IP (`GEO_DRAW_DAILY_LIMIT_GUEST_IP`), số tài khoản tạo mới mỗi ngày từ một IP cũng bị giới hạn (`GEO_DRAW_REGISTER_LIMIT_IP`), và cả máy chủ có tổng lượt AI tối đa mỗi ngày (`GEO_DRAW_DAILY_LIMIT_TOTAL`). Trên VPS, ứng dụng chỉ tin địa chỉ IP do Traefik chuyển tới (`TRAEFIK_PROXY_IPS`), nên không ai giả được IP để lách giới hạn.

Máy chủ chỉ chạy **một** tiến trình uvicorn: các lượt đang chạy và luồng cập nhật trực tiếp nằm trong bộ nhớ của tiến trình đó, nên đừng tăng `--workers` hay chạy nhiều bản sao.

## Quản trị

Đặt `ADMIN_USERNAME` và `ADMIN_PASSWORD` trong `.env` trước lần chạy đầu tiên: khi khởi động, nếu chưa có quản trị viên nào, máy chủ tạo tài khoản đó (hoặc cấp quyền cho tài khoản cùng tên đã có, giữ mật khẩu cũ) và ghi một dòng vào log. Sau đó hai biến này không còn tác dụng.

Quản trị viên mở **Trang quản trị** từ menu tài khoản (góc dưới thanh bên), hoặc vào `/admin`:
- **Người dùng**: tìm theo tên; xem ngày tạo, lần hoạt động gần nhất, số cuộc trò chuyện, lượt AI hôm nay; đặt lại mật khẩu, đổi hạn mức AI riêng, cấp hoặc bỏ quyền quản trị, khóa hoặc mở khóa, xóa tài khoản cùng dữ liệu. Không ai tự khóa, tự bỏ quyền hay tự xóa chính mình được, nên luôn còn ít nhất một quản trị viên.
- **System prompt**: sửa prompt của trợ giảng (chế độ Gợi ý và Lời giải chi tiết), có Khôi phục mặc định. Phần rào chắn không đưa đáp án và phần báo tiến độ luôn được giữ, chỉ xem được.

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
