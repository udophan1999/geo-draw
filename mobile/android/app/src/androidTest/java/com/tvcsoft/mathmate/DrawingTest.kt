package com.tvcsoft.mathmate

import android.content.Intent
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createEmptyComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.replaceText
import androidx.test.espresso.matcher.ViewMatchers.isAssignableFrom
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.tvcsoft.mathmate.ui.composer.MathEditText
import org.junit.After
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** The figure of a geometry problem, drawn for real by the parser (no AI) on the test server (iOS: DrawingTests). */
@OptIn(ExperimentalTestApi::class)
@RunWith(AndroidJUnit4::class)
class DrawingTest {
    @get:Rule val compose = createEmptyComposeRule()
    private lateinit var scenario: ActivityScenario<MainActivity>

    @Before
    fun launch() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        (context.applicationContext as MathMateApplication).resetForTests()
        val api = InstrumentationRegistry.getArguments().getString("api") ?: "http://10.0.2.2:8797"
        scenario = ActivityScenario.launch(Intent(context, MainActivity::class.java).putExtra("uiTesting", true).putExtra("api", api))
        waitFor("tryAsGuest")
        compose.onNodeWithTag("tryAsGuest").performClick()
        useParser()
    }

    @After
    fun close() = scenario.close()

    private fun waitFor(tag: String, timeout: Long = 10_000) = compose.waitUntilAtLeastOneExists(hasTestTag(tag), timeout)

    /** Settings → "Parser nhanh": figures are drawn on the server without the AI. */
    private fun useParser() {
        waitFor("accountMenu")
        compose.onNodeWithTag("accountMenu").performClick()
        compose.onNodeWithTag("openSettings").performClick()
        compose.waitUntilAtLeastOneExists(hasText("Parser nhanh"), 10_000)
        compose.onNodeWithText("Parser nhanh").performClick()
        compose.onNodeWithTag("saveSettings").performClick()
        waitFor("newConversation")
    }

    @Test
    fun aGeometryProblemIsDrawnAndCanBeRefined() {
        compose.onNodeWithTag("newConversation").performClick()
        waitFor("send")
        onView(isAssignableFrom(MathEditText::class.java)).perform(replaceText("Cho tam giác ABC vuông tại A, AB = 3, AC = 4."))
        compose.onNodeWithTag("send").performClick()

        // The card in the chat shows the drawing once the server has drawn it.
        compose.waitUntilAtLeastOneExists(hasText("Chạm để xem, phóng to, chỉnh hình"), 120_000)
        compose.onNodeWithTag("figureCard").performClick()
        waitFor("drawingVersion")
        compose.onNodeWithText("Phiên bản mới nhất").assertExists()
        waitFor("drawingImage")
        compose.onNodeWithTag("shareDrawing").assertExists()

        // The drawing opens full screen and closes again.
        compose.onNodeWithTag("fullscreenDrawing").performClick()
        waitFor("fullscreenImage")
        compose.onNodeWithTag("closeFullscreen").performClick()
        compose.waitUntilDoesNotExist(hasTestTag("fullscreenImage"), 5_000)

        // A refinement draws a second version; the first stays one tap away.
        compose.onNodeWithTag("refineField").performTextInput("Vẽ đường cao AH")
        compose.onNodeWithTag("sendRefine").performClick()
        waitFor("version-2", 120_000)
        compose.onNodeWithText("Đã yêu cầu: “Vẽ đường cao AH”").assertExists()
        compose.onNodeWithTag("version-1").performClick()
        compose.onNodeWithText("Phiên bản 1/2").assertExists()
    }
}
