package ru.rynok.app.ui.stats

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import ru.rynok.app.RynokApp
import java.util.concurrent.TimeUnit

data class PeriodStats(val plannedTotal: Double, val actualTotal: Double, val listCount: Int) {
    val difference: Double get() = actualTotal - plannedTotal
}

data class StatsUiState(val week: PeriodStats, val month: PeriodStats) {
    val hasData get() = month.listCount > 0
}

private val EMPTY_PERIOD = PeriodStats(0.0, 0.0, 0)

class StatsViewModel(application: Application) : AndroidViewModel(application) {

    private val repo get() = getApplication<RynokApp>().shoppingRepository

    val uiState: StateFlow<StatsUiState> = repo.observeArchive()
        .map { lists ->
            val now = System.currentTimeMillis()
            val weekStart = now - TimeUnit.DAYS.toMillis(7)
            val monthStart = now - TimeUnit.DAYS.toMillis(30)

            suspend fun aggregate(since: Long): PeriodStats {
                val inRange = lists.filter { (it.completedAt ?: 0L) >= since }
                val actual = inRange.sumOf { repo.actualTotalForList(it.id) }
                val planned = inRange.sumOf { it.plannedTotal }
                return PeriodStats(planned, actual, inRange.size)
            }

            StatsUiState(week = aggregate(weekStart), month = aggregate(monthStart))
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), StatsUiState(EMPTY_PERIOD, EMPTY_PERIOD))
}
