package ru.konstruktor.eskiz.ui

import android.app.Application
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.Adjust
import androidx.compose.material.icons.filled.Architecture
import androidx.compose.material.icons.filled.AutoFixHigh
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Photo
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material.icons.filled.RoundedCorner
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Straighten
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material.icons.filled.TouchApp
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import ru.konstruktor.eskiz.data.Stamp
import ru.konstruktor.eskiz.export.Exporters
import ru.konstruktor.eskiz.geom.CalibMode
import ru.konstruktor.eskiz.geom.dist
import ru.konstruktor.eskiz.render.fmtMm

private fun toolIcon(t: Tool): ImageVector = when (t) {
    Tool.SELECT -> Icons.Filled.TouchApp
    Tool.POINT -> Icons.Filled.Adjust
    Tool.LINE -> Icons.Filled.Timeline
    Tool.ARC -> Icons.Filled.RoundedCorner
    Tool.DIM -> Icons.Filled.Straighten
    Tool.CIRCLE -> Icons.Filled.RadioButtonUnchecked
    Tool.AUTO -> Icons.Filled.AutoFixHigh
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditorScreen(projectId: String, onBack: () -> Unit) {
    val ctx = LocalContext.current
    val app = ctx.applicationContext as Application
    val vm: EditorViewModel = viewModel(key = projectId) { EditorViewModel(app, projectId) }
    val snack = remember { SnackbarHostState() }

    var menu by remember { mutableStateOf(false) }
    var shareMenu by remember { mutableStateOf(false) }
    var renameDlg by remember { mutableStateOf(false) }
    var stampDlg by remember { mutableStateOf(false) }
    var calibDlg by remember { mutableStateOf(false) }
    var clearDlg by remember { mutableStateOf(false) }

    BackHandler {
        when {
            vm.pending.isNotEmpty() || vm.circlePts.isNotEmpty() -> vm.cancelPending()
            vm.selection != null -> vm.selection = null
            else -> { vm.saveNow(); onBack() }
        }
    }

    LaunchedEffect(vm.message) {
        vm.message?.let { snack.showSnackbar(it); vm.message = null }
    }

    fun share(kind: ExportKind) {
        shareMenu = false
        vm.export(kind) { files -> Exporters.share(ctx, files, "Отправить чертёж") }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snack) },
        topBar = {
            TopAppBar(
                title = {
                    Text(vm.project.name, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.clickable { renameDlg = true })
                },
                navigationIcon = {
                    IconButton(onClick = { vm.saveNow(); onBack() }) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Назад") }
                },
                actions = {
                    IconButton(onClick = vm::undo, enabled = vm.canUndo) { Icon(Icons.AutoMirrored.Filled.Undo, "Отменить") }
                    IconButton(onClick = { vm.mode = if (vm.mode == ViewMode.PHOTO) ViewMode.DRAWING else ViewMode.PHOTO }) {
                        Icon(if (vm.mode == ViewMode.PHOTO) Icons.Filled.Architecture else Icons.Filled.Photo,
                            if (vm.mode == ViewMode.PHOTO) "Чертёж" else "Фото")
                    }
                    Box {
                        IconButton(onClick = { shareMenu = true }) { Icon(Icons.Filled.Share, "Поделиться") }
                        DropdownMenu(shareMenu, onDismissRequest = { shareMenu = false }) {
                            DropdownMenuItem(text = { Text("Чертёж — картинка PNG") }, onClick = { share(ExportKind.DRAWING_PNG) })
                            DropdownMenuItem(text = { Text("Фото с размерами") }, onClick = { share(ExportKind.PHOTO) })
                            DropdownMenuItem(text = { Text("Чертёж — PDF") }, onClick = { share(ExportKind.PDF) })
                            DropdownMenuItem(text = { Text("DXF для КОМПАС / AutoCAD") }, onClick = { share(ExportKind.DXF) })
                            HorizontalDivider()
                            DropdownMenuItem(text = { Text("Всё сразу") }, onClick = { share(ExportKind.ALL) })
                        }
                    }
                    Box {
                        IconButton(onClick = { menu = true }) { Icon(Icons.Filled.MoreVert, "Ещё") }
                        DropdownMenu(menu, onDismissRequest = { menu = false }) {
                            DropdownMenuItem(text = { Text("Переименовать") }, onClick = { menu = false; renameDlg = true })
                            DropdownMenuItem(text = { Text("Штамп чертежа") }, onClick = { menu = false; stampDlg = true })
                            DropdownMenuItem(text = { Text("Повернуть чертёж на 90°") }, onClick = { menu = false; vm.rotateDrawing() })
                            HorizontalDivider()
                            CheckItem("Пошаговый показ размеров", vm.stepMode) {
                                vm.stepMode = it
                                if (it) vm.stepCount = 1
                            }
                            CheckItem("Показывать размеры", vm.showDims) { vm.showDims = it }
                            CheckItem("Показывать контур", vm.showLines) { vm.showLines = it }
                            HorizontalDivider()
                            DropdownMenuItem(text = { Text("Найти лист-мишень") }, onClick = { menu = false; vm.detectSheet() })
                            if (vm.project.sheetH != null) {
                                DropdownMenuItem(text = { Text("Не использовать лист-мишень") }, onClick = { menu = false; vm.removeSheet() })
                            }
                            DropdownMenuItem(text = { Text("Очистить разметку") }, onClick = { menu = false; clearDlg = true })
                        }
                    }
                },
            )
        },
        bottomBar = {
            if (vm.mode == ViewMode.PHOTO) {
                NavigationBar {
                    for (t in Tool.entries) {
                        NavigationBarItem(
                            selected = vm.tool == t,
                            onClick = { vm.tool = t; vm.cancelPending(); if (t != Tool.SELECT) vm.selection = null },
                            icon = { Icon(toolIcon(t), t.title) },
                            label = { Text(t.title, fontSize = 10.sp, maxLines = 1) },
                        )
                    }
                }
            }
        },
    ) { pad ->
        Box(Modifier.padding(pad).fillMaxSize()) {
            if (vm.mode == ViewMode.PHOTO) PhotoCanvas(vm) else DrawingCanvas(vm)

            Column(Modifier.align(Alignment.TopCenter).padding(8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                CalibChip(vm) { calibDlg = true }
                if (vm.mode == ViewMode.PHOTO) {
                    Spacer(Modifier.size(6.dp))
                    Surface(color = Color(0xCC000000), shape = RoundedCornerShape(8.dp)) {
                        Text(hint(vm), color = Color.White, fontSize = 13.sp, modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp))
                    }
                }
            }

            Column(Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(8.dp)) {
                if (vm.stepMode) StepBar(vm)
                if (vm.mode == ViewMode.PHOTO) vm.selection?.let { SelectionCard(vm, it) }
            }

            vm.busy?.let { msg ->
                Surface(Modifier.align(Alignment.Center), shape = RoundedCornerShape(12.dp), tonalElevation = 6.dp, shadowElevation = 6.dp) {
                    Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(Modifier.size(28.dp))
                        Spacer(Modifier.width(16.dp))
                        Text(msg)
                    }
                }
            }
        }
    }

    vm.dialog?.let { DimInputDialog(vm, it) }
    if (renameDlg) TextDialog("Название", vm.project.name, onDismiss = { renameDlg = false }) { vm.rename(it); renameDlg = false }
    if (stampDlg) StampDialog(vm.project.stamp, onDismiss = { stampDlg = false }) { vm.setStamp(it); stampDlg = false }
    if (calibDlg) CalibDialog(vm) { calibDlg = false }
    if (clearDlg) AlertDialog(
        onDismissRequest = { clearDlg = false },
        title = { Text("Очистить разметку?") },
        text = { Text("Будут удалены все точки, линии и размеры. Фото останется. Можно отменить кнопкой «Отменить».") },
        confirmButton = { TextButton(onClick = { vm.clearAll(); clearDlg = false }) { Text("Очистить") } },
        dismissButton = { TextButton(onClick = { clearDlg = false }) { Text("Отмена") } },
    )
}

