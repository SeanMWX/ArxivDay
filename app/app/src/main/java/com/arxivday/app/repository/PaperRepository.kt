package com.arxivday.app.repository

import com.arxivday.app.data.local.AppDatabase
import com.arxivday.app.data.local.FavoriteDao
import com.arxivday.app.data.local.toFavoriteEntity
import com.arxivday.app.data.model.Paper
import com.arxivday.app.data.remote.NetworkModule
import kotlinx.coroutines.flow.Flow

class PaperRepository(db: AppDatabase) {

    private val api get() = NetworkModule.getApiService()
    private val dao: FavoriteDao = db.favoriteDao()

    // --- Remote ---

    suspend fun checkHealth(): String = api.getHealth().status

    suspend fun getLatestDate(): String = api.getLatest().date

    suspend fun getArticles(
        date: String? = null,
        category: String? = null,
        page: Int = 1,
        pageSize: Int = 20,
    ): List<Paper> =
        api.getArticles(date = date, category = category, page = page, pageSize = pageSize).items

    suspend fun getCategories(): List<String> = api.getCategories().categories

    suspend fun getCalendarDays(): List<String> = api.getCalendar().days

    // --- Local favorites (Room) ---

    fun getAllFavorites(): Flow<List<com.arxivday.app.data.local.FavoriteEntity>> =
        dao.getAllFavorites()

    fun searchFavorites(query: String): Flow<List<com.arxivday.app.data.local.FavoriteEntity>> =
        dao.searchFavorites(query)

    fun isFavorite(entryId: String): Flow<Boolean> = dao.isFavorite(entryId)

    suspend fun addFavorite(paper: Paper) = dao.insertFavorite(paper.toFavoriteEntity())

    suspend fun removeFavorite(entryId: String) = dao.deleteFavorite(entryId)
}
