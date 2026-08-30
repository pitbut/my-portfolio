package com.robutpit.roachrace.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.robutpit.roachrace.data.SaveState
import com.robutpit.roachrace.model.*
import com.robutpit.roachrace.ui.theme.*

enum class Screen { SELECT, TRAIN, TRACK, MULTIPLAYER, RACE, RESULTS }

@Composable
fun StepNav(current: Screen, canGoTrain: Boolean, canGoTrack: Boolean, canGoRace: Boolean, canGoResults: Boolean, onNav: (Screen) -> Unit) {
    val steps = listOf(
        Screen.SELECT to "1. Таракан",
        Screen.TRAIN to "2. Тренировка",
        Screen.TRACK to "3. Трасса",
        Screen.RACE to "4. Гонка",
        Screen.RESULTS to "5. Результат",
    )
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        steps.forEach { (screen, label) ->
            val enabled = when (screen) {
                Screen.SELECT -> true
                Screen.TRAIN -> canGoTrain
                Screen.TRACK -> canGoTrack
                Screen.RACE -> canGoRace
                Screen.RESULTS -> canGoResults
                else -> true
            }
            val active = current == screen
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .background(if (active) Amber else BgCard)
                    .border(1.dp, if (active) Color.Transparent else LineColor, RoundedCornerShape(20.dp))
                    .clickable(enabled = enabled) { onNav(screen) }
                    .padding(horizontal = 10.dp, vertical = 6.dp),
            ) {
                Text(label, fontSize = 11.sp, color = if (active) Color(0xFF241A0C) else if (enabled) TextDim else TextDim.copy(alpha = 0.35f))
            }
        }
    }
}

@Composable
fun RoachBadge(save: SaveState) {
    val breed = save.breed ?: return
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(BgCard)
            .border(1.dp, LineColor, RoundedCornerShape(14.dp))
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RoachPreview(44, Color(colorById(save.colorId).colorLong))
        Spacer(Modifier.width(10.dp))
        Column {
            Text(breed.displayName, fontWeight = FontWeight.SemiBold, color = TextMain)
            Text(
                "Скорость ${save.levels.speed} · Выносливость ${save.levels.stamina} · Стресс ${save.levels.stress} · Сытость ${save.satiety}%",
                fontSize = 11.sp, color = TextDim,
            )
        }
    }
}

@Composable
fun CardBox(content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(BgCard)
            .border(1.dp, LineColor, RoundedCornerShape(16.dp))
            .padding(16.dp),
        content = content,
    )
}

@Composable
fun PrimaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = Color(0xFF241A0C), disabledContainerColor = Amber.copy(alpha = 0.35f)),
        shape = RoundedCornerShape(12.dp),
    ) { Text(text, fontWeight = FontWeight.SemiBold) }
}

@Composable
fun SecondaryButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.outlinedButtonColors(contentColor = TextMain),
        border = androidx.compose.foundation.BorderStroke(1.dp, LineColor),
        shape = RoundedCornerShape(12.dp),
    ) { Text(text) }
}

@Composable
fun SelectScreen(save: SaveState, onBreed: (Breed) -> Unit, onColor: (String) -> Unit, onConfirm: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("Выбери породу", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text("Порода задаёт базовые характеристики, тренировка меняет их дальше.", fontSize = 12.sp, color = TextDim, modifier = Modifier.padding(bottom = 10.dp))
            val columns = Breed.entries.chunked(2)
            columns.forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(bottom = 10.dp)) {
                    row.forEach { breed ->
                        val selected = save.breed == breed
                        Column(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(14.dp))
                                .background(if (selected) BgCardHi else BgFaint)
                                .border(2.dp, if (selected) Amber else LineColor, RoundedCornerShape(14.dp))
                                .clickable { onBreed(breed) }
                                .padding(10.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                        ) {
                            RoachPreview(40, Color(colorById(save.colorId).colorLong))
                            Text(breed.displayName, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = TextMain, modifier = Modifier.padding(top = 4.dp))
                            Text(breed.description, fontSize = 10.sp, color = TextDim, modifier = Modifier.padding(top = 2.dp))
                            Text(
                                "Скор ${"%.2f".format(breed.baseSpeed)} · Вын ${"%.2f".format(breed.baseStamina)} · Стресс ${"%.2f".format(breed.baseStress)}",
                                fontSize = 9.sp, color = Amber, modifier = Modifier.padding(top = 3.dp),
                            )
                        }
                    }
                    if (row.size == 1) Spacer(Modifier.weight(1f))
                }
            }
        }

        CardBox {
            Text("Окрас (косметика)", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text("Не влияет на характеристики — только на вид.", fontSize = 12.sp, color = TextDim, modifier = Modifier.padding(bottom = 10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ROACH_COLORS.forEach { c ->
                    val selected = save.colorId == c.id
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .clip(CircleShape)
                            .background(Color(c.colorLong))
                            .border(3.dp, if (selected) Amber else Color.Transparent, CircleShape)
                            .clickable { onColor(c.id) },
                    )
                }
            }
        }

        PrimaryButton("Дальше → тренировка", modifier = Modifier.fillMaxWidth(), enabled = save.breed != null, onClick = onConfirm)
    }
}