@Composable
private fun CheckItem(text: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    DropdownMenuItem(
        text = { Text(text) },
        onClick = { onChange(!checked) },
        trailingIcon = { Checkbox(checked = checked, onCheckedChange = onChange) },
    )
}

private fun hint(vm: EditorViewModel): String = when (vm.tool) {
    Tool.SELECT -> "Коснитесь объекта, чтобы выбрать. Точку можно перетащить."
    Tool.POINT -> "Ставьте точки. Касание по линии контура — новая вершина в ней"
    Tool.ARC -> when {
        vm.arcFromLine != null -> "Точка, через которую пройдёт дуга"
        vm.pending.isEmpty() -> "Дуга: коснитесь линии (станет дугой) или поставьте начало"
        vm.pending.size == 1 -> "Дуга: точка на дуге"
        else -> "Дуга: конец"
    }
    Tool.LINE -> if (vm.pending.isEmpty()) "Линия: первая точка" else "Следующая точка. Ещё раз на последнюю — конец линии"
    Tool.DIM -> if (vm.pending.isEmpty()) "Размер: первая точка или коснитесь линии контура" else "Размер: вторая точка"
    Tool.CIRCLE -> "Отверстие: точка ${vm.circlePts.size + 1} из 3 на краю"
    Tool.AUTO -> "Коснитесь детали или обведите её рамкой пальцем"
}

