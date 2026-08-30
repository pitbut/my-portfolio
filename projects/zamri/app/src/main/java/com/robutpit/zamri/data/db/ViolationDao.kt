package com.robutpit.zamri.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface ViolationDao {

    @Insert
    suspend fun insert(violation: ViolationEntity): Long

    @Query("SELECT * FROM violations ORDER BY timestampMillis DESC")
    fun observeAll(): Flow<List<ViolationEntity>>

    @Query("SELECT * FROM violations WHERE round = :round ORDER BY timestampMillis DESC")
    fun observeByRound(round: Int): Flow<List<ViolationEntity>>

    @Query("SELECT COUNT(*) FROM violations WHERE round = :round")
    suspend fun countForRound(round: Int): Int

    @Query("SELECT COUNT(*) FROM violations")
    suspend fun countAll(): Int

    @Query("DELETE FROM violations")
    suspend fun clearAll()
}
