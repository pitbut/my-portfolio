package ru.rynok.app.data.remote

import org.json.JSONArray
import org.json.JSONObject

/**
 * События, которыми телефоны обмениваются через сервер-релей.
 * Формат JSON должен совпадать с тем, что понимает projects/rynok/server.
 */
sealed class SyncEvent {

    data class ItemPayload(
        val id: String,
        val name: String,
        val quantity: String,
        val plannedPrice: Double?,
    )

    data class ListUpdate(
        val listId: String,
        val items: List<ItemPayload>,
        val plannedTotal: Double,
    ) : SyncEvent()

    data class ItemUpdate(
        val listId: String,
        val itemId: String,
        val purchased: Boolean,
        val actualPrice: Double?,
    ) : SyncEvent()

    data class ChatMessage(
        val id: String,
        val chatType: String, // TEXT | VOICE | VIDEO
        val text: String?,
        val mediaId: String?,
        val durationMs: Long?,
        val timestamp: Long,
        /** Заполняется только для входящих событий — сервер подставляет роль отправителя. */
        val fromRole: String? = null,
    ) : SyncEvent()

    data class BudgetSummary(
        val listId: String,
        val completed: Boolean,
        val plannedTotal: Double,
        val actualTotal: Double,
    ) : SyncEvent()

    /** Служебное подтверждение подключения от сервера — на него просто не реагируем. */
    data object Connected : SyncEvent()

    data object Unknown : SyncEvent()
}

fun SyncEvent.toJson(): String {
    val root = JSONObject()
    when (this) {
        is SyncEvent.ListUpdate -> {
            root.put("type", "list:update")
            val payload = JSONObject()
            payload.put("listId", listId)
            payload.put("plannedTotal", plannedTotal)
            val itemsArray = JSONArray()
            items.forEach { item ->
                val itemJson = JSONObject()
                itemJson.put("id", item.id)
                itemJson.put("name", item.name)
                itemJson.put("quantity", item.quantity)
                if (item.plannedPrice != null) itemJson.put("plannedPrice", item.plannedPrice)
                itemsArray.put(itemJson)
            }
            payload.put("items", itemsArray)
            root.put("payload", payload)
        }
        is SyncEvent.ItemUpdate -> {
            root.put("type", "item:update")
            val payload = JSONObject()
            payload.put("listId", listId)
            payload.put("itemId", itemId)
            payload.put("purchased", purchased)
            if (actualPrice != null) payload.put("actualPrice", actualPrice)
            root.put("payload", payload)
        }
        is SyncEvent.ChatMessage -> {
            root.put("type", "chat:message")
            val payload = JSONObject()
            payload.put("id", id)
            payload.put("chatType", chatType)
            if (text != null) payload.put("text", text)
            if (mediaId != null) payload.put("mediaId", mediaId)
            if (durationMs != null) payload.put("durationMs", durationMs)
            payload.put("timestamp", timestamp)
            root.put("payload", payload)
        }
        is SyncEvent.BudgetSummary -> {
            root.put("type", "budget:summary")
            val payload = JSONObject()
            payload.put("listId", listId)
            payload.put("completed", completed)
            payload.put("plannedTotal", plannedTotal)
            payload.put("actualTotal", actualTotal)
            root.put("payload", payload)
        }
        SyncEvent.Connected, SyncEvent.Unknown -> Unit
    }
    return root.toString()
}

fun parseSyncEvent(raw: String): SyncEvent {
    return try {
        val root = JSONObject(raw)
        val payload = root.optJSONObject("payload") ?: JSONObject()
        when (root.optString("type")) {
            "connected" -> SyncEvent.Connected
            "list:update" -> {
                val itemsArray = payload.optJSONArray("items") ?: JSONArray()
                val items = (0 until itemsArray.length()).map { i ->
                    val itemJson = itemsArray.getJSONObject(i)
                    SyncEvent.ItemPayload(
                        id = itemJson.getString("id"),
                        name = itemJson.getString("name"),
                        quantity = itemJson.optString("quantity", ""),
                        plannedPrice = if (itemJson.has("plannedPrice")) itemJson.getDouble("plannedPrice") else null,
                    )
                }
                SyncEvent.ListUpdate(
                    listId = payload.getString("listId"),
                    items = items,
                    plannedTotal = payload.optDouble("plannedTotal", 0.0),
                )
            }
            "item:update" -> SyncEvent.ItemUpdate(
                listId = payload.getString("listId"),
                itemId = payload.getString("itemId"),
                purchased = payload.optBoolean("purchased", false),
                actualPrice = if (payload.has("actualPrice")) payload.getDouble("actualPrice") else null,
            )
            "chat:message" -> SyncEvent.ChatMessage(
                id = payload.getString("id"),
                chatType = payload.optString("chatType", "TEXT"),
                text = if (payload.has("text")) payload.getString("text") else null,
                mediaId = if (payload.has("mediaId")) payload.getString("mediaId") else null,
                durationMs = if (payload.has("durationMs")) payload.getLong("durationMs") else null,
                timestamp = payload.optLong("timestamp", System.currentTimeMillis()),
                fromRole = if (root.has("fromRole")) root.getString("fromRole") else null,
            )
            "budget:summary" -> SyncEvent.BudgetSummary(
                listId = payload.getString("listId"),
                completed = payload.optBoolean("completed", false),
                plannedTotal = payload.optDouble("plannedTotal", 0.0),
                actualTotal = payload.optDouble("actualTotal", 0.0),
            )
            else -> SyncEvent.Unknown
        }
    } catch (e: Exception) {
        SyncEvent.Unknown
    }
}
