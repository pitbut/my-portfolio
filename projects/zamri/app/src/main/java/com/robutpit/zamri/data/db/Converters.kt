package com.robutpit.zamri.data.db

import androidx.room.TypeConverter

class Converters {
    @TypeConverter
    fun fromSide(side: ViolationSide): String = side.name

    @TypeConverter
    fun toSide(value: String): ViolationSide = ViolationSide.valueOf(value)
}
