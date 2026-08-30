package com.robutpit.roachrace.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.robutpit.roachrace.data.BreedStat
import com.robutpit.roachrace.ui.theme.*

@Composable
fun BreedStatsScreen(stats: List<BreedStat>, onBack: () -> Unit) {
    val ranked = stats.sortedWith(compareByDescending<BreedStat> { it.winRatePercent }.thenByDescending { it.wins })
    val totalRaces = stats.sumOf { it.races }
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("📊 Статистика побед по видам", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text(
                if (totalRaces == 0) "Пока ни одной гонки на этом телефоне — статистика появится после первого заезда."
                else "Считается по всем заездам (соло и по Bluetooth), сыгранным на этом телефоне.",
                fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
            )
            ranked.forEachIndexed { i, s ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 8.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(if (i == 0 && s.races > 0) BgCardHi else BgFaint)
                        .border(1.dp, if (i == 0 && s.races > 0) Amber else LineColor, RoundedCornerShape(12.dp))
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(s.breed.displayName, fontSize = 13.sp, color = TextMain, fontWeight = FontWeight.SemiBold)
                        Text("${s.wins} побед из ${s.races} заездов", fontSize = 10.sp, color = TextDim)
                    }
                    Text(
                        if (s.races == 0) "—" else "${s.winRatePercent}%",
                        fontSize = 16.sp, color = Amber, fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }
        SecondaryButton("← назад", onClick = onBack)
    }
}
