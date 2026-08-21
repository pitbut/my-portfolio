package ru.rynok.app.ui.family

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import ru.rynok.app.R

private enum class Mode { NONE, JOIN }

@Composable
fun FamilySetupScreen(onFamilyReady: () -> Unit) {
    val viewModel: FamilyViewModel = viewModel()
    val state by viewModel.state.collectAsState()
    var mode by remember { mutableStateOf(Mode.NONE) }
    var codeInput by remember { mutableStateOf("") }

    if (state is FamilySetupState.Done) {
        onFamilyReady()
        return
    }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Icon(Icons.Filled.ShoppingCart, contentDescription = null, modifier = Modifier.size(64.dp))
            Text(
                text = stringResource(R.string.family_setup_title),
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 12.dp, bottom = 32.dp),
            )

            when (val current = state) {
                is FamilySetupState.CodeReady -> {
                    Text(stringResource(R.string.family_code_label), fontSize = 16.sp)
                    Text(
                        text = current.code,
                        fontSize = 40.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(vertical = 16.dp),
                    )
                    Text(
                        stringResource(R.string.family_code_share_hint),
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(bottom = 24.dp),
                    )
                    Button(onClick = { viewModel.confirmCodeShared() }, modifier = Modifier.fillMaxWidth()) {
                        Text("Продолжить")
                    }
                }
                FamilySetupState.Loading -> CircularProgressIndicator()
                is FamilySetupState.Error -> {
                    Text(current.message, color = MaterialTheme.colorScheme.error, textAlign = TextAlign.Center)
                    Button(onClick = { viewModel.resetToChoosing(); mode = Mode.NONE }, modifier = Modifier.padding(top = 16.dp)) {
                        Text("Назад")
                    }
                }
                else -> {
                    when (mode) {
                        Mode.NONE -> {
                            Button(onClick = { viewModel.createFamily() }, modifier = Modifier.fillMaxWidth()) {
                                Text(stringResource(R.string.family_create_button))
                            }
                            OutlinedButton(
                                onClick = { mode = Mode.JOIN },
                                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                            ) {
                                Text(stringResource(R.string.family_join_button))
                            }
                        }
                        Mode.JOIN -> {
                            OutlinedTextField(
                                value = codeInput,
                                onValueChange = { if (it.length <= 6) codeInput = it.filter(Char::isDigit) },
                                label = { Text(stringResource(R.string.family_code_hint)) },
                                modifier = Modifier.width(200.dp),
                            )
                            Button(
                                onClick = { viewModel.joinFamily(codeInput) },
                                modifier = Modifier.padding(top = 16.dp),
                            ) {
                                Text("Присоединиться")
                            }
                        }
                    }
                }
            }
        }
    }
}
