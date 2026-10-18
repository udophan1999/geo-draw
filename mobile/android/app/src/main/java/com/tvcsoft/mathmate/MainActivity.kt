package com.tvcsoft.mathmate

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.tvcsoft.mathmate.ui.MathMateRoot
import com.tvcsoft.mathmate.ui.theme.MathMateTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // UI tests start the app with `uiTesting` (credentials in memory) and `api` (their server).
        val testing = TestingOptions(
            active = intent.getBooleanExtra("uiTesting", false),
            apiUrl = intent.getStringExtra("api"),
        )
        val container = (application as MathMateApplication).container(testing)
        setContent { MathMateTheme { MathMateRoot(container) } }
    }
}
