package com.arxivday.app.ui.detail

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.outlined.StarOutline
import androidx.compose.material3.BottomAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChange
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arxivday.app.data.model.Paper
import com.arxivday.app.repository.PaperRepository
import com.arxivday.app.ui.components.CategoryChip
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class PaperDetailViewModel(
    val paper: Paper,
    private val repo: PaperRepository,
) : ViewModel() {

    val isFavorite = repo.isFavorite(paper.entryId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), false)

    fun toggleFavorite() {
        viewModelScope.launch {
            if (isFavorite.value) {
                repo.removeFavorite(paper.entryId)
            } else {
                repo.addFavorite(paper)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun PaperDetailScreen(
    viewModel: PaperDetailViewModel,
    onBack: () -> Unit,
    onViewed: (String) -> Unit,
    onNextPaper: () -> Unit,
    onPreviousPaper: () -> Unit,
) {
    val paper = viewModel.paper
    val isFavorite by viewModel.isFavorite.collectAsState()
    val context = LocalContext.current
    val scrollState = rememberScrollState()
    var showEnSummary by remember { mutableStateOf(false) }

    LaunchedEffect(paper.entryId) {
        scrollState.scrollTo(0)
        onViewed(paper.entryId)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("论文详情") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                    }
                },
            )
        },
        bottomBar = {
            BottomAppBar {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    FilledTonalButton(
                        onClick = { viewModel.toggleFavorite() },
                        modifier = Modifier.weight(1f),
                    ) {
                        Icon(
                            imageVector = if (isFavorite) Icons.Filled.Star else Icons.Outlined.StarOutline,
                            contentDescription = null,
                        )
                        Text(if (isFavorite) "已收藏" else "收藏")
                    }
                    OutlinedButton(
                        onClick = {
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(paper.arxivUrl))
                            context.startActivity(intent)
                        },
                        modifier = Modifier.weight(1f),
                    ) {
                        Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = null)
                        Text("原文")
                    }
                    IconButton(
                        onClick = {
                            val intent = Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_TEXT, "${paper.title}\n${paper.arxivUrl}")
                            }
                            context.startActivity(Intent.createChooser(intent, "分享论文"))
                        }
                    ) {
                        Icon(Icons.Default.Share, contentDescription = "分享")
                    }
                }
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
                .pointerInput(paper.entryId) {
                    awaitEachGesture {
                        val down = awaitFirstDown(
                            requireUnconsumed = false,
                            pass = PointerEventPass.Initial,
                        )
                        val startedAtTop = scrollState.value <= 8
                        val startedAtBottom = scrollState.value >= scrollState.maxValue - 8
                        var totalDrag = 0f
                        while (true) {
                            val event = awaitPointerEvent(PointerEventPass.Initial)
                            val change = event.changes.firstOrNull { it.id == down.id } ?: break
                            if (!change.pressed) break
                            totalDrag += change.positionChange().y
                        }
                        when {
                            startedAtBottom && totalDrag < -120f -> {
                                onNextPaper()
                            }
                            startedAtTop && totalDrag > 120f -> {
                                onPreviousPaper()
                            }
                        }
                    }
                }
                .verticalScroll(scrollState)
                .padding(horizontal = 20.dp, vertical = 8.dp),
        ) {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                paper.categoryList.forEach { cat -> CategoryChip(label = cat) }
            }

            Spacer(Modifier.height(12.dp))

            if (paper.cnTitle.isNotBlank()) {
                Text(
                    text = paper.cnTitle,
                    style = MaterialTheme.typography.headlineMedium,
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = paper.title,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontStyle = FontStyle.Italic,
                )
            } else {
                Text(
                    text = paper.title,
                    style = MaterialTheme.typography.headlineMedium,
                )
            }

            Spacer(Modifier.height(16.dp))
            HorizontalDivider()
            Spacer(Modifier.height(12.dp))

            Text("中文摘要", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(6.dp))
            Text(
                text = paper.cnSummary.ifBlank { "暂无中文摘要" },
                style = MaterialTheme.typography.bodyLarge,
                lineHeight = MaterialTheme.typography.bodyLarge.lineHeight,
            )

            Spacer(Modifier.height(12.dp))

            TextButton(onClick = { showEnSummary = !showEnSummary }) {
                Text(if (showEnSummary) "收起英文摘要" else "展开英文摘要")
            }
            if (showEnSummary) {
                Spacer(Modifier.height(4.dp))
                Text(
                    text = paper.summary,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Spacer(Modifier.height(16.dp))
            HorizontalDivider()
            Spacer(Modifier.height(12.dp))

            Text("作者", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(4.dp))
            Text(
                text = paper.authors,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            if (paper.published.isNotBlank()) {
                Spacer(Modifier.height(10.dp))
                Text("发布日期", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(4.dp))
                Text(
                    text = paper.published.take(10),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Spacer(Modifier.height(80.dp))
        }
    }
}
