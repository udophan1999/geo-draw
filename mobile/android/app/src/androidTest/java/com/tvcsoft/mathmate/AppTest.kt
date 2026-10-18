package com.tvcsoft.mathmate

import android.content.Intent
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performImeAction
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.getOrNull
import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.pressKey
import androidx.test.espresso.action.ViewActions.replaceText
import androidx.test.espresso.action.ViewActions.typeText
import androidx.test.espresso.matcher.ViewMatchers.isAssignableFrom
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import android.view.KeyEvent
import com.tvcsoft.mathmate.ui.composer.CHIP
import com.tvcsoft.mathmate.ui.composer.MathEditText
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.After
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

/**
 * The app against web/e2e/server.py (the real API on a throwaway folder, with a fake AI): start
 * it with `.venv/bin/python web/e2e/server.py 8797` from the repo root. The emulator reaches the
 * computer at 10.0.2.2; `-e api <url>` points elsewhere. Problems are not geometry, so no Manim
 * render runs (as in the Playwright and XCUITest suites).
 */
@OptIn(ExperimentalTestApi::class)
@RunWith(AndroidJUnit4::class)
class AppTest {
    @get:Rule val compose = createEmptyComposeRule()
    private lateinit var scenario: ActivityScenario<MainActivity>

    private val api: String =
        InstrumentationRegistry.getArguments().getString("api") ?: "http://10.0.2.2:8797"

