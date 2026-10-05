package ru.konstruktor.eskiz.ui

import android.app.Application
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
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
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.export.Exporters
import ru.konstruktor.eskiz.geom3d.MultiView
import ru.konstruktor.eskiz.render.fmtMm
import java.io.File

private val ROLE_HINT = mapOf(
    MultiView.Role.FRONT to "главный вид: вверху чертежа — верх детали",
    MultiView.Role.TOP to "вверху чертежа — задняя сторона детали",
    MultiView.Role.LEFT to "смотрим слева: справа на чертеже — передняя сторона",
    MultiView.Role.RIGHT to "смотрим справа: слева на чертеже — передняя сторона",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ModelScreen(modelId: String, onBack: () -> Unit, onOpenSketch: (String) -> Unit) {
    val ctx = LocalContext.current
    val app = ctx.applicationContext as Application
    val vm: ModelViewModel = viewModel(key = "model-$modelId") { ModelViewModel(app, modelId) }
    val snack = remember { SnackbarHostState() }
    var picker by remember { mutableStateOf<MultiView.Role?>(null) }
    var exportDlg by remember { mutableStateOf(false) }
    var renameDlg by remember { mutableStateOf(false) }
    var toSave by remember { mutableStateOf<File?>(null) }
    val saver = rememberLauncherForActivityResult(CreateDocument()) { uri ->
        val f = toSave
        if (uri != null && f != null) vm.saveFile(f, uri)
        toSave = null
    }

    BackHandler(onBack = onBack)
    LaunchedEffect(vm.message) { vm.message?.let { snack.showSnackbar(it); vm.message = null } }
    // Возврат из эскиза: пересобираем с учётом правок.
    LaunchedEffect(Unit) { vm.refreshSketches() }

    Scaffold(
        snackbarHost = { SnackbarHost(snack) },
        topBar = {
            TopAppBar(
                title = { Text(vm.model.name, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.clickable { renameDlg = true }) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Назад") } },
                actions = {
                    IconButton(onClick = { exportDlg = true }, enabled = vm.result != null) { Icon(Icons.Filled.Share, "Экспорт") }
                },
            )
        },
    ) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().verticalScroll(rememberScrollState())) {
            Preview3D(vm)
            Column(Modifier.padding(horizontal = 12.dp)) {
                vm.result?.let { r ->
                    Text(
                        "Габарит ${fmtMm(r.size.x)} × ${fmtMm(r.size.y)} × ${fmtMm(r.size.z)} мм · объём ${fmtMm(r.solid.volume / 1000)} см³",
                        fontWeight = FontWeight.Medium, modifier = Modifier.padding(top = 8.dp),
                    )
                    for (w in r.warnings) Text("⚠ $w", color = Color(0xFFE65100), fontSize = 13.sp)
                }
                vm.error?.let { Text("⚠ $it", color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp)) }
                Spacer(Modifier.height(8.dp))
                Text(
                    "Выберите эскизы для 2–3 видов. Контур каждого вида выдавливается в направлении взгляда, " +
                        "деталь — их общая часть. Отверстия и вырезы вида проходят насквозь.",
                    fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                for (role in MultiView.Role.entries) {
                    ViewSlot(vm, role, onPick = { picker = role }, onOpenSketch = onOpenSketch)
                }
                if (vm.model.views.size == 1) {
                    var t by remember { mutableStateOf(vm.model.thickness?.let(::fmtMm) ?: "") }
                    OutlinedTextField(
                        value = t,
                        onValueChange = {
                            t = it.filter { c -> c.isDigit() || c == '.' || c == ',' }
                            vm.setThickness(t.replace(',', '.').toDoubleOrNull()?.takeIf { v -> v > 0 })
                        },
                        label = { Text("Толщина (для одного вида), мм") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        modifier = Modifier.padding(vertical = 8.dp),
                    )
                }
                Text(
                    "Ориентацию вида задаёт чертёж эскиза: если вид повёрнут, в эскизе меню → «Повернуть чертёж на 90°». " +
                        "Если деталь получилась зеркальной — отметьте «Зеркально».",
                    fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(vertical = 12.dp),
                )
            }
        }
        vm.busy?.let { msg ->
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Surface(shape = RoundedCornerShape(12.dp), tonalElevation = 6.dp, shadowElevation = 6.dp) {
                    Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(Modifier.size(28.dp)); Spacer(Modifier.width(16.dp)); Text(msg)
                    }
                }
            }
        }
    }

    picker?.let { role ->
        SketchPicker(vm, role, onDismiss = { picker = null }) { id -> vm.setView(role, id); picker = null }
    }
    if (renameDlg) TextDialog("Название модели", vm.model.name, onDismiss = { renameDlg = false }) { vm.rename(it); renameDlg = false }
    if (exportDlg) {
        var kind by remember { mutableStateOf(Model3DExport.STEP) }
        fun go(save: Boolean) {
            exportDlg = false
            vm.export(kind) { f ->
                if (save) { toSave = f; saver.launch(f.name to Exporters.mimeOf(f)) }
                else Exporters.share(ctx, listOf(f), "Отправить 3D-модель")
            }
        }
        AlertDialog(
            onDismissRequest = { exportDlg = false },
            title = { Text("Экспорт 3D") },
            text = {
                Column {
                    for (k in Model3DExport.entries) Row(Modifier.fillMaxWidth().clickable { kind = k }, verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(kind == k, { kind = k }); Text(k.title, fontSize = 14.sp)
                    }
                    if (vm.model.views.size > 1) Text(
                        "Модель по нескольким видам записывается плоскими гранями: отверстия и скругления — многогранные (точность 0,02 мм).",
                        fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp),
                    )
                }
            },
            confirmButton = {
                Row {
                    TextButton(onClick = { go(true) }) { Text("Сохранить в файл") }
                    TextButton(onClick = { go(false) }) { Text("Отправить") }
                }
            },
            dismissButton = { TextButton(onClick = { exportDlg = false }) { Text("Отмена") } },
        )
    }
}

