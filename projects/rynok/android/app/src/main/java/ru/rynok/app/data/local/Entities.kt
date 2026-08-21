package ru.rynok.app.data.local

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

enum class ListStatus {
    DRAFT,      // жена ещё составляет список
    SENT,       // список отправлен, муж ещё не начал покупки
    SHOPPING,   // муж отмечает покупки
    COMPLETED,  // покупки завершены, список ушёл в архив
}

@Entity(tableName = "shopping_lists")
data class ShoppingListEntity(
    @PrimaryKey val id: String,
    val status: ListStatus,
    val createdAt: Long,
    val sentAt: Long? = null,
    val completedAt: Long? = null,
    /** Плановый бюджет, зафиксированный на момент отправки списка. */
    val plannedTotal: Double = 0.0,
)

@Entity(
    tableName = "shopping_items",
    foreignKeys = [
        ForeignKey(
            entity = ShoppingListEntity::class,
            parentColumns = ["id"],
            childColumns = ["listId"],
            onDelete = ForeignKey.CASCADE,
        )
    ],
    indices = [Index("listId")],
)
data class ShoppingItemEntity(
    @PrimaryKey val id: String,
    val listId: String,
    val position: Int,
    val name: String,
    val quantity: String,
    val plannedPrice: Double? = null,
    val actualPrice: Double? = null,
    val purchased: Boolean = false,
)

enum class ChatMessageType { TEXT, VOICE, VIDEO }

@Entity(tableName = "chat_messages")
data class ChatMessageEntity(
    @PrimaryKey val id: String,
    val familyId: String,
    val fromRole: String, // "wife" | "husband"
    val type: ChatMessageType,
    val text: String? = null,
    /** Путь к файлу на этом устройстве (записан сам или скачан из relay). */
    val localMediaPath: String? = null,
    val durationMs: Long? = null,
    val timestamp: Long,
)
