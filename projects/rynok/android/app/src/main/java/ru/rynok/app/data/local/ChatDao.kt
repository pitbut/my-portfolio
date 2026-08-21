package ru.rynok.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface ChatDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertMessage(message: ChatMessageEntity)

    @Query("SELECT * FROM chat_messages WHERE familyId = :familyId ORDER BY timestamp ASC")
    fun observeMessages(familyId: String): Flow<List<ChatMessageEntity>>

    @Query("DELETE FROM chat_messages WHERE familyId = :familyId")
    suspend fun clearChat(familyId: String)
}
