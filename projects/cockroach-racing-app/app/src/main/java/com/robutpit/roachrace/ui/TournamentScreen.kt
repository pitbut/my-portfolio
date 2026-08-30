package com.robutpit.roachrace.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.robutpit.roachrace.model.TournamentEntry
import com.robutpit.roachrace.ui.theme.*

@Composable
fun TournamentScreen(entries: List<TournamentEntry>, onNextHeat: () -> Unit, onFinish: () -> Unit) {
    val ranked = entries.sortedByDescending { it.points }
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("🏆 Турнирная таблица", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text(
                "Очки за место в заезде (1-е — 10, 2-е — 8, 3-е — 6…), суммируются по всем заездам. " +
                    "Полная таблица хранится на телефоне хоста.",
                fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
            )
            if (ranked.isEmpty()) {
                Text("Пока нет результатов — проведи первый заезд.", fontSize = 12.sp, color = TextDim)
            } else {
                ranked.forEachIndexed { i, e ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 8.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(if (i == 0) BgCardHi else BgFaint)
                            .border(1.dp, if (i == 0) Amber else LineColor, RoundedCornerShape(12.dp))
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            modifier = Modifier.size(26.dp).clip(CircleShape).background(BgCard).border(1.dp, LineColor, CircleShape),
                            contentAlignment = Alignment.Center,
                        ) { Text("${i + 1}", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextMain) }
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text(e.name, fontSize = 13.sp, color = TextMain, fontWeight = FontWeight.SemiBold)
                            Text("${e.heats} заездов · лучшее место — ${e.bestPlace}", fontSize = 10.sp, color = TextDim)
                        }
                        Text("${e.points} очк", fontSize = 13.sp, color = Amber, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            PrimaryButton("Следующий заезд →", onClick = onNextHeat)
            SecondaryButton("Завершить турнир", onClick = onFinish)
        }
    }
}
