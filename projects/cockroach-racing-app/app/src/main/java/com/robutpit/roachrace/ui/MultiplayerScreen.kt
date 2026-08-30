package com.robutpit.roachrace.ui

import android.bluetooth.BluetoothDevice
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.robutpit.roachrace.bluetooth.LinkState
import com.robutpit.roachrace.bluetooth.MAX_PEERS
import com.robutpit.roachrace.bluetooth.deviceLabel
import com.robutpit.roachrace.ui.theme.*

enum class MpRole { NONE, HOST, JOIN }

@Composable
fun MultiplayerScreen(
    role: MpRole,
    state: LinkState,
    hostPeerNames: List<String>,
    bondedDevices: List<BluetoothDevice>,
    discoveredDevices: List<BluetoothDevice>,
    onPickHost: () -> Unit,
    onPickJoin: () -> Unit,
    onDeviceSelected: (BluetoothDevice) -> Unit,
    onRescan: () -> Unit,
    onStartRace: () -> Unit,
    onRetry: () -> Unit,
    onBack: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("Bluetooth-турнир", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text(
                "Один телефон создаёт игру — он же и хост. Остальные (до $MAX_PEERS человек) подключаются к нему. " +
                    "Хост запросит разрешение стать видимым по Bluetooth на 5 минут — обязательно разреши. " +
                    "Присоединяющиеся жмут «Присоединиться» и «🔍 Искать», пока хост не появится в списке " +
                    "(если телефоны уже спарены в системных настройках Bluetooth — хост сразу в «сопряжённых устройствах»).",
                fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(top = 6.dp, bottom = 10.dp),
            )

            when (role) {
                MpRole.NONE -> {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        PrimaryButton("Создать игру (хост)", onClick = onPickHost)
                        SecondaryButton("Присоединиться", onClick = onPickJoin)
                    }
                }
                MpRole.HOST -> HostPanel(state, hostPeerNames, onStartRace, onRetry)
                MpRole.JOIN -> JoinPanel(state, bondedDevices, discoveredDevices, onDeviceSelected, onRescan, onRetry)
            }
        }
        SecondaryButton("← назад к трассе", onClick = onBack)
    }
}

@Composable
private fun HostPanel(state: LinkState, peerNames: List<String>, onStartRace: () -> Unit, onRetry: () -> Unit) {
    when (state) {
        is LinkState.Failed -> Column {
            Text("Ошибка: ${state.reason}", fontSize = 12.sp, color = Red, modifier = Modifier.padding(bottom = 8.dp))
            SecondaryButton("Повторить", onClick = onRetry)
        }
        else -> Column {
            if (peerNames.isEmpty()) {
                Text("Ожидание подключений…", fontSize = 12.sp, color = TextDim, modifier = Modifier.padding(bottom = 10.dp))
            } else {
                Text("Подключились (${peerNames.size}/$MAX_PEERS):", fontSize = 12.sp, color = Green, modifier = Modifier.padding(bottom = 6.dp))
                peerNames.forEach { name ->
                    Text("🪳 $name", fontSize = 13.sp, color = TextMain, modifier = Modifier.padding(vertical = 2.dp))
                }
                Spacer(Modifier.height(10.dp))
            }
            PrimaryButton(
                if (peerNames.isEmpty()) "Ждём хотя бы одного игрока…" else "🏁 Начать гонку с ${peerNames.size} игроками",
                enabled = peerNames.isNotEmpty(),
                onClick = onStartRace,
            )
        }
    }
}

@Composable
private fun JoinPanel(
    state: LinkState,
    bonded: List<BluetoothDevice>,
    discovered: List<BluetoothDevice>,
    onDeviceSelected: (BluetoothDevice) -> Unit,
    onRescan: () -> Unit,
    onRetry: () -> Unit,
) {
    when (state) {
        is LinkState.Connecting -> Text("Подключение…", fontSize = 12.sp, color = TextDim)
        is LinkState.Connected -> Text("Подключено к ${state.peerName}. Ждём, когда хост запустит гонку… (другие тоже могут ещё подключаться)", fontSize = 12.sp, color = Green)
        is LinkState.Failed -> Column {
            Text("Ошибка: ${state.reason}", fontSize = 12.sp, color = Red, modifier = Modifier.padding(bottom = 8.dp))
            SecondaryButton("Повторить поиск", onClick = onRetry)
        }
        else -> Column {
            Text("Уже сопряжённые устройства:", fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(bottom = 6.dp))
            if (bonded.isEmpty()) {
                Text("Нет сопряжённых устройств — сначала спарьте телефоны в системных настройках Bluetooth.", fontSize = 11.sp, color = TextDim)
            }
            LazyColumn(modifier = Modifier.heightIn(max = 160.dp)) {
                items(bonded) { d ->
                    DeviceRow(deviceLabel(d)) { onDeviceSelected(d) }
                }
            }
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
                Text("Поиск новых поблизости:", fontSize = 11.sp, color = TextDim)
                SecondaryButton("🔍 Искать", onClick = onRescan)
            }
            LazyColumn(modifier = Modifier.heightIn(max = 160.dp)) {
                items(discovered) { d ->
                    DeviceRow(deviceLabel(d)) { onDeviceSelected(d) }
                }
            }
        }
    }
}

@Composable
private fun DeviceRow(label: String, onClick: () -> Unit) {
    Text(
        "📱 $label",
        fontSize = 13.sp, color = TextMain,
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(BgFaint)
            .border(1.dp, LineColor, RoundedCornerShape(10.dp))
            .clickable { onClick() }
            .padding(10.dp),
    )
}
