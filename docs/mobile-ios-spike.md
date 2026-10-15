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

## App spike trên simulator

`mobile/ios/Spikes/UISpike` (XcodeGen: `xcodegen generate`; chạy một màn bằng `-screen inline|composer|sse`). Đã chạy trên iPhone 15 (iOS 17.2) và iPhone 17 Pro (iOS 26.5).

| Hạng mục | Kết quả |
|---|---|
| Công thức trong dòng chữ | `Text` + `Text(Image)` qua interpolation, `baselineOffset(-descent)`: công thức nằm đúng baseline và xuống dòng cùng chữ; Markdown đậm, hệ phương trình, phân số, cung, vectơ, tích phân, chữ tiếng Việt đều đúng; `$` chưa đóng (đang stream) giữ nguyên là chữ. Giống hệt nhau trên iOS 17 và 26 |
| Công thức khối | Ảnh trong `ScrollView` ngang; công thức quá dài cuộn được, không làm vỡ bố cục |
| Liquid Glass | `mmGlass(in:)`: `glassEffect` trên iOS 26, `.ultraThinMaterial` trên iOS 17. Build và chạy được trên cả hai |
| Ô soạn tin | `UITextView` + `FormulaAttachment`: gõ `$…$` thành chip, Backspace ngay sau đó trả lại `$latex$`, Backspace về sau xóa cả chip, dán `$…$` thành chip, xuất `$latex$` khớp web. 3 XCUITest qua trên cả iOS 17 và 26 (`UITests/ComposerTests.swift`). Quy tắc dùng `NSRegularExpression` (đo UTF-16 như `NSTextStorage`) |
| Con trỏ trong công thức | Port `MTDisplay+Editing` của kostub/MathEditor (MIT) vào fork: `closestIndex(to:)` và `caretPosition(for:)` cho dòng chữ, phân số, căn, mũ/chỉ số. Chạm vào công thức trên simulator đặt con trỏ đúng chỗ, kể cả lồng nhiều cấp (tử số → căn → trước Δ: `[2, 4:[3, 6:[0]]]`). 6 test trong fork + 1 XCUITest (`UITests/CursorTests.swift`) qua trên iOS 17 và 26 |
| SSE | `URLSession.bytes` + `SSEParser` tự viết, với `web/e2e/server.py` (API thật, AI giả): lấy guest id qua `X-Guest-Id`, nhận 110 `delta` và các sự kiện `message`/`progress`/`conversation`/`done`, câu trả lời hiển thị dần |

Fork cần thêm vài thay đổi để app tự vẽ và chỉnh công thức: `MTTypesetter.createLineForMathList(_:font:style:)` (`e7af82a`), `MTDisplay.position`/`textColor` (`61d0237`) thành `public`, và phần chỉnh sửa (`f09276c`). Khác với iosMath, SwiftMath tính bề rộng của chữ có số mũ bao luôn số mũ, nên khi hai khung chồng nhau thì số mũ được ưu tiên, và vị trí con trỏ trên một dòng đo bằng CTLine.

Cần chỉnh khi làm thật:
- Công thức khối nên căn giữa khi vừa màn hình (hiện căn trái).
- Cỡ chữ công thức hơi nhỏ hơn chữ thường (Termes có x-height thấp hơn SF): thử nhân khoảng 1,1.
- `MathSegments` của spike chỉ tách `$`/`$$`; bản thật phải chạy `MathNormalizer` (port `normalizeMath`) trước và qua `shared/fixtures`.
- `MTDisplay.position` là trạng thái dùng chung: vẽ ở một chỗ rồi hit-test ở chỗ khác sẽ lệch. Bản thật nên giữ display ở gốc 0 và chỉ dịch context khi vẽ.

## Kết luận spike

**Làm tiếp, không đổi hướng.** Bốn rủi ro lớn của giai đoạn 1 đều đã có lời giải chạy được trên iOS 17 và 26: hiển thị công thức (fork SwiftMath + TeX Gyre Termes, 104/104 và 134/134), công thức trong dòng chữ, ô soạn tin có chip, con trỏ trong công thức, và SSE với server thật.

Ước lượng giai đoạn 5 (trình soạn công thức) giữ ở 4–6 tuần: phần hit-test và con trỏ đã có; còn lại là thao tác trên `MTMathList` (chèn, xóa theo cấu trúc, placeholder; tham khảo `MTMathList+Editing` và `MTEditableMathLabel` của MathEditor), bàn phím toán và thư viện mẫu.

## Còn lại

- [ ] Đo lại với dữ liệu production (cần một bản backup)
