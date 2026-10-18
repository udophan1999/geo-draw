# Checklist tiến độ app Android

Kế hoạch ở [mobile-android-plan.md](mobile-android-plan.md); app iOS là bản gốc để port ([mobile-ios-checklist.md](mobile-ios-checklist.md)). Đánh `[x]` khi xong và ghi mã commit hoặc ngày bên cạnh.

**Ký hiệu:** ⚠️ rủi ro cao · 📱 cần máy Android thật hoặc tài khoản Google Play/Firebase · 🔁 phải làm cả trên web/iOS để giữ ngang bằng

---

## Giai đoạn 0: Backend

- [x] `X-Client: android` dùng chung đường token Bearer / `X-Guest-Id` với iOS (có từ trước)
- [x] `GET /api/app-config` trả thêm `min_android_build`, `android_store_url` (+ test, `.env.example`)
- [ ] `devices.platform = android` + gửi push qua FCM HTTP v1 (giai đoạn 7)

## Giai đoạn 1: Spike

- [x] Chọn thư viện toán: fork AndroidMath (`xuanthinhJB/AndroidMath@mathmate`), bản làm việc ở `../AndroidMath`, composite build
- [x] Fork `xuanthinhJB/AndroidMath`, nhánh `mathmate` (`42f10c7`); JitPack build được, app build từ artifact (`-Pmathmate.jitpack`) qua (2026-10-18)
- [x] ⚠️ Độ phủ cú pháp (parser): 96/104 mẫu với upstream → 104/104 với fork; danh sách lệnh ở plan §4
- [ ] ⚠️ Đo trên câu trả lời thật của gia sư (dữ liệu người dùng, chỉ đọc; cần bạn cho phép)
- [x] ⚠️ Fork: lệnh còn thiếu (`\dfrac`, `\overrightarrow`, cung, `\backsim`, `\varnothing`, `cases` không `&`, `\implies`, `\leqslant`, `\dots`…) → 104/104 (2026-10-17)
- [x] ⚠️ Fork: accent rộng và mũi tên co giãn (`scaleX`), xuất LaTeX đúng (`\widehat`, `\overrightarrow`) (2026-10-17)
- [x] Vẽ công thức trên emulator: 104 mẫu, xem bằng mắt (TeX Gyre Termes, chữ tiếng Việt) (2026-10-17)
- [x] Công thức trong dòng chữ (`ReplacementSpan`, đúng baseline, xuống dòng cùng chữ) (2026-10-17)

## Giai đoạn 2: Nền tảng

- [x] Project Gradle (Kotlin DSL, version catalog, wrapper 8.14.3), `app` Compose, minSdk 26
- [x] `scripts/dev_android.sh` (`run` / `test` / `unit` / `open`): tự chọn JDK 17, mở emulator, `10.0.2.2` cho emulator và `adb reverse` cho máy thật (2026-10-18)
- [x] Icon thích ứng từ `web/public/logo.svg` (có icon đơn sắc cho Android 13+)
- [x] Debug/Release với `API_BASE_URL`; HTTP thường chỉ cho phép trong bản debug
- [x] `Models.kt` (kotlinx.serialization, snake_case), `ApiClient` (X-Client, Bearer, X-Guest-Id, lỗi tiếng Việt, multipart, SSE)
- [x] `KeystoreCredentials` (token mã hóa AES-GCM bằng Android Keystore), loại khỏi sao lưu
- [x] `SessionStore`, `ConversationsStore`, `ChatStore` (theo lại job khi rớt mạng)
- [x] Codec toán: `MathNormalizer`, `LatexToPlain`, `MessageTextCodec`, `MathBlocks` qua `shared/fixtures`
- [x] 24 unit test JVM (fixtures dùng chung, ApiClient với MockWebServer, các store, SSE)
- [x] 62 test JVM trong fork (39 của upstream + 7 ký hiệu sách giáo khoa + 15 trình soạn công thức + spike)
- [x] 8 test trên emulator với `web/e2e/server.py`: vẽ 85 mẫu + 25 công thức, khách hỏi và stream, lỗi AI, sai mật khẩu, tên trùng + gợi ý, trình soạn ra `\frac{1}{2}`, chip `$…$` + Backspace, hình vẽ bằng parser + chỉnh hình ra phiên bản 2
- [x] APK release 9 MB (C++ runtime tĩnh, strip symbol, bỏ 2 font không dùng)
- [x] Theme Material 3 theo màu web, sáng/tối (2026-10-17)
- [x] Màn chào: đăng nhập (401/429/403), đăng ký (gợi ý tên khi trùng), dùng thử (2026-10-17)
- [x] Danh sách cuộc trò chuyện: kéo để làm mới, đổi tên, xóa (xác nhận), cuộc mới, nhắc khách đăng nhập (2026-10-17)
- [x] Cài đặt: cách vẽ/mô hình/chất lượng/video, quy ước vẽ, lượt AI, đăng xuất, xóa tài khoản (2026-10-17)
- [x] Màn "Cập nhật MathMate" khi `versionCode` < `min_android_build` (2026-10-17)

## Giai đoạn 3: Chat

