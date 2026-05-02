package com.arxivday.app.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arxivday.app.data.model.Paper
import com.arxivday.app.repository.PaperRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class ReadFilter {
    ALL,
    UNREAD,
    READ,
}

data class HomeUiState(
    val sourcePapers: List<Paper> = emptyList(),
    val papers: List<Paper> = emptyList(),
    val categories: List<String> = emptyList(),
    val selectedCategory: String? = null,
    val selectedReadFilter: ReadFilter = ReadFilter.ALL,
    val selectedDate: String? = null,
    val currentPage: Int = 1,
    val canLoadMore: Boolean = true,
    val isLoading: Boolean = false,
    val isLoadingMore: Boolean = false,
    val error: String? = null,
    val loadMoreError: String? = null,
    val favoritedIds: Set<String> = emptySet(),
    val viewedIds: Set<String> = emptySet(),
    val viewedHistory: List<String> = emptyList(),
)

class HomeViewModel(
    private val repo: PaperRepository,
    initialViewedIds: Set<String> = emptySet(),
    initialViewedHistory: List<String> = emptyList(),
    private val onViewedStateChanged: (Set<String>, List<String>) -> Unit = { _, _ -> },
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        HomeUiState(
            viewedIds = initialViewedIds,
            viewedHistory = initialViewedHistory,
        )
    )
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        loadInitial()
        observeFavorites()
    }

    private fun loadInitial() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                error = null,
                loadMoreError = null,
                currentPage = 1,
                canLoadMore = true,
            )
            runCatching {
                coroutineScope {
                    val categories = async { repo.getCategories() }
                    val latestDate = async { repo.getLatestDate() }
                    val papers = async { repo.getArticles(page = 1, pageSize = PAGE_SIZE) }
                    Triple(categories.await(), latestDate.await(), papers.await())
                }
            }.onSuccess { (categories, date, papers) ->
                _uiState.value = _uiState.value.copy(
                    sourcePapers = papers,
                    papers = papers.visiblePapers(
                        viewedIds = _uiState.value.viewedIds,
                        readFilter = _uiState.value.selectedReadFilter,
                    ),
                    categories = categories,
                    selectedDate = date.ifBlank { null },
                    currentPage = 1,
                    canLoadMore = papers.size >= PAGE_SIZE,
                    isLoading = false,
                    error = null,
                    loadMoreError = null,
                )
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    sourcePapers = emptyList(),
                    papers = emptyList(),
                    categories = emptyList(),
                    isLoading = false,
                    canLoadMore = false,
                    error = "加载失败：${error.message ?: error::class.java.simpleName}",
                )
            }
        }
    }

    private fun observeFavorites() {
        viewModelScope.launch {
            repo.getAllFavorites().collect { favs ->
                _uiState.value = _uiState.value.copy(
                    favoritedIds = favs.map { it.entryId }.toSet()
                )
            }
        }
    }

    fun selectCategory(category: String?) {
        _uiState.value = _uiState.value.copy(selectedCategory = category)
        reload()
    }

    fun selectReadFilter(filter: ReadFilter) {
        val state = _uiState.value
        val nextFilter = if (state.selectedReadFilter == filter) ReadFilter.ALL else filter
        _uiState.value = state.copy(
            selectedReadFilter = nextFilter,
            papers = state.sourcePapers.visiblePapers(
                viewedIds = state.viewedIds,
                readFilter = nextFilter,
            ),
        )
    }

    fun refresh() = reload()

    private fun reload() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            val state = _uiState.value
            runCatching {
                repo.getArticles(
                    date = state.selectedDate,
                    category = state.selectedCategory,
                    page = 1,
                    pageSize = PAGE_SIZE,
                )
            }.onSuccess { papers ->
                _uiState.value = _uiState.value.copy(
                    sourcePapers = papers,
                    papers = papers.visiblePapers(
                        viewedIds = _uiState.value.viewedIds,
                        readFilter = _uiState.value.selectedReadFilter,
                    ),
                    currentPage = 1,
                    canLoadMore = papers.size >= PAGE_SIZE,
                    isLoading = false,
                    error = null,
                    loadMoreError = null,
                )
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    sourcePapers = emptyList(),
                    papers = emptyList(),
                    isLoading = false,
                    canLoadMore = false,
                    error = "加载失败：${error.message ?: error::class.java.simpleName}",
                )
            }
        }
    }

    fun loadMore() {
        val state = _uiState.value
        if (state.isLoading || state.isLoadingMore || !state.canLoadMore) return

        viewModelScope.launch {
            val nextPage = state.currentPage + 1
            _uiState.value = state.copy(isLoadingMore = true, loadMoreError = null)

            runCatching {
                repo.getArticles(
                    date = state.selectedDate,
                    category = state.selectedCategory,
                    page = nextPage,
                    pageSize = PAGE_SIZE,
                )
            }.onSuccess { newPapers ->
                val knownIds = _uiState.value.sourcePapers.map { it.entryId }.toSet()
                val merged = _uiState.value.sourcePapers + newPapers.filter { it.entryId !in knownIds }
                _uiState.value = _uiState.value.copy(
                    sourcePapers = merged,
                    papers = merged.visiblePapers(
                        viewedIds = _uiState.value.viewedIds,
                        readFilter = _uiState.value.selectedReadFilter,
                    ),
                    currentPage = nextPage,
                    canLoadMore = newPapers.size >= PAGE_SIZE,
                    isLoadingMore = false,
                    loadMoreError = null,
                )
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    isLoadingMore = false,
                    loadMoreError = "加载更多失败：${error.message ?: error::class.java.simpleName}",
                )
            }
        }
    }

    fun markViewed(entryId: String) {
        val state = _uiState.value
        val viewedIds = state.viewedIds + entryId
        val viewedHistory = if (state.viewedHistory.lastOrNull() == entryId) {
            state.viewedHistory
        } else {
            state.viewedHistory + entryId
        }
        _uiState.value = state.copy(
            viewedIds = viewedIds,
            viewedHistory = viewedHistory,
            papers = state.sourcePapers.visiblePapers(
                viewedIds = viewedIds,
                readFilter = state.selectedReadFilter,
            ),
        )
        onViewedStateChanged(viewedIds, viewedHistory)
    }

    fun nextUnreadAfter(entryId: String): Paper? {
        val state = _uiState.value
        val papers = state.sourcePapers
        if (papers.isEmpty()) return null

        val currentIndex = papers.indexOfFirst { it.entryId == entryId }.takeIf { it >= 0 } ?: -1
        val afterCurrent = if (currentIndex >= 0) papers.drop(currentIndex + 1) else papers
        val beforeCurrent = if (currentIndex > 0) papers.take(currentIndex) else emptyList()

        return afterCurrent.firstOrNull { it.entryId !in state.viewedIds } ?:
            beforeCurrent.firstOrNull { it.entryId !in state.viewedIds }
    }

    fun previousViewedBefore(entryId: String): Paper? {
        val state = _uiState.value
        val index = state.viewedHistory.lastIndexOf(entryId)
        if (index <= 0) return null
        val previousEntryId = state.viewedHistory[index - 1]
        return state.sourcePapers.firstOrNull { it.entryId == previousEntryId }
    }

    fun toggleFavorite(paper: Paper) {
        viewModelScope.launch {
            if (_uiState.value.favoritedIds.contains(paper.entryId)) {
                repo.removeFavorite(paper.entryId)
            } else {
                repo.addFavorite(paper)
            }
        }
    }
}

private const val PAGE_SIZE = 20

private fun List<Paper>.visiblePapers(
    viewedIds: Set<String>,
    readFilter: ReadFilter,
): List<Paper> =
    filter { paper ->
        when (readFilter) {
            ReadFilter.ALL -> true
            ReadFilter.UNREAD -> paper.entryId !in viewedIds
            ReadFilter.READ -> paper.entryId in viewedIds
        }
    }.orderForReading(viewedIds)

private fun List<Paper>.orderForReading(viewedIds: Set<String>): List<Paper> =
    withIndex()
        .sortedWith(
            compareBy<IndexedValue<Paper>> { it.value.entryId in viewedIds }
                .thenBy { it.index }
        )
        .map { it.value }
