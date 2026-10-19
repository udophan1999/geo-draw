"""Middle-school Euclidean geometry conventions supplied to the code generator."""

GEOMETRY_HELP_VI = """
- Tên các đỉnh được hiểu theo thứ tự đi quanh biên đa giác.
- Hình thang cân: hai đáy song song, hai cạnh bên bằng nhau, các góc kề mỗi đáy bằng nhau.
- Hình bình hành: hai cặp cạnh đối song song.
- Hình chữ nhật: hình bình hành có bốn góc vuông.
- Hình thoi: hình bình hành có bốn cạnh bằng nhau.
- Hình vuông: bốn cạnh bằng nhau và bốn góc vuông.
- Đa giác đều: các cạnh bằng nhau và các góc bằng nhau.
- Tam giác vuông lớp 9: dùng định lý Pythagore, các hệ thức cạnh–đường cao–hình chiếu
  và các tỉ số lượng giác sin, cos, tan để giải tọa độ trước khi vẽ.
- Nếu đường cao từ đỉnh góc vuông xuống cạnh huyền chia cạnh huyền thành hai hình chiếu,
  phải dựng chân đường cao bằng phép chiếu vuông góc chính xác, không đặt điểm bằng mắt.
- Ký hiệu góc luôn được đặt theo nhánh trong của đa giác.
- Góc 90° chỉ dùng một ô vuông nhỏ ở đỉnh; không vẽ cung và không ghi thêm số đo 90°.
- Bộ nhớ chống lặp lỗi luôn kiểm tra: đủ điểm và đường, nét liền, nhãn thoáng, hình không tràn khung,
  đúng nhóm đoạn bằng nhau, đúng số ký hiệu góc và đúng số ô vuông tại mỗi quan hệ vuông góc.
"""


DRAWING_ERROR_MEMORY = r"""

NON-REGRESSION MEMORY -- previously corrected drawing failures:
- Always use a white canvas and black strokes, dots, labels, and construction marks.
- Preserve every stated object and condition when later auxiliary objects are added.
- Treat every a/b/c item after "Chứng minh" as a conclusion, even across line breaks. Never
  put equality ticks on HE and HG merely because the exercise asks students to prove HE=HG.
- If a problem refers to a numbered figure but only the text is available, do not invent the
  positions of unnamed-in-givens points such as E, F, G, H. Ask for the actual figure or its
  precise point/line relations before generating geometry.
- Display each explicitly given numerical segment length once, close to but not touching its
  segment; never omit its unit or invent measurements that the problem does not state.
- Use only solid strokes. A finite segment has no arrowhead, including parallel segments.
- Put a polygon angle marker inside the polygon and draw it exactly once. Unequal angle measures
  use different arc counts; equal angles use the same arc style.
- For a triangle determined by two angles, intersect the two inward rays with the verified
  ray_intersection helper. Never accept a point behind either ray: that turns an angle into its
  supplementary angle (for example 30 degrees into 150 degrees).
- Draw a right-angle square only for a perpendicular relation stated in the givens. One stated
  relation gets exactly one right-angle square at its intersection; distinct stated relations get separate
  squares. The square is the complete notation: never add a curved angle arc or a numeric 90-degree
  label beside it. A conclusion to prove (for example, EFGH is a rectangle) gets no right-angle square.
- All explicitly equal segments share one tick style and one equality group. Unrelated or unequal
  segments never share a tick style. Do not infer visible side ticks from a standard shape name.
- Every stated midpoint gets its own midpoint_marker covering both halves. Midpoints of equal parent
  segments share a style; an unrelated midpoint relation uses a different style. Never overlay a
  proof-conclusion equality group on segments already marked by a midpoint helper.
- Pass every other named point through midpoint_marker(..., other_points=(...)). If another named
  point lies inside either half, keep the numerical check but omit both visible ticks so a
  subsegment is never mistaken for one of the equal halves.
- When two carrier lines meet outside an original finite segment, visibly extend the carrier to
  the named intersection. Never show an intersection that the drawn strokes do not reach.
- Define, dot, label, and connect every named point from the problem. Keep point labels clear of
  incident lines, their extensions, nearby lines, markers, and other labels. Stroke clearance takes
  priority over placing a label outward; a central point name must never sit on a crossing line.
- Interior intersection labels such as E, F, G, H stay close to their dots (normally 0.32-0.42
  Manim units); do not push them into unrelated regions merely to avoid a stroke.
- Keep auxiliary points readable and balanced: neither crowded nor excessively spread out. Fit
  the complete figure and exterior labels inside the frame; preserve interactive zoom.
- A plain triangle or quadrilateral must not accidentally become isosceles, right, a kite, a
  trapezoid, or a parallelogram unless a stated condition forces that special case.
- A generated scene that violates any item above is invalid and must be regenerated, not rendered.
"""