@Composable
private fun CalibChip(vm: EditorViewModel, onClick: () -> Unit) {
    val c = vm.calibration
    val modeText = when (c.mode) {
        CalibMode.FULL -> "точно · ${c.usedCount} разм."
        CalibMode.TILT -> "приблизительно · ${c.usedCount} разм. · добавьте размер"
        CalibMode.SCALE -> "только масштаб · ${c.usedCount} разм. · нужны ещё, лучше диагональ"
        CalibMode.NONE -> ""
    }
    val base = when {
        !c.calibrated -> "Нет масштаба — введите известный размер"
        c.sheet && c.usedCount == 0 -> "Лист-мишень · точно"
        c.sheet -> "Лист + $modeText"
        else -> modeText.replaceFirstChar { it.uppercaseChar() }
    }
    val sigma = c.sigmaRel?.let { " · ±" + fmtMm(it * 100) + "%" } ?: ""
    val bad = c.outliers.size
    Surface(
        color = if (bad > 0) Color(0xFFB71C1C) else if (c.calibrated) Color(0xFF1B5E20) else Color(0xFF37474F),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.clickable(onClick = onClick),
    ) {
        Text(
            base + sigma + if (bad > 0) " · ⚠ не сходится: $bad" else "",
            color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
        )
    }
}

@Composable
private fun StepBar(vm: EditorViewModel) {
    val total = DrawingOrder.all(vm.project).size
    Surface(shape = RoundedCornerShape(12.dp), tonalElevation = 4.dp, shadowElevation = 4.dp, modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
            IconButton(onClick = { vm.stepCount = (vm.stepCount - 1).coerceAtLeast(0) }) { Icon(Icons.Filled.ChevronLeft, "Назад") }
            Text("Размеры: ${vm.stepCount.coerceAtMost(total)} из $total")
            IconButton(onClick = { vm.stepCount = (vm.stepCount + 1).coerceAtMost(total) }) { Icon(Icons.Filled.ChevronRight, "Вперёд") }
            IconButton(onClick = { vm.stepMode = false }) { Icon(Icons.Filled.Close, "Закрыть") }
        }
    }
}

