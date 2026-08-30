package com.robutpit.roachrace.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.robutpit.roachrace.data.SaveState
import com.robutpit.roachrace.engine.GymMode
import com.robutpit.roachrace.engine.TrainGymEngine
import com.robutpit.roachrace.model.RoachEconomy
import com.robutpit.roachrace.model.colorById
import com.robutpit.roachrace.ui.theme.*

private fun Offset.toNorm(size: Size) = Offset(x / size.width, y / size.height)

private fun formatCooldown(ms: Long): String {
    if (ms <= 0) return ""
    val totalMinutes = (ms / 60_000).toInt().coerceAtLeast(1)
    val h = totalMinutes / 60
    val m = totalMinutes % 60
    return if (h > 0) "через ${h} ч ${m} мин" else "через $m мин"
}

@Composable
fun TrainGymScreen(
    save: SaveState,
    engine: TrainGymEngine,
    now: Long,
    onResetRoach: () -> Unit,
    onNext: () -> Unit,
) {
    val roachColor = Color(colorById(save.colorId).colorLong)
    val mode = engine.mode.value
    val trait = save.trait()
    val satiety = RoachEconomy.currentSatiety(save, now, trait)
    val feedCooldown = RoachEconomy.feedCooldownRemainingMs(save, now)
    val canTrain = RoachEconomy.canTrain(save, now, trait)
    val trainCooldown = RoachEconomy.trainCooldownRemainingMs(save, now)

    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("Зал для тренировок", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text(
                "Тапни по полу — поставишь препятствие (тапни по нему ещё раз — уберёшь). Потяни пальцем рядом с тараканом — подтолкнёшь его. " +
                    "Не тыкай прямо в него — может раздавить.",
                fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(top = 4.dp, bottom = 6.dp),
            )
            trait?.let {
                Text("Характер: ${it.displayName} — ${it.description}", fontSize = 11.sp, color = Amber, modifier = Modifier.padding(bottom = 10.dp))
            }

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(280.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(Color(0xFF20241C))
                    .border(1.dp, LineColor, RoundedCornerShape(16.dp))
                    .pointerInput(engine) {
                        detectTapGestures { offset ->
                            engine.handleTap(offset.toNorm(size = Size(size.width.toFloat(), size.height.toFloat())))
                        }
                    }
                    .pointerInput(engine) {
                        detectDragGestures(
                            onDrag = { change, dragAmount ->
                                val norm = change.position.toNorm(Size(size.width.toFloat(), size.height.toFloat()))
                                if (engine.isNearRoach(norm)) {
                                    change.consume()
                                    engine.handlePush(Offset(dragAmount.x / size.width, dragAmount.y / size.height))
                                }
                            },
                        )
                    },
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val w = size.width
                    val h = size.height

                    engine.obstacles.forEach { o ->
                        drawCircle(Red.copy(alpha = 0.75f), radius = 9f, center = Offset(o.x * w, o.y * h))
                        drawCircle(Color(0xFF1A140D), radius = 9f, center = Offset(o.x * w, o.y * h), style = androidx.compose.ui.graphics.drawscope.Stroke(2f))
                    }

                    engine.foodPos?.let { f ->
                        drawCircle(Color(0xFFD9A46B), radius = 8f, center = Offset(f.x * w, f.y * h))
                        drawCircle(Color(0xFF7A5230), radius = 8f, center = Offset(f.x * w, f.y * h), style = androidx.compose.ui.graphics.drawscope.Stroke(1.5f))
                    }

                    if (!engine.squished.value) {
                        // Same visual scale as the race track, not a smaller
                        // generic placeholder — this is the actual roach.
                        val roachSize = save.breed?.sizeDp?.times(1.35f) ?: 24f
                        drawRoach(Offset(engine.pos.x * w, engine.pos.y * h), roachSize, roachColor, engine.legPhase, engine.wobble.floatValue)
                    } else {
                        drawCircle(roachColor.copy(alpha = 0.6f), radius = 26f, center = Offset(engine.pos.x * w, engine.pos.y * h))
                    }
                }

                if (engine.squished.value) {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text("💥 Раздавлен", fontSize = 15.sp, color = Red, fontWeight = FontWeight.SemiBold)
                        Text("Не рассчитал силу тапа", fontSize = 11.sp, color = TextDim)
                    }
                } else {
                    val statusText = when (mode) {
                        GymMode.WANDER -> null
                        GymMode.EATING -> if (engine.eatingArrived.value) "Ест… 🍞" else "Идёт к еде…"
                        GymMode.TRAINING -> "Тренируется… 💪"
                    }
                    statusText?.let {
                        Text(
                            it, fontSize = 12.sp, color = Amber,
                            modifier = Modifier.align(Alignment.TopCenter).padding(top = 8.dp),
                        )
                    }
                    if (mode != GymMode.WANDER) {
                        LinearProgressIndicator(
                            progress = { (1f - engine.sessionTimer.floatValue / engine.sessionDuration).coerceIn(0f, 1f) },
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .fillMaxWidth()
                                .padding(10.dp)
                                .height(6.dp)
                                .clip(RoundedCornerShape(4.dp)),
                            color = Amber, trackColor = BgFaint,
                        )
                    }
                }
            }

            StatBar("Сытость", "$satiety%", satiety / 100f, Amber)
            StatBar("Скорость", "${save.levels.speed}/${RoachEconomy.MAX_LEVEL}", save.levels.speed / RoachEconomy.MAX_LEVEL.toFloat(), Amber)
            StatBar("Выносливость", "${save.levels.stamina}/${RoachEconomy.MAX_LEVEL}", save.levels.stamina / RoachEconomy.MAX_LEVEL.toFloat(), Green)
            StatBar("Стрессоустойчивость", "${save.levels.stress}/${RoachEconomy.MAX_LEVEL}", save.levels.stress / RoachEconomy.MAX_LEVEL.toFloat(), Color(0xFF8FB3C9))
            Text(
                "Рост — дело не одного дня: кормить и тренировать можно с перерывами в часы, максимум набирается примерно за неделю активной игры и дальше растёт медленнее.",
                fontSize = 10.sp, color = TextDim, modifier = Modifier.padding(bottom = 4.dp),
            )

            if (engine.squished.value) {
                PrimaryButton("Завести нового таракана", modifier = Modifier.fillMaxWidth().padding(top = 8.dp), onClick = onResetRoach)
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(top = 8.dp)) {
                    PrimaryButton(
                        when {
                            mode == GymMode.EATING -> "Ест…"
                            feedCooldown > 0 -> "🍞 ${formatCooldown(feedCooldown)}"
                            else -> "🍞 Кормить"
                        },
                        enabled = mode == GymMode.WANDER && feedCooldown <= 0,
                        onClick = { engine.startFeeding() },
                    )
                    PrimaryButton(
                        when {
                            mode == GymMode.TRAINING -> "Тренируется…"
                            trainCooldown > 0 -> "💪 ${formatCooldown(trainCooldown)}"
                            !canTrain -> "💪 Мало сытости"
                            else -> "💪 Тренировать"
                        },
                        enabled = mode == GymMode.WANDER && canTrain,
                        onClick = { engine.startTraining() },
                    )
                }
                SecondaryButton("Сменить таракана", modifier = Modifier.padding(top = 8.dp), onClick = onResetRoach)
            }
        }
        PrimaryButton("Дальше → выбор трассы", modifier = Modifier.fillMaxWidth(), enabled = mode == GymMode.WANDER && !engine.squished.value, onClick = onNext)
    }
}