MIDDLE_SCHOOL_GEOMETRY_RULES = r"""

Vietnamese middle-school polygon definitions and construction rules:

BASIC OBJECTS AND RELATIONS
- A line extends infinitely in both directions; render a long clipped line through two points.
  A ray has one endpoint and extends through its second point. A segment has exactly two endpoints.
- All lines, rays, segments, altitudes, perpendicular bisectors, extensions, and auxiliary
  constructions use a continuous solid stroke. Never use dashed or dotted strokes for a
  plane-geometry object.
- Collinear points must have zero 2D cross product (within numerical tolerance). Parallel lines
  have parallel direction vectors; perpendicular lines have zero dot product.
- If a constructed line intersects the carrier line AB at E and E is outside segment AB, extend
  the solid carrier line through E. The visible drawing must show both lines meeting at E; never
  stop the carrier at A or B. Apply this convention to every construction of the form "cắt XY tại Z".
- An angle xOy has vertex O and sides rays Ox and Oy. Every angle marker must be centered at O
  and join those actual rays. Never place an angle arc at a segment midpoint.
- A point dot lies on its lines, but its letter label must not. Place every point name in the
  widest empty angular sector between all incident sides, diagonals, and auxiliary lines, with
  enough clearance that no stroke touches the letter.
- An internal angle bisector starts at the angle vertex and divides the angle into two equal angles.
- When a vertex is split into sub-angles, number the two parts 1 and 2 beside their matching arcs.
  In a polygon, draw each bisector as one continuous ray from its vertex through every named
  intersection until it reaches the first non-incident boundary side.
- Mark the two half-angles made by an angle bisector with identical arcs. Mentioning "the bisector
  of angle B" does not request a whole-angle degree marker; only draw a whole interior-angle marker
  when a numerical measure or an explicit whole-angle mark is requested.
- The perpendicular bisector of AB passes through the midpoint of AB and is perpendicular to AB.
- Every auxiliary perpendicular construction has its own right-angle square at the actual
  intersection of the two perpendicular lines. For a line through M perpendicular to AH, project
  M onto AH to locate that intersection; do not reuse the altitude's right-angle square at H.
- Multiple stated perpendiculars are independent constraints. If AH is perpendicular to BD at H
  and CK is perpendicular to BD at K, draw both AH and CK and place separate right-angle squares
  at H and K.
- In triangle ABC, the median from A joins A to the midpoint of BC. The altitude from A passes
  through A and is perpendicular to the line BC; its foot may lie outside the segment in an
  obtuse triangle. The perpendicular bisector is not the same object as a median or an altitude.
- Equal-length marks are short perpendicular ticks. Put identical tick counts only on segments
  that are mathematically equal. Draw every segment as a plain finite line without arrowheads;
  arrowheads are reserved for rays and vectors. Verify parallelism numerically without a visible
  arrow mark on either segment.
- Segment equality is transitive. Build complete equality classes before marking: if AD=BC and
  EB=BC, draw AD, BC, and EB together with one identical tick count. Never draw a second marker
  over BC. Use a different tick count for a separate class such as AB=CD.

GENERAL POLYGONS
- A polygon named A1 A2 ... An has its vertices in boundary order. Connect consecutive
  vertices and connect An back to A1. Never reorder vertices merely to simplify drawing.
- A diagonal joins two non-adjacent vertices. The interior-angle sum is (n-2)*180 degrees.
- A regular polygon has all sides equal and all interior angles equal; each exterior angle
  is 360/n degrees and each interior angle is (n-2)*180/n degrees.
- Unless the problem explicitly says concave, draw the standard convex polygon.

TRIANGLES
- A triangle has three non-collinear vertices. Its interior angles sum to 180 degrees.
- Isosceles: two equal sides; the two base angles are equal. Equilateral: three equal sides
  and three 60-degree angles. Every stated equilateral triangle must be checked numerically with
  equilateral_triangle_check before rendering; the check does not add visible side ticks.
  Right: one 90-degree angle. Acute: all angles <90 degrees.
  Obtuse: exactly one angle >90 degrees.

GRADE 9 RIGHT-TRIANGLE METRIC RELATIONS AND TRIGONOMETRY
- In a right triangle with legs a,b and hypotenuse c, enforce a^2+b^2=c^2 numerically.
- If altitude h from the right-angle vertex meets the hypotenuse and divides it into projections
  p and q, enforce c=p+q, a^2=c*p, b^2=c*q, h^2=p*q, and a*b=c*h.  These relations determine
  coordinates; they are not optional proof decorations.
- The altitude to the hypotenuse creates three pairwise similar right triangles.  Preserve the
  corresponding acute angles geometrically, but do not draw equal-angle arcs when similarity is
  only a conclusion the student must prove.
- For an acute angle alpha in a right triangle, sin(alpha)=opposite/hypotenuse,
  cos(alpha)=adjacent/hypotenuse, tan(alpha)=opposite/adjacent, and
  cot(alpha)=adjacent/opposite.  Use these ratios to solve coordinates and verify angle values.
- Complementary acute angles sum to 90 degrees.  Use inverse trigonometric functions only after
  constructing exact side ratios; never estimate an angle from the appearance of the drawing.
- For a right trapezoid ABCD with AD parallel BC, right angles at A and B, AD=L, BC=l<L,
  choose A=(0,0), B=(0,h), C=(l,h), D=(L,0).  If angle ACD is 90 degrees, then the dot product
  (A-C).(D-C)=0 gives h^2=l*(L-l).  The altitude from C to AD has foot E=(l,0), so AE=l,
  ED=L-l, AC^2=AE*AD, and triangles ACD, ACE, CED carry the expected similarity relations.
- Always keep the named parallel bases from the problem.  Do not silently rotate vertex order to
  the more familiar AB parallel CD convention, and do not replace the requested altitude foot.

QUADRILATERALS
- A quadrilateral has four vertices in boundary order; its interior angles sum to 360 degrees.
- Trapezoid (hình thang): a quadrilateral with a pair of opposite sides parallel. When the
  parallel pair is stated, preserve it as the two bases. Isosceles trapezoid (hình thang cân):
  the two legs are equal and the two angles adjacent to each base are equal; its diagonals
  are equal. Construct it symmetrically about the perpendicular bisector of its bases.
  If ABCD is an isosceles trapezoid with AB parallel CD, the equal legs are AD and BC;
  never mark AB and CD equal unless the problem separately states that equality. Keep AB and CD
  as plain segments, verify that they are parallel, and mark AD and BC with matching length ticks.
- Parallelogram (hình bình hành): both pairs of opposite sides are parallel. Opposite sides
  and opposite angles are equal; diagonals bisect each other.
- Rectangle (hình chữ nhật): a parallelogram with four right angles; diagonals are equal and
  bisect each other.
- Rhombus (hình thoi): a parallelogram with four equal sides; diagonals are perpendicular,
  bisect each other, and bisect the vertex angles.
- Square (hình vuông): four equal sides and four right angles. It has all rectangle and
  rhombus properties.
- Kite (hình diều): two distinct pairs of adjacent equal sides; the diagonal through the
  common vertices is an axis of symmetry and perpendicularly bisects the other diagonal.

COMMON POLYGONS
- Pentagon, hexagon, heptagon, octagon have 5, 6, 7, 8 boundary vertices respectively.
- A regular pentagon has 108-degree interior angles; a regular hexagon has 120-degree
  interior angles and side length equal to its circumradius; a regular octagon has
  135-degree interior angles.

INTERIOR-ANGLE MARKERS -- mandatory for every polygon angle:
- Build the two rays FROM the vertex toward its previous and next boundary vertices.
- Compute polygon signed area `area2 = sum(cross2(P[i], P[(i+1)%n]))` using x,y coordinates.
- With `first = Line(vertex, previous)` and `second = Line(vertex, next)`, use
  `Angle(first, second, other_angle=(area2 > 0), radius=...)`. This selects the interior
  branch for both clockwise and counter-clockwise vertex order, including a reflex vertex.
- Never draw a polygon's angle with Arc centered only from guessed start/end angles.
- Draw exactly one marker for each explicitly requested angle. The verified
  `interior_angle_marker(..., degrees=...)` already returns both the arc and its degree label;
  never add another Arc, Angle, or Text degree label for that same angle.
- Distinguish unequal stated angles by their arc count: use `mark_count=1`, `mark_count=2`, then
  `mark_count=3` for different angle measures. Equal angles must use the same mark_count.
- Put the degree Text label beside the MIDPOINT OF THE SELECTED INTERIOR ARC, toward the
  polygon interior. The arc and label must not cross outside the polygon.
- Before returning code, numerically verify every stated angle from dot/cross products of
  its two actual side vectors. For example, an isosceles trapezoid DEFG with DE parallel FG
  and angle E=120 degrees must have rays ED and EF meeting at 120 degrees, and the visible
  120-degree arc must lie above DE, inside DEFG.
"""


