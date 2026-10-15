# Kế hoạch app iOS native cho MathMate

App iOS viết bằng SwiftUI, dùng Liquid Glass trên iOS 26 và lui về material trên iOS 17–25. Phạm vi là ngang bằng web ngay từ bản đầu, kể cả trình soạn công thức. Android làm sau bằng Kotlin + Jetpack Compose.

## 1. Phạm vi: ngang bằng web

Danh sách tính năng lấy từ `web/src` (chỉ phần dành cho học sinh):

| Nhóm | Tính năng | Nguồn trên web |
|---|---|---|
| Tài khoản | Đăng nhập, đăng ký (gợi ý tên khi trùng, 409), khóa sau 5 lần sai (429), tài khoản bị khóa (403), dùng thử không cần tài khoản, đăng xuất | `routes/auth.tsx`, `lib/guest.ts` |
| Cuộc trò chuyện | Danh sách, đổi tên, xóa, cuộc mới, bài mẫu khi chat trống (`/api/examples`) | `Sidebar.tsx`, `ChatPage.tsx` |
| Gia sư | Stream câu trả lời (`delta`), Gợi ý/Lời giải, 5 bậc gợi ý, "Gợi ý sâu hơn", "Đã giải xong", tin lỗi AI (`meta.error`), hạn mức (429) và hiển thị quota | `TutorBar.tsx`, `lib/chat.tsx` |
| Tin nhắn | Markdown + LaTeX, sao chép (giữ `$latex$`), sửa tin cuối ✏️ (409 khi gia sư đang trả lời) | `MessageList.tsx`, `MathMarkdown.tsx`, `lib/math.ts` |
| Soạn tin | Công thức nằm trong dòng chữ (chip), gõ hoặc dán `$…$` thành chip, chạm chip để sửa, Backspace trả lại LaTeX, thanh ký hiệu, trình soạn công thức với 7 tab mẫu, `latexToPlain`, ảnh (chọn ảnh, dán, kéo thả) | `Composer.tsx`, `useMathEditor.tsx`, `MathInput.tsx`, `formulaTemplates.ts`, `plainMath.ts`, `messageText.ts` |
| Hình vẽ | Tự vẽ bài hình phẳng (`figure_job`/`figure_skipped`), nút "Vẽ hình", các phiên bản hình, "Yêu cầu chỉnh hình", "Vẽ lại" khi lỗi, phóng to, video | `DrawingPanel.tsx`, `ZoomImage.tsx` |
| Cài đặt | mode/model/quality/animate, quy ước vẽ (`/api/help`) | `SettingsDialog.tsx` |
| Phiên bản | Báo khi có bản mới | `lib/version.ts` (trên iOS thay bằng phiên bản tối thiểu) |

**Ngoài phạm vi:** trang quản trị (vẫn dùng web) và trình chỉnh hình thủ công (trên web đang ẩn bằng `SHOW_ADVANCED = false`).

**Thêm riêng cho iOS** (cũng giúp qua review của Apple):
- chụp đề bằng VisionKit
- thông báo đẩy khi vẽ xong hoặc gia sư trả lời xong lúc app chạy nền
- Live Activity khi đang vẽ
- chia sẻ hình
- haptics
- đọc lại lịch sử khi không có mạng
- giao diện chia cột trên iPad

## 2. Quyết định kỹ thuật

- **iOS 17+**, build bằng Xcode 26 / iOS 26 SDK, Swift 6 (strict concurrency), SwiftUI + Observation (`@Observable`). Dùng UIKit khi SwiftUI chưa đủ: ô soạn tin là `UITextView`, bàn phím toán là `inputView`.
- **Liquid Glass có phương án dự phòng.** Mọi chỗ dùng glass đi qua một lớp bọc duy nhất, để sau này nâng phiên bản tối thiểu thì chỉ phải sửa một chỗ:
  ```swift
  extension View {
      @ViewBuilder
      func mmGlass<S: Shape>(in shape: S, interactive: Bool = false) -> some View {
          if #available(iOS 26, *) {
              glassEffect(interactive ? .regular.interactive() : .regular, in: shape)
          } else {
              background(.ultraThinMaterial, in: shape)
          }
      }
  }
  ```
  Tương tự có `MMGlassContainer` (là `GlassEffectContainer` trên iOS 26, `Group` trên bản cũ) và `.mmGlassID(_:in:)`.
