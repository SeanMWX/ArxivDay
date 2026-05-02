package com.arxivday.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface FavoriteDao {

    @Query("SELECT * FROM favorites ORDER BY savedAt DESC")
    fun getAllFavorites(): Flow<List<FavoriteEntity>>

    @Query("SELECT * FROM favorites WHERE entryId = :entryId LIMIT 1")
    suspend fun getFavoriteById(entryId: String): FavoriteEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertFavorite(favorite: FavoriteEntity)

    @Query("DELETE FROM favorites WHERE entryId = :entryId")
    suspend fun deleteFavorite(entryId: String)

    @Query("SELECT EXISTS(SELECT 1 FROM favorites WHERE entryId = :entryId)")
    fun isFavorite(entryId: String): Flow<Boolean>

    @Query("""
        SELECT * FROM favorites
        WHERE cnTitle LIKE '%' || :query || '%'
           OR enTitle LIKE '%' || :query || '%'
           OR authors LIKE '%' || :query || '%'
        ORDER BY savedAt DESC
    """)
    fun searchFavorites(query: String): Flow<List<FavoriteEntity>>
}
