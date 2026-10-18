# Kế hoạch app Android native cho MathMate

Tiến độ theo dõi ở [mobile-android-checklist.md](mobile-android-checklist.md).

App Android viết bằng Kotlin + Jetpack Compose (Material 3), Android 8.0+ (minSdk 26). Phạm vi giống app iOS: ngang bằng web ngay từ bản đầu, kể cả trình soạn công thức, không dùng WebView. App iOS đi trước nên bản Android **port từ app iOS**, giữ cùng kiến trúc, cùng tên lớp và cùng cách làm; phần nào giống thì [mobile-ios-plan.md](mobile-ios-plan.md) là tài liệu gốc (bảng tính năng §1, backend §3, hiển thị toán §6, ô soạn tin §7, trình soạn công thức §8, chat và hình vẽ §9).

## 1. Phạm vi

Giống bảng §1 của plan iOS (chỉ phần dành cho học sinh; trang quản trị vẫn dùng web). Phần native thay cho phần riêng của iOS:

| iOS | Android |
|---|---|
| Liquid Glass (iOS 26) + material | Material 3, màu thương hiệu (xanh `#2563EB`, tối `#60A5FA`), không dùng màu động của hệ thống |
| Keychain | `SharedPreferences` riêng của app, token mã hóa bằng khóa AES trong Android Keystore; loại khỏi sao lưu (`data_extraction_rules.xml`) |
| VisionKit chụp đề | ML Kit Document Scanner (Google Play services), dự phòng bằng camera thường |
| `PhotosPicker` | Photo Picker của hệ thống (không cần quyền) |
| APNs | FCM (Firebase Cloud Messaging) |
| Live Activity | Thông báo tiến độ (foreground) khi đang vẽ — làm sau |
| iPad chia cột | Màn rộng (tablet, gập): danh sách | chat | hình vẽ bằng Material 3 adaptive — làm sau |
| `UITextView` + `NSTextAttachment` | `EditText` + `ReplacementSpan` (chip công thức) |
| `Text` + `Image` (công thức trong dòng) | `TextView` + `ReplacementSpan` vẽ công thức đúng baseline |

## 2. Quyết định kỹ thuật

- **Kotlin 2.2, AGP 8.13, Gradle 8.14, Compose BOM 2025.12**, compileSdk 36, targetSdk 36, minSdk 26. Một module `app`; Core (API, job, codec toán) nằm trong package `core`, không phụ thuộc giao diện, test được trên JVM.
- **Thư viện:** OkHttp (HTTP và SSE, tự đọc từng dòng bằng `SseParser` như iOS), kotlinx.serialization (JSON snake_case qua `JsonNamingStrategy.SnakeCase`), coroutines, Navigation Compose, Media3 ExoPlayer (video). Không dùng WebView.
- **Trạng thái:** các store (`SessionStore`, `ConversationsStore`, `ChatStore`) dùng snapshot state của Compose (`mutableStateOf`, `mutableStateMapOf`), giống `@Observable` trên iOS; coroutine scope được truyền vào để test trên JVM.
- **Cấu hình build:** Debug gọi `http://10.0.2.2:8000` (máy tính, nhìn từ emulator; cho phép HTTP chỉ trong bản debug qua `network_security_config`), Release gọi `https://mathmate.tonyvibecode.com`. UI test truyền `uiTesting` và `api` qua intent.
- **Dữ liệu dùng chung:** task `syncSharedData` chép `shared/symbols.json` và `shared/formula_templates.json` vào assets lúc build; unit test đọc `shared/fixtures/math_cases.json`. Sửa ở `shared/`, không sửa trong app.
- **Ngôn ngữ:** giao diện tiếng Việt; chỉ ghi "MathMate" hoặc "AI", không bao giờ ghi tên nhà cung cấp AI.

## 3. Backend

Phần lớn đã có từ giai đoạn 0 của iOS: `X-Client: android` (`api/deps.py` `APP_CLIENTS`), token Bearer, `X-Guest-Id`, xóa tài khoản.

