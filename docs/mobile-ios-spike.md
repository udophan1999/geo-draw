# Spike giai đoạn 1: SwiftMath

Ngày 2026-10-15, SwiftMath 1.7.3, Xcode 26.5. Mã spike ở `mobile/ios/Spikes/MathSpike` (`swift run MathSpike <formulas.json> <thư mục>`): parse từng công thức, ghi lỗi, xuất PNG để xem bằng mắt.

## Kết quả đo

| Tập công thức | Render được | Lỗi |
|---|---|---|
| 85 mẫu trong `shared/formula_templates.json` + 19 ca `latexToPlain` | 96/104 (92%) | `\overrightarrow`, `\overset{\frown}`, `\backsim`, `\varnothing`, `cases` |
| 134 công thức khác nhau từ 51 câu trả lời thật của gia sư (dữ liệu local, đọc ở chế độ chỉ đọc) | 127/134 (95%) | toàn bộ 7 lỗi là `\dfrac` |

Chất lượng hiển thị (xem bằng mắt): tốt. Phân số, căn, mũ/chỉ số, `\lim`, `\sum`, `\int`, `\widehat{ABC}`, `\overline`, ℕℤℚℝ, `\{a \mid b\}`, hệ phương trình (khi có `&`) đều đúng.

Dữ liệu local còn ít (51 câu trả lời). Nên chạy lại với dữ liệu production (đọc từ một bản backup) trước khi chốt.

## Vấn đề và cách xử lý

| # | Vấn đề | Mức độ | Cách xử lý |
|---|---|---|---|
| 1 | **Chữ tiếng Việt trong `\text{…}` bị bỏ đi không báo lỗi** (`\text{Vậy}` → "Vy"). `MTMathAtomFactory.atom(forCharacter:)` chỉ nhận ASCII, Cyrillic và các chữ có dấu kiểu Latin-1; ậ, ằ, ờ, ư, đ trả về `nil` | Cao (sai nội dung) | Fork SwiftMath: nhận mọi chữ cái (`Character.isLetter`) làm atom `.ordinary`. Font: Latin Modern thiếu "đ"; TeX Gyre Termes, Libertinus Math và Garamond Math có đủ tiếng Việt, chọn một trong ba hoặc dùng font dự phòng cho ký tự thiếu |
| 2 | `\dfrac`, `\tfrac` không có | Cao (AI dùng thường xuyên) | Luật viết lại trong `MathNormalizer`: `\dfrac` → `\frac` (trong công thức khối thì giống hệt; trong dòng thì nhỏ hơn KaTeX một chút) |
| 3 | `cases` lỗi khi các dòng không có `&` ("cases environment can only have 2 columns") | Cao (hệ phương trình là mẫu có sẵn) | Viết lại: thêm `&` vào cuối mỗi dòng không có `&`; hoặc sửa trong fork |
| 4 | `\overrightarrow` không có; `\vec{AB}` chỉ đặt mũi tên trên A | Trung bình (vectơ lớp 10) | Fork: thêm accent co giãn như `\widehat` (dùng glyph mũi tên mở rộng của font) |
| 5 | Cung `\overset{\frown}{AB}` (`\overset`, `\stackrel`, `\overparen` đều không có) | Trung bình (cung tròn lớp 9) | Fork: thêm `\overset`, hoặc viết lại thành accent cung co giãn |
| 6 | `\backsim`, `\varnothing` không có | Thấp | Viết lại: `\backsim` → `\sim` (hoặc ký tự ∽), `\varnothing` → `\emptyset` |
| 7 | `\boxed`, `\operatorname`, `\cancel` không có | Thấp (chưa thấy trong dữ liệu thật) | `\operatorname{tg}` → `\mathrm{tg}`; các lệnh khác: hiện mã LaTeX dự phòng |
| 8 | `\color` bị bỏ qua | Không sao | App luôn vẽ chữ một màu |

## API cho trình soạn công thức

- `MTMathListDisplay` có `ascent`, `descent`, `range` và các display con: đủ để căn baseline cho công thức trong dòng chữ và tính vị trí con trỏ.
- Có `MTMathListIndex` (mô hình chỉ số theo nhánh: nucleus/superscript/subscript/numerator/…), cùng mô hình với MathEditor.
- Chưa có hàm "điểm → chỉ số" (`closestIndexToPoint`) và "chỉ số → vị trí con trỏ": port từ phần mở rộng `MTMathListDisplay+Editing` của kostub/MathEditor (viết cho iosMath, cùng cấu trúc).

## Kết luận tạm thời

**Tiếp tục với SwiftMath, nhưng dùng một bản fork** (vấn đề 1, 4, 5 cần sửa mã nguồn; vấn đề 2, 3, 6, 7 xử lý bằng luật viết lại trong `MathNormalizer`). Ước lượng thêm khoảng 3–5 ngày cho fork, chưa đổi ước lượng của giai đoạn 5.

## Còn lại trong spike

- [ ] Công thức trong dòng chữ (`Text` + `Image`, căn baseline) trên simulator iOS 17 và 26
- [ ] `UITextView` + `NSTextAttachment` (chip, Backspace trả lại LaTeX)
- [ ] Port `closestIndexToPoint` và vẽ con trỏ trên một công thức
- [ ] SSE bằng `URLSession.bytes` với server thật
- [ ] Chạy lại phép đo với dữ liệu production
