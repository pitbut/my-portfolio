package ru.rynok.app.ui.stats

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import ru.rynok.app.domain.formatMoney

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StatsScreen() {
    val viewModel: StatsViewModel = viewModel()
    val state by viewModel.uiState.collectAsState()

    Scaffold(topBar = { TopAppBar(title = { Text("Статистика") }) }) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            if (!state.hasData) {
                Text("Пока нет данных для статистики")
            } else {
                PeriodCard(title = "Эта неделя", stats = state.week)
                PeriodCard(title = "Этот месяц", stats = state.month)
                BarsChart(week = state.week, month = state.month)
            }
        }
    }
}

@Composable
private fun PeriodCard(title: String, stats: PeriodStats) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(title, fontWeight = FontWeight.Bold)
            Text("План ${formatMoney(stats.plannedTotal)} / факт ${formatMoney(stats.actualTotal)} · ${stats.listCount} списков")
        }
    }
}

@Composable
private fun BarsChart(week: PeriodStats, month: PeriodStats) {
    val plannedColor = MaterialTheme.colorScheme.secondary
    val actualColor = MaterialTheme.colorScheme.primary
    val maxValue = maxOf(week.plannedTotal, week.actualTotal, month.plannedTotal, month.actualTotal, 1.0)

    Card(modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
        Canvas(modifier = Modifier.fillMaxWidth().height(180.dp).padding(16.dp)) {
            val groupWidth = size.width / 2
            val barWidth = groupWidth / 4

            fun drawBar(groupIndex: Int, barIndex: Int, value: Double, color: Color) {
                val heightRatio = (value / maxValue).toFloat().coerceIn(0f, 1f)
                val barHeight = size.height * heightRatio
                val x = groupIndex * groupWidth + groupWidth / 2 - barWidth + barIndex * barWidth
                drawRect(
                    color = color,
                    topLeft = Offset(x, size.height - barHeight),
                    size = Size(barWidth * 0.8f, barHeight),
                )
            }

            drawBar(0, 0, week.plannedTotal, plannedColor)
            drawBar(0, 1, week.actualTotal, actualColor)
            drawBar(1, 0, month.plannedTotal, plannedColor)
            drawBar(1, 1, month.actualTotal, actualColor)
        }
        Text(
            "Слева — неделя, справа — месяц. Жёлтый — план, зелёный — факт",
            modifier = Modifier.padding(bottom = 12.dp, start = 16.dp, end = 16.dp),
            style = MaterialTheme.typography.bodySmall,
        )
    }
}
