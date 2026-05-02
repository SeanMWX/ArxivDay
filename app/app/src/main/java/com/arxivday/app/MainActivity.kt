package com.arxivday.app

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.arxivday.app.data.local.AppDatabase
import com.arxivday.app.data.model.Paper
import com.arxivday.app.data.remote.DEFAULT_API_BASE_URL
import com.arxivday.app.data.remote.DEFAULT_API_KEY
import com.arxivday.app.data.remote.NetworkModule
import com.arxivday.app.repository.PaperRepository
import com.arxivday.app.ui.calendar.CalendarScreen
import com.arxivday.app.ui.calendar.CalendarViewModel
import com.arxivday.app.ui.detail.PaperDetailScreen
import com.arxivday.app.ui.detail.PaperDetailViewModel
import com.arxivday.app.ui.favorites.FavoritesScreen
import com.arxivday.app.ui.favorites.FavoritesViewModel
import com.arxivday.app.ui.home.HomeScreen
import com.arxivday.app.ui.home.HomeViewModel
import com.arxivday.app.ui.navigation.BottomNavigationBar
import com.arxivday.app.ui.navigation.Screen
import com.arxivday.app.ui.settings.SettingsScreen
import com.arxivday.app.ui.theme.ArxivDayTheme
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

private val Context.dataStore by preferencesDataStore(name = "arxivday_prefs")
private val API_URL_KEY = stringPreferencesKey("api_base_url")
private val API_KEY_KEY = stringPreferencesKey("api_key")
private val VIEWED_IDS_KEY = stringSetPreferencesKey("viewed_ids")
private val VIEWED_HISTORY_KEY = stringPreferencesKey("viewed_history")
private const val VIEWED_HISTORY_LIMIT = 500

private data class ApiSettings(
    val baseUrl: String,
    val apiKey: String,
)

private data class InitialAppState(
    val apiSettings: ApiSettings,
    val viewedIds: Set<String>,
    val viewedHistory: List<String>,
)

class MainActivity : ComponentActivity() {

    private val db by lazy { (application as ArxivDayApp).database }
    private val repo by lazy { PaperRepository(db) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val initialState = runBlocking {
            val prefs = dataStore.data.first()
            val savedBaseUrl = prefs[API_URL_KEY]?.trim()
            val baseUrl = if (savedBaseUrl.isNullOrBlank() || savedBaseUrl.isFrontendUrl()) {
                DEFAULT_API_BASE_URL
            } else {
                savedBaseUrl
            }
            InitialAppState(
                apiSettings = ApiSettings(
                    baseUrl = baseUrl,
                    apiKey = prefs[API_KEY_KEY]?.ifBlank { DEFAULT_API_KEY } ?: DEFAULT_API_KEY,
                ),
                viewedIds = prefs[VIEWED_IDS_KEY] ?: emptySet(),
                viewedHistory = prefs[VIEWED_HISTORY_KEY].toViewedHistory(),
            )
        }
        NetworkModule.setBaseUrl(initialState.apiSettings.baseUrl)
        NetworkModule.setApiKey(initialState.apiSettings.apiKey)

        setContent {
            ArxivDayTheme {
                ArxivDayApp(
                    repo = repo,
                    initialViewedIds = initialState.viewedIds,
                    initialViewedHistory = initialState.viewedHistory,
                    onViewedStateChanged = { viewedIds, viewedHistory ->
                        lifecycleScope.launch {
                            dataStore.edit { prefs ->
                                prefs[VIEWED_IDS_KEY] = viewedIds
                                prefs[VIEWED_HISTORY_KEY] = viewedHistory
                                    .takeLast(VIEWED_HISTORY_LIMIT)
                                    .joinToString("\n")
                            }
                        }
                    },
                )
            }
        }
    }
}

private fun String.isFrontendUrl(): Boolean {
    val normalized = trim().trimEnd('/').lowercase()
    return normalized == "arxivday.com" ||
            normalized == "http://arxivday.com" ||
            normalized == "https://arxivday.com"
}

private fun String?.toViewedHistory(): List<String> =
    this?.lines()
        ?.map { it.trim() }
        ?.filter { it.isNotEmpty() }
        ?: emptyList()

@Composable
fun ArxivDayApp(
    repo: PaperRepository,
    initialViewedIds: Set<String>,
    initialViewedHistory: List<String>,
    onViewedStateChanged: (Set<String>, List<String>) -> Unit,
) {
    val navController = rememberNavController()
    var selectedPaper by remember { mutableStateOf<Paper?>(null) }

    val repoFactory = remember(repo, initialViewedIds, initialViewedHistory, onViewedStateChanged) {
        object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T = when {
                modelClass.isAssignableFrom(HomeViewModel::class.java) -> HomeViewModel(
                    repo = repo,
                    initialViewedIds = initialViewedIds,
                    initialViewedHistory = initialViewedHistory,
                    onViewedStateChanged = onViewedStateChanged,
                ) as T
                modelClass.isAssignableFrom(CalendarViewModel::class.java) -> CalendarViewModel(repo) as T
                modelClass.isAssignableFrom(FavoritesViewModel::class.java) -> FavoritesViewModel(repo) as T
                else -> throw IllegalArgumentException("Unknown ViewModel: ${modelClass.name}")
            }
        }
    }
    val homeVm = viewModel<HomeViewModel>(factory = repoFactory)

    Scaffold(
        bottomBar = { BottomNavigationBar(navController) }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Home.route,
            modifier = Modifier.padding(innerPadding),
        ) {
            composable(Screen.Home.route) {
                HomeScreen(
                    viewModel = homeVm,
                    onPaperClick = { paper ->
                        selectedPaper = paper
                        navController.navigate(Screen.PaperDetail.createRoute(paper.entryId))
                    },
                )
            }

            composable(Screen.Calendar.route) {
                val vm = viewModel<CalendarViewModel>(factory = repoFactory)
                CalendarScreen(
                    viewModel = vm,
                    onDateSelected = { date ->
                        navController.navigate(Screen.Home.route) {
                            popUpTo(Screen.Home.route) { inclusive = true }
                        }
                        // TODO: pass selected date to HomeViewModel
                    },
                )
            }

            composable(Screen.Favorites.route) {
                val vm = viewModel<FavoritesViewModel>(factory = repoFactory)
                FavoritesScreen(
                    viewModel = vm,
                    onPaperClick = { paper ->
                        selectedPaper = paper
                        navController.navigate(Screen.PaperDetail.createRoute(paper.entryId))
                    },
                )
            }

            composable(Screen.Settings.route) {
                SettingsScreen(
                    onHealthCheck = { repo.checkHealth() },
                )
            }

            composable(
                route = Screen.PaperDetail.route,
                arguments = listOf(navArgument("entryId") { type = NavType.StringType }),
            ) {
                val paper = selectedPaper
                if (paper != null) {
                    val detailVm = remember(paper.entryId) {
                        PaperDetailViewModel(paper, repo)
                    }
                    PaperDetailScreen(
                        viewModel = detailVm,
                        onBack = { navController.popBackStack() },
                        onViewed = { entryId -> homeVm.markViewed(entryId) },
                        onNextPaper = {
                            homeVm.nextUnreadAfter(paper.entryId)?.let { nextPaper ->
                                selectedPaper = nextPaper
                            }
                        },
                        onPreviousPaper = {
                            homeVm.previousViewedBefore(paper.entryId)?.let { previousPaper ->
                                selectedPaper = previousPaper
                            }
                        },
                    )
                }
            }
        }
    }
}
