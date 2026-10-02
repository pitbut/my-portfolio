package ru.konstruktor.eskiz.ui

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.activity.result.contract.ActivityResultContract
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ru.konstruktor.eskiz.export.Extrusion
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.render.fmtMm
import kotlin.math.min

/** «Сохранить как…»: имя файла и тип передаются при запуске. */
class CreateDocument : ActivityResultContract<Pair<String, String>, Uri?>() {
    override fun createIntent(context: Context, input: Pair<String, String>) =
        Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
            .setType(input.second).putExtra(Intent.EXTRA_TITLE, input.first)

    override fun parseResult(resultCode: Int, intent: Intent?): Uri? =
        if (resultCode == Activity.RESULT_OK) intent?.data else null
}

/**
 * Окно экспорта: формат, а затем «Сохранить в файл» или «Отправить».
 * Для STEP — толщина детали и предпросмотр 3D.
 */
@Composable
fun ExportDialog(vm: EditorViewModel, onDismiss: () -> Unit, onExport: (ExportKind, save: Boolean) -> Unit) {
    var kind by remember { mutableStateOf(ExportKind.DRAWING_PNG) }
    var thickText by remember { mutableStateOf(vm.project.thickness?.let(::fmtMm) ?: "") }
    val thickness = thickText.replace(',', '.').toDoubleOrNull()?.takeIf { it > 0 }
    val (profile, profileError) = remember(vm.project, vm.calibration) { vm.profileOrError() }
    val needs3d = kind == ExportKind.STEP
    val ready = !needs3d || (profile != null && thickness != null)

    fun go(save: Boolean) {
        if (needs3d || kind == ExportKind.ALL) thickness?.let { if (it != vm.project.thickness) vm.setThickness(it) }
        onExport(kind, save)
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Экспорт") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                for (k in ExportKind.entries) {
                    Row(
                        Modifier.fillMaxWidth().clickable { kind = k }.padding(vertical = 2.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RadioButton(selected = kind == k, onClick = { kind = k })
                        Text(k.title, fontSize = 14.sp)
                    }
                }
                if (needs3d || kind == ExportKind.ALL) {
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = thickText,
                        onValueChange = { thickText = it.filter { c -> c.isDigit() || c == '.' || c == ',' } },
                        label = { Text("Толщина детали, мм") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    )
                    if (profileError != null) {
                        Text("3D не получится: $profileError", color = MaterialTheme.colorScheme.error, fontSize = 13.sp)
                    } else if (profile != null && thickness != null) {
                        Spacer(Modifier.height(8.dp))
                        Canvas(
                            Modifier.fillMaxWidth().height(170.dp)
                                .background(Color(0xFFECEFF1), RoundedCornerShape(8.dp)),
                        ) { drawIso(profile, thickness) }
                        Text(
                            "Контур выдавлен на ${fmtMm(thickness)} мм: вырезов и отверстий ${profile.inner.size}. " +
                                "STEP открывается в КОМПАС, SolidWorks, FreeCAD, Fusion.",
                            fontSize = 12.sp,
                        )
                    }
                }
            }
        },
        confirmButton = {
            Row {
                TextButton(enabled = ready, onClick = { go(save = true) }) { Text("Сохранить в файл") }
                TextButton(enabled = ready, onClick = { go(save = false) }) { Text("Отправить") }
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } },
    )
}

/** Изометрия тела выдавливания: нижний и верхний контуры и вертикальные рёбра. */
private fun DrawScope.drawIso(profile: Extrusion.Profile, t: Double) {
    val c30 = 0.8660254; val s30 = 0.5
    fun iso(p: P, z: Double) = P((p.x - p.y) * c30, -((p.x + p.y) * s30 + z))
    val loops = listOf(profile.outer) + profile.inner
    val all = loops.flatMap { l -> l.polygon.flatMap { listOf(iso(it, 0.0), iso(it, t)) } }
    val minX = all.minOf { it.x }; val maxX = all.maxOf { it.x }
    val minY = all.minOf { it.y }; val maxY = all.maxOf { it.y }
    val k = min(size.width / (maxX - minX).coerceAtLeast(1e-6), size.height / (maxY - minY).coerceAtLeast(1e-6)) * 0.88
    val ox = (size.width - (maxX - minX) * k) / 2; val oy = (size.height - (maxY - minY) * k) / 2
    fun o(q: P) = Offset((ox + (q.x - minX) * k).toFloat(), (oy + (q.y - minY) * k).toFloat())
    val back = Color(0xFF90A4AE); val front = Color(0xFF1565C0)
    for (l in loops) {
        val poly = l.edges.flatMap { it.sample(16).dropLast(1) }
        for (i in poly.indices) {
            val a = poly[i]; val b = poly[(i + 1) % poly.size]
            drawLine(back, o(iso(a, 0.0)), o(iso(b, 0.0)), strokeWidth = 2f)
        }
        // Вертикальные рёбра — в вершинах контура.
        for (e in l.edges) drawLine(front, o(iso(e.p, 0.0)), o(iso(e.p, t)), strokeWidth = 2f)
        for (i in poly.indices) {
            val a = poly[i]; val b = poly[(i + 1) % poly.size]
            drawLine(front, o(iso(a, t)), o(iso(b, t)), strokeWidth = 3f)
        }
    }
}
