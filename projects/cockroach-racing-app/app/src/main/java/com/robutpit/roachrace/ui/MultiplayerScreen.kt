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
import com.robutpit.roachrace.bluetooth.deviceLabel
import com.robutpit.roachrace.ui.theme.*

enum class MpRole { NONE, HOST, JOIN }

@Composable
fun MultiplayerScreen(
    role: MpRole,
    state: LinkState,
    bondedDevices: List<BluetoothDevice>,
    discoveredDevices: List<BluetoothDevice>,
    onPickHost: () -> Unit,
    onPickJoin: () -> Unit,
    onDeviceSelected: (BluetoothDevice) -> Unit,
    onRescan: () -> Unit,
    onProceed: () -> Unit,
    onRetry: () -> Unit,
    onBack: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        CardBox {
            Text("Bluetooth-гонка вдвоём", fontWeight = FontWeight.SemiBold, fontSize = 17.sp, color = TextMain)
            Text(
                "Один телефон создаёт игру, второй — присоединяется. Оба увидят одно общее поле. " +
                    "Работает через классический Bluetooth (RFCOMM); заранее спарьте телефоны в системных настройках Bluetooth для надёжности.",
                fontSize = 11.sp, color = TextDim, modifier = Modifier.padding(top = 6.dp, bottom = 10.dp),
            )

            when (role) {
                MpRole.NONE -> {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        PrimaryButton("Создать игру (хост)", onClick = onPickHost)
                        SecondaryButton("Присоединиться", onClick = onPickJoin)
                    }
                }
                MpRole.HOST -> HostPanel(state, onProceed, onRetry)
                MpRole.JOIN -> JoinPanel(state, bondedDevices, discoveredDevices, onDeviceSelected, onRescan, onRetry)
            }
        }
        SecondaryButton("← назад к трассе", onClick = onBack)
    }
}

@Composable
private fun HostPanel(state: LinkState, onProceed: () -> Unit, onRetry: () -> Unit) {
    when (state) {
        is LinkState.Idle -> Text("Запуск…", fontSize = 12.sp, color = TextDim)
        is LinkState.Listening -> Text("Ожидание подключения второго телефона…", fontSize = 12.sp, color = TextDim)
        is LinkState.Connecting -> Text("Подключение…", fontSize = 12.sp, color = TextDim)
        is LinkState.Connected -> Column {
            Text("Подключено: ${state.peerName}", fontSize = 13.sp, color = Green, modifier = Modifier.padding(bottom = 8.dp))
            PrimaryButton("Дальше → выбрать трассу и начать", onClick = onProceed)
        }
        is LinkState.Failed -> Column {
            Text("Ошибка: ${state.reason}", fontSize = 12.sp, color = Red, modifier = Modifier.padding(bottom = 8.dp))
            SecondaryButton("Повторить", onClick = onRetry)
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
        is LinkState.Connected -> Text("Подключено к ${state.peerName}. Ждём, когда хост выберет трассу и запустит гонку…", fontSize = 12.sp, color = Green)
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