- **Thư viện (SwiftPM):**
  - [SwiftMath](https://github.com/mgriebling/SwiftMath) để vẽ LaTeX bằng CoreText
  - [swift-markdown](https://github.com/swiftlang/swift-markdown) để parse Markdown
  - [swift-snapshot-testing](https://github.com/pointfreeco/swift-snapshot-testing) cho snapshot test

  Không dùng WebView ở đâu cả.
- **Lưu trữ:** token trong Keychain; cache cuộc trò chuyện và tin nhắn bằng SwiftData để đọc offline.
- **Ngôn ngữ:** chuỗi tiếng Việt trong String Catalog (`Localizable.xcstrings`). Giao diện chỉ ghi "MathMate" hoặc "AI", không bao giờ ghi tên nhà cung cấp AI.

## 3. Giai đoạn 0: sửa backend (≈1 tuần)

Mọi thay đổi giữ nguyên hành vi của web (cookie) và có test trong `tests/`.

1. **Auth bằng token Bearer.** `get_owner` trong `api/deps.py` đọc `Authorization: Bearer <token>` trước, rồi mới đến cookie `geo_session`. Token dùng chung bảng sessions của `AccountStore`.
   - `login`/`register` trả thêm `token` trong body khi client gửi `X-Client: ios`. Web không đổi gì.
   - `logout` đọc token từ cả header lẫn cookie.
2. **Khách dùng thử không dùng cookie.** Middleware `guest_cookie` ưu tiên header `X-Guest-Id` (kiểm tra bằng `valid_guest_id`). Khi thiếu, server cấp id mới và trả lại qua header `X-Guest-Id`. App lưu id này trong Keychain để giữ lại cuộc trò chuyện sau khi cài lại app.
3. **Xóa tài khoản ngay trong app** (Apple bắt buộc theo guideline 5.1.1(v) khi app có đăng ký). Thêm `DELETE /api/auth/me` (yêu cầu nhập lại mật khẩu), dùng lại logic xóa của `admin.py`: `delete_owner`, xóa tài khoản và thư mục `users/<id>`.
4. **Thông báo đẩy** (đã làm, xem checklist bên dưới khi chạy trên máy thật):
   - Bảng `devices` (owner, apns_token, platform, updated_at), viết theo quy ước store (`?`, `ON CONFLICT`, `db.sql()`).
   - Thêm `POST/DELETE /api/devices`.
   - Một `PushSender` gửi APNs qua HTTP/2 với JWT ký bằng khóa `.p8`. Biến môi trường mới: `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_KEY_PATH`, `APNS_TOPIC`, `APNS_SANDBOX`.
   - Job vẽ hoặc job gia sư kết thúc mà không còn ai nghe SSE thì gửi push, kèm `conversation_id` để mở thẳng cuộc trò chuyện.
   - Không cấu hình APNs thì bỏ qua, giống cách `ai_available` đang hoạt động.
5. **Phiên bản tối thiểu:** thêm `GET /api/app-config` trả `{min_ios_build}`. App cũ hơn sẽ hiện màn "Cập nhật MathMate". Đây là bản iOS của `lib/version.ts`.
6. **Ghi rõ trong tài liệu:** SSE `/api/jobs/{id}/events` phát lại *mọi* sự kiện từ đầu ở mỗi lần kết nối (`sent = 0`) và giữ job 1 giờ. Vì vậy khi kết nối lại, client phải xóa phần `reply` đang có và dựng lại từ các `delta`.
7. **Ghi chú cho client:** `image_url`/`video_url` là đường dẫn tương đối và cần header auth, nên app tải ảnh bằng `URLSession` của chính nó (không dùng `AsyncImage`) và cache theo `?v=`.

### Checklist APNs khi chạy trên iPhone thật

Simulator không nhận được token APNs thật, nên mọi bước dưới đây cần iPhone thật và tài khoản Apple Developer trả phí.

1. **Khóa APNs (một lần):** developer.apple.com → Keys → "+" → bật *Apple Push Notifications service* → tải `AuthKey_<KEY_ID>.p8`. Apple chỉ cho tải **một lần**, nên phải cất kỹ, ví dụ trong trình quản lý mật khẩu.
2. **App ID:** bundle id (ví dụ `com.tonyvibecode.mathmate`) bật capability *Push Notifications*. Trong Xcode: target → Signing & Capabilities → `+ Push Notifications` và `+ Background Modes → Remote notifications`.
3. **Máy chủ:** điền `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_TOPIC` (= bundle id) và `APNS_KEY` (hoặc `APNS_KEY_PATH`) vào `.env` khi chạy trên máy, và vào managed config của Jenkins cho production. Sau đó khởi động lại server.
4. **Môi trường:** bản build chạy từ Xcode nhận token **sandbox**; TestFlight và App Store nhận token **production**. App gửi đúng `environment` khi gọi `POST /api/devices` (đọc `aps-environment` trong entitlements, hoặc dùng `#if DEBUG`). Gửi sai thì APNs trả `BadDeviceToken` và server xóa token đó.
5. **Mạng:** iPhone phải gọi được tới API (cùng Wi-Fi với máy chạy `uvicorn --host 0.0.0.0`, hoặc dùng domain production). Máy chủ phải ra được Internet tới `api.push.apple.com:443` và `api.sandbox.push.apple.com:443`.
6. **Kiểm tra:** đăng nhập trên iPhone, cho phép thông báo, gửi một câu hỏi rồi về màn hình chính. Thông báo "MathMate đã trả lời" phải hiện ra; chạm vào thì mở đúng cuộc trò chuyện. Nếu không thấy, đọc log `mathmate.push` trên máy chủ.

## 4. Cấu trúc thư mục `mobile/ios/`

```
mobile/ios/
  MathMate.xcodeproj
  MathMate/
    App/                MathMateApp, AppDelegate (APNs), Router (deep link /c/:id)
    DesignSystem/       Glass.swift (mmGlass…), Colors, Typography, Haptics, Brand
    Core/
      API/              APIClient (async/await, Bearer, X-Guest-Id), Models.swift (Codable theo api/schemas.py), APIError (detail + suggestions)
      Jobs/             SSEParser (event:/data:), JobFollower (AsyncStream<JobEvent>, tự kết nối lại)
      Auth/             Keychain, SessionStore (@Observable: me, quota, user)
      Cache/            SwiftData models, ImageLoader
      Math/             MathNormalizer (port lib/math.ts), LatexToPlain (port plainMath.ts), MessageTextCodec (port messageText.ts)
    Features/
      Auth/             LoginView, RegisterView (gợi ý tên), GuestNotice
      Conversations/    ConversationList (đổi tên, xóa), ExamplesView
      Chat/             ChatStore (= ChatProvider: pending, figures), ChatView, MessageList, MessageBubble, TutorBar
      MathText/         MathMarkdownView, InlineMathRenderer, MathImageCache
      Composer/         ComposerView, ComposerTextView (UITextView), FormulaAttachment, SymbolBar
      FormulaEditor/    MathModel (AST), MathCursor, LatexParser, LatexSerializer, EditorView, MathKeyboard, TemplateGallery
      Drawing/          DrawingPanel, DrawingVersions, RefineBox, ZoomableImage, VideoPlayer
      Settings/         SettingsView, HelpView, DeleteAccountView
    Resources/          Localizable.xcstrings, Assets, PrivacyInfo.xcprivacy
  MathMateTests/        Swift Testing + snapshot
  MathMateUITests/      XCUITest với server giả (web/e2e/server.py)
  MathMateWidgets/      Live Activity
shared/
  formula_templates.json   # chuyển từ formulaTemplates.ts, web và iOS cùng đọc
  symbols.json             # thanh ký hiệu
  fixtures/math_cases.json # ca kiểm thử chung cho normalizeMath, latexToPlain, toMessageText
```

Các file trong `shared/` giữ web, iOS và sau này cả Android dùng cùng dữ liệu. Web sửa `formulaTemplates.ts` để import từ JSON, và test web chạy trên cùng fixtures với iOS.

## 5. Giao diện và Liquid Glass

Theo HIG của Apple, glass dành cho **lớp điều khiển và điều hướng**, không dùng cho nội dung. Bong bóng tin nhắn và hình vẽ là nền đặc; còn các phần nổi phía trên thì dùng glass.

- **iPhone:** `NavigationStack` đi từ danh sách đến chat. Hình vẽ là một thẻ trong chat, chạm vào thì mở sheet có detents `.medium`/`.large`; trên iOS 26, sheet tự có glass.
- **iPad:** `NavigationSplitView` ba cột (danh sách | chat | hình vẽ), giống bố cục desktop của web.
- **Composer nổi:** thanh soạn tin dùng `mmGlass(in: .rect(cornerRadius: 24))` nằm trên nội dung đang cuộn, có `safeAreaInset(edge: .bottom)`.
- **TutorBar:** nằm trong `MMGlassContainer`. Nút Gợi ý/Lời giải dùng `glassEffectID`, nên khi chuyển chế độ thì morph sang nhau. 5 chấm bậc gợi ý có animation và haptic `.selection` khi lên bậc. "Đã giải xong" có hiệu ứng nhỏ.
- **Thanh ký hiệu và nút trong bàn phím toán:** dùng `.buttonStyle(.glass)` trên iOS 26, `.bordered` trên bản cũ.
- **Toolbar:** dùng toolbar hệ thống để tự có glass. Nhóm nút bằng `ToolbarSpacer` (iOS 26).
- Kiểm tra mọi màn hình ở cả bốn tổ hợp: iOS 26 / iOS 17 × sáng / tối, kèm Dynamic Type và Reduce Transparency. Khi bật Reduce Transparency, hệ thống tự bỏ glass; cần kiểm tra lại độ tương phản.

## 6. Hiển thị toán (thay KaTeX)

1. `MathNormalizer`: port nguyên văn `normalizeMath`, gồm `\[…\]`, `\(…\)`, đưa `$$` ra dòng riêng và đổi `\tag{n}` thành `\qquad (n)`. Kiểm thử bằng `shared/fixtures`.
2. Tách công thức trước khi parse Markdown: thay mỗi `$…$`/`$$…$$` bằng placeholder để swift-markdown không làm hỏng `_` và `*` bên trong.
3. **Công thức trong dòng:** SwiftMath vẽ ra `UIImage` (có cache theo latex + cỡ chữ + màu + giao diện sáng/tối), ghép vào `Text` bằng `Text(Image(uiImage:)).baselineOffset(-descent)` để công thức xuống dòng cùng chữ.
4. **Công thức khối:** dùng `MathBlockView` có cuộn ngang khi công thức dài hơn màn hình.
5. **Khi đang stream:** nhận `delta` và render lại với tối đa khoảng 20 lần/giây. Chỉ parse lại đoạn cuối. Dấu `$` chưa đóng thì tạm hiện dưới dạng chữ thường.
6. **Rủi ro lớn nhất: SwiftMath có thể không hỗ trợ đủ cú pháp như KaTeX.** Spike ở giai đoạn 1 sẽ chạy toàn bộ mẫu trong `formulaTemplates`, các lệnh trong `plainMath` và một tập câu trả lời thật của gia sư qua SwiftMath. Các lệnh cần chú ý: `\widehat`, `\overset{\frown}`, `\backsim`, `cases`, `\left\{ … \mid … \right\}`, `\mathbb`, `\overrightarrow`.
   - Lệnh nào thiếu thì thêm luật viết lại trong `MathNormalizer`; thiếu nhiều thì fork SwiftMath và bổ sung.
   - Cuối cùng vẫn không vẽ được thì hiện mã LaTeX bằng font monospace, giống cách KaTeX báo lỗi.
   - Lấy câu trả lời thật bằng cách **chỉ đọc** từ dữ liệu, không ghi gì vào `generated/`.

## 7. Ô soạn tin có công thức trong dòng chữ (thay Tiptap)

- `ComposerTextView`: một `UITextView` bọc bằng `UIViewRepresentable`. Mỗi công thức là một `FormulaAttachment` (lớp con của `NSTextAttachment`, lưu `latex`), vẽ bằng SwiftMath và căn baseline theo chữ.
- **Hành vi giống web:**
  - Gõ `$…$` đóng lại thì thành chip.
  - Dán chữ có `$…$` thì chuyển thành chip; dán ảnh thì đính kèm ảnh.
  - Chạm chip thì mở trình soạn công thức với latex đó.
  - Backspace ngay sau chip thì chip trở lại thành `$latex$` để sửa.
  - `MessageTextCodec` chuyển qua lại giữa ô soạn và `$latex$` + `\n`. Codec này cũng dùng cho ✏️ sửa tin, giống `fromMessageText`.
- **Phím Enter:** trên bàn phím ảo, Return xuống dòng và nút gửi để gửi, theo thói quen iOS. Với bàn phím vật lý (iPad), dùng `UIKeyCommand`: Enter gửi, Shift+Enter xuống dòng, giống web.
- **Đính kèm ảnh:** nút 📎 mở menu Chụp đề (VisionKit) / Thư viện ảnh (`PhotosPicker`), có dán ảnh và kéo thả trên iPad. Ảnh được nén JPEG và giới hạn kích thước trước khi gửi multipart.
- **Thanh ký hiệu:** đọc từ `shared/symbols.json`, dạng thanh glass nằm ngay trên bàn phím.

## 8. Trình soạn công thức (thay MathLive): phần lớn nhất

Đây là một editor có cấu trúc, không phải một ô gõ LaTeX.

- **Mô hình:** cây `MathNode`, gồm row, symbol, frac, sqrt/root, sup/sub, fence `( [ { |`, accent (`\widehat`, `\overline`, `\overrightarrow`, cung), cases/matrix, text, placeholder. `MathCursor` là đường đi tới một vị trí trong cây, có vùng chọn.
- **Mẫu:** đọc `shared/formula_templates.json`. `#?` thành placeholder; `#@` lấy vùng chọn, hoặc nếu không có vùng chọn thì lấy atom ngay trước con trỏ. Sau khi chèn, con trỏ nhảy tới placeholder đầu tiên, giống `selectionMode: 'placeholder'` của MathLive.
- **Hiển thị:** dựng LaTeX từ cây rồi cho SwiftMath vẽ. Vị trí con trỏ và vùng chạm lấy từ display list của SwiftMath (`MTMathListDisplay` có toạ độ từng atom). Tham khảo [kostub/MathEditor](https://github.com/kostub/MathEditor), một editor viết trên iosMath (tiền thân của SwiftMath), để biết cách tính vị trí con trỏ.
- **Bàn phím toán:** dùng `inputView` riêng thay bàn phím hệ thống (giống `inputmode=none` + bàn phím ảo của MathLive), gồm 4 trang: `123`, `abc`, `∠△ Hình học`, `f(x) Hàm`. Có phím di chuyển con trỏ, Tab để nhảy sang placeholder kế tiếp, và nút bàn phím hệ thống khi cần gõ chữ.
- **Thư viện mẫu:** 7 tab như web, các ô mẫu vẽ bằng SwiftMath, nằm trong sheet glass phía trên bàn phím toán.
- **Mở lại công thức có sẵn:** `LatexParser` đọc được tập LaTeX mà các mẫu và `latexToPlain` tạo ra. Gặp lệnh không biết thì chuyển sang chế độ "Sửa LaTeX" (một ô chữ thường, xem trước trực tiếp), để không bao giờ làm mất công thức.
- **Khi chèn công thức:** chạy `LatexToPlain` trước. Công thức đơn giản thì chèn thành chữ Unicode (`BC²=AB²+AC²`), còn lại thì chèn thành chip, giống web.
- **Undo/redo:** lưu lịch sử của cây; lắc máy để hoàn tác.
- **Tiêu chí ngang bằng:** dựng lại được mọi mẫu trong 7 tab, sửa từng ô trống, xóa theo cấu trúc (Backspace ở đầu tử số thì tách phân số), và LaTeX xuất ra khớp với web cho cùng một thao tác. Có test so sánh.

## 9. Chat, job và hình vẽ

- `ChatStore` (`@Observable`, một instance cho cả app) tương đương `lib/chat.tsx`:
  - `pending[conversationId]`: bong bóng tạm, nhãn tiến độ, `reply` từ `delta`
  - `figures[conversationId]`: job đang vẽ
  - theo dõi job từ `figure_job`
  - chuyển sang cuộc trò chuyện mới khi job tạo ra nó
  - tải lại cuộc trò chuyện khi job kết thúc
- `JobFollower` đọc SSE bằng `URLSession.bytes(for:)` trong một `Task`:
  - Khi app vào nền, kết nối bị ngắt và job vẫn chạy trên server.
  - Khi app quay lại, nếu job còn thì kết nối lại (dựng lại `reply` từ đầu, xem §3.6); nếu hết thì tải lại cuộc trò chuyện.
  - Push báo job xong sẽ mở thẳng cuộc trò chuyện.
- **Bảng hình vẽ:**
  - các phiên bản (chọn hình đang xem)
  - "Yêu cầu chỉnh hình" kèm danh sách yêu cầu đã gửi
  - "Vẽ lại" khi lỗi
  - hình phóng to và kéo được (`ScrollView` có zoom, hoặc `UIScrollView`)
  - video bằng `AVPlayer`
  - `ShareLink` để lưu hoặc gửi hình
- **Live Activity** (ActivityKit) khi đang vẽ, cập nhật nhãn tiến độ; trên iOS 26 nó hiện cả trong Dynamic Island.

## 10. Kiểm thử và CI

- **Unit test (Swift Testing):** `MathNormalizer`, `LatexToPlain`, `MessageTextCodec`, `LatexParser`/`Serializer` (chạy vòng: parse rồi serialize phải ra như cũ), `SSEParser` và `ChatStore` (dùng `URLProtocol` giả). Dùng chung `shared/fixtures` với web.
- **Snapshot test:** hiển thị toán, các bong bóng, TutorBar, mỗi cái chụp ở iOS 17 và iOS 26, sáng và tối.
- **UI test (XCUITest):** chạy với `web/e2e/server.py` (API thật trên thư mục tạm + AI giả trả lời theo từ khóa), giống Playwright. Đề bài không phải hình học để không phải render bằng Manim.
- **CI:** Jenkins chạy trên Linux không build được iOS. Dùng Xcode Cloud hoặc GitHub Actions macOS, cộng fastlane để đẩy lên TestFlight. Server test của backend vẫn ở Jenkins như hiện tại.

## 11. Chuẩn bị nộp App Store

- Có xóa tài khoản trong app (§3.3). Không cần Sign in with Apple, vì app không dùng đăng nhập bên thứ ba (guideline 4.8).
- Có chế độ dùng thử không bắt đăng ký, đúng guideline 5.1.1. Gửi Apple một tài khoản demo khi nộp.
- Có `PrivacyInfo.xcprivacy` và nhãn quyền riêng tư (ảnh, nội dung người dùng, định danh). Mô tả quyền camera và thư viện ảnh bằng tiếng Việt.
- Trả lời bộ câu hỏi xếp hạng tuổi một cách cẩn thận, vì người dùng là học sinh 11–18 tuổi và app có nội dung do AI tạo ra.
- Mọi kết nối đều qua HTTPS (ATS). Production đã có sẵn qua Traefik.

## 12. Lộ trình (một người làm)

| Giai đoạn | Nội dung | Ước lượng |
|---|---|---|
| 0 | Backend: Bearer, `X-Guest-Id`, xóa tài khoản, devices + APNs, app-config, tách `shared/` | 1 tuần |
| 1 | **Spike rủi ro:** độ phủ cú pháp của SwiftMath, công thức trong dòng chữ (Text+Image), `UITextView` + attachment, con trỏ trên display list của SwiftMath, SSE. Kết thúc bằng quyết định làm tiếp hay đổi hướng | 1–1,5 tuần |
| 2 | Nền tảng: project, DesignSystem glass + dự phòng, APIClient, đăng nhập/đăng ký/dùng thử, danh sách cuộc trò chuyện, cài đặt | 1,5–2 tuần |
| 3 | Chat: stream, MathMarkdownView, TutorBar, các action, sao chép/sửa tin, ảnh, quota và lỗi | 2 tuần |
| 4 | Composer với công thức trong dòng chữ + thanh ký hiệu | 1,5 tuần |
| 5 | Trình soạn công thức: AST, con trỏ, bàn phím toán, thư viện mẫu, parser, undo | 4–6 tuần |
| 6 | Hình vẽ: bảng, phiên bản, chỉnh hình, zoom, video, chia sẻ | 1 tuần |
| 7 | Tính năng native: push, Live Activity, cache offline, iPad chia cột, haptics | 1,5 tuần |
| 8 | QA (bốn tổ hợp iOS 17/26 × sáng/tối, Dynamic Type, VoiceOver), TestFlight, nộp App Store | 1,5–2 tuần |
| | **Tổng** | **≈ 15–19 tuần** |

Giai đoạn 4–5 có thể chạy song song với 6–7 nếu có thêm người làm.

## 13. Chuẩn bị cho Android sau này

- Backend sau giai đoạn 0 không có gì riêng cho iOS (Bearer, `X-Guest-Id`, `devices.platform` để thêm FCM).
- `shared/` (mẫu công thức, ký hiệu, fixtures) dùng nguyên cho Kotlin.
- Kiến trúc chia lớp như trên: Core (API, Jobs, Math codec) tương ứng một module Kotlin; FormulaEditor tách mô hình (AST, con trỏ, parser) khỏi phần vẽ, để port sang Kotlin dễ.
- Thư viện hiển thị toán trên Android cần chọn riêng (ví dụ JLaTeXMath-android) và cũng phải qua một spike về độ phủ cú pháp tương tự.

## 14. Việc cần làm trong repo khi bắt đầu

- Cập nhật `CLAUDE.md`: mục `mobile/ios/`, `shared/`, auth bằng Bearer/`X-Guest-Id`, push, và quy tắc "tính năng mới cho học sinh phải có trên cả web lẫn iOS, hoặc được ghi vào bảng ở §1 với lý do".
- Giữ bảng §1 làm checklist ngang bằng; đánh dấu từng dòng khi iOS làm xong.
