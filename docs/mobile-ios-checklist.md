# Checklist tiến độ app iOS

Kế hoạch chi tiết nằm ở [mobile-ios-plan.md](mobile-ios-plan.md); các số `§` ở dưới trỏ về file đó. Mỗi việc nên làm xong trong khoảng nửa ngày đến hai ngày. Đánh `[x]` khi xong và ghi mã commit, PR hoặc ngày bên cạnh.

**Ký hiệu:** ⚠️ rủi ro cao · 🍎 cần tài khoản Apple Developer hoặc iPhone thật · 🔁 phải làm cả trên web để giữ ngang bằng

---

## Giai đoạn 0: Backend (§3)

### Xác thực cho app
- [x] Token Bearer: `login`/`register` trả `token` khi có `X-Client: ios`; `get_owner` và `logout` đọc `Authorization: Bearer` (`ce46382`)
- [x] Guest id qua header `X-Guest-Id`; server cấp id mới qua header phản hồi, không đặt cookie (`ce46382`)
- [x] Hạn của session: hết hạn sau 90 ngày không dùng, `last_used` ghi tối đa mỗi giờ một lần (`9154f21`)
- [ ] Quyết định nhánh đích cho PR: `dev` hay `master`

### Tài khoản
- [x] `DELETE /api/auth/me`: hỏi lại mật khẩu, tính vào khóa đăng nhập, chặn quản trị viên cuối cùng (`8e6586d`)
- [x] 🔁 Nút "Xóa tài khoản" trong phần Cài đặt của web (`56921ef`)

### Thông báo đẩy
- [x] Bảng `devices` + `POST/DELETE /api/devices` (`3b5074f`)
- [x] `PushNotifier` + `ApnsClient` (HTTP/2, JWT ES256), xóa token chết (`3b5074f`)
- [x] Gửi push khi job kết thúc mà không ai xem (`watched_at_end`) (`3b5074f`)
- [x] `migrate_sqlite` chép cả bảng `devices`; sửa luôn lỗi mất `role`/`daily_limit` khi chép (`6c8e0dc`)

### Cấu hình app và dữ liệu dùng chung
- [x] `GET /api/app-config` trả `{min_ios_build, ios_store_url}`, kèm test (`e283c6b`)
- [x] Tạo `shared/formula_templates.json` từ `formulaTemplates.ts`; 🔁 web import từ JSON (alias `@shared`)
- [x] Tạo `shared/symbols.json` từ `SYMBOLS` trong `MathInput.tsx`; 🔁 web import từ JSON
- [x] Tạo `shared/fixtures/math_cases.json` cho `normalizeMath`, `latexToPlain`, `toMessageText`; 🔁 test web `e2e/shared-fixtures.spec.ts` đọc fixtures này
- [ ] 🔁 Lỗi: hai chip công thức liền nhau xuất ra `$x$$y$`, dễ bị hiểu thành `$$` (công thức khối). Cần quyết định cách tách (ví dụ thêm khoảng trắng) rồi thêm ca này vào fixtures
- [ ] `latexToPlain` chưa đổi `\backsim` (mẫu "Tam giác đồng dạng" nên vẫn là chip); thêm vào nếu muốn hiện thành `∽`
- [x] Cập nhật `CLAUDE.md` (mục `shared/`, `app-config`, hạn session)
- [ ] Mở PR cho giai đoạn 0

---

## Giai đoạn 1: Spike rủi ro (§6, §7, §8): quyết định làm tiếp hay đổi hướng

- [x] ⚠️ Project thử với SwiftMath, render toàn bộ 7 tab mẫu công thức: 104/104 với fork, xem [mobile-ios-spike.md](mobile-ios-spike.md)
- [x] ⚠️ Kiểm tra riêng các lệnh: upstream `main` đã có `\overrightarrow`, `\dfrac`, `\varnothing`, `cases`; fork thêm cung và `\backsim`
- [x] ⚠️ Đo trên câu trả lời thật (local: 51 câu, 134 công thức): 134/134 với upstream `main`
- [ ] Đo lại với dữ liệu production (từ bản backup, chỉ đọc)
- [x] ⚠️ Fork SwiftMath (`xuanthinhJB/SwiftMath@mathmate`, `8da9a4e`): cung `\overset{\frown}`, `\backsim`; chọn font TeX Gyre Termes (đủ tiếng Việt)
- [ ] Công thức trong dòng chữ: `Text` + `Image` căn baseline, xuống dòng đúng, cả sáng/tối và Dynamic Type
- [ ] `UITextView` + `NSTextAttachment`: chèn chip, Backspace trả lại `$latex$`, xuất `toMessageText`
- [ ] ⚠️ Con trỏ trong trình soạn công thức: lấy toạ độ atom từ `MTMathListDisplay`; tham khảo kostub/MathEditor
- [ ] SSE bằng `URLSession.bytes`: đọc đủ `delta`, kết nối lại sau khi app vào nền
- [ ] **Kết luận spike**, ghi vào plan: danh sách luật viết lại LaTeX, có cần fork SwiftMath không, ước lượng lại giai đoạn 5