@Composable
private fun SelectionCard(vm: EditorViewModel, s: Selection) {
    val v = vm.values()
    val cal = vm.calibration
    val p = vm.project
    var title = ""
    var detail: String? = null
    var warn: String? = null
    var editLabel: String? = null
    when (s) {
        is Selection.Dim -> {
            val d = p.dims.firstOrNull { it.id == s.id } ?: return
            title = "Размер"
            if (d.known != null) {
                detail = fmtMm(d.known) + " мм — введён"
                v.computedDim(d.id)?.let { detail += " (по фото ≈${fmtMm(it)})" }
            } else {
                val c = v.computedDim(d.id)
                detail = if (c == null) "Нужна калибровка — введите хотя бы один известный размер"
                else "≈" + fmtMm(c) + (v.dimUncertainty(d.id)?.let { " ±" + fmtMm(it) } ?: "") + " мм — вычислен"
            }
            cal.outliers[d.id]?.let { warn = "По остальным размерам получается ${fmtMm(it)} мм — проверьте" }
            editLabel = "Изменить"
        }
        is Selection.Circle -> {
            val c = p.circles.firstOrNull { it.id == s.id } ?: return
            title = "Отверстие"
            detail = if (c.known != null) "Ø" + fmtMm(c.known) + " мм — введён"
            else v.computedCircle(c.id)?.let { "Ø≈" + fmtMm(it) + (v.circleUncertainty(c.id)?.let { u -> " ±" + fmtMm(u) } ?: "") + " мм — вычислен" }
                ?: "Диаметр появится после калибровки"
            cal.outliers[c.id]?.let { warn = "По остальным размерам получается Ø${fmtMm(it)} — проверьте" }
            editLabel = "Ввести Ø"
        }
        is Selection.Line -> {
            val l = p.lines.firstOrNull { it.id == s.id } ?: return
            title = "Линия контура"
            val a = p.point(l.a); val b = p.point(l.b)
            if (a != null && b != null && cal.calibrated) detail = "≈" + fmtMm(dist(cal.toMm(a.p), cal.toMm(b.p))) + " мм"
            editLabel = "Проставить размер"
        }
        is Selection.Point -> { title = "Точка"; detail = "Перетащите, чтобы уточнить. При удалении соседние точки контура соединятся" }
        is Selection.Arc -> {
            val a = p.arcs.firstOrNull { it.id == s.id } ?: return
            title = "Дуга"
            detail = if (a.known != null) "R" + fmtMm(a.known) + " мм — введён"
            else v.computedArc(a.id)?.let { "R≈" + fmtMm(it) + (v.arcUncertainty(a.id)?.let { u -> " ±" + fmtMm(u) } ?: "") + " мм — вычислен" }
                ?: "Радиус появится после калибровки"
            cal.outliers[a.id]?.let { warn = "По остальным размерам получается R${fmtMm(it)} — проверьте" }
            editLabel = "Ввести R"
        }
    }
    Surface(shape = RoundedCornerShape(12.dp), tonalElevation = 4.dp, shadowElevation = 6.dp, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(start = 16.dp, end = 4.dp, top = 8.dp, bottom = 4.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(title, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                IconButton(onClick = { vm.selection = null }) { Icon(Icons.Filled.Close, "Закрыть") }
            }
            detail?.let { Text(it) }
            warn?.let { Text("⚠ $it", color = MaterialTheme.colorScheme.error) }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                if (s is Selection.Dim) {
                    val on = vm.isOnDrawing(s.id)
                    TextButton(onClick = { vm.toggleOnDrawing(s.id) }) { Text(if (on) "На чертеже ✓" else "На чертеже ✗") }
                }
                editLabel?.let { TextButton(onClick = vm::editSelection) { Text(it) } }
                TextButton(onClick = vm::deleteSelection) { Text("Удалить", color = MaterialTheme.colorScheme.error) }
            }
        }
    }
}

