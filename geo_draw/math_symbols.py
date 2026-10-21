"""Vietnamese lower-secondary (THCS, grades 6–9) mathematical notation."""

THCS_MATH_SYMBOLS_VI = r"""
=== TỪ ĐIỂN KÝ HIỆU TOÁN THCS (LỚP 6–9) ===
Luôn đọc ký hiệu theo ngữ cảnh của đề; không suy diễn một chữ cái chỉ từ hình dạng của nó.

1. SỐ, TẬP HỢP VÀ QUAN HỆ
- N hoặc ℕ: tập số tự nhiên; N* hoặc ℕ*: số tự nhiên khác 0; Z hoặc ℤ: số nguyên;
  Q hoặc ℚ: số hữu tỉ; I: số vô tỉ; R hoặc ℝ: số thực. Khi đang nói đường tròn, R/r lại là bán kính.
- x ∈ A: x thuộc A; x ∉ A: x không thuộc A; A ⊂ B hoặc A ⊆ B: A là tập con của B;
  ∅: tập rỗng; A ∪ B: hợp; A ∩ B: giao; A\B: hiệu; |A| hoặc n(A): số phần tử của A.
- {…}: tập hợp hoặc hệ điều kiện tùy bố cục; (a;b), [a;b], (a;b], [a;b): các khoảng/đoạn số.
- =: bằng; ≠: khác; <: nhỏ hơn; >: lớn hơn; ≤: nhỏ hơn hoặc bằng; ≥: lớn hơn hoặc bằng;
  ≈: xấp xỉ; ≡: đồng nhất hoặc đồng dư tùy ngữ cảnh; ⇒: suy ra; ⇔: tương đương.

2. PHÉP TÍNH, LŨY THỪA, CĂN VÀ TỈ LỆ
- +: cộng; −: trừ hoặc số đối; ×, ·: nhân; :, / hoặc gạch phân số: chia; ±: cộng hoặc trừ.
- a^n: lũy thừa cơ số a, số mũ n; a², a³: bình phương, lập phương; √a: căn bậc hai;
  ³√a: căn bậc ba; |a|: giá trị tuyệt đối; n!: giai thừa nếu xuất hiện.
- %: phần trăm; ‰: phần nghìn; a:b: tỉ số; a/b=c/d hoặc a:b=c:d: tỉ lệ thức;
  k: hệ số tỉ lệ; x∝y: x tỉ lệ với y nếu sách/đề dùng ký hiệu này.
- a|b: a là ước của b (b chia hết cho a); a∤b: a không là ước của b;
  UCLN(a,b) hoặc gcd(a,b): ước chung lớn nhất; BCNN(a,b) hoặc lcm(a,b): bội chung nhỏ nhất.

3. ĐẠI SỐ, PHƯƠNG TRÌNH VÀ BẤT PHƯƠNG TRÌNH
- x, y, z: ẩn hoặc biến; a, b, c, m, n: hệ số/tham số khi đề quy định; biểu thức P(x), A(x)…
  là biểu thức theo x, không được nhầm P với xác suất hoặc chu vi khi ngữ cảnh là đại số.
- ax+b=0: phương trình; ax+b>0, ≥0, <0, ≤0: bất phương trình; S hoặc tập viết trong ngoặc
  nhọn có thể là tập nghiệm khi đề nói "tập nghiệm". Dấu ngoặc lớn ghép nhiều dòng là một hệ.
- ĐKXĐ: điều kiện xác định; x≠a: loại giá trị a; nghiệm viết x=x₀; vô nghiệm: S=∅;
  nghiệm đúng với mọi x: S=R. Ký hiệu ⇔ chỉ dùng cho biến đổi tương đương, ⇒ cho phép suy ra.
- Các hằng đẳng thức dùng a,b: (a±b)², a²−b², (a±b)³, a³±b³; không coi a,b là độ dài
  nếu bài không nói đến hình học.

4. HÀM SỐ VÀ MẶT PHẲNG TỌA ĐỘ
- y=f(x): hàm số; x: biến số/hoành độ; y: giá trị hàm/tung độ; f(a): giá trị tại x=a;
  D hoặc D_f: tập xác định. y=ax+b: hàm số bậc nhất; a: hệ số góc, b: tung độ gốc;
  y=ax² (a≠0): hàm số bậc hai dạng học ở THCS.
- Oxy: hệ trục tọa độ; O: gốc; Ox: trục hoành; Oy: trục tung; A(x;y): điểm có tọa độ
  (x;y). G hoặc (d) có thể là đồ thị; d trong ngữ cảnh này thường là tên đường thẳng.
- Δx, Δy: độ thay đổi nếu đề dùng; k=(y₂−y₁)/(x₂−x₁): hệ số góc qua hai điểm.

5. HÌNH HỌC PHẲNG
- A, B, C…: điểm; a, b, c, d: tên đường thẳng; AB: đoạn thẳng hoặc độ dài AB theo ngữ cảnh;
  (AB): đường thẳng AB nếu đề dùng ngoặc; [AB]: đoạn AB; Ax hoặc [Ax): tia gốc A qua x.
- A∈d, A∉d: A thuộc/không thuộc d; a∥b: song song; a⊥b: vuông góc;
  a∩b={O}: cắt nhau tại O. Không tự hiểu d là đường kính khi d đang gọi tên đường thẳng.
- ∠ABC hoặc góc ABC: góc có đỉnh B; m∠ABC: số đo; °: độ; ′: phút; ″: giây;
  ∠A=90°: góc vuông. Trên hình chỉ đánh dấu bằng ô vuông nhỏ, không ghi thêm 90°.
- ΔABC: tam giác; ΔABC≅ΔDEF: bằng nhau; ΔABC∼ΔDEF: đồng dạng; □ABCD: tứ giác;
  AB=CD: hai đoạn bằng nhau; ký hiệu vạch/cung giống nhau lần lượt chỉ đoạn/góc bằng nhau.
- a, b, c thường là độ dài ba cạnh; h hoặc h_a: chiều cao; m_a: trung tuyến; l_a: phân giác;
  p=(a+b+c)/2: nửa chu vi tam giác nếu đề định nghĩa; C: chu vi; S: diện tích.
- (O): đường tròn tâm O; (O;R): đường tròn tâm O bán kính R; R hoặc r: bán kính;
  d: đường kính và d=2R khi ngữ cảnh đang nói độ dài đường kính; OA=R nếu A∈(O).
- AB có hai đầu trên đường tròn: dây AB; dây đi qua O: đường kính; ⌢AB: cung AB;
  tiếp tuyến tại A vuông góc OA; cát tuyến cắt đường tròn tại hai điểm.
- π: số pi; C=2πR=πd: chu vi đường tròn; S=πR²: diện tích hình tròn.
- Trong tam giác vuông: c thường là cạnh huyền nếu đề đặt như vậy; sin, cos, tan, cot là các
  tỉ số lượng giác. Không quyết định cạnh đối/kề nếu chưa xác định góc đang xét.

6. HÌNH KHỐI VÀ ĐẠI LƯỢNG HÌNH HỌC
- C: chu vi; S: diện tích; S_đáy hoặc B: diện tích đáy tùy sách; Sxq: diện tích xung quanh;
  Stp: diện tích toàn phần; V: thể tích; h: chiều cao; l: đường sinh; R/r: bán kính.
- Hình hộp chữ nhật thường có kích thước a,b,h; V=abh. Lăng trụ: V=S_đáy·h.
  Hình chóp: V=(1/3)S_đáy·h. Hình trụ: Sxq=2πRh, V=πR²h.
  Hình nón: Sxq=πRl, V=(1/3)πR²h. Hình cầu: S=4πR², V=(4/3)πR³.
- Độ dài dùng mm, cm, dm, m, km; diện tích dùng đơn vị vuông cm², m²…; thể tích dùng
  đơn vị khối cm³, m³…; dung tích thường mL, L. Không bỏ đơn vị và không trộn bậc đơn vị.

7. THỐNG KÊ VÀ XÁC SUẤT
- n hoặc N: số quan sát/tổng số phần tử; x_i: giá trị thứ i; n_i: tần số;
  f_i=n_i/N: tần số tương đối; % là tần số tương đối phần trăm.
- x̄: số trung bình cộng; M_e hoặc Me: trung vị; M_o hoặc Mo: mốt; R: khoảng biến thiên trong
  thống kê. Không nhầm R này với bán kính khi bài không nói về đường tròn.
- Ω: không gian mẫu; A, B: biến cố; P(A): xác suất của A; 0≤P(A)≤1; Ā hoặc A^c: biến cố đối;
  P(Ā)=1−P(A). Với các kết quả đồng khả năng: P(A)=n(A)/n(Ω).

8. QUY TẮC GIẢI NGHĨA
- Một chữ cái không có nghĩa cố định ngoài ngữ cảnh: R có thể là bán kính, số thực hoặc khoảng
  biến thiên; d có thể là đường kính, đường thẳng hay khoảng cách; C có thể là chu vi, một điểm
  hoặc một hằng số; S có thể là diện tích hoặc tập nghiệm; P có thể là điểm, xác suất hay biểu thức.
- Ưu tiên cụm từ đi kèm: "đường tròn tâm O" → (O); "bán kính" → R/r; "đường kính" → d;
  "chu vi" → C; "diện tích" → S; "thể tích" → V. Giữ nguyên ký hiệu riêng nếu đề đã quy ước khác.
- Khi trả lời học sinh, lần đầu xuất hiện nên viết cả tên và ký hiệu, ví dụ "bán kính $R$";
  không thay đổi ký hiệu mà đề bài đang dùng và không dùng cùng một chữ cho hai đại lượng trong một lời giải.
""".strip()
