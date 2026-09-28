"""Middle-school Euclidean geometry conventions supplied to the code generator."""

GEOMETRY_HELP_VI = """
- Tên các đỉnh được hiểu theo thứ tự đi quanh biên đa giác.
- Hình thang cân: hai đáy song song, hai cạnh bên bằng nhau, các góc kề mỗi đáy bằng nhau.
- Hình bình hành: hai cặp cạnh đối song song.
- Hình chữ nhật: hình bình hành có bốn góc vuông.
- Hình thoi: hình bình hành có bốn cạnh bằng nhau.
- Hình vuông: bốn cạnh bằng nhau và bốn góc vuông.
- Đa giác đều: các cạnh bằng nhau và các góc bằng nhau.
- Ký hiệu góc luôn được đặt theo nhánh trong của đa giác.
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
  squares. A conclusion to prove (for example, EFGH is a rectangle) gets no right-angle square.
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