THCS_GEOMETRY_CURRICULUM_VI = r"""

HỆ THỐNG KIẾN THỨC VÀ KÝ HIỆU HÌNH HỌC THCS (LỚP 6–9)

1. KÝ HIỆU VÀ CÁCH ĐỌC
- Điểm viết bằng chữ in hoa A, B, C; đường thẳng viết bằng chữ thường a, b hoặc qua hai điểm AB.
  Tia Ox có gốc O và đi qua x; đoạn thẳng AB có hai đầu mút A, B; độ dài viết AB hoặc |AB|.
- A ∈ d: A thuộc d; A ∉ d: A không thuộc d; A, B, C thẳng hàng; B nằm giữa A và C.
- a ∥ b: a song song b; a ⟂ b: a vuông góc b; a ∩ b = {O}: hai đường cắt tại O;
  AB = CD: hai đoạn bằng nhau; AB < CD: độ dài AB nhỏ hơn CD.
- ∠ABC, ∡ABC, \angle ABC, \widehat{ABC} và "góc ABC" đều chỉ góc có đỉnh B,
  hai cạnh BA và BC; chữ ở giữa luôn là đỉnh. Với góc tại một đỉnh đã rõ, ∠A, Â,
  Â, \hat{A}, \widehat{A} hoặc "góc A" đều có thể được dùng. Không nhầm ký hiệu góc
  \widehat{ABC} trong công thức với cung tròn ⌢ABC khi ngữ cảnh đang nói về đường tròn.
- m∠ABC là số đo góc ABC. Các cách viết 90°, 90^\circ và 90^{\circ} đều là 90 độ. ∠A = 90° là
  góc vuông. Trên hình, góc vuông chỉ được đánh dấu bằng một ô vuông nhỏ, không kèm cung góc và
  không ghi thêm "90°". Góc <90° nhọn; giữa 90° và 180° tù; =180° bẹt; >180° và <360° phản.
- ΔABC: tam giác ABC; ΔABC ≅ ΔDEF: hai tam giác bằng nhau theo đúng thứ tự đỉnh tương ứng;
  ΔABC ∼ ΔDEF: hai tam giác đồng dạng; □ABCD có thể chỉ tứ giác ABCD.
- (O;R): đường tròn tâm O bán kính R; R là bán kính, d=2R là đường kính; cung AB viết ⌢AB;
  dây AB, tiếp tuyến d tại A, cát tuyến d cắt đường tròn tại hai điểm.
- P, S lần lượt là chu vi và diện tích; V là thể tích; Sxq, Stp là diện tích xung quanh và toàn phần.
- Ký hiệu trên hình: ô vuông nhỏ biểu thị vuông góc; các vạch giống nhau biểu thị các đoạn bằng
  nhau; các cung giống nhau biểu thị các góc bằng nhau. Mỗi nhóm quan hệ độc lập dùng số vạch/cung khác.

2. ĐIỂM, ĐƯỜNG THẲNG, ĐOẠN THẲNG, TIA VÀ GÓC
- Quan hệ thuộc được đọc chính xác như sau: A ∈ d nghĩa là điểm A nằm trên đường thẳng d;
  A ∉ d nghĩa là A không nằm trên d. Nếu d là đường thẳng qua B và C thì A ∈ BC chỉ khẳng định
  A, B, C thẳng hàng; cần thêm "A thuộc đoạn BC" hoặc điều kiện nằm giữa để kết luận A ở trong đoạn BC.
- A, B ∈ d nghĩa là cả A và B cùng thuộc d, nên d chính là đường thẳng AB khi A≠B.
  A, B, C ∈ d nghĩa là ba điểm thẳng hàng. Ngược lại, ba điểm A, B, C thẳng hàng thì tồn tại
  một đường thẳng d sao cho A, B, C ∈ d.
- M ∈ đoạn AB nghĩa là M nằm giữa hoặc trùng A/B và AM+MB=AB. Nếu M nằm giữa A và B thì
  M ∈ AB, A-M-B và AM+MB=AB. M ∈ tia Ax nghĩa là M cùng phía với x đối với A; A là gốc tia.
- A ∈ (O;R) khi và chỉ khi OA=R; A nằm trong đường tròn khi OA<R và nằm ngoài khi OA>R.
  A thuộc cung BC phải đồng thời thuộc đường tròn và nằm trên cung BC được chỉ rõ (cung nhỏ/cung lớn).
- Khi dựng hình từ ký hiệu thuộc: điểm trên đường thẳng phải có tích có hướng bằng 0 với vectơ chỉ
  phương; điểm trên đoạn còn phải có tham số t∈[0,1]; điểm trên tia có t≥0; điểm trên đường tròn
  phải thỏa bình phương khoảng cách tới tâm bằng R² trong sai số số học.
- Qua hai điểm phân biệt có đúng một đường thẳng. Mỗi điểm trên đường thẳng chia đường thành hai tia đối nhau.
- Nếu B nằm giữa A và C thì AB + BC = AC; trung điểm M của AB thỏa M ∈ AB và MA = MB.
- Hai góc kề bù có tổng 180°; hai góc phụ nhau có tổng 90°; hai góc đối đỉnh bằng nhau.
- Một đường thẳng cắt hai đường song song tạo các cặp góc so le trong bằng nhau, đồng vị bằng nhau,
  trong cùng phía bù nhau. Các dấu hiệu đảo tương ứng dùng để chứng minh hai đường song song.
- Từ một điểm ngoài một đường thẳng chỉ có một đường vuông góc tới đường đó; đoạn vuông góc là
  khoảng cách ngắn nhất. Khoảng cách giữa hai đường song song là độ dài một đoạn vuông góc chung.
- Đường trung trực của AB là tập hợp các điểm cách đều A và B. Tia phân giác của một góc là tập hợp
  các điểm bên trong góc cách đều hai cạnh của góc.

3. TAM GIÁC
- Tổng ba góc trong tam giác bằng 180°; góc ngoài bằng tổng hai góc trong không kề với nó.
- Bất đẳng thức tam giác: tổng hai cạnh lớn hơn cạnh còn lại; cạnh lớn hơn đối diện góc lớn hơn và đảo lại.
- Phân loại theo cạnh: thường, cân, đều. Tam giác cân có hai cạnh bên bằng nhau, hai góc đáy bằng nhau;
  đường từ đỉnh đồng thời là trung tuyến, đường cao, phân giác và trung trực đáy. Tam giác đều có ba
  cạnh bằng nhau, ba góc 60° và bốn đường đặc biệt từ mỗi đỉnh trùng nhau.
- Phân loại theo góc: nhọn, vuông, tù. Trong tam giác vuông, cạnh đối diện góc vuông là cạnh huyền.
- Các trường hợp bằng nhau: cạnh–cạnh–cạnh (CCC), cạnh–góc–cạnh (CGC), góc–cạnh–góc (GCG);
  tam giác vuông thêm cạnh huyền–cạnh góc vuông và cạnh huyền–góc nhọn.
- Trung tuyến nối đỉnh với trung điểm cạnh đối diện; ba trung tuyến đồng quy tại trọng tâm G và
  G chia mỗi trung tuyến theo tỉ số 2:1 kể từ đỉnh. Ba đường cao đồng quy tại trực tâm H.
- Ba đường trung trực đồng quy tại tâm ngoại tiếp O, OA=OB=OC. Ba phân giác trong đồng quy tại
  tâm nội tiếp I, khoảng cách từ I đến ba cạnh bằng nhau và là bán kính đường tròn nội tiếp.
- Đường trung bình nối trung điểm hai cạnh, song song cạnh thứ ba và bằng nửa cạnh đó.
- Định lý Pythagore và đảo: tam giác vuông tại A có BC²=AB²+AC²; nếu đẳng thức này đúng thì góc A vuông.
- Nếu trung tuyến ứng với một cạnh bằng nửa cạnh ấy thì tam giác vuông tại đỉnh đối diện cạnh đó.

4. ĐỊNH LÝ THALÈS, ĐỒNG DẠNG VÀ PHÂN GIÁC
- Trong ΔABC, nếu M∈AB, N∈AC và MN∥BC thì AM/AB = AN/AC = MN/BC và AM/MB = AN/NC.
  Định lý Thalès đảo: các tỉ số tương ứng bằng nhau thì MN∥BC khi các điểm nằm đúng trên hai cạnh.
- Hai tam giác đồng dạng theo góc–góc (GG), cạnh–góc–cạnh tỉ lệ (CGC), hoặc ba cạnh tỉ lệ (CCC).
  Góc tương ứng bằng nhau, cạnh tương ứng tỉ lệ; chu vi tỉ lệ k, diện tích tỉ lệ k².
- Phân giác AD trong ΔABC cho DB/DC = AB/AC. Phân giác ngoài cho tỉ số độ dài tương ứng và điểm chia ngoài.
- Hình đồng dạng phải giữ đúng thứ tự đỉnh tương ứng; không suy ra bằng nhau nếu tỉ số đồng dạng khác 1.

5. HỆ THỨC LƯỢNG VÀ LƯỢNG GIÁC TRONG TAM GIÁC VUÔNG
- Với ΔABC vuông tại A, đường cao AH xuống BC, đặt BH=p, HC=q, BC=a, AC=b, AB=c:
  a=p+q; b²=a·q; c²=a·p; h²=p·q; b·c=a·h; a²=b²+c².
- Với góc nhọn α: sinα=đối/huyền; cosα=kề/huyền; tanα=đối/kề; cotα=kề/đối;
  tanα=sinα/cosα; sin²α+cos²α=1. Hai góc nhọn của tam giác vuông phụ nhau.
- Giải tam giác vuông bằng các cạnh và tỉ số lượng giác; tọa độ dựng hình phải được tính từ hệ thức,
  không ước lượng theo dáng hình.

6. TỨ GIÁC VÀ ĐA GIÁC
- Tổng góc trong tứ giác là 360°. Tổng góc trong n-giác là (n−2)·180°; tổng góc ngoài là 360°.
- Hình thang có một cặp cạnh đối song song; hai góc kề một cạnh bên bù nhau. Đường trung bình song song
  hai đáy và bằng nửa tổng hai đáy. Hình thang vuông có một cạnh bên vuông góc hai đáy.
- Hình thang cân có hai cạnh bên bằng nhau, hai góc kề mỗi đáy bằng nhau và hai đường chéo bằng nhau.
  Dấu hiệu: hình thang có hai góc kề một đáy bằng nhau hoặc hai đường chéo bằng nhau.
- Hình bình hành có hai cặp cạnh đối song song; cạnh đối bằng nhau, góc đối bằng nhau, hai góc kề bù,
  hai đường chéo cắt nhau tại trung điểm mỗi đường. Dấu hiệu tương ứng gồm: cạnh đối song song/bằng nhau,
  một cặp cạnh đối vừa song song vừa bằng nhau, hoặc hai đường chéo cắt nhau tại trung điểm.
- Hình chữ nhật là hình bình hành có một góc vuông; có bốn góc vuông và hai đường chéo bằng nhau,
  cắt nhau tại trung điểm. Dấu hiệu: hình bình hành có một góc vuông hoặc hai đường chéo bằng nhau.
- Hình thoi là hình bình hành có hai cạnh kề bằng nhau; bốn cạnh bằng nhau, hai đường chéo vuông góc,
  cắt nhau tại trung điểm và phân giác các góc. Dấu hiệu: hình bình hành có hai cạnh kề bằng nhau,
  hai đường chéo vuông góc hoặc một đường chéo là phân giác một góc.
- Hình vuông vừa là hình chữ nhật vừa là hình thoi: bốn cạnh bằng nhau, bốn góc vuông; đường chéo bằng
  nhau, vuông góc, cắt nhau tại trung điểm và phân giác các góc.
- Hình diều có hai cặp cạnh kề bằng nhau; đường chéo nối hai đỉnh chung là trục đối xứng, vuông góc
  và chia đôi đường chéo kia, đồng thời phân giác hai góc ở hai đỉnh chung.
- Đa giác đều có các cạnh và góc bằng nhau; góc trong bằng (n−2)·180°/n, góc ngoài bằng 360°/n.

7. ĐƯỜNG TRÒN
- Mọi điểm trên (O;R) cách O một khoảng R. Đường kính là dây lớn nhất và bằng 2R.
- Đường kính vuông góc một dây thì đi qua trung điểm dây và chia đôi cung căng dây; đảo lại đúng.
  Hai dây bằng nhau khi và chỉ khi cách tâm bằng nhau, và khi đó căng hai cung bằng nhau.
- Góc ở tâm bằng số đo cung bị chắn. Góc nội tiếp bằng nửa số đo cung bị chắn; các góc nội tiếp cùng
  chắn một cung bằng nhau; góc nội tiếp chắn nửa đường tròn bằng 90°.
- Góc tạo bởi tiếp tuyến và dây cung bằng nửa số đo cung bị chắn. Bán kính tới tiếp điểm vuông góc
  tiếp tuyến; đường thẳng vuông góc bán kính tại điểm trên đường tròn là tiếp tuyến.
- Từ một điểm ngoài đường tròn, hai tiếp tuyến có độ dài bằng nhau; đường nối điểm đó với tâm là
  phân giác góc tạo bởi hai tiếp tuyến và trung trực dây nối hai tiếp điểm.
- Tứ giác nội tiếp có tổng hai góc đối bằng 180°; đảo lại, tứ giác có một cặp góc đối bù thì nội tiếp.
  Các dấu hiệu khác: hai đỉnh cùng nhìn một đoạn dưới góc bằng nhau; góc ngoài bằng góc trong đối diện.
- Công suất điểm: hai cát tuyến PAB, PCD cho PA·PB=PC·PD; tiếp tuyến PT và cát tuyến PAB cho PT²=PA·PB.
- Độ dài đường tròn C=2πR=πd; độ dài cung n° là n/360·2πR; diện tích hình tròn S=πR²;
  diện tích quạt tròn n° là n/360·πR².

8. ĐỐI XỨNG, PHÉP BIẾN HÌNH VÀ TỌA ĐỘ
- Đối xứng trục bảo toàn khoảng cách và góc; trục là trung trực đoạn nối một điểm với ảnh của nó.
  Đối xứng tâm O biến M thành M' sao cho O là trung điểm MM'. Tịnh tiến bảo toàn vectơ dịch chuyển.
- Trên mặt phẳng tọa độ: A(x₁,y₁), B(x₂,y₂), AB=√((x₂−x₁)²+(y₂−y₁)²),
  trung điểm M((x₁+x₂)/2,(y₁+y₂)/2). Hai vectơ cùng phương khi định thức bằng 0, vuông góc khi tích vô hướng bằng 0.
- Đồ thị hình học phải giữ đúng tỉ lệ trên hai trục khi dùng khoảng cách, góc, đường tròn hoặc vuông góc.

9. CHU VI, DIỆN TÍCH VÀ HÌNH KHÔNG GIAN
- Tam giác: S=1/2·a·hₐ. Tam giác vuông: S=1/2 tích hai cạnh góc vuông. Hình chữ nhật: S=ab;
  hình vuông: S=a²; hình bình hành: S=a·h; hình thoi: S=1/2·d₁·d₂;
  hình thang: S=1/2·(a+b)·h; đa giác: chia thành các hình cơ bản không chồng lấn.
- Lăng trụ đứng: V=Sđáy·h, Sxq=Pđáy·h. Hình hộp chữ nhật: V=abc; Stp=2(ab+bc+ca).
- Hình chóp: V=1/3·Sđáy·h. Hình trụ: V=πR²h, Sxq=2πRh, Stp=2πRh+2πR².
- Hình nón: V=1/3·πR²h, đường sinh l=√(R²+h²), Sxq=πRl, Stp=πRl+πR².
- Hình cầu: S=4πR², V=4/3·πR³. Trong hình không gian, nét khuất có thể dùng nét đứt theo quy ước;
  quy tắc nét liền của GeoDraw áp dụng cho hình học phẳng.

10. QUY TẮC SUY LUẬN VÀ DỰNG HÌNH
- Phân biệt giả thiết với kết luận: chỉ vẽ ký hiệu quan hệ được cho hoặc đã dùng để định nghĩa phép dựng;
  không đánh dấu trước điều cần chứng minh. Định nghĩa hình làm ràng buộc tọa độ nhưng không tự tạo mọi ký hiệu.
- Mọi điểm phụ phải được xác định bằng giao điểm, hình chiếu, trung điểm, tỉ số, quỹ tích hoặc phép biến hình
  nêu trong đề. Không đặt điểm bằng mắt; kiểm tra số học song song, vuông góc, thẳng hàng, bằng nhau và góc.
- Tên đa giác theo thứ tự đi quanh biên. Tên góc có đỉnh ở chữ giữa. Tên tam giác bằng nhau/đồng dạng
  phải cùng thứ tự tương ứng. Khi dữ kiện mâu thuẫn hoặc thiếu hình tham chiếu, dừng và yêu cầu làm rõ.
"""

# The same curriculum powers the generator, the API help endpoint and the
# Streamlit settings panel, so linked clients cannot drift to different rules.
MIDDLE_SCHOOL_GEOMETRY_RULES += THCS_GEOMETRY_CURRICULUM_VI
GEOMETRY_HELP_VI += THCS_GEOMETRY_CURRICULUM_VI