/** Предпросмотр: программный рендер, вращение пальцем. */
@Composable
private fun Preview3D(vm: ModelViewModel) {
    var size by remember { mutableStateOf(IntSize.Zero) }
    var yaw by remember { mutableFloatStateOf(-35f) }
    var pitch by remember { mutableFloatStateOf(25f) }
    val result = vm.result
    val bmp by produceState<Bitmap?>(null, result, size, yaw, pitch) {
        value = withContext(Dispatchers.Default) {
            // Рендер в половинном разрешении — быстро и достаточно чётко.
            vm.render(size.width / 2, size.height / 2, Math.toRadians(yaw.toDouble()), Math.toRadians(pitch.toDouble()))
        }
    }
    Box(
        Modifier.fillMaxWidth().height(300.dp).background(Color(0xFFECEFF1))
            .onSizeChanged { size = it }
            .pointerInput(Unit) {
                detectDragGestures { ch, d ->
                    ch.consume()
                    yaw -= d.x * 0.4f
                    pitch = (pitch + d.y * 0.4f).coerceIn(-89f, 89f)
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        when {
            vm.building -> CircularProgressIndicator()
            result == null -> Text(
                if (vm.model.views.isEmpty()) "Выберите эскизы видов ниже" else "Модель пока не построена",
                color = Color(0xFF546E7A),
            )
            else -> bmp?.let { Image(it.asImageBitmap(), "3D-модель", contentScale = ContentScale.FillBounds, modifier = Modifier.fillMaxSize()) }
        }
        if (result != null) Text(
            "Вращайте пальцем", fontSize = 11.sp, color = Color(0xFF78909C),
            modifier = Modifier.align(Alignment.BottomEnd).padding(6.dp),
        )
    }
}

@Composable
private fun ViewSlot(vm: ModelViewModel, role: MultiView.Role, onPick: () -> Unit, onOpenSketch: (String) -> Unit) {
    val ref = vm.viewOf(role)
    val sketch = ref?.let { r -> vm.sketches.firstOrNull { it.id == r.projectId } }
    val err = vm.viewErrors[role]
    Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row(Modifier.padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(64.dp).background(Color(0xFF263238), RoundedCornerShape(6.dp)).clickable(onClick = onPick)) {
                sketch?.let { Thumb64(vm.projects.thumb(it.id)) }
            }
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(role.title, fontWeight = FontWeight.Bold)
                Text(ROLE_HINT[role] ?: "", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(sketch?.name ?: if (ref != null) "эскиз удалён" else "не выбран", fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                err?.let { Text("⚠ $it", color = MaterialTheme.colorScheme.error, fontSize = 12.sp) }
                Row(horizontalArrangement = Arrangement.spacedBy(0.dp), verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onPick) { Text(if (ref == null) "Выбрать" else "Заменить") }
                    if (ref != null) {
                        TextButton(onClick = { onOpenSketch(ref.projectId) }) { Text("Открыть") }
                        TextButton(onClick = { vm.setView(role, null) }) { Text("Убрать") }
                    }
                }
                if (ref != null) Row(Modifier.clickable { vm.toggleMirror(role) }, verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(ref.mirror, { vm.toggleMirror(role) }); Text("Зеркально", fontSize = 13.sp)
                }
            }
        }
    }
}

@Composable
private fun Thumb64(file: File) {
    val bmp by produceState<Bitmap?>(null, file) { value = withContext(Dispatchers.IO) { BitmapFactory.decodeFile(file.absolutePath) } }
    bmp?.let { Image(it.asImageBitmap(), null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize()) }
}

@Composable
private fun SketchPicker(vm: ModelViewModel, role: MultiView.Role, onDismiss: () -> Unit, onPick: (String) -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Эскиз для вида «${role.title}»") },
        text = {
            if (vm.sketches.isEmpty()) Text("Сначала сделайте эскизы видов детали (вкладка «Эскизы»).")
            else LazyColumn(Modifier.height(400.dp)) {
                items(vm.sketches, key = { it.id }) { p: Project ->
                    Row(Modifier.fillMaxWidth().clickable { onPick(p.id) }.padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(56.dp).background(Color(0xFF263238), RoundedCornerShape(6.dp))) { Thumb64(vm.projects.thumb(p.id)) }
                        Spacer(Modifier.width(10.dp))
                        Column {
                            Text(p.name, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text("размеров ${p.dims.size + p.circles.size + p.arcs.size}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Отмена") } },
    )
}
