# geo-draw

Ứng dụng web nhận đề hình học phẳng bằng tiếng Việt từ văn bản hoặc ảnh, dùng DeepSeek tạo scene Manim rồi render thành ảnh hoặc video. Parser cục bộ cũ vẫn có sẵn để vẽ nhanh các hình cơ bản mà không gọi API.

## Chạy ứng dụng

```powershell
cd C:\Users\Nhu\geo-draw
.\.venv-codex\Scripts\Activate.ps1
streamlit run app.py
```

Nếu máy đã có Python riêng và muốn tạo lại môi trường chuẩn `.venv`, bạn có thể dùng
tên đó thay cho `.venv-codex`. Project hiện dùng `.venv-codex` vì môi trường cũ
trỏ tới bản Python đã bị gỡ khỏi máy.

Mở địa chỉ Streamlit hiển thị, thường là `http://localhost:8501`.

## Thiết lập DeepSeek

1. Tạo API key trong trang quản lý DeepSeek.
2. Dán key vào ô **DeepSeek API key** ở sidebar; hoặc sao chép `.env.example` thành `.env` rồi điền:

```env
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_VISION_MODEL=deepseek-v4-flash-vision-exp
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

Không commit tệp `.env`. Ứng dụng không ghi API key vào scene, log hoặc mã nguồn.

Hai lựa chọn model:

- `deepseek-v4-flash`: nhanh, phù hợp đa số đề.
- `deepseek-v4-pro`: ưu tiên chất lượng cho đề phức tạp.

## Cách hoạt động

- **DeepSeek AI**: gửi đề bài đến `/chat/completions`, nhận mã `GeoScene`, kiểm tra cú pháp và chặn import/lệnh nguy hiểm trước khi render. Nếu lần render đầu lỗi, ứng dụng gửi log cho DeepSeek sửa một lần.
- **Ảnh đề bài**: click vùng clipboard rồi nhấn **Ctrl+V** để dán ảnh trực tiếp; chọn tệp PNG/JPG/WEBP/GIF vẫn có trong mục dự phòng. Bấm **Đọc đề từ ảnh**, kiểm tra văn bản nhận dạng rồi bấm **Vẽ hình**. Ảnh chỉ được gửi khi người dùng chủ động bấm nút đọc.
- **Dựng hình thủ công**: mở tab **Dựng hình** để chọn điểm/cạnh và hạ đường vuông góc, dựng tia phân giác, đường trung trực hoặc đường trung tuyến. Trung điểm, cung góc bằng nhau và ô vuông góc được thêm tự động; **Xóa thao tác cuối** hoàn tác phép dựng gần nhất.
- **Parser nhanh**: chạy hoàn toàn cục bộ, phù hợp tam giác, tứ giác, đường tròn, trung điểm, đường cao và trung tuyến cơ bản.
- Nhãn dùng `Text` nên ảnh tĩnh không cần cài LaTeX. Video cần FFmpeg.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Lưu ý: kiểm tra tĩnh làm giảm rủi ro khi chạy mã do AI tạo nhưng không phải sandbox bảo mật tuyệt đối. Chỉ sử dụng API/model đáng tin cậy và luôn xem mục **Mã Manim đã sinh** khi cần kiểm tra.
