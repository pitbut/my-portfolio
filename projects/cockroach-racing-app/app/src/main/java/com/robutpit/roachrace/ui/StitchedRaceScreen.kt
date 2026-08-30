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

/** "Combined field" race screen: phones are placed in a row and each shows
 * only its own slice of the track — [mySegmentIndex] of [totalSegments] —
 * so a roach visually runs off the right edge of one phone and appears at
 * the left edge of the next. Reuses the same [RaceEngine] and Bluetooth
 * state-sync as the shared-field [RaceScreen]; only the drawing differs. */
@Composable
fun StitchedRaceScreen(
    engine: RaceEngine,
    mySegmentIndex: Int,
    totalSegments: Int,
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
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SecondaryButton("←", onClick = onBackToTrack)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text("${engine.track.emoji} ${engine.track.displayName} — экран ${mySegmentIndex + 1} из $totalSegments", fontWeight = FontWeight.SemiBold, fontSize = 13.sp, color = TextMain)
                Text("Сложенное поле — телефоны стоят в ряд слева направо", fontSize = 10.sp, color = Amber)
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
                val segLen = engine.track.distance / totalSegments
                val segStart = mySegmentIndex * segLen
                val segEnd = segStart + segLen
                val margin = segLen * 0.18f
                val viewStart = segStart - margin
                val viewEnd = segEnd + margin
                val viewSpan = viewEnd - viewStart

                fun xOf(progress: Float) = ((progress - viewStart) / viewSpan) * w

                if (mySegmentIndex == 0) {
                    val startX = xOf(0f)
                    drawRect(Amber.copy(alpha = 0.5f), topLeft = Offset(startX - 2f, 0f), size = Size(4f, h))
                }
                if (mySegmentIndex == totalSegments - 1) {
                    val finishX = xOf(engine.track.distance)
                    drawRect(Amber.copy(alpha = 0.7f), topLeft = Offset(finishX - 2f, 0f), size = Size(4f, h))
                }

                engine.track.obstacles.forEach { o ->
                    val opos = o.pos * engine.track.distance
                    if (opos in viewStart..viewEnd) {
                        val x = xOf(opos)
                        drawRect(Red.copy(alpha = 0.45f), topLeft = Offset(x - 3f, 0f), size = Size(6f, h))
                    }
                }

                val laneH = h / engine.racers.size
                engine.racers.forEachIndexed { i, r ->
                    val x = xOf(r.progress.floatValue)
                    if (x < -60f || x > w + 60f) return@forEachIndexed
                    val y = i * laneH + laneH / 2 + r.wobbleCur.value * (laneH * 0.28f)
                    val roachSize = r.sizeDp * 1.7f
                    if (r.spookTimer.value > 0f) {
                        drawCircle(Red.copy(alpha = 0.35f), radius = roachSize * 1.9f, center = Offset(x, y))
                    }
                    drawRoach(Offset(x, y), roachSize, Color(r.colorLong), r.legPhase, r.wobbleCur.value, headingDegrees = 180f)
                    if (r.isPlayer) {
                        drawCircle(Amber, radius = roachSize * 2f, center = Offset(x, y), style = androidx.compose.ui.graphics.drawscope.Stroke(3f))
                    }
                }

                if (mySegmentIndex > 0) drawRect(Color.White.copy(alpha = 0.05f), topLeft = Offset(0f, 0f), size = Size(w * 0.06f, h))
                if (mySegmentIndex < totalSegments - 1) drawRect(Color.White.copy(alpha = 0.05f), topLeft = Offset(w * 0.94f, 0f), size = Size(w * 0.06f, h))
            }
            if (mySegmentIndex > 0) Text("←", fontSize = 20.sp, color = TextDim, modifier = Modifier.align(Alignment.CenterStart).padding(start = 4.dp))
            if (mySegmentIndex < totalSegments - 1) Text("→", fontSize = 20.sp, color = TextDim, modifier = Modifier.align(Alignment.CenterEnd).padding(end = 4.dp))
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
