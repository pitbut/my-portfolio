package com.robutpit.roachrace.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.robutpit.roachrace.engine.RaceEngine
import com.robutpit.roachrace.ui.theme.*

/** Full-bleed race screen: the track runs the long (vertical) way, using
 * nearly the whole screen height, with lanes side by side as columns —
 * requested instead of the old small horizontal strip. */
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
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SecondaryButton("←", onClick = onBackToTrack)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text("${engine.track.emoji} ${engine.track.displayName}", fontWeight = FontWeight.SemiBold, fontSize = 15.sp, color = TextMain)
                multiplayerHint?.let { Text(it, fontSize = 10.sp, color = Amber) }
            }
            PrimaryButton(if (engine.running.value) "Идёт…" else "🏁 Старт", enabled = !engine.running.value && !engine.done.value, onClick = onStart)
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .padding(horizontal = 10.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(Color(engine.track.themeColor))
                .border(1.dp, LineColor, RoundedCornerShape(18.dp)),
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val w = size.width
                val h = size.height
                val laneW = w / engine.racers.size
                val padTop = 46f
                val padBottom = 40f
                val travel = h - padTop - padBottom

                engine.racers.forEachIndexed { i, _ ->
                    val x0 = i * laneW
                    drawRect(
                        color = if (i % 2 == 0) Color.White.copy(alpha = 0.02f) else Color.White.copy(alpha = 0.045f),
                        topLeft = Offset(x0, 0f), size = Size(laneW, h),
                    )
                }

                engine.track.obstacles.forEach { o ->
                    val y = (h - padBottom) - o.pos * travel
                    drawRect(Red.copy(alpha = 0.5f), topLeft = Offset(0f, y - 3f), size = Size(w, 6f))
                }

                val finishY = padTop
                drawRect(Amber.copy(alpha = 0.6f), topLeft = Offset(0f, finishY - 2f), size = Size(w, 4f))

                engine.racers.forEachIndexed { i, r ->
                    val x = i * laneW + laneW / 2 + r.wobbleCur.value * (laneW * 0.28f)
                    val y = (h - padBottom) - (r.progress.floatValue / engine.track.distance) * travel
                    val roachSize = r.sizeDp * 2.1f
                    if (r.spookTimer.value > 0f) {
                        drawCircle(Red.copy(alpha = 0.35f), radius = roachSize * 1.9f, center = Offset(x, y))
                    }
                    drawRoach(Offset(x, y), roachSize, Color(r.colorLong), r.legPhase, r.wobbleCur.value, headingDegrees = 90f)
                    if (r.isPlayer) {
                        drawCircle(Amber, radius = roachSize * 2f, center = Offset(x, y), style = androidx.compose.ui.graphics.drawscope.Stroke(3f))
                    }
                }
            }

            Text(
                "🏁 финиш", fontSize = 10.sp, color = Amber,
                modifier = Modifier.align(Alignment.TopCenter).padding(top = 6.dp),
            )
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 210.dp)
                .verticalScroll(rememberScrollState())
                .padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            CardBox {
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    engine.racers.forEach { r ->
                        Text(
                            (if (r.isPlayer) "★ " else "") + r.name,
                            fontSize = 10.sp,
                            color = if (r.spookTimer.value > 0f) Red else TextDim,
                        )
                    }
                }
            }
            CardBox {
                SensorRow("🎤 Крик/хлопок пугает соперника", micLevel, micStatus, active = micActive, onToggle = onToggleMic)
                Spacer(Modifier.height(10.dp))
                SensorRow("📳 Стук по столу пугает соперника", motionLevel, motionStatus, active = motionActive, onToggle = onToggleMotion)
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 8.dp)) {
                    Checkbox(checked = hardcore, onCheckedChange = onHardcoreChange, colors = CheckboxDefaults.colors(checkedColor = Amber))
                    Text("Шум может напугать и моего таракана (хардкор)", fontSize = 11.sp, color = TextDim)
                }
            }
            if (engine.log.isNotEmpty()) {
                CardBox {
                    LazyColumn(modifier = Modifier.heightIn(max = 120.dp)) {
                        items(engine.log.asReversed()) { line ->
                            Text(line, fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(vertical = 2.dp))
                        }
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
        verticalAlignment = Alignment.CenterVertically,
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
