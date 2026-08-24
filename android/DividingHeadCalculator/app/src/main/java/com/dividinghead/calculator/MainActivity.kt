package com.dividinghead.calculator

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.dividinghead.calculator.ui.navigation.DividingHeadNavGraph
import com.dividinghead.calculator.ui.theme.DividingHeadTheme
import com.dividinghead.calculator.viewmodel.AppViewModelFactory
import com.dividinghead.calculator.viewmodel.SettingsViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val app = application as DividingHeadApplication
        val factory = AppViewModelFactory(app)

        setContent {
            val settingsViewModel: SettingsViewModel = viewModel(factory = factory)
            val settings by settingsViewModel.settings.collectAsState()

            DividingHeadTheme(
                themeMode = settings.themeMode,
                largeFontForShop = settings.largeFontForShop
            ) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    DividingHeadNavGraph(factory = factory)
                }
            }
        }
    }
}