@Composable
fun StatBar(label: String, displayValue: String, progress: Float, color: Color) {
    Column(modifier = Modifier.padding(bottom = 10.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, fontSize = 12.sp, color = TextDim)
            Text(displayValue, fontSize = 12.sp, color = TextDim)
        }
        LinearProgressIndicator(
            progress = { progress.coerceIn(0f, 1f) },
            modifier = Modifier
                .fillMaxWidth()
                .height(9.dp)
                .clip(RoundedCornerShape(6.dp)),
            color = color,
            trackColor = BgFaint,
        )
    }
}

@Composable
fun TrackScreen(selectedTrackId: String?, onPick: (String) -> Unit, onSolo: () -> Unit, onMultiplayer: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("Выбери трассу", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text("Каждая трасса по-своему проверяет характеристики.", fontSize = 12.sp, color = TextDim, modifier = Modifier.padding(bottom = 10.dp))
            TRACKS.forEach { t ->
                val selected = selectedTrackId == t.id
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .background(if (selected) BgCardHi else BgFaint)
                        .border(2.dp, if (selected) Amber else LineColor, RoundedCornerShape(14.dp))
                        .clickable { onPick(t.id) }
                        .padding(12.dp)
                        .padding(bottom = if (t != TRACKS.last()) 0.dp else 0.dp),
                ) {
                    Text(t.displayName, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, color = TextMain)
                    Text(t.description, fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(top = 2.dp))
                    Text("Дистанция ${t.distance.toInt()} · важно: ${t.tags.joinToString(", ")}", fontSize = 10.sp, color = Amber, modifier = Modifier.padding(top = 4.dp))
                }
                Spacer(Modifier.height(10.dp))
            }
        }
        PrimaryButton("Гонка соло (3 бота) →", modifier = Modifier.fillMaxWidth(), enabled = selectedTrackId != null, onClick = onSolo)
        SecondaryButton("🔵 Гонка по Bluetooth вдвоём →", modifier = Modifier.fillMaxWidth(), onClick = onMultiplayer)
    }
}

@Composable
fun ResultsScreen(rows: List<Triple<Int, String, String>>, playerPlace: Int, total: Int, onAnotherTrack: () -> Unit, onTrainMore: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("Результаты", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain, modifier = Modifier.padding(bottom = 10.dp))
            LazyColumn(modifier = Modifier.heightIn(max = 400.dp)) {
                items(rows) { (place, name, time) ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 8.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(BgFaint)
                            .border(1.dp, if (place == playerPlace) Amber else LineColor, RoundedCornerShape(12.dp))
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            modifier = Modifier.size(26.dp).clip(CircleShape).background(BgCard).border(1.dp, LineColor, CircleShape),
                            contentAlignment = Alignment.Center,
                        ) { Text("$place", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextMain) }
                        Spacer(Modifier.width(10.dp))
                        Text(name, fontSize = 13.sp, color = TextMain, modifier = Modifier.weight(1f))
                        Text(time, fontSize = 11.sp, color = TextDim)
                    }
                }
            }
        }
        CardBox {
            val medal = if (playerPlace == 1) " Победа! 🏆" else ""
            Text("Твой таракан финишировал на $playerPlace месте из $total.$medal", fontSize = 13.sp, color = TextDim, modifier = Modifier.padding(bottom = 10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                PrimaryButton("Другая трасса", onClick = onAnotherTrack)
                SecondaryButton("Ещё потренировать", onClick = onTrainMore)
            }
        }
    }
}
