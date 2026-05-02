package com.arxivday.app.data.model

import com.google.gson.annotations.SerializedName

data class ArticlesResponse(
    @SerializedName("items") val items: List<Paper> = emptyList(),
    @SerializedName("total") val total: Int = 0,
    @SerializedName("page") val page: Int = 1,
    @SerializedName("page_size") val pageSize: Int = 20,
)

data class LatestResponse(
    @SerializedName("date") val date: String = "",
    @SerializedName("count") val count: Int = 0,
)

data class HealthResponse(
    @SerializedName("status") val status: String = "",
)

data class CalendarResponse(
    @SerializedName("years") val years: List<Int> = emptyList(),
    @SerializedName("days") val days: List<String> = emptyList(),
)

data class CategoriesResponse(
    @SerializedName("categories") val categories: List<String> = emptyList(),
)
