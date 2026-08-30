package com.robutpit.zamri

import android.app.Application
import com.robutpit.zamri.data.GameRepository
import com.robutpit.zamri.data.SettingsStore
import com.robutpit.zamri.data.db.ZamriDatabase

/** Holds app-wide singletons (DB, repository, settings) without a DI framework. */
class ZamriApp : Application() {

    val database: ZamriDatabase by lazy { ZamriDatabase.build(this) }
    val settingsStore: SettingsStore by lazy { SettingsStore(this) }
    val repository: GameRepository by lazy {
        GameRepository(applicationContext, database.violationDao())
    }
}