    @Before
    fun launch() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        // A fresh container per test: credentials in memory, no remembered guest choice.
        (context.applicationContext as MathMateApplication).resetForTests()
        val intent = Intent(context, MainActivity::class.java).putExtra("uiTesting", true).putExtra("api", api)
        scenario = ActivityScenario.launch(intent)
    }

    @After
    fun close() = scenario.close()

    private fun waitFor(tag: String, timeout: Long = 10_000) = try {
        compose.waitUntilAtLeastOneExists(hasTestTag(tag), timeout)
    } catch (error: Throwable) {
        // What was on screen instead.
        throw AssertionError("no '$tag' in:\n" + compose.onAllNodes(androidx.compose.ui.test.isRoot()).fetchSemanticsNodes().joinToString("\n") { root ->
            dump(root, 0)
        }, error)
    }

    private fun dump(node: androidx.compose.ui.semantics.SemanticsNode, depth: Int): String {
        val line = "  ".repeat(depth) + node.config.toString()
        return (listOf(line) + node.children.map { dump(it, depth + 1) }).joinToString("\n")
    }
    private fun waitForText(text: String, timeout: Long = 10_000) = compose.waitUntilAtLeastOneExists(hasText(text, substring = true), timeout)

    private fun startAsGuest() {
        waitFor("tryAsGuest")
        compose.onNodeWithTag("tryAsGuest").performClick()
        waitFor("newConversation")
    }

    private fun typeInComposer(text: String) {
        onView(isAssignableFrom(MathEditText::class.java)).perform(typeText(text))
    }

    @Test
    fun aGuestAsksAndTheReplyStreamsIn() {
        startAsGuest()
        compose.onNodeWithTag("newConversation").performClick()
        waitFor("send")
        typeInComposer("Giai x+1=3")
        compose.onNodeWithTag("send").performClick()
        // The fake AI's hint, then the tutor bar at level 2.
        waitForText("sang vế phải", 15_000)
        waitFor("hintLevel")
        compose.waitUntil(10_000) {
            compose.onAllNodesWithTag("hintLevel").fetchSemanticsNodes().any { node ->
                node.config.getOrNull(SemanticsProperties.ContentDescription)?.any { it.startsWith("Bậc 2/5") } == true
            }
        }
        compose.onNodeWithTag("userMessage").assertIsDisplayed()
    }

    @Test
    fun deeperHintAndAnAiErrorAreShown() {
        startAsGuest()
        compose.onNodeWithTag("newConversation").performClick()
        waitFor("send")
        // Espresso cannot type Vietnamese letters as key events.
        onView(isAssignableFrom(MathEditText::class.java)).perform(replaceText("lỗi ai"))
        compose.onNodeWithTag("send").performClick()
        // The tutor saved an error message (meta.error), shown in the conversation.
        compose.waitUntilAtLeastOneExists(hasTestTag("assistantMessage"), 15_000)
    }

    @Test
    fun aWrongPasswordIsRefused() {
        waitFor("username")
        compose.onNodeWithTag("username").performTextInput("khong-co-ai")
        compose.onNodeWithTag("password").performTextInput("sai-mat-khau")
        // Submit from the keyboard: the form's buttons may sit under it.
        compose.onNodeWithTag("password").performImeAction()
        waitFor("authError")
        compose.onNodeWithText("Sai tên đăng nhập hoặc mật khẩu.", substring = true).assertExists()
    }

    @Test
    fun registeringATakenNameOffersFreeOnes() {
        val name = "hs" + UUID.randomUUID().toString().take(8)
        waitFor("showRegister")
        compose.onNodeWithTag("showRegister").performScrollTo().performClick()
        compose.onNodeWithTag("username").performTextInput(name)
        compose.onNodeWithTag("password").performTextInput("hinhhoc1")
        compose.onNodeWithTag("confirmPassword").performTextInput("hinhhoc1")
        compose.onNodeWithTag("confirmPassword").performImeAction()
        // Password hashing makes registering slow on a busy test server.
        waitFor("newConversation", 30_000)

        // Signed in: sign out, then register the same name again.
        compose.onNodeWithTag("accountMenu").performClick()
        compose.onNodeWithText("Đăng xuất").performClick()
        waitFor("showRegister")
        compose.onNodeWithTag("showRegister").performScrollTo().performClick()
        compose.onNodeWithTag("username").performTextInput(name)
        compose.onNodeWithTag("password").performTextInput("hinhhoc1")
        compose.onNodeWithTag("confirmPassword").performTextInput("hinhhoc1")
        compose.onNodeWithTag("confirmPassword").performImeAction()
        waitFor("suggestion", 30_000)
        compose.onAllNodesWithTag("suggestion").fetchSemanticsNodes().isNotEmpty()
    }

    @Test
    fun theFormulaEditorWritesAFractionIntoTheMessage() {
        startAsGuest()
        compose.onNodeWithTag("newConversation").performClick()
        waitFor("openFormula")
        compose.onNodeWithTag("openFormula").performClick()
        waitFor("formulaEditor")
        compose.onNodeWithTag("key-1").performClick()
        compose.onNodeWithTag("key-frac").performClick()
        compose.onNodeWithTag("key-2").performClick()
        compose.waitUntil(5_000) {
            compose.onAllNodes(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "\\frac{1}{2}")).fetchSemanticsNodes().isNotEmpty()
        }
        compose.onNodeWithTag("insertFormula").performClick()
        // A fraction cannot be plain text: it becomes a chip, `$\frac{1}{2}$` in the message.
        compose.waitUntil(5_000) {
            compose.onAllNodesWithTag("composer").fetchSemanticsNodes().any { node ->
                node.config.getOrNull(SemanticsProperties.ContentDescription)?.any { it.contains("\$\\frac{1}{2}\$") } == true
            }
        }
    }

    @Test
    fun theRootsOfTheSymbolBarOpenTheEditorWithTheirSlot() {
        startAsGuest()
        compose.onNodeWithTag("newConversation").performClick()
        waitFor("toggleSymbols")
        compose.onNodeWithTag("toggleSymbols").performClick()
        compose.onNode(SemanticsMatcher.expectValue(SemanticsProperties.ContentDescription, listOf("Căn bậc hai"))).performClick()
        waitFor("formulaEditor")
        compose.onNodeWithTag("key-2").performClick() // into the root's slot
        compose.onNodeWithTag("insertFormula").performClick()
        // A root stays a formula, drawn with its bar (as text, √123 would not show where it ends).
        composerText { text -> assertTrue("a chip: $text", text.contains(CHIP)) }

        compose.onNode(SemanticsMatcher.expectValue(SemanticsProperties.ContentDescription, listOf("Căn bậc ba"))).performClick()
        waitFor("formulaEditor")
        compose.onNodeWithTag("key-8").performClick()
        compose.onNodeWithTag("insertFormula").performClick()
        compose.waitUntil(5_000) {
            compose.onAllNodesWithTag("composer").fetchSemanticsNodes().any { node ->
                node.config.getOrNull(SemanticsProperties.ContentDescription)?.any { it == "\$\\sqrt{2}\$ \$\\sqrt[3]{8}\$ " } == true
            }
        }
    }

    @Test
    fun typedDollarsBecomeAChipAndBackspaceGivesTheSourceBack() {
        startAsGuest()
        compose.onNodeWithTag("newConversation").performClick()
        waitFor("send")
        typeInComposer("Cho \$x^2\$")
        composerText { text -> assertTrue("a chip: $text", text.contains(CHIP)) }
        onView(isAssignableFrom(MathEditText::class.java)).perform(pressKey(KeyEvent.KEYCODE_DEL))
        composerText { text -> assertEquals("Cho \$x^2\$", text.toString()) }
        typeInComposer(" va")
        composerText { text -> assertFalse(text.contains(CHIP)) }
    }

    private fun composerText(check: (CharSequence) -> Unit) {
        onView(isAssignableFrom(MathEditText::class.java)).check { view, _ -> check((view as MathEditText).text) }
    }
}
