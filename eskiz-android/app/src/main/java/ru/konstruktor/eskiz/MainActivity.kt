package ru.konstruktor.eskiz

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color
import org.opencv.android.OpenCVLoader
import ru.konstruktor.eskiz.ui.EditorScreen
import ru.konstruktor.eskiz.ui.ModelScreen
import ru.konstruktor.eskiz.ui.ProjectListScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!OpenCVLoader.initLocal()) Log.e("Eskiz", "OpenCV не загрузился")
        enableEdgeToEdge()
        setContent {
            EskizTheme {
                // Стек экранов: "p:<id>" — эскиз, "m:<id>" — 3D-модель; пусто — список.
                var stack by rememberSaveable { mutableStateOf(listOf<String>()) }
                var tab by rememberSaveable { mutableStateOf(0) }
                fun push(s: String) { stack = stack + s }
                fun pop() { stack = stack.dropLast(1) }
                val top = stack.lastOrNull()
                when {
                    top == null -> ProjectListScreen(
                        tab = tab, onTab = { tab = it },
                        onOpen = { push("p:$it") }, onOpenModel = { push("m:$it") },
                    )
                    top.startsWith("p:") -> EditorScreen(top.removePrefix("p:"), onBack = ::pop)
                    else -> ModelScreen(top.removePrefix("m:"), onBack = ::pop, onOpenSketch = { push("p:$it") })
                }
            }
        }
    }
}

@Composable
fun EskizTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val scheme = if (dark) darkColorScheme(
        primary = Color(0xFF90CAF9), secondary = Color(0xFFFFCA28),
    ) else lightColorScheme(
        primary = Color(0xFF1565C0), secondary = Color(0xFFFFA000),
    )
    MaterialTheme(colorScheme = scheme, content = content)
}
