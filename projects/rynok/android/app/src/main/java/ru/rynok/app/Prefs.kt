package ru.rynok.app

import android.content.Context

enum class FamilyRole(val wireValue: String) {
    WIFE("wife"),
    HUSBAND("husband");

    companion object {
        fun fromWire(value: String?): FamilyRole? = entries.firstOrNull { it.wireValue == value }
    }
}

/**
 * Настройки семьи хранятся только локально на устройстве: id семьи, роль
 * этого телефона и код приглашения. Сервер этих данных не хранит.
 */
class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("rynok_prefs", Context.MODE_PRIVATE)

    var familyId: String?
        get() = sp.getString(KEY_FAMILY_ID, null)
        set(value) = sp.edit().putString(KEY_FAMILY_ID, value).apply()

    var role: FamilyRole?
        get() = FamilyRole.fromWire(sp.getString(KEY_ROLE, null))
        set(value) = sp.edit().putString(KEY_ROLE, value?.wireValue).apply()

    var familyCode: String?
        get() = sp.getString(KEY_FAMILY_CODE, null)
        set(value) = sp.edit().putString(KEY_FAMILY_CODE, value).apply()

    val isFamilyConfigured: Boolean
        get() = familyId != null && role != null

    fun clearFamily() {
        sp.edit().remove(KEY_FAMILY_ID).remove(KEY_ROLE).remove(KEY_FAMILY_CODE).apply()
    }

    companion object {
        private const val KEY_FAMILY_ID = "family_id"
        private const val KEY_ROLE = "role"
        private const val KEY_FAMILY_CODE = "family_code"
    }
}
