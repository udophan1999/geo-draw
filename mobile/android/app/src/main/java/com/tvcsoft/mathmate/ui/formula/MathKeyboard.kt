package com.tvcsoft.mathmate.ui.formula

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.filled.Backspace
import androidx.compose.material.icons.filled.KeyboardCapslock
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.tvcsoft.mathmate.core.SharedData
import com.tvcsoft.mathmate.ui.math.MathRenderer
import com.tvcsoft.mathmate.ui.theme.Haptics

/** One key of the math keyboard. */
data class MathKey(
    val id: String,
    /** What the key shows: LaTeX drawn by the renderer, or plain text when `text` is set. */
    val label: String,
    val text: Boolean,
    /** Read by TalkBack. */
    val spoken: String,
    val action: Action,
) {
    sealed interface Action {
        /** Keys for MTMathEditor.insert, in order. */
        data class Keys(val keys: List<String>) : Action
        /** A gallery-style template (`#?` slots, `#@` the term before the caret). */
        data class Template(val latex: String) : Action
    }

    companion object {
        fun latex(id: String, label: String, spoken: String, vararg keys: String) = MathKey(id, label, false, spoken, Action.Keys(keys.toList()))
        fun template(id: String, label: String, spoken: String, template: String) = MathKey(id, label, false, spoken, Action.Template(template))
        fun plain(character: String, spoken: String = character, key: String = character) = MathKey(character, character, true, spoken, Action.Keys(listOf(key)))
    }
}

private enum class Page(val title: String) { NUMBERS("123"), LETTERS("abc"), GEOMETRY("Hình"), FUNCTIONS("f(x)"), GALLERY("Mẫu") }

/** The on-screen keyboard of the formula editor (web: MathLive's virtual keyboard; iOS: MathKeyboard). */
@Composable
fun MathKeyboard(model: FormulaEditorModel) {
    var page by rememberSaveable { mutableStateOf(Page.NUMBERS) }
    var uppercase by rememberSaveable { mutableStateOf(true) }
    val context = LocalContext.current
    fun press(key: MathKey) {
        Haptics.tick(context)
        when (val action = key.action) {
            is MathKey.Action.Keys -> action.keys.forEach(model::key)
            is MathKey.Action.Template -> model.template(action.latex)
        }
    }
    Surface(color = MaterialTheme.colorScheme.surfaceContainer) {
        Column(Modifier.fillMaxWidth().padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(Modifier.height(232.dp)) {
                when (page) {
                    Page.NUMBERS -> KeyGrid(numbers, ::press)
                    Page.GEOMETRY -> KeyGrid(geometry, ::press)
                    Page.FUNCTIONS -> KeyGrid(functions, ::press)
                    Page.LETTERS -> Letters(uppercase, { uppercase = !uppercase }, ::press)
                    Page.GALLERY -> TemplateGallery { model.template(it) }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                for (item in Page.entries) {
                    val selected = page == item
                    Box(
                        Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceContainerHigh)
                            .clickable { page = item }
                            .sizeIn(minWidth = 40.dp, minHeight = 36.dp)
                            .padding(horizontal = 8.dp)
                            .testTag("page-${item.title}"),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            item.title, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold,
                            color = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
                        )
                    }
                }
                Spacer(Modifier.weight(1f))
                Control(Icons.AutoMirrored.Filled.ArrowBack, "Sang trái", "key-left") { model.left() }
                Control(Icons.AutoMirrored.Filled.ArrowForward, "Sang phải", "key-right") { model.right() }
                Control(Icons.AutoMirrored.Filled.Backspace, "Xóa", "key-backspace") { model.backspace() }
            }
        }
    }
}

@Composable
private fun Control(icon: ImageVector, spoken: String, tag: String, action: () -> Unit) {
    Box(
        Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surfaceContainerHigh)
            .clickable(onClick = action)
            .size(width = 44.dp, height = 36.dp)
            .semantics { contentDescription = spoken }
            .testTag(tag),
        contentAlignment = Alignment.Center,
    ) { Icon(icon, contentDescription = null, modifier = Modifier.size(20.dp)) }
}

@Composable
private fun KeyGrid(rows: List<List<MathKey>>, onPress: (MathKey) -> Unit) {
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        for (row in rows) {
            Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                for (key in row) KeyButton(key) { onPress(key) }
            }
        }
    }
}

