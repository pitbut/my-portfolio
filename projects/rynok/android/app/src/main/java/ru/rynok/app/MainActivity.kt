package ru.rynok.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import ru.rynok.app.ui.nav.RynokNavHost
import ru.rynok.app.ui.theme.RynokTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            RynokTheme {
                RynokNavHost()
            }
        }
    }
}
