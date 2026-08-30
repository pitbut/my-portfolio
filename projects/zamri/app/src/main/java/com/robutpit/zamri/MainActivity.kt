package com.robutpit.zamri

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.robutpit.zamri.ui.ArchiveViewModel
import com.robutpit.zamri.ui.ArchiveViewModelFactory
import com.robutpit.zamri.ui.GameViewModel
import com.robutpit.zamri.ui.GameViewModelFactory
import com.robutpit.zamri.ui.screens.ArchiveScreen
import com.robutpit.zamri.ui.screens.GameScreen
import com.robutpit.zamri.ui.screens.SettingsScreen
import com.robutpit.zamri.ui.screens.StartScreen
import com.robutpit.zamri.ui.theme.ZamriTheme

private object Routes {
    const val START = "start"
    const val SETTINGS = "settings"
    const val GAME = "game"
    const val ARCHIVE = "archive"
}

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)

        val app = application as ZamriApp
        val gameViewModel by viewModels<GameViewModel> { GameViewModelFactory(app) }
        val archiveViewModel by viewModels<ArchiveViewModel> { ArchiveViewModelFactory(app) }

        setContent {
            ZamriTheme {
                val navController = rememberNavController()
                KeepScreenOnWhileGameRuns(navController)

                NavHost(navController = navController, startDestination = Routes.START) {
                    composable(Routes.START) {
                        StartScreen(
                            onPlay = { navController.navigate(Routes.GAME) },
                            onSettings = { navController.navigate(Routes.SETTINGS) },
                            onArchive = { navController.navigate(Routes.ARCHIVE) }
                        )
                    }
                    composable(Routes.SETTINGS) {
                        SettingsScreen(
                            viewModel = gameViewModel,
                            onBack = { navController.popBackStack() }
                        )
                    }
                    composable(Routes.GAME) {
                        GameScreen(
                            viewModel = gameViewModel,
                            onFinished = {
                                gameViewModel.returnToIdle()
                                navController.popBackStack(Routes.START, inclusive = false)
                            },
                            onOpenArchive = { navController.navigate(Routes.ARCHIVE) }
                        )
                    }
                    composable(Routes.ARCHIVE) {
                        ArchiveScreen(
                            viewModel = archiveViewModel,
                            onBack = { navController.popBackStack() }
                        )
                    }
                }
            }
        }
    }
}

/** Keeps the screen awake for the whole game screen, matching the spec's "always-on during play". */
@androidx.compose.runtime.Composable
private fun KeepScreenOnWhileGameRuns(navController: NavHostController) {
    val context = LocalContext.current
    val backStackEntry by navController.currentBackStackEntryAsState()
    val onGameScreen = backStackEntry?.destination?.route == Routes.GAME

    DisposableEffect(onGameScreen) {
        val window = (context as? android.app.Activity)?.window
        if (onGameScreen) {
            window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
        onDispose {
            window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }
}
