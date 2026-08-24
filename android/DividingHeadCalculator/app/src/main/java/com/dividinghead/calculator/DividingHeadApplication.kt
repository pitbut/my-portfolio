package com.dividinghead.calculator

import android.app.Application
import com.dividinghead.calculator.data.HistoryRepository
import com.dividinghead.calculator.data.PresetRepository
import com.dividinghead.calculator.data.datastore.SettingsRepository
import com.dividinghead.calculator.data.db.AppDatabase

/** Simple manual dependency container — no DI framework needed for an app this size. */
class DividingHeadApplication : Application() {

    lateinit var database: AppDatabase
        private set
    lateinit var settingsRepository: SettingsRepository
        private set
    lateinit var presetRepository: PresetRepository
        private set
    lateinit var historyRepository: HistoryRepository
        private set

    override fun onCreate() {
        super.onCreate()
        database = AppDatabase.getInstance(this)
        settingsRepository = SettingsRepository(this)
        presetRepository = PresetRepository(database.presetDao())
        historyRepository = HistoryRepository(database.historyDao())
    }
}