---

## Giai đoạn 2: Nền tảng (§2, §4, §5)

### Project
- [ ] Tạo `mobile/ios/MathMate.xcodeproj`: iOS 17+, Swift 6, SwiftUI lifecycle, bundle id
- [ ] Thêm SwiftPM: SwiftMath, swift-markdown, swift-snapshot-testing
- [ ] `Localizable.xcstrings` (vi), `PrivacyInfo.xcprivacy`, icon app, màn hình khởi động
- [ ] Cấu hình build Debug/Release với `API_BASE_URL` (máy local / production)
- [ ] Cập nhật `.gitignore` cho Xcode (`xcuserdata`, `DerivedData`)

### Design system
- [ ] `mmGlass(in:interactive:)`, `MMGlassContainer`, `mmGlassID`, mỗi cái có phương án dự phòng cho iOS 17
- [ ] Màu (theo `index.css` của web), cỡ chữ, `Brand` ("MathMate"), haptics
- [ ] Preview mỗi component ở 4 tổ hợp: iOS 26 / 17 × sáng / tối

### Core
- [ ] `Models.swift`: Codable cho `Me`, `Conversation`, `Message`, `Settings`, `Example`, `Progress`, `APIError` (`detail` + `suggestions`)
- [ ] `APIClient`: async/await, tự gắn `X-Client`, `Authorization`, `X-Guest-Id`; lưu `X-Guest-Id` mới
- [ ] `Keychain`: token và guest id (giữ lại sau khi cài lại app)
- [ ] `SSEParser` + `JobFollower` (`AsyncStream<JobEvent>`), có unit test
- [ ] `ImageLoader` có header auth và cache theo `?v=`

### Màn hình
- [ ] `SessionStore` (`@Observable`): `me`, `quota`, trạng thái đăng nhập / khách
- [ ] Đăng nhập: lỗi 401, khóa 429, tài khoản bị khóa 403
- [ ] Đăng ký: gợi ý tên khi trùng (409), chạm gợi ý thì điền vào ô
- [ ] "Dùng thử không cần tài khoản" + nhắc "Đăng nhập để lưu lại lịch sử hỏi đáp"
- [ ] Danh sách cuộc trò chuyện: kéo để làm mới, đổi tên, xóa (vuốt + xác nhận), cuộc mới
- [ ] Bài mẫu khi chat trống (`/api/examples`)
- [ ] Cài đặt: mode/model/quality/animate, quy ước vẽ (`/api/help`), đăng xuất (gọi `DELETE /api/devices` trước)
- [ ] Xóa tài khoản trong Cài đặt (hỏi mật khẩu, xác nhận hai bước)
- [ ] Màn "Cập nhật MathMate" khi build cũ hơn `min_ios_build`

---

## Giai đoạn 3: Chat (§6, §9)

- [ ] `MathNormalizer`: port `normalizeMath`, chạy qua `shared/fixtures`
- [ ] `MathMarkdownView`: Markdown + công thức trong dòng + công thức khối cuộn ngang
- [ ] `MathImageCache` theo latex + cỡ chữ + màu + giao diện sáng/tối
- [ ] Phương án dự phòng khi SwiftMath không vẽ được: hiện mã LaTeX bằng font monospace
- [ ] `ChatStore`: `pending` (bong bóng tạm, nhãn tiến độ, `reply` từ `delta`), `figures`, theo dõi `figure_job`
- [ ] Stream mượt: tối đa khoảng 20 lần render/giây, chỉ parse lại đoạn cuối, `$` chưa đóng hiện thành chữ
- [ ] Kết nối lại khi app quay lại từ nền: xóa `reply` rồi dựng lại từ đầu
- [ ] Cuộc trò chuyện mới: chuyển sang cuộc vừa tạo khi job tạo ra nó
- [ ] `TutorBar`: Gợi ý/Lời giải (morph bằng `glassEffectID`), 5 chấm bậc gợi ý, "Gợi ý sâu hơn", "Đã giải xong"
- [ ] Các action `deeper`/`solution`/`hint`
- [ ] Tin lỗi AI (`meta.error`), hết quota (429), máy chủ chưa có khóa AI (503)
- [ ] Hiển thị quota còn lại
- [ ] Sao chép tin nhắn (giữ `$latex$`)
- [ ] ✏️ Sửa tin cuối: 409 khi gia sư đang trả lời; sửa tin đầu thì đổi đề và tên
- [ ] Gửi ảnh: `PhotosPicker`, nén JPEG, giới hạn kích thước
- [ ] Ảnh trong bong bóng của học sinh
- [ ] `figure_skipped`: báo lý do không vẽ hình

