package ru.konstruktor.eskiz.ui

import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SmallFloatingActionButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.data.ProjectStore
import ru.konstruktor.eskiz.export.Exporters
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun ProjectListScreen(onOpen: (String) -> Unit) {
    val ctx = LocalContext.current
    val store = remember { ProjectStore(ctx) }
    val scope = rememberCoroutineScope()
    var refresh by remember { mutableStateOf(0) }
    val projects by produceState<List<Project>?>(null, refresh) {
        value = withContext(Dispatchers.IO) { store.list() }
    }
    var busy by remember { mutableStateOf(false) }
    var menu by remember { mutableStateOf(false) }
    var about by remember { mutableStateOf(false) }
    var toDelete by remember { mutableStateOf<Project?>(null) }

    fun createFrom(uri: Uri) {
        busy = true
        scope.launch {
            val p = withContext(Dispatchers.IO) {
                runCatching { store.create(uri, "Эскиз ${(projects?.size ?: 0) + 1}") }.getOrNull()
            }
            busy = false
            if (p != null) onOpen(p.id)
        }
    }

    val captureFile = remember { File(ctx.cacheDir, "camera/capture.jpg").apply { parentFile?.mkdirs() } }
    val captureUri = remember { FileProvider.getUriForFile(ctx, ctx.packageName + ".files", captureFile) }
    val camera = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        if (ok) createFrom(captureUri)
    }
    val gallery = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) createFrom(uri)
    }
    var importError by remember { mutableStateOf<String?>(null) }
    val importer = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        busy = true
        scope.launch {
            val r = withContext(Dispatchers.IO) { runCatching { store.importArchive(uri) } }
            busy = false
            r.onSuccess { onOpen(it.id) }.onFailure { importError = it.message ?: "Не удалось открыть файл" }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Эскиз") },
                actions = {
                    Box {
                        IconButton(onClick = { menu = true }) { Icon(Icons.Filled.MoreVert, "Меню") }
                        DropdownMenu(menu, onDismissRequest = { menu = false }) {
                            DropdownMenuItem(text = { Text("Лист-мишень A4 (PDF для печати)") }, onClick = {
                                menu = false
                                scope.launch {
                                    val f = withContext(Dispatchers.Default) { Exporters.markerSheetPdf(ctx) }
                                    Exporters.share(ctx, listOf(f), "Лист-мишень")
                                }
                            })
                            DropdownMenuItem(text = { Text("Открыть проект (.eskiz)") }, onClick = {
                                menu = false
                                importer.launch(arrayOf("application/zip", "application/octet-stream", "*/*"))
                            })
                            DropdownMenuItem(text = { Text("Как пользоваться") }, onClick = { menu = false; about = true })
                        }
                    }
                },
            )
        },
        floatingActionButton = {
            Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(12.dp)) {
                SmallFloatingActionButton(onClick = {
                    gallery.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                }) { Icon(Icons.Filled.PhotoLibrary, "Из галереи") }
                ExtendedFloatingActionButton(
                    onClick = { camera.launch(captureUri) },
                    icon = { Icon(Icons.Filled.PhotoCamera, null) },
                    text = { Text("Новый эскиз") },
                )
            }
        },
    ) { pad ->
        Box(Modifier.padding(pad).fillMaxSize()) {
            val list = projects
            when {
                list == null -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                list.isEmpty() -> Column(
                    Modifier.align(Alignment.Center).padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Icon(Icons.Filled.PhotoCamera, null, Modifier.size(64.dp), tint = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.size(16.dp))
                    Text(
                        "Сфотографируйте деталь — приложение найдёт контур, а вы введёте размеры, которые намерили. " +
                            "Остальные размеры посчитаются сами.",
                        textAlign = TextAlign.Center,
                    )
                }
                else -> LazyVerticalGrid(
                    columns = GridCells.Adaptive(160.dp),
                    contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 140.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(list, key = { it.id }) { p ->
                        Card(Modifier.combinedClickable(onClick = { onOpen(p.id) }, onLongClick = { toDelete = p })) {
                            Thumb(store.thumb(p.id))
                            Column(Modifier.padding(10.dp)) {
                                Text(p.name, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleSmall)
                                Text(
                                    SimpleDateFormat("d MMM yyyy, HH:mm", Locale("ru")).format(Date(p.updated)) +
                                        " · размеров ${p.dims.size + p.circles.size}",
                                    fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                }
            }
            if (busy) CircularProgressIndicator(Modifier.align(Alignment.Center))
        }
    }

    importError?.let { e ->
        AlertDialog(
            onDismissRequest = { importError = null },
            title = { Text("Не удалось открыть") },
            text = { Text(e) },
            confirmButton = { TextButton(onClick = { importError = null }) { Text("OK") } },
        )
    }

    toDelete?.let { p ->
        AlertDialog(
            onDismissRequest = { toDelete = null },
            title = { Text("Удалить «${p.name}»?") },
            text = { Text("Фото и все размеры будут удалены без возможности восстановления.") },
            confirmButton = { TextButton(onClick = { store.delete(p.id); toDelete = null; refresh++ }) { Text("Удалить") } },
            dismissButton = { TextButton(onClick = { toDelete = null }) { Text("Отмена") } },
        )
    }

    if (about) AlertDialog(
        onDismissRequest = { about = false },
        title = { Text("Как пользоваться") },
        text = {
            Text(
                "1. Снимите деталь как можно ровнее сверху, лучше на контрастном фоне.\n" +
                    "2. Инструмент «Авто» — коснитесь детали или обведите её рамкой: найдутся контур и отверстия.\n" +
                    "3. «Размер» — коснитесь линии или двух точек и введите намеренное значение. " +
                    "Вводите все размеры, какие смогли замерить.\n" +
                    "4. Остальные размеры посчитаются сами (синие, со знаком ≈). Красные — не сходятся с остальными.\n" +
                    "5. Кнопка чертежа сверху — чистый чертёж на листе A4. «Поделиться» — PNG, PDF или DXF в Telegram и куда угодно.\n\n" +
                    "Для максимальной точности распечатайте лист-мишень (меню) и кладите деталь на него.\n\n" +
                    "Удалить эскиз — долгое нажатие на карточку.",
                fontSize = 14.sp,
            )
        },
        confirmButton = { TextButton(onClick = { about = false }) { Text("Понятно") } },
    )
}

@Composable
private fun Thumb(file: File) {
    val bmp by produceState<android.graphics.Bitmap?>(null, file) {
        value = withContext(Dispatchers.IO) { BitmapFactory.decodeFile(file.absolutePath) }
    }
    Box(Modifier.fillMaxWidth().aspectRatio(4f / 3f).background(Color(0xFF263238))) {
        bmp?.let {
            Image(it.asImageBitmap(), null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
        }
    }
}
