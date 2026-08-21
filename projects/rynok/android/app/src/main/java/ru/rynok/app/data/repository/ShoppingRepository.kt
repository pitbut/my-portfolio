package ru.rynok.app.data.repository

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.launch
import ru.rynok.app.FamilyRole
import ru.rynok.app.Prefs
import ru.rynok.app.data.local.ListStatus
import ru.rynok.app.data.local.ShoppingItemEntity
import ru.rynok.app.data.local.ShoppingListDao
import ru.rynok.app.data.local.ShoppingListEntity
import ru.rynok.app.data.remote.RelayClient
import ru.rynok.app.data.remote.SyncEvent
import java.util.UUID

data class BudgetSnapshot(val planned: Double, val actual: Double) {
    val difference: Double get() = actual - planned
}

/**
 * Единая точка правды для списка покупок на этом устройстве: читает/пишет
 * Room и одновременно отправляет/принимает события через RelayClient, чтобы
 * оба телефона семьи видели один и тот же список почти в реальном времени.
 */
class ShoppingRepository(
    private val listDao: ShoppingListDao,
    private val relayClient: RelayClient,
    private val prefs: Prefs,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    init {
        scope.launch {
            relayClient.events.collect { event -> handleIncoming(event) }
        }
    }

    fun observeActiveList(): Flow<ShoppingListEntity?> = listDao.observeActiveList()
    fun observeItems(listId: String): Flow<List<ShoppingItemEntity>> = listDao.observeItems(listId)
    fun observeArchive(): Flow<List<ShoppingListEntity>> = listDao.observeArchive()

    /** Жена начинает составлять новый список. */
    suspend fun createDraftList(): String {
        val listId = UUID.randomUUID().toString()
        listDao.insertList(
            ShoppingListEntity(id = listId, status = ListStatus.DRAFT, createdAt = System.currentTimeMillis())
        )
        return listId
    }

    suspend fun addOrUpdateItem(
        listId: String,
        itemId: String?,
        name: String,
        quantity: String,
        plannedPrice: Double?,
        position: Int,
    ) {
        listDao.insertItem(
            ShoppingItemEntity(
                id = itemId ?: UUID.randomUUID().toString(),
                listId = listId,
                position = position,
                name = name,
                quantity = quantity,
                plannedPrice = plannedPrice,
            )
        )
    }

    suspend fun removeItem(item: ShoppingItemEntity) {
        listDao.deleteItem(item)
    }

    /** Жена отправляет готовый список мужу. */
    suspend fun sendList(listId: String) {
        val items = listDao.getItemsOnce(listId)
        val plannedTotal = items.sumOf { it.plannedPrice ?: 0.0 }
        val existing = listDao.getListOnce(listId)
        val list = ShoppingListEntity(
            id = listId,
            status = ListStatus.SENT,
            createdAt = existing?.createdAt ?: System.currentTimeMillis(),
            sentAt = System.currentTimeMillis(),
            plannedTotal = plannedTotal,
        )
        listDao.updateList(list)

        relayClient.send(
            SyncEvent.ListUpdate(
                listId = listId,
                items = items.map {
                    SyncEvent.ItemPayload(it.id, it.name, it.quantity, it.plannedPrice)
                },
                plannedTotal = plannedTotal,
            )
        )
    }

    /** Муж отмечает товар купленным (или снимает отметку) и сообщает об этом жене. */
    suspend fun markPurchased(listId: String, item: ShoppingItemEntity, purchased: Boolean, actualPrice: Double?) {
        listDao.updateItem(item.copy(purchased = purchased, actualPrice = actualPrice))
        markShoppingStartedIfNeeded(listId)

        relayClient.send(
            SyncEvent.ItemUpdate(listId = listId, itemId = item.id, purchased = purchased, actualPrice = actualPrice)
        )
    }

    /** Переводим список в статус "идут покупки" при первой отметке товара. */
    private suspend fun markShoppingStartedIfNeeded(listId: String) {
        val current = listDao.getListOnce(listId) ?: return
        if (current.status == ListStatus.SENT) {
            listDao.updateList(current.copy(status = ListStatus.SHOPPING))
        }
    }

    suspend fun remainingItems(listId: String): List<ShoppingItemEntity> =
        listDao.getItemsOnce(listId).filter { !it.purchased }

    suspend fun actualTotalForList(listId: String): Double = listDao.getActualTotalForList(listId)

    suspend fun budgetSnapshot(listId: String, plannedTotal: Double): BudgetSnapshot {
        val actual = listDao.getActualTotalForList(listId)
        return BudgetSnapshot(planned = plannedTotal, actual = actual)
    }

    /** Муж завершает покупки — список уходит в архив на обоих телефонах. */
    suspend fun finishShopping(listId: String, plannedTotal: Double) {
        val actualTotal = listDao.getActualTotalForList(listId)
        val existing = listDao.getListOnce(listId)
        listDao.updateList(
            ShoppingListEntity(
                id = listId,
                status = ListStatus.COMPLETED,
                createdAt = existing?.createdAt ?: System.currentTimeMillis(),
                sentAt = existing?.sentAt,
                completedAt = System.currentTimeMillis(),
                plannedTotal = plannedTotal,
            )
        )
        relayClient.send(
            SyncEvent.BudgetSummary(listId = listId, completed = true, plannedTotal = plannedTotal, actualTotal = actualTotal)
        )
    }

    private suspend fun handleIncoming(event: SyncEvent) {
        val myRole = prefs.role ?: return
        when (event) {
            is SyncEvent.ListUpdate -> {
                // Приходит мужу от жены: создаём/обновляем список и товары локально.
                if (myRole != FamilyRole.HUSBAND) return
                listDao.insertList(
                    ShoppingListEntity(
                        id = event.listId,
                        status = ListStatus.SENT,
                        createdAt = System.currentTimeMillis(),
                        sentAt = System.currentTimeMillis(),
                        plannedTotal = event.plannedTotal,
                    )
                )
                listDao.clearItems(event.listId)
                listDao.insertItems(
                    event.items.mapIndexed { index, item ->
                        ShoppingItemEntity(
                            id = item.id,
                            listId = event.listId,
                            position = index,
                            name = item.name,
                            quantity = item.quantity,
                            plannedPrice = item.plannedPrice,
                        )
                    }
                )
            }
            is SyncEvent.ItemUpdate -> {
                // Приходит жене от мужа: обновляем локальную копию отметки о покупке.
                if (myRole != FamilyRole.WIFE) return
                val items = listDao.getItemsOnce(event.listId)
                val existing = items.firstOrNull { it.id == event.itemId } ?: return
                listDao.updateItem(existing.copy(purchased = event.purchased, actualPrice = event.actualPrice))
            }
            is SyncEvent.BudgetSummary -> {
                if (myRole != FamilyRole.WIFE) return
                if (!event.completed) return
                val items = listDao.getItemsOnce(event.listId)
                if (items.isEmpty()) return
                val existing = listDao.getListOnce(event.listId)
                listDao.updateList(
                    ShoppingListEntity(
                        id = event.listId,
                        status = ListStatus.COMPLETED,
                        createdAt = existing?.createdAt ?: System.currentTimeMillis(),
                        sentAt = existing?.sentAt,
                        completedAt = System.currentTimeMillis(),
                        plannedTotal = event.plannedTotal,
                    )
                )
            }
            else -> Unit
        }
    }
}