---

## Giai đoạn 4: Composer (§7)

- [ ] `ComposerTextView` (`UIViewRepresentable`), tự giãn chiều cao, có giới hạn tối đa
- [ ] `FormulaAttachment`: chip vẽ bằng SwiftMath, căn baseline
- [ ] `MessageTextCodec`: chuyển qua lại giữa ô soạn và `$latex$`/`\n`, chạy qua `shared/fixtures`
- [ ] Gõ `$…$` đóng lại thì thành chip
- [ ] Dán chữ có `$…$` thì thành chip; dán ảnh thì đính kèm
- [ ] Chạm chip để sửa trong trình soạn công thức
- [ ] Backspace ngay sau chip trả lại `$latex$`
- [ ] Return xuống dòng, nút gửi để gửi; bàn phím vật lý: Enter gửi, Shift+Enter xuống dòng (`UIKeyCommand`)
- [ ] Thanh ký hiệu (từ `shared/symbols.json`) dạng thanh glass trên bàn phím
- [ ] Nút 📎: Chụp đề (VisionKit) / Thư viện ảnh; xem trước và gỡ ảnh
- [ ] Kéo thả ảnh trên iPad
- [ ] Thanh soạn tin nổi dùng glass + `safeAreaInset`, né bàn phím đúng
- [ ] Nút "Vẽ hình" trong composer khi chưa có bảng hình vẽ

---

## Giai đoạn 5: Trình soạn công thức (§8) ⚠️ lớn nhất

### Mô hình
- [ ] `MathNode`: row, symbol, frac, sqrt/root, sup/sub, fence, accent, cases/matrix, text, placeholder
- [ ] `MathCursor`: vị trí, vùng chọn, đi trái/phải/lên/xuống theo cấu trúc
- [ ] `LatexSerializer` (cây → LaTeX)
- [ ] `LatexParser` cho tập LaTeX của các mẫu và `latexToPlain`; gặp lệnh lạ thì báo để chuyển sang chế độ sửa LaTeX thô
- [ ] Test vòng: parse rồi serialize phải ra như cũ, với mọi mẫu trong `shared/formula_templates.json`

### Thao tác
- [ ] Chèn mẫu: `#?` thành placeholder, `#@` lấy vùng chọn hoặc atom ngay trước con trỏ
- [ ] Sau khi chèn, nhảy tới placeholder đầu tiên; Tab sang placeholder kế tiếp
- [ ] Xóa theo cấu trúc (Backspace ở đầu tử số thì tách phân số, v.v.)
- [ ] Undo/redo, lắc máy để hoàn tác

### Hiển thị và nhập
- [ ] `EditorView`: render bằng SwiftMath, vẽ con trỏ và vùng chọn, chạm để đặt con trỏ
- [ ] Bàn phím toán (`inputView`) gồm 4 trang: `123`, `abc`, `∠△`, `f(x)`; phím di chuyển; nút chuyển sang bàn phím hệ thống
- [ ] Thư viện mẫu 7 tab (ô mẫu vẽ bằng SwiftMath) trong sheet glass
- [ ] Chế độ "Sửa LaTeX" thô, xem trước trực tiếp
- [ ] `LatexToPlain`: port `plainMath.ts`; công thức đơn giản thì chèn thành chữ Unicode
- [ ] Nhãn tiếng Việt cho mọi phím và tooltip

### Ngang bằng web
- [ ] Bảng so sánh: cùng thao tác trên web và iOS ra cùng LaTeX, cho mọi mẫu ở 7 tab
- [ ] VoiceOver đọc được công thức (dùng `accessibilityLabel` từ `latexToPlain` hoặc LaTeX)

---

## Giai đoạn 6: Hình vẽ (§9)

- [ ] Thẻ hình vẽ trong chat; chạm vào mở sheet (`.medium`/`.large`)
- [ ] iPad: cột thứ ba của `NavigationSplitView`
- [ ] Chọn phiên bản hình đang xem
- [ ] "Yêu cầu chỉnh hình" + danh sách yêu cầu đã gửi
- [ ] Nhãn tiến độ khi đang vẽ; "Vẽ lại" khi lỗi
- [ ] Phóng to / kéo hình (double-tap để zoom)
- [ ] Video bằng `AVPlayer`
- [ ] `ShareLink`: lưu vào Ảnh / gửi đi