1. **Phiên bản tối thiểu (đã làm):** `GET /api/app-config` trả thêm `min_android_build` (`GEO_DRAW_MIN_ANDROID_BUILD`, so với `versionCode`) và `android_store_url` (`ANDROID_PLAY_STORE_URL`).
2. **Thông báo đẩy (giai đoạn 7):** `devices.platform` nhận `android`, token FCM; `PushNotifier` gửi qua FCM HTTP v1 (khóa service account), cùng điều kiện `watched_at_end` như APNs. Cần một project Firebase và `google-services.json` (không commit).

## 4. Hiển thị toán: fork AndroidMath

Không có SwiftMath cho Android. Dùng [AndroidMath](https://github.com/gregcockroft/AndroidMath) (MIT), bản Kotlin của iosMath — tổ tiên của SwiftMath, **cùng kiến trúc** (`MTMathList`, `MTMathListBuilder`, `MTTypesetter`, `MTMathListDisplay`, `MTCTLineDisplay`…). Nhờ vậy phần soạn thảo của fork SwiftMath (`MTMathEditor`, `MTMathList+Editing`, `MTDisplay+Editing`) port sang gần như từng dòng. AndroidMath đọc font OpenType MATH bằng FreeType (JNI, build bằng NDK) và có sẵn TeX Gyre Termes.

- **Fork:** `xuanthinhJB/AndroidMath`, nhánh `mathmate`, giống `xuanthinhJB/SwiftMath@mathmate`. Bản làm việc nằm cạnh repo (`../AndroidMath`, như `../SwiftMath`). `settings.gradle.kts` tự dùng bản đó qua composite build (`includeBuild`) khi thư mục tồn tại; nếu không có thì lấy artifact JitPack `com.github.xuanthinhJB:AndroidMath` (phiên bản trong `gradle/libs.versions.toml`). `-Pmathmate.jitpack` buộc dùng JitPack.
- **Spike cú pháp (2026-10-17):** bản upstream đọc được **96/104** mẫu (85 mẫu trong `shared/formula_templates.json` + 19 ca `latexToPlain`), giống SwiftMath 1.7.3 trước khi fork. Thiếu: `\overrightarrow`, cung `\overset{\frown}{…}`, `\backsim`, `\varnothing`, `cases` không có `&`. Thử thêm các lệnh gia sư hay dùng: thiếu `\dfrac`/`\tfrac`, `\implies`, `\leqslant`/`\geqslant`, `\dots`, `\stackrel`, `\overparen`, `\boxed`, `\cancel`. Chưa đo trên câu trả lời thật (cần dữ liệu người dùng, chỉ đọc).
- **Đã làm trong fork** (nhánh `mathmate`, commit `42f10c7`, JitPack `com.github.xuanthinhJB:AndroidMath:42f10c7`): **104/104** mẫu; vẽ được cả 85 mẫu và 25 công thức mẫu trên emulator (xem bằng mắt: đúng).
  - Lệnh: `\dfrac`/`\tfrac`, `\overrightarrow`/`\overleftarrow`/`\overleftrightarrow`, cung (`\overset{\frown}`, `\stackrel{\frown}`, `\overparen`, `\wideparen`, xuất lại thành `\overset{\frown}{…}` như web), `\backsim`, `\frown`, `\smile`, `\varnothing`, `\implies`, `\impliedby`, `\leqslant`, `\geqslant`, `\nparallel`, `\dots`, `cases` một cột.
  - `MTAccent.name` giữ lệnh gốc: `\widehat` không thành `\hat`, `\overrightarrow` không thành `\vec`. Accent rộng và mũi tên co giãn theo nội dung, kéo glyph ngang (`MTGlyphDisplay.scaleX`) khi biến thể lớn nhất vẫn ngắn.
  - Chữ Unicode: giữ mọi chữ trong `\text{…}` (tiếng Việt), ký hiệu Unicode trong công thức thành lệnh (≥ → `\geq`); chữ font toán không có thì vẽ bằng font serif của hệ thống (Noto Serif), như CoreText tự lấy font dự phòng trên iOS. Upstream bỏ hết ký tự ngoài ASCII.
  - `f'` thành `f^{\prime}` như TeX (upstream và SwiftMath đều bỏ dấu `'`, nên mẫu `f'(…)` trên iOS cũng mất dấu phẩy trên — cần sửa bên fork SwiftMath).
  - Sửa lỗi `findVariantGlyph` trả glyph 0 (`.notdef`); test library không còn lọt vào app; C++ runtime tĩnh (APK release 52 MB → 9 MB).
  - Soạn thảo (package `com.agog.mathdisplay.edit`): `MTMathListIndex` (có `INNER_LIST`), `MTMathListEditing`, `MTDisplayEditing` (chạm → chỉ số, chỉ số → vị trí con trỏ), `MTMathEditor`; 15 test JVM port từ `MathEditorTests` của fork SwiftMath, ra đúng cùng LaTeX.
- **Trong app:** `MathRenderer` dựng `MTMathListDisplay` (cache theo latex + cỡ chữ + màu), `MathSpan` (`ReplacementSpan`) đặt công thức đúng baseline trong `TextView`, công thức khối cuộn ngang khi quá rộng; không vẽ được thì hiện mã LaTeX bằng font monospace.

## 5. Cấu trúc thư mục `mobile/android/`

```
mobile/android/
  settings.gradle.kts      composite build với ../AndroidMath
  gradle/libs.versions.toml
  app/
    src/main/java/com/tvcsoft/mathmate/
      MathMateApplication.kt  AppContainer (ApiClient + các store), TestingOptions
      MainActivity.kt
      core/
        api/       Models.kt (theo api/schemas.py), ApiClient.kt (OkHttp, Bearer, X-Guest-Id, SSE), ApiError
        auth/      Credentials (Keystore), SessionStore
        jobs/      SseParser
        chat/      ChatStore (= ChatProvider), ConversationsStore
        math/      MathNormalizer, LatexToPlain, MessageTextCodec, MathBlocks
        SharedData.kt
      ui/
        theme/  auth/  conversations/  chat/  math/  composer/  formula/  drawing/  settings/
    src/test/         JUnit trên JVM: fixtures dùng chung, ApiClient (MockWebServer), các store
    src/androidTest/  Compose UI test với web/e2e/server.py (API thật + AI giả)
```

## 6. Kiểm thử

- **Unit test (JVM):** `MathNormalizer`, `LatexToPlain`, `MessageTextCodec` qua `shared/fixtures`; `SseParser`; `ApiClient`, `SessionStore`, `ChatStore` (gồm mất kết nối giữa chừng) với MockWebServer. Chạy: `./gradlew :app:testDebugUnitTest`.
- **Fork AndroidMath:** test JVM cho parser, serializer và mô hình soạn thảo (`./gradlew :mathdisplaylib:testDebugUnitTest` trong `../AndroidMath`); test trên thiết bị cho typeset và hit-test.
- **UI test (Compose):** chạy với `web/e2e/server.py` trên máy (emulator gọi `10.0.2.2`), đề bài không phải hình học để không phải render Manim, giống Playwright và XCUITest.

## 7. Lộ trình

| Giai đoạn | Nội dung |
|---|---|
| 0 | Backend: `min_android_build`; sau này FCM |
| 1 | Spike: fork AndroidMath, độ phủ cú pháp, vẽ công thức trên thiết bị, công thức trong dòng chữ |
| 2 | Nền tảng: project, theme, Core, đăng nhập/đăng ký/dùng thử, danh sách, cài đặt |
| 3 | Chat: stream, `MathText`, TutorBar, các action, sao chép/sửa tin, ảnh, quota và lỗi |
| 4 | Composer: chip công thức, thanh ký hiệu, ảnh (chọn, chụp, dán) |
| 5 | Trình soạn công thức: port `MTMathEditor`, canvas + con trỏ, bàn phím toán, thư viện mẫu |
| 6 | Hình vẽ: bảng, phiên bản, chỉnh hình, zoom, video, chia sẻ |
| 7 | Native: FCM, cache offline, màn rộng |
| 8 | QA, Play Console (nhãn an toàn dữ liệu, xếp hạng nội dung), phát hành |
