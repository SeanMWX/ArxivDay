package com.arxivday.app.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import java.time.LocalTime
import java.time.format.DateTimeFormatter

private const val HEALTH_CHECK_INTERVAL_MS = 10 * 60 * 1000L

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onHealthCheck: suspend () -> String,
) {
    var isChecking by remember { mutableStateOf(false) }
    var healthMessage by remember { mutableStateOf("等待自动检测") }
    var lastCheckedAt by remember { mutableStateOf<String?>(null) }
    var isHealthy by remember { mutableStateOf<Boolean?>(null) }

    LaunchedEffect(Unit) {
        while (true) {
            isChecking = true
            isHealthy = null
            healthMessage = "检测中..."

            runCatching { onHealthCheck() }
                .onSuccess { status ->
                    isHealthy = status == "ok"
                    healthMessage = if (status == "ok") {
                        "服务器在线"
                    } else {
                        "服务器返回状态：$status"
                    }
                }
                .onFailure { error ->
                    isHealthy = false
                    healthMessage = "连接失败：${error.message ?: error::class.java.simpleName}"
                }

            lastCheckedAt = LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss"))
            isChecking = false
            delay(HEALTH_CHECK_INTERVAL_MS)
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("设置") }) },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .padding(20.dp),
        ) {
            Text("服务器状态", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(12.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                if (isChecking) {
                    CircularProgressIndicator(
                        modifier = Modifier
                            .padding(end = 10.dp)
                            .size(22.dp),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Icon(
                        imageVector = when (isHealthy) {
                            true -> Icons.Default.CheckCircle
                            false -> Icons.Default.CloudOff
                            null -> Icons.Default.Refresh
                        },
                        contentDescription = null,
                        tint = when (isHealthy) {
                            true -> MaterialTheme.colorScheme.primary
                            false -> MaterialTheme.colorScheme.error
                            null -> MaterialTheme.colorScheme.onSurfaceVariant
                        },
                        modifier = Modifier.padding(end = 10.dp),
                    )
                }

                Column {
                    Text(
                        text = healthMessage,
                        style = MaterialTheme.typography.bodyMedium,
                        color = when (isHealthy) {
                            true -> MaterialTheme.colorScheme.primary
                            false -> MaterialTheme.colorScheme.error
                            null -> MaterialTheme.colorScheme.onSurfaceVariant
                        },
                    )
                    Text(
                        text = lastCheckedAt?.let { "上次检测：$it" } ?: "每 10 分钟自动检测一次",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Spacer(Modifier.height(32.dp))

            Text("关于", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(4.dp))
            Text(
                text = "ArxivDay\n版本 1.0",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
