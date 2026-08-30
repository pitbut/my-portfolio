package com.robutpit.zamri.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters

@Database(entities = [ViolationEntity::class], version = 1, exportSchema = false)
@TypeConverters(Converters::class)
abstract class ZamriDatabase : RoomDatabase() {

    abstract fun violationDao(): ViolationDao

    companion object {
        fun build(context: Context): ZamriDatabase =
            Room.databaseBuilder(
                context.applicationContext,
                ZamriDatabase::class.java,
                "zamri.db"
            ).build()
    }
}
