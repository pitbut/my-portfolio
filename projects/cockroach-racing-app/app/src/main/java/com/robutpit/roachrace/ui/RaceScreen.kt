package com.robutpit.roachrace.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.robutpit.roachrace.engine.RaceEngine
import com.robutpit.roachrace.ui.theme.*

@Composable
fun RaceScreen(
    engine: RaceEngine,
    onStart: () -> Unit,
    onBackToTrack: () -> Unit,
    micActive: Boolean,
    micLevel: Float,
    micStatus: String,
    onToggleMic: () -> Unit,
    motionActive: Boolean,
    motionLevel: Float,
    motionStatus: String,
    onToggleMotion: () -> Unit,
    hardcore: Boolean,
    onHardcoreChange: (Boolean) -> Unit,
    multiplayerHint: String? = null,
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        CardBox {
            multiplayerHint?.let {
                Text(it, fontSize = 11.sp, color = Amber, modifier = Modifier.padding(bottom = 8.dp))
            }
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(280.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(Color(0xFF20241C))
                    .border(1.dp, LineColor, RoundedCornerShape(14.dp)),
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val w = size.width
                    val h = size.height
                    val laneH = h / engine.racers.size
                    val pad = 30f

                    engine.racers.forEachIndexed { i, _ ->
                        val y0 = i * laneH
                        drawRect(
                            color = if (i % 2 == 0) Color.White.copy(alpha = 0.02f) else Color.White.copy(alpha = 0.045f),
                            topLeft = Offset(0f, y0), size = androidx.compose.ui.geometry.Size(w, laneH),
                        )
                    }

                    engine.track.obstacles.forEach { o ->
                        val x = pad + o.pos * (w - pad * 2)
                        drawRect(Red.copy(alpha = 0.55f), topLeft = Offset(x - 3f, 0f), size = androidx.compose.ui.geometry.Size(6f, h))
                    }

                    engine.racers.forEachIndexed { i, r ->
                        val y = i * laneH + laneH / 2
                        val x = pad + (r.progress.floatValue / engine.track.distance) * (w - pad * 2)
                        val center = Offset(x, y + r.wobbleCur.value * 10f)
                        drawRoach(center, r.sizeDp * 1.6f, Color(r.colorLong), r.legPhase, r.wobbleCur.value)
                    }
                }
                engine.racers.forEachIndexed { i, r ->
                    val laneHDp = 280.dp / engine.racers.size
                    Text(
                        (if (r.isPlayer) "★ " else "") + r.name + (if (r.spookTimer.value > 0f) " 😱" else ""),
                        fontSize = 10.sp,
                        color = if (r.spookTimer.value > 0f) Red else TextMain,
                        modifier = Modifier
                            .padding(start = 6.dp, top = laneHDp * i + 4.dp),
                    )
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(top = 10.dp)) {
                PrimaryButton(if (engine.running.value) "Гонка идёт…" else "🏁 Старт", enabled = !engine.running.value && !engine.done.value, onClick = onStart)
                SecondaryButton("← сменить трассу", onClick = onBackToTrack)
            }
        }

        CardBox {
            SensorRow("🎤 Крик/хлопок пугает соперника", micLevel, micStatus, active = micActive, onToggle = onToggleMic)
            Spacer(Modifier.height(10.dp))
            SensorRow("📳 Стук по столу пугает соперника", motionLevel, motionStatus, active = motionActive, onToggle = onToggleMotion)
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically, modifier = Modifier.padding(top = 8.dp)) {
                Checkbox(checked = hardcore, onCheckedChange = onHardcoreChange, colors = CheckboxDefaults.colors(checkedColor = Amber))
                Text("Шум может напугать и моего таракана (хардкор)", fontSize = 11.sp, color = TextDim)
            }
        }

        if (engine.log.isNotEmpty()) {
            CardBox {
                LazyColumn(modifier = Modifier.heightIn(max = 140.dp)) {
                    items(engine.log.asReversed()) { line ->
                        Text(line, fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(vertical = 2.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun SensorRow(label: String, level: Float, status: String, active: Boolean, onToggle: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(BgFaint)
            .border(1.dp, LineColor, RoundedCornerShape(12.dp))
            .padding(10.dp),
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
    ) {
        Text(label, fontSize = 12.sp, color = TextMain, modifier = Modifier.width(150.dp))
        Box(
            modifier = Modifier
                .weight(1f)
                .height(8.dp)
                .padding(horizontal = 8.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(BgDeep)
                .border(1.dp, LineColor, RoundedCornerShape(6.dp)),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(level.coerceIn(0f, 1f))
                    .clip(RoundedCornerShape(6.dp))
                    .background(if (level > 0.5f) Red else Green),
            )
        }
        Text(status, fontSize = 10.sp, color = TextDim, modifier = Modifier.width(64.dp))
        SecondaryButton(if (active) "Выключить" else "Включить", onClick = onToggle)
    }
}
