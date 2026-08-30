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
import com.robutpit.roachrace.model.colorById
import com.robutpit.roachrace.ui.theme.*

private fun Offset.toNorm(size: Size) = Offset(x / size.width, y / size.height)

@Composable
fun TrainGymScreen(
    save: SaveState,
    engine: TrainGymEngine,
    onResetRoach: () -> Unit,
    onNext: () -> Unit,
) {
    val roachColor = Color(colorById(save.colorId).colorLong)
    val mode = engine.mode.value

    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("Зал для тренировок", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text(
                "Тапни по полу — поставишь препятствие (тапни по нему ещё раз — уберёшь). Потяни пальцем рядом с тараканом — подтолкнёшь его.",
                fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(top = 4.dp, bottom = 10.dp),
            )

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

                    val roachSize = 15f
                    drawRoach(Offset(engine.pos.x * w, engine.pos.y * h), roachSize, roachColor, engine.legPhase, engine.wobble.floatValue)
                }

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

            StatBar("Сытость", "${save.satiety}%", save.satiety / 100f, Amber)
            StatBar("Скорость", "${save.levels.speed}/10", save.levels.speed / 10f, Amber)
            StatBar("Выносливость", "${save.levels.stamina}/10", save.levels.stamina / 10f, Green)
            StatBar("Стрессоустойчивость", "${save.levels.stress}/10", save.levels.stress / 10f, Color(0xFF8FB3C9))

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(top = 8.dp)) {
                PrimaryButton(
                    if (mode == GymMode.EATING) "Ест…" else "🍞 Кормить",
                    enabled = mode == GymMode.WANDER,
                    onClick = { engine.startFeeding() },
                )
                PrimaryButton(
                    if (mode == GymMode.TRAINING) "Тренируется…" else "💪 Тренировать",
                    enabled = mode == GymMode.WANDER && save.satiety >= 20,
                    onClick = { engine.startTraining() },
                )
            }
            SecondaryButton("Сменить таракана", modifier = Modifier.padding(top = 8.dp), onClick = onResetRoach)
        }
        PrimaryButton("Дальше → выбор трассы", modifier = Modifier.fillMaxWidth(), enabled = mode == GymMode.WANDER, onClick = onNext)
    }
}