@Composable
private fun DimInputDialog(vm: EditorViewModel, d: DimDialog) {
    val p = vm.project
    val cal = vm.calibration
    val isCircle = d.circleId != null
    val isArc = d.arcId != null
    val existing: Double? = when {
        d.circleId != null -> p.circles.firstOrNull { it.id == d.circleId }?.known
        d.arcId != null -> p.arcs.firstOrNull { it.id == d.arcId }?.known
        d.dimId != null -> p.dims.firstOrNull { it.id == d.dimId }?.known
        else -> p.dims.firstOrNull { (it.a == d.a && it.b == d.b) || (it.a == d.b && it.b == d.a) }?.known
    }
    val computed: Double? = when {
        !cal.calibrated -> null
        d.circleId != null -> vm.values().computedCircle(d.circleId)
        d.arcId != null -> vm.values().computedArc(d.arcId)
        else -> {
            val a = p.point(d.a); val b = p.point(d.b)
            if (a != null && b != null) dist(cal.toMm(a.p), cal.toMm(b.p)) else null
        }
    }
    var text by remember(d) { mutableStateOf(existing?.let(::fmtMm) ?: "") }
    val value = text.replace(',', '.').toDoubleOrNull()?.takeIf { it > 0 }
    val focus = remember { FocusRequester() }
    LaunchedEffect(d) { runCatching { focus.requestFocus() } }

    AlertDialog(
        onDismissRequest = { vm.dialog = null },
        title = { Text(if (isCircle) "Диаметр отверстия" else if (isArc) "Радиус дуги" else "Размер") },
        text = {
            Column {
                Text(
                    if (computed != null) "По фото: ≈${fmtMm(computed)} мм.\nЕсли вы его намерили — введите точное значение."
                    else "Введите намеренное значение. Чем больше известных размеров — тем точнее остальные.",
                    fontSize = 14.sp,
                )
                Spacer(Modifier.size(10.dp))
                OutlinedTextField(
                    value = text,
                    onValueChange = { text = it.filter { ch -> ch.isDigit() || ch == '.' || ch == ',' } },
                    label = { Text(if (isCircle) "Ø, мм" else if (isArc) "R, мм" else "мм") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.focusRequester(focus),
                )
            }
        },
        confirmButton = {
            TextButton(enabled = value != null, onClick = { vm.saveDim(d, value) }) { Text("Сохранить") }
        },
        dismissButton = {
            Row {
                TextButton(onClick = { vm.dialog = null }) { Text("Отмена") }
                TextButton(onClick = { vm.saveDim(d, null) }) { Text("Вычислять") }
            }
        },
    )
}

@Composable
private fun CalibDialog(vm: EditorViewModel, onDismiss: () -> Unit) {
    val c = vm.calibration
    val p = vm.project
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Калибровка") },
        text = {
            Column {
                Text(
                    "Калибровка строится по всем введённым размерам сразу. Чем их больше — тем точнее остальные.\n\n" +
                        "• Вводите не только стороны, но и 1–2 диагонали: по одним сторонам форма может «перекоситься».\n" +
                        "• 1–3 размера дают в основном масштаб — снимайте строго сверху.\n" +
                        "• От 6 размеров с диагоналями учитывается и перспектива — можно снимать под углом.\n" +
                        "• Лист-мишень под деталью даёт точную калибровку сразу, без ввода размеров.\n\n" +
                        "У каждого вычисленного размера показана погрешность (±). " +
                        "Мерить нужно в одной плоскости: всё, что выше или ниже неё, будет с ошибкой.",
                    fontSize = 14.sp,
                )
                if (c.outliers.isNotEmpty()) {
                    Spacer(Modifier.size(10.dp))
                    Text("Не сходятся с остальными:", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.error)
                    for ((id, pred) in c.outliers) {
                        val known = p.dims.firstOrNull { it.id == id }?.known ?: p.circles.firstOrNull { it.id == id }?.known
                        Text("• введено ${known?.let(::fmtMm) ?: "?"}, по остальным ${fmtMm(pred)} мм", color = MaterialTheme.colorScheme.error)
                    }
                    Text("Проверьте замер или точки размера.", fontSize = 13.sp)
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Понятно") } },
    )
}

@Composable
fun TextDialog(title: String, initial: String, onDismiss: () -> Unit, onOk: (String) -> Unit) {
    var text by remember { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { OutlinedTextField(text, { text = it }, singleLine = true) },
        confirmButton = { TextButton(onClick = { onOk(text.trim()) }) { Text("OK") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } },
    )
}

@Composable
private fun StampDialog(initial: Stamp, onDismiss: () -> Unit, onOk: (Stamp) -> Unit) {
    var title by remember { mutableStateOf(initial.title) }
    var author by remember { mutableStateOf(initial.author) }
    var material by remember { mutableStateOf(initial.material) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Штамп чертежа") },
        text = {
            Column {
                OutlinedTextField(title, { title = it }, label = { Text("Наименование (пусто — название эскиза)") }, singleLine = true)
                OutlinedTextField(author, { author = it }, label = { Text("Разработал") }, singleLine = true)
                OutlinedTextField(material, { material = it }, label = { Text("Материал") }, singleLine = true)
            }
        },
        confirmButton = { TextButton(onClick = { onOk(Stamp(title.trim(), author.trim(), material.trim())) }) { Text("Сохранить") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } },
    )
}
