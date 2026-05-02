package com.arxivday.app.ui.calendar

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arxivday.app.repository.PaperRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.YearMonth

data class CalendarUiState(
    val availableDays: Set<String> = emptySet(),
    val currentYearMonth: YearMonth = YearMonth.now(),
    val isLoading: Boolean = false,
)

class CalendarViewModel(private val repo: PaperRepository) : ViewModel() {

    private val _uiState = MutableStateFlow(CalendarUiState())
    val uiState: StateFlow<CalendarUiState> = _uiState.asStateFlow()

    init {
        loadCalendar()
    }

    private fun loadCalendar() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            val allDays = runCatching {
                repo.getCalendarDays().toSet()
            }.getOrDefault(emptySet())
            _uiState.value = _uiState.value.copy(availableDays = allDays, isLoading = false)
        }
    }

    fun goToPreviousMonth() {
        _uiState.value = _uiState.value.copy(
            currentYearMonth = _uiState.value.currentYearMonth.minusMonths(1)
        )
    }

    fun goToNextMonth() {
        _uiState.value = _uiState.value.copy(
            currentYearMonth = _uiState.value.currentYearMonth.plusMonths(1)
        )
    }
}
