package com.dividinghead.calculator.data

import com.dividinghead.calculator.data.db.HistoryDao
import com.dividinghead.calculator.data.db.HistoryEntity
import kotlinx.coroutines.flow.Flow

class HistoryRepository(private val historyDao: HistoryDao) {
    val history: Flow<List<HistoryEntity>> = historyDao.observeAll()

    suspend fun record(mode: String, summary: String, details: String) {
        historyDao.insert(
            HistoryEntity(
                timestamp = System.currentTimeMillis(),
                mode = mode,
                summary = summary,
                details = details
            )
        )
    }

    suspend fun delete(entity: HistoryEntity) = historyDao.delete(entity)

    suspend fun clear() = historyDao.clear()
}
