package com.arxivday.app.data.remote

import com.arxivday.app.data.model.ArticlesResponse
import com.arxivday.app.data.model.CalendarResponse
import com.arxivday.app.data.model.CategoriesResponse
import com.arxivday.app.data.model.HealthResponse
import com.arxivday.app.data.model.LatestResponse
import retrofit2.http.GET
import retrofit2.http.Query

interface ArxivApiService {

    @GET("latest")
    suspend fun getLatest(): LatestResponse

    @GET("health")
    suspend fun getHealth(): HealthResponse

    @GET("articles")
    suspend fun getArticles(
        @Query("date") date: String? = null,
        @Query("category") category: String? = null,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
    ): ArticlesResponse

    @GET("calendar")
    suspend fun getCalendar(): CalendarResponse

    @GET("categories")
    suspend fun getCategories(): CategoriesResponse
}