@Composable
private fun Letters(uppercase: Boolean, onShift: () -> Unit, onPress: (MathKey) -> Unit) {
    val rows = listOf("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM").map { row ->
        row.map { MathKey.plain(if (uppercase) it.toString() else it.lowercase()) }
    }
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        rows.forEachIndexed { index, row ->
            Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                if (index == 2) {
                    Box(
                        Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .clip(RoundedCornerShape(8.dp))
                            .background(MaterialTheme.colorScheme.surfaceContainerHigh)
                            .clickable(onClick = onShift)
                            .semantics { contentDescription = if (uppercase) "Chữ thường" else "Chữ hoa" }
                            .testTag("key-shift"),
                        contentAlignment = Alignment.Center,
                    ) { Icon(Icons.Filled.KeyboardCapslock, null) }
                }
                for (key in row) KeyButton(key) { onPress(key) }
            }
        }
        Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            for (key in listOf(MathKey.plain(","), MathKey.plain("'", "phẩy trên"), MathKey.plain("("), MathKey.plain(")"), MathKey.plain("|"))) {
                KeyButton(key) { onPress(key) }
            }
        }
    }
}

@Composable
private fun RowScope.KeyButton(key: MathKey, onClick: () -> Unit) {
    val color = MaterialTheme.colorScheme.onSurface.toArgb()
    val density = LocalDensity.current
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 1.dp,
        modifier = Modifier
            .weight(1f)
            .fillMaxHeight()
            .semantics { contentDescription = key.spoken }
            .testTag("key-${key.id}"),
    ) {
        Box(contentAlignment = Alignment.Center) {
            if (key.text) {
                Text(key.label, style = MaterialTheme.typography.titleLarge)
            } else {
                val math = remember(key.label, color) { MathRenderer.render(key.label, with(density) { 22.dp.toPx() }, color) }
                if (math != null) {
                    Image(
                        math.bitmap.asImageBitmap(), contentDescription = null,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.widthIn(max = 62.dp).heightIn(max = 40.dp),
                    )
                } else {
                    Text(key.spoken, style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}

/** The formula gallery (web: the MathLive dialog's tabs), from shared/formula_templates.json. */
@Composable
fun TemplateGallery(onPick: (String) -> Unit) {
    var group by rememberSaveable { mutableStateOf(SharedData.formulaGroups.firstOrNull()?.id ?: "") }
    val current = SharedData.formulaGroups.firstOrNull { it.id == group }
    val color = MaterialTheme.colorScheme.onSurface.toArgb()
    val density = LocalDensity.current
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            for (item in SharedData.formulaGroups) {
                val selected = item.id == group
                Box(
                    Modifier
                        .clip(RoundedCornerShape(50))
                        .background(if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceContainerHigh)
                        .clickable { group = item.id }
                        .padding(horizontal = 12.dp, vertical = 6.dp),
                ) {
                    Text(item.name, style = MaterialTheme.typography.labelLarge, color = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface)
                }
            }
        }
        LazyVerticalGrid(
            columns = GridCells.Adaptive(if (current?.wide == true) 160.dp else 72.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(current?.items.orEmpty()) { template ->
                // \square is the renderer's empty-slot box.
                val latex = template.latex.replace("#?", "\\square ").replace("#@", "\\square ")
                val math = remember(latex, color) { MathRenderer.render(latex, with(density) { 17.dp.toPx() }, color) }
                Surface(
                    onClick = { onPick(template.latex) },
                    shape = RoundedCornerShape(10.dp),
                    color = MaterialTheme.colorScheme.surface,
                    modifier = Modifier.height(52.dp).semantics { contentDescription = template.label }.testTag("template"),
                ) {
                    Box(Modifier.padding(horizontal = 6.dp), contentAlignment = Alignment.Center) {
                        if (math != null) {
                            Image(math.bitmap.asImageBitmap(), contentDescription = null, contentScale = ContentScale.Fit, modifier = Modifier.heightIn(max = 36.dp))
                        } else {
                            Text(template.label, style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
        }
    }
}

// Pages (the same keys as the iOS app)

private val numbers = listOf(
    listOf(MathKey.plain("7"), MathKey.plain("8"), MathKey.plain("9"), MathKey.plain("÷", "chia"), MathKey.latex("frac", "\\frac{\\square}{\\square}", "phân số", "/")),
    listOf(MathKey.plain("4"), MathKey.plain("5"), MathKey.plain("6"), MathKey.plain("×", "nhân"), MathKey.template("square", "\\square^{2}", "bình phương", "#@^{2}")),
    listOf(MathKey.plain("1"), MathKey.plain("2"), MathKey.plain("3"), MathKey.plain("−", "trừ", "-"), MathKey.latex("power", "\\square^{\\square}", "lũy thừa", "^")),
    listOf(MathKey.plain("0"), MathKey.plain(","), MathKey.plain("="), MathKey.plain("+", "cộng"), MathKey.latex("sqrt", "\\sqrt{\\square}", "căn bậc hai", "\\sqrt")),
    listOf(MathKey.plain("x"), MathKey.plain("y"), MathKey.plain("("), MathKey.plain(")"), MathKey.latex("subscript", "\\square_{\\square}", "chỉ số dưới", "_")),
)

private val geometry = listOf(
    listOf(
        MathKey.latex("angle", "\\angle", "góc", "\\angle"), MathKey.latex("triangle", "\\triangle", "tam giác", "\\triangle"),
        MathKey.latex("perp", "\\perp", "vuông góc", "\\perp"), MathKey.latex("parallel", "\\parallel", "song song", "\\parallel"),
        MathKey.latex("similar", "\\backsim", "đồng dạng", "\\backsim"),
    ),
    listOf(
        MathKey.template("hat", "\\widehat{\\square}", "góc (mũ)", "\\widehat{#?}"),
        MathKey.template("segment", "\\overline{\\square}", "đoạn thẳng", "\\overline{#?}"),
        MathKey.template("vector", "\\overrightarrow{\\square}", "vectơ", "\\overrightarrow{#?}"),
        MathKey.template("arc", "\\overset{\\frown}{\\square}", "cung", "\\overset{\\frown}{#?}"),
        MathKey.latex("degree", "\\square^{\\circ}", "độ", "^", "\\circ", "^"),
    ),
    listOf(
        MathKey.latex("pi", "\\pi", "pi", "\\pi"), MathKey.latex("cong", "=", "bằng", "="),
        MathKey.latex("ne", "\\ne", "khác", "\\ne"), MathKey.latex("cdot", "\\cdot", "chấm nhân", "\\cdot"),
        MathKey.latex("nthroot", "\\sqrt[\\square]{\\square}", "căn bậc n", "\\nthroot"),
    ),
    listOf(MathKey.plain("A"), MathKey.plain("B"), MathKey.plain("C"), MathKey.plain("D"), MathKey.plain("O")),
    listOf(MathKey.plain("H"), MathKey.plain("M"), MathKey.plain("N"), MathKey.plain("E"), MathKey.plain("F")),
)

private val functions = listOf(
    listOf(
        MathKey.latex("sin", "\\sin", "sin", "\\sin"), MathKey.latex("cos", "\\cos", "cos", "\\cos"),
        MathKey.latex("tan", "\\tan", "tan", "\\tan"), MathKey.latex("cot", "\\cot", "cot", "\\cot"),
        MathKey.template("log", "\\log_{\\square}", "logarit", "\\log_{#?}#?"),
    ),
    listOf(
        MathKey.latex("le", "\\le", "nhỏ hơn hoặc bằng", "\\le"), MathKey.latex("ge", "\\ge", "lớn hơn hoặc bằng", "\\ge"),
        MathKey.latex("lt", "<", "nhỏ hơn", "<"), MathKey.latex("gt", ">", "lớn hơn", ">"),
        MathKey.latex("approx", "\\approx", "xấp xỉ", "\\approx"),
    ),
    listOf(
        MathKey.latex("pm", "\\pm", "cộng trừ", "\\pm"), MathKey.latex("infty", "\\infty", "vô cực", "\\infty"),
        MathKey.latex("Delta", "\\Delta", "delta", "\\Delta"), MathKey.latex("alpha", "\\alpha", "alpha", "\\alpha"),
        MathKey.latex("abs", "|\\square|", "giá trị tuyệt đối", "||"),
    ),
    listOf(
        MathKey.latex("in", "\\in", "thuộc", "\\in"), MathKey.latex("notin", "\\notin", "không thuộc", "\\notin"),
        MathKey.latex("subset", "\\subset", "tập con", "\\subset"), MathKey.latex("cup", "\\cup", "hợp", "\\cup"),
        MathKey.latex("cap", "\\cap", "giao", "\\cap"),
    ),
    listOf(
        MathKey.latex("implies", "\\Rightarrow", "suy ra", "\\Rightarrow"), MathKey.latex("iff", "\\Leftrightarrow", "tương đương", "\\Leftrightarrow"),
        MathKey.latex("ln", "\\ln", "ln", "\\ln"), MathKey.template("int", "\\int", "tích phân", "\\int_{#?}^{#?}#?"),
        MathKey.template("sum", "\\sum", "tổng", "\\sum_{#?}^{#?}#?"),
    ),
)
