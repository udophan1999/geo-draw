# Spike giai đoạn 1: SwiftMath

Ngày 2026-10-15, SwiftMath 1.7.3, Xcode 26.5. Mã spike ở `mobile/ios/Spikes/MathSpike` (`swift run MathSpike <formulas.json> <thư mục>`): parse từng công thức, ghi lỗi, xuất PNG để xem bằng mắt.

## Kết quả đo

| Tập công thức | SwiftMath 1.7.3 | upstream `main` | Fork `mathmate` + TeX Gyre Termes |
|---|---|---|---|
| 85 mẫu trong `shared/formula_templates.json` + 19 ca `latexToPlain` | 96/104 | 100/104 | **104/104** |
| 134 công thức khác nhau từ 51 câu trả lời thật của gia sư (dữ liệu local, đọc ở chế độ chỉ đọc) | 127/134 | 134/134 | **134/134** |

Bản 1.7.3 (bản phát hành mới nhất) đã cũ: upstream `main` đã thêm `\dfrac`, `\overrightarrow` co giãn, `\varnothing`, sửa `cases` không có `&` và sửa lỗi `\left…\right` lặp nội dung. Chữ tiếng Việt trong `\text{…}` cũng hiển thị đúng trên `main`.

Chất lượng hiển thị (xem bằng mắt): tốt. Phân số, căn, mũ/chỉ số, `\lim`, `\sum`, `\int`, `\widehat{ABC}`, vectơ, cung, ℕℤℚℝ, `\{a \mid b\}`, hệ phương trình đều đúng.

Dữ liệu local còn ít (51 câu trả lời). Nên chạy lại với dữ liệu production (đọc từ một bản backup) trước khi chốt.

## Fork

https://github.com/xuanthinhJB/SwiftMath, nhánh `mathmate` (dựa trên upstream `main`), commit `8da9a4e`:

- `\overset{\frown}{AB}`, `\stackrel{\frown}{AB}`, `\overparen`, `\wideparen`: cung co giãn theo nội dung, dựng trên glyph U+23DC như `\widehat`. `\overset`/`\stackrel` với thứ khác ở trên vẫn báo lỗi `invalidCommand`.
- `\backsim` (∽), `\frown`, `\smile`.
- `Tests/SwiftMathTests/TextbookNotationTests.swift` (6 test, gồm cả kiểm tra chữ tiếng Việt không bị mất); toàn bộ 575 test của SwiftMath đều qua.

Khi cần cập nhật upstream: `git fetch upstream && git rebase upstream/main` trong fork. Có thể gửi PR cho upstream sau (phần cung và `\backsim` hữu ích cho người khác).

## Font

Latin Modern (mặc định) thiếu "đ", nên "đ" được lấy từ font khác và trông lệch hẳn. **Chọn TeX Gyre Termes** (kiểu Times, giống sách giáo khoa Việt Nam; có đủ chữ tiếng Việt, cung, ∽). Libertinus Math cũng đủ, có thể đổi sau. App gọi `MTFontManager().termesFont(withSize:)`.

## Vấn đề còn lại

| # | Vấn đề | Mức độ | Cách xử lý |
|---|---|---|---|
| 1 | `\boxed`, `\cancel` không có | Thấp (chưa thấy trong dữ liệu thật) | Hiện mã LaTeX dự phòng; thêm vào fork nếu dữ liệu production có |
| 2 | `\color` bị bỏ qua | Không sao | App luôn vẽ chữ một màu |
| 3 | `\operatorname` không có | Thấp | Luật viết lại `\operatorname{tg}` → `\mathrm{tg}` trong `MathNormalizer` |

## API cho trình soạn công thức

- `MTMathListDisplay` có `ascent`, `descent`, `range` và các display con: đủ để căn baseline cho công thức trong dòng chữ và tính vị trí con trỏ.
- Có `MTMathListIndex` (mô hình chỉ số theo nhánh: nucleus/superscript/subscript/numerator/…), cùng mô hình với MathEditor.
- Chưa có hàm "điểm → chỉ số" (`closestIndexToPoint`) và "chỉ số → vị trí con trỏ": port từ phần mở rộng `MTMathListDisplay+Editing` của kostub/MathEditor (viết cho iosMath, cùng cấu trúc).

## Kết luận

**Dùng SwiftMath qua fork `xuanthinhJB/SwiftMath@mathmate` với font TeX Gyre Termes.** Phần hiển thị công thức không còn rủi ro lớn. Fork đã xong (nhỏ hơn ước lượng 3–5 ngày, vì upstream `main` đã sửa phần lớn), nên ước lượng của giai đoạn 3 và 5 giữ nguyên.

## Còn lại trong spike

- [ ] Công thức trong dòng chữ (`Text` + `Image`, căn baseline) trên simulator iOS 17 và 26
- [ ] `UITextView` + `NSTextAttachment` (chip, Backspace trả lại LaTeX)
- [ ] Port `closestIndexToPoint` và vẽ con trỏ trên một công thức
- [ ] SSE bằng `URLSession.bytes` với server thật
- [ ] Chạy lại phép đo với dữ liệu production
