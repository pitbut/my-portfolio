package ru.rynok.app.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface ShoppingListDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertList(list: ShoppingListEntity)

    @Update
    suspend fun updateList(list: ShoppingListEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertItems(items: List<ShoppingItemEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertItem(item: ShoppingItemEntity)

    @Update
    suspend fun updateItem(item: ShoppingItemEntity)

    @Delete
    suspend fun deleteItem(item: ShoppingItemEntity)

    @Query("SELECT * FROM shopping_lists WHERE id = :listId")
    fun observeList(listId: String): Flow<ShoppingListEntity?>

    @Query("SELECT * FROM shopping_lists WHERE id = :listId")
    suspend fun getListOnce(listId: String): ShoppingListEntity?

    @Query("SELECT * FROM shopping_items WHERE listId = :listId ORDER BY position")
    fun observeItems(listId: String): Flow<List<ShoppingItemEntity>>

    /** Список, который сейчас "живой": составляется, отправлен или идут покупки. */
    @Query("SELECT * FROM shopping_lists WHERE status != 'COMPLETED' ORDER BY createdAt DESC LIMIT 1")
    fun observeActiveList(): Flow<ShoppingListEntity?>

    @Query("SELECT * FROM shopping_lists WHERE status = 'COMPLETED' ORDER BY completedAt DESC")
    fun observeArchive(): Flow<List<ShoppingListEntity>>

    @Query("SELECT * FROM shopping_items WHERE listId = :listId ORDER BY position")
    suspend fun getItemsOnce(listId: String): List<ShoppingItemEntity>

    @Query("SELECT * FROM shopping_lists WHERE status = 'COMPLETED' AND completedAt >= :since ORDER BY completedAt DESC")
    suspend fun getCompletedSince(since: Long): List<ShoppingListEntity>

    @Query("SELECT COALESCE(SUM(actualPrice), 0.0) FROM shopping_items WHERE listId = :listId AND purchased = 1")
    suspend fun getActualTotalForList(listId: String): Double

    @Query("DELETE FROM shopping_items WHERE listId = :listId")
    suspend fun clearItems(listId: String)
}
