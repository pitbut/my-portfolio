package ru.rynok.app.ui.nav

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import ru.rynok.app.FamilyRole
import ru.rynok.app.RynokApp
import ru.rynok.app.ui.archive.ArchiveScreen
import ru.rynok.app.ui.chat.ChatScreen
import ru.rynok.app.ui.family.FamilySetupScreen
import ru.rynok.app.ui.list.ShoppingListScreen
import ru.rynok.app.ui.shopping.ShoppingModeScreen
import ru.rynok.app.ui.stats.StatsScreen

private const val ROUTE_FAMILY_SETUP = "family_setup"
private const val ROUTE_LIST = "list"
private const val ROUTE_SHOPPING = "shopping"
private const val ROUTE_CHAT = "chat"
private const val ROUTE_ARCHIVE = "archive"
private const val ROUTE_STATS = "stats"

private data class BottomTab(val route: String, val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

@Composable
fun RynokNavHost() {
    val context = LocalContext.current
    val app = context.applicationContext as RynokApp
    val navController = rememberNavController()

    // Держим WebSocket-соединение, пока приложение видно пользователю.
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> if (app.prefs.isFamilyConfigured) app.relayClient.connect()
                Lifecycle.Event.ON_STOP -> app.relayClient.disconnect()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    val homeRoute = if (app.prefs.role == FamilyRole.HUSBAND) ROUTE_SHOPPING else ROUTE_LIST
    val startDestination = if (app.prefs.isFamilyConfigured) homeRoute else ROUTE_FAMILY_SETUP

    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBottomBar = currentRoute != null && currentRoute != ROUTE_FAMILY_SETUP

    val tabs = if (app.prefs.role == FamilyRole.HUSBAND) {
        listOf(
            BottomTab(ROUTE_SHOPPING, "Покупки", Icons.Filled.ShoppingCart),
            BottomTab(ROUTE_CHAT, "Чат", Icons.Filled.Chat),
            BottomTab(ROUTE_ARCHIVE, "Архив", Icons.Filled.History),
            BottomTab(ROUTE_STATS, "Статистика", Icons.Filled.Assessment),
        )
    } else {
        listOf(
            BottomTab(ROUTE_LIST, "Список", Icons.Filled.List),
            BottomTab(ROUTE_CHAT, "Чат", Icons.Filled.Chat),
            BottomTab(ROUTE_ARCHIVE, "Архив", Icons.Filled.History),
            BottomTab(ROUTE_STATS, "Статистика", Icons.Filled.Assessment),
        )
    }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    tabs.forEach { tab ->
                        val selected = currentRoute?.let { route ->
                            backStackEntry?.destination?.hierarchy?.any { it.route == tab.route }
                        } ?: false
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(tab.route) {
                                    popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = startDestination,
            modifier = Modifier.padding(padding),
        ) {
            composable(ROUTE_FAMILY_SETUP) {
                FamilySetupScreen(onFamilyReady = {
                    val target = if (app.prefs.role == FamilyRole.HUSBAND) ROUTE_SHOPPING else ROUTE_LIST
                    navController.navigate(target) {
                        popUpTo(ROUTE_FAMILY_SETUP) { inclusive = true }
                    }
                })
            }
            composable(ROUTE_LIST) { ShoppingListScreen() }
            composable(ROUTE_SHOPPING) { ShoppingModeScreen() }
            composable(ROUTE_CHAT) { ChatScreen() }
            composable(ROUTE_ARCHIVE) { ArchiveScreen() }
            composable(ROUTE_STATS) { StatsScreen() }
        }
    }
}
