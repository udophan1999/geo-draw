package com.tvcsoft.mathmate.ui.theme

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/** The name shown to users. The app never names the AI provider (CLAUDE.md). */
object Brand {
    const val APP_NAME = "MathMate"

    /** The web's primary blue (web/src/index.css), lighter in the dark. */
    val primaryLight = Color(0xFF2563EB)
    val primaryDark = Color(0xFF60A5FA)
    val success = Color(0xFF16A34A)
}

private val Light = lightColorScheme(
    primary = Brand.primaryLight,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDBEAFE),
    onPrimaryContainer = Color(0xFF1E3A8A),
    secondaryContainer = Color(0xFFEFF6FF),
    background = Color.White,
    surface = Color.White,
    surfaceContainerLowest = Color.White,
    surfaceContainerLow = Color(0xFFF8FAFC),
    surfaceContainer = Color(0xFFF1F5F9),
    surfaceContainerHigh = Color(0xFFE9EEF5),
    error = Color(0xFFDC2626),
)

private val Dark = darkColorScheme(
    primary = Brand.primaryDark,
    onPrimary = Color(0xFF0B1220),
    primaryContainer = Color(0xFF1E3A8A),
    onPrimaryContainer = Color(0xFFDBEAFE),
    secondaryContainer = Color(0xFF172554),
    background = Color(0xFF0B0B0C),
    surface = Color(0xFF0B0B0C),
    surfaceContainerLowest = Color(0xFF0B0B0C),
    surfaceContainerLow = Color(0xFF161618),
    surfaceContainer = Color(0xFF1C1C1F),
    surfaceContainerHigh = Color(0xFF26262A),
    error = Color(0xFFF87171),
)

/** Material 3 in the brand colours; no dynamic (wallpaper) colours, so the app looks like the web. */
@Composable
fun MathMateTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) Dark else Light, content = content)
}

/** Light taps for the moments that matter: a deeper hint, a sent message, a finished drawing. */
object Haptics {
    private fun vibrator(context: Context): Vibrator? =
        if (Build.VERSION.SDK_INT >= 31) {
            (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }

    fun tick(context: Context) = play(context, VibrationEffect.EFFECT_TICK)
    fun success(context: Context) = play(context, VibrationEffect.EFFECT_DOUBLE_CLICK)

    private fun play(context: Context, effect: Int) {
        if (Build.VERSION.SDK_INT < 29) return
        try {
            vibrator(context)?.vibrate(VibrationEffect.createPredefined(effect))
        } catch (_: Exception) {
        }
    }
}