---

## Giai đoạn 7: Tính năng native (§9)

### Thông báo đẩy 🍎
- [ ] Xin quyền thông báo vào lúc hợp lý (sau câu hỏi đầu tiên, không hỏi ngay khi mở app)
- [ ] Đăng ký token với `POST /api/devices`, gửi đúng `environment` (`#if DEBUG` → sandbox)
- [ ] Gửi lại token sau khi đăng nhập / đăng xuất / chuyển sang khách
- [ ] `willPresent`: ẩn banner khi đang mở đúng cuộc trò chuyện đó
- [ ] Chạm thông báo thì mở `conversation_id`
- [ ] 🍎 **Checklist APNs trên máy thật** (§3, "Checklist APNs khi chạy trên iPhone thật"):
  - [ ] Tạo khóa `.p8` và cất kỹ (chỉ tải được một lần)
  - [ ] App ID bật Push Notifications; Xcode thêm capability Push + Background Modes → Remote notifications
  - [ ] Điền `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_TOPIC`, `APNS_KEY` vào `.env` local
  - [ ] Thử trên iPhone với build từ Xcode (sandbox): nhận "MathMate đã trả lời"
  - [ ] Điền `APNS_*` vào managed config của Jenkins (production)
  - [ ] Thử lại với build TestFlight (production)

### Khác
- [ ] Live Activity khi đang vẽ (ActivityKit, Dynamic Island trên iOS 26)
- [ ] Cache offline bằng SwiftData: đọc lại danh sách và tin nhắn khi không có mạng
- [ ] Haptics: lên bậc gợi ý, gửi tin, vẽ xong
- [ ] iPad: `NavigationSplitView` ba cột, phím tắt bàn phím vật lý

---

## Giai đoạn 8: QA và phát hành (§10, §11)

### Kiểm thử
- [ ] Unit test: `MathNormalizer`, `LatexToPlain`, `MessageTextCodec`, parser/serializer, `SSEParser`, `ChatStore`
- [ ] Snapshot test: công thức, bong bóng, TutorBar ở 4 tổ hợp iOS 17/26 × sáng/tối
- [ ] XCUITest chạy với `web/e2e/server.py` (AI giả): đăng nhập, gửi câu hỏi, gợi ý sâu hơn, sửa tin, công thức
- [ ] CI cho iOS: Xcode Cloud hoặc GitHub Actions macOS + fastlane
- [ ] Kiểm tra thủ công: Dynamic Type lớn nhất, Reduce Transparency, VoiceOver, iPhone SE (màn nhỏ), iPad
- [ ] Kiểm tra mạng chập chờn: chuyển Wi-Fi ↔ 4G giữa lúc đang stream

### App Store 🍎
- [ ] Tài khoản Apple Developer, App ID, chứng chỉ, provisioning
- [ ] Trang App Store Connect: tên, mô tả tiếng Việt, ảnh chụp màn hình (6.9", 6.5", iPad), từ khóa
- [ ] Nhãn quyền riêng tư (ảnh, nội dung người dùng, định danh) khớp với `PrivacyInfo.xcprivacy`
- [ ] Mô tả quyền camera và thư viện ảnh bằng tiếng Việt
- [ ] Bộ câu hỏi xếp hạng tuổi (học sinh 11–18 tuổi, nội dung do AI tạo)
- [ ] URL chính sách quyền riêng tư và trang hỗ trợ
- [ ] Tài khoản demo cho Apple review + ghi chú về chế độ dùng thử
- [ ] TestFlight nội bộ → TestFlight cho một nhóm học sinh/giáo viên thử
- [ ] Nộp review → phát hành

---

## Việc lặt vặt

- [ ] Giữ bảng ngang bằng ở §1 của plan; mỗi tính năng mới cho học sinh trên web đều thêm một dòng vào checklist này
- [ ] Cập nhật `CLAUDE.md` khi có `mobile/ios/` (cách build, cách chạy test, quy ước)

## Sau này: Android (§13)

- [ ] Spike hiển thị toán trên Android (JLaTeXMath-android hoặc thư viện khác) với cùng tập công thức
- [ ] Thêm `platform: android` + FCM cho `devices` và `PushNotifier`
- [ ] Port Core (API, Jobs, Math codec) và mô hình FormulaEditor sang Kotlin