- [x] `MathText`: Markdown đơn giản + công thức trong dòng + công thức khối cuộn ngang (2026-10-17)
- [x] Bong bóng học sinh/gia sư, ảnh trong bong bóng (tải kèm phiên đăng nhập) (2026-10-17)
- [x] Stream `delta`, nhãn tiến độ, `$` chưa đóng hiện thành chữ (2026-10-17)
- [x] `TutorBar`: Gợi ý/Lời giải (hỏi xác nhận), 5 chấm bậc, "Gợi ý sâu hơn", "Đã giải xong" (2026-10-17)
- [x] Tin lỗi AI, hết quota (429), máy chủ chưa có khóa AI (503), `figure_skipped` (2026-10-17)
- [x] Sao chép tin nhắn (giữ `$latex$`), sửa tin cuối (2026-10-17)
- [x] Bài mẫu khi chat trống (2026-10-17)
- [x] Theo lại job khi app quay lại từ nền (2026-10-17)

## Giai đoạn 4: Composer

- [x] `EditText` + chip công thức (`ReplacementSpan`), `MessageTextCodec` hai chiều (2026-10-17)
- [x] Gõ `$…$` thành chip, Backspace ngay sau trả lại `$latex$`, dán `$…$` thành chip (2026-10-17)
- [x] Chạm chip để sửa trong trình soạn công thức (2026-10-17)
- [x] Thanh ký hiệu (`shared/symbols.json`) (2026-10-17)
- [x] 🔁 Nút √ và ∛ của thanh ký hiệu mở trình soạn công thức với căn có sẵn ô trống (`template` trong `shared/symbols.json`); căn luôn là chip công thức (không thành chữ √123 vì không thấy căn đến đâu); web và iOS làm giống (2026-10-18)
- [x] Ảnh: Photo Picker, camera (`TakePicture`), dán ảnh; nén JPEG ≤ 2048 px (2026-10-17)
- [ ] ML Kit Document Scanner (cắt và làm phẳng trang như VisionKit)
- [x] Bàn phím rời: Enter gửi, Shift+Enter xuống dòng (bỏ qua khi bộ gõ đang ghép chữ) (2026-10-17)
- [x] "Vẽ hình" khi chưa có bảng hình vẽ (2026-10-17)

## Giai đoạn 5: Trình soạn công thức ⚠️

- [x] Fork: `MTMathListIndex` (+ `innerList`), `MTMathList+Editing`, `MTDisplay+Editing`, `MTMathEditor` + test JVM (2026-10-17)
- [x] Canvas công thức: con trỏ, ô trống tại con trỏ tô đen, chạm để đặt con trỏ, bàn phím rời gõ được (2026-10-17)
- [ ] Con trỏ nhấp nháy (hiện đứng yên)
- [ ] Đo thử chạm vào phân số/căn/mũ trên thiết bị (test hit-test trên emulator)
- [x] Bàn phím toán 4 trang + trang Mẫu (7 tab từ `shared/`) (2026-10-17)
- [x] Chế độ "Sửa LaTeX" (bảng như `cases` mở ở đây) (2026-10-17)
- [x] `LatexToPlain` khi chèn: công thức đơn giản thành chữ Unicode (2026-10-17)
- [ ] TalkBack đọc được phím và công thức

## Giai đoạn 6: Hình vẽ

- [x] Thẻ hình vẽ trong chat, bảng hình vẽ dạng bottom sheet (2026-10-17)
- [x] Phiên bản, "Yêu cầu chỉnh hình", "Vẽ lại" khi lỗi, nhãn tiến độ (2026-10-17)
- [x] Phóng to/kéo, chạm hai lần, nút −/vừa khung/+ (2026-10-17)
- [x] Video (Media3), chia sẻ/lưu hình (2026-10-17)

## Giai đoạn 7: Native

- [ ] 📱 FCM: xin quyền thông báo (Android 13+) lúc hợp lý, đăng ký token, mở đúng cuộc trò chuyện khi chạm
- [ ] Cache offline danh sách và tin nhắn
- [ ] Màn rộng: danh sách | chat | hình vẽ
- [ ] Haptics

## Giai đoạn 8: QA và phát hành 📱

- [ ] UI test Compose với `web/e2e/server.py`: dùng thử, đăng nhập sai, đăng ký + gợi ý, chat, công thức, hình vẽ
- [ ] Kiểm tra: chữ lớn nhất, TalkBack, màn nhỏ, chế độ tối, mạng chập chờn
- [ ] Ký app (keystore upload, không commit), Play App Signing
- [ ] Play Console: mô tả tiếng Việt, ảnh chụp, nhãn an toàn dữ liệu, xếp hạng nội dung (học sinh, nội dung AI), chính sách quyền riêng tư, tài khoản demo
- [ ] Thử nội bộ → thử kín → phát hành

## Việc lặt vặt

- [x] Cập nhật `CLAUDE.md`: mục `mobile/android/`, cách build/test, fork AndroidMath (2026-10-17)
- [ ] Lỗi đã thấy một lần: gửi phím (adb `input text`) khi chưa chạm ô soạn tin, trong lúc chuyển màn, làm màn hình trắng; chưa tái hiện được
