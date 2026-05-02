package com.arxivday.app.data.model

import com.google.gson.annotations.SerializedName

data class Paper(
    @SerializedName("id") val id: Int = 0,
    @SerializedName("title") val title: String = "",
    @SerializedName("CN_title") val cnTitle: String = "",
    @SerializedName("summary") val summary: String = "",
    @SerializedName("CN_summary") val cnSummary: String = "",
    @SerializedName("authors") val authors: String = "",
    @SerializedName("categories") val categories: String = "",
    @SerializedName("primary_category") val primaryCategory: String = "",
    @SerializedName("entry_id") val entryId: String = "",
    @SerializedName("published") val published: String = "",
    @SerializedName("updated") val updated: String = "",
    @SerializedName("doi") val doi: String? = null,
    @SerializedName("journal_ref") val journalRef: String? = null,
) {
    val categoryList: List<String>
        get() = categories.split(",").map { it.trim() }.filter { it.isNotEmpty() }

    val authorList: List<String>
        get() = authors.split(",").map { it.trim() }.filter { it.isNotEmpty() }

    val arxivUrl: String
        get() = if (entryId.startsWith("http")) entryId
                else "https://arxiv.org/abs/${entryId.substringAfterLast("/")}"

    val displayTitle: String
        get() = cnTitle.ifBlank { title }

    val displayDate: String
        get() = (updated.ifBlank { published }).take(10)
}
