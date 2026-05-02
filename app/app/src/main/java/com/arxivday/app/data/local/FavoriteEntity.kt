package com.arxivday.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.arxivday.app.data.model.Paper

@Entity(tableName = "favorites")
data class FavoriteEntity(
    @PrimaryKey val entryId: String,
    val cnTitle: String,
    val enTitle: String,
    val cnSummary: String,
    val enSummary: String,
    val authors: String,
    val categories: String,
    val primaryCategory: String,
    val published: String,
    val arxivUrl: String,
    val savedAt: Long = System.currentTimeMillis(),
) {
    fun toPaper() = Paper(
        entryId = entryId,
        cnTitle = cnTitle,
        title = enTitle,
        cnSummary = cnSummary,
        summary = enSummary,
        authors = authors,
        categories = categories,
        primaryCategory = primaryCategory,
        published = published,
    )
}

fun Paper.toFavoriteEntity() = FavoriteEntity(
    entryId = entryId,
    cnTitle = cnTitle,
    enTitle = title,
    cnSummary = cnSummary,
    enSummary = summary,
    authors = authors,
    categories = categories,
    primaryCategory = primaryCategory,
    published = published,
    arxivUrl = arxivUrl,
)
