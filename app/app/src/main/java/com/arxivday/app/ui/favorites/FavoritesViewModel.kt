package com.arxivday.app.ui.favorites

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arxivday.app.data.local.FavoriteEntity
import com.arxivday.app.repository.PaperRepository
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@OptIn(ExperimentalCoroutinesApi::class)
class FavoritesViewModel(private val repo: PaperRepository) : ViewModel() {

    val searchQuery = MutableStateFlow("")

    val favorites: StateFlow<List<FavoriteEntity>> = searchQuery
        .flatMapLatest { query ->
            if (query.isBlank()) repo.getAllFavorites()
            else repo.searchFavorites(query)
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun setQuery(q: String) { searchQuery.value = q }

    fun remove(entryId: String) {
        viewModelScope.launch { repo.removeFavorite(entryId) }
    }
}
