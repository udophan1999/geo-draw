// Templates for the formula editor, in the spirit of Word's equation gallery.
// In `latex`, `#?` is an empty slot to fill in and `#@` takes the current selection (or the
// term just before the caret), as MathLive's insert() understands them.

export type FormulaTemplate = { label: string; latex: string }
export type FormulaGroup = { id: string; name: string; wide?: boolean; items: FormulaTemplate[] }

const t = (label: string, latex: string): FormulaTemplate => ({ label, latex })

export const FORMULA_GROUPS: FormulaGroup[] = [
  {
    id: 'basic', name: 'Cơ bản', items: [
      t('Phân số', '\\frac{#@}{#?}'),
      t('Hỗn số', '#?\\frac{#?}{#?}'),
      t('Căn bậc hai', '\\sqrt{#?}'),
      t('Căn bậc n', '\\sqrt[#?]{#?}'),
      t('Lũy thừa', '#@^{#?}'),
      t('Bình phương', '#@^2'),
      t('Chỉ số dưới', '#@_{#?}'),
      t('Giá trị tuyệt đối', '\\left|#?\\right|'),
      t('Ngoặc tròn', '\\left(#?\\right)'),
      t('Ngoặc vuông', '\\left[#?\\right]'),
      t('Ngoặc nhọn', '\\left\\{#?\\right\\}'),
      t('Phần trăm', '#?\\%'),
    ],
  },
  {
    id: 'symbols', name: 'Ký hiệu', items: [
      t('Nhỏ hơn hoặc bằng', '\\le'), t('Lớn hơn hoặc bằng', '\\ge'), t('Khác', '\\ne'),
      t('Xấp xỉ', '\\approx'), t('Cộng trừ', '\\pm'), t('Nhân', '\\times'), t('Chia', '\\div'),
      t('Chấm nhân', '\\cdot'), t('Vô cực', '\\infty'), t('Pi', '\\pi'), t('Độ', '^\\circ'),
      t('Alpha', '\\alpha'), t('Beta', '\\beta'), t('Gamma', '\\gamma'), t('Delta', '\\Delta'),
      t('Phi', '\\varphi'),
    ],
  },
  {
    id: 'geometry', name: 'Hình học', items: [
      t('Góc', '\\widehat{#?}'), t('Góc (ký hiệu)', '\\angle #?'), t('Tam giác', '\\triangle #?'),
      t('Vuông góc', '\\perp'), t('Song song', '\\parallel'), t('Đoạn thẳng', '\\overline{#?}'),
      t('Vectơ', '\\overrightarrow{#?}'), t('Cung', '\\overset{\\frown}{#?}'),
      t('Đồng dạng', '\\backsim'), t('Số đo độ', '#?^\\circ'),
      t('Tam giác bằng nhau', '\\triangle #?=\\triangle #?'),
      t('Tam giác đồng dạng', '\\triangle #?\\backsim\\triangle #?'),
    ],
  },
  {
    id: 'trig', name: 'Lượng giác', items: [
      t('sin', '\\sin #?'), t('cos', '\\cos #?'), t('tan', '\\tan #?'), t('cot', '\\cot #?'),
      t('sin²', '\\sin^2 #?'), t('cos²', '\\cos^2 #?'), t('sin góc', '\\sin\\widehat{#?}'),
      t('cos góc', '\\cos\\widehat{#?}'),
    ],
  },
  {
    id: 'algebra', name: 'Đại số & giải tích', items: [
      t('Hệ 2 phương trình', '\\begin{cases}#?\\\\#?\\end{cases}'),
      t('Hệ 3 phương trình', '\\begin{cases}#?\\\\#?\\\\#?\\end{cases}'),
      t('Hàm số', 'f(#?)'), t('Đạo hàm', "f'(#?)"), t('Logarit', '\\log_{#?}#?'),
      t('Logarit tự nhiên', '\\ln #?'), t('Giới hạn', '\\lim_{#?\\to #?}#?'),
      t('Tổng', '\\sum_{#?}^{#?}#?'), t('Tích phân', '\\int_{#?}^{#?}#?\\,dx'),
      t('Nghiệm x₁, x₂', 'x_{1,2}'),
    ],
  },
  {
    id: 'sets', name: 'Tập hợp & logic', items: [
      t('Thuộc', '\\in'), t('Không thuộc', '\\notin'), t('Tập con', '\\subset'), t('Hợp', '\\cup'),
      t('Giao', '\\cap'), t('Tập rỗng', '\\varnothing'), t('Suy ra', '\\Rightarrow'),
      t('Tương đương', '\\Leftrightarrow'), t('Với mọi', '\\forall'), t('Tồn tại', '\\exists'),
      t('Số tự nhiên', '\\mathbb{N}'), t('Số nguyên', '\\mathbb{Z}'), t('Số hữu tỉ', '\\mathbb{Q}'),
      t('Số thực', '\\mathbb{R}'), t('Tập hợp', '\\left\\{#?\\mid #?\\right\\}'),
    ],
  },
  {
    id: 'formulas', name: 'Công thức mẫu', wide: true, items: [
      t('Định lý Pythagore', 'BC^2=AB^2+AC^2'),
      t('Hệ thức lượng: đường cao', 'AH^2=BH\\cdot CH'),
      t('Hệ thức lượng: cạnh góc vuông', 'AB^2=BH\\cdot BC'),
      t('Bình phương một tổng', '(a+b)^2=a^2+2ab+b^2'),
      t('Bình phương một hiệu', '(a-b)^2=a^2-2ab+b^2'),
      t('Hiệu hai bình phương', 'a^2-b^2=(a-b)(a+b)'),
      t('Biệt thức', '\\Delta=b^2-4ac'),
      t('Công thức nghiệm', 'x_{1,2}=\\frac{-b\\pm\\sqrt{\\Delta}}{2a}'),
      t('Hệ thức Vi-ét', 'x_1+x_2=-\\frac{b}{a},\\ x_1x_2=\\frac{c}{a}'),
      t('Diện tích tam giác', 'S=\\frac{1}{2}ah'),
      t('Đường tròn', 'C=2\\pi R,\\ S=\\pi R^2'),
      t('Lượng giác cơ bản', '\\sin^2x+\\cos^2x=1'),
    ],
  },
]
