package com.dividinghead.calculator.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.dividinghead.calculator.ui.screens.differential.DifferentialIndexingScreen
import com.dividinghead.calculator.ui.screens.headsettings.HeadSettingsScreen
import com.dividinghead.calculator.ui.screens.helical.HelicalIndexingScreen
import com.dividinghead.calculator.ui.screens.history.HistoryScreen
import com.dividinghead.calculator.ui.screens.simple.SimpleIndexingScreen
import com.dividinghead.calculator.ui.screens.start.StartScreen
import com.dividinghead.calculator.viewmodel.AppViewModelFactory

@Composable
fun DividingHeadNavGraph(factory: AppViewModelFactory) {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = Routes.START) {
        composable(Routes.START) {
            StartScreen(
                onSimple = { navController.navigate(Routes.SIMPLE) },
                onDifferential = { navController.navigate(Routes.DIFFERENTIAL) },
                onHelical = { navController.navigate(Routes.HELICAL) },
                onSettings = { navController.navigate(Routes.HEAD_SETTINGS) },
                onHistory = { navController.navigate(Routes.HISTORY) }
            )
        }
        composable(Routes.HEAD_SETTINGS) {
            HeadSettingsScreen(factory = factory, onBack = { navController.popBackStack() })
        }
        composable(Routes.SIMPLE) {
            SimpleIndexingScreen(factory = factory, onBack = { navController.popBackStack() })
        }
        composable(Routes.DIFFERENTIAL) {
            DifferentialIndexingScreen(factory = factory, onBack = { navController.popBackStack() })
        }
        composable(Routes.HELICAL) {
            HelicalIndexingScreen(factory = factory, onBack = { navController.popBackStack() })
        }
        composable(Routes.HISTORY) {
            HistoryScreen(factory = factory, onBack = { navController.popBackStack() })
        }
    }
}
