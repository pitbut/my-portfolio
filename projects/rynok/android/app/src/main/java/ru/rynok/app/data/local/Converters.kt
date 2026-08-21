package ru.rynok.app.data.local

import androidx.room.TypeConverter

class Converters {
    @TypeConverter
    fun listStatusToString(value: ListStatus): String = value.name

    @TypeConverter
    fun stringToListStatus(value: String): ListStatus = ListStatus.valueOf(value)

    @TypeConverter
    fun chatTypeToString(value: ChatMessageType): String = value.name

    @TypeConverter
    fun stringToChatType(value: String): ChatMessageType = ChatMessageType.valueOf(value)
}
