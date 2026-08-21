package ru.rynok.app

import android.app.Application
import ru.rynok.app.data.local.AppDatabase
import ru.rynok.app.data.remote.RelayClient
import ru.rynok.app.data.repository.ChatRepository
import ru.rynok.app.data.repository.ShoppingRepository

/**
 * Простой ручной "DI-контейнер": никаких фреймворков, чтобы не раздувать
 * зависимости учебного проекта. Все синглтоны собираются здесь один раз
 * и переиспользуются экранами через LocalContext.applicationContext.
 */
class RynokApp : Application() {

    lateinit var database: AppDatabase
        private set

    lateinit var prefs: Prefs
        private set

    lateinit var relayClient: RelayClient
        private set

    lateinit var shoppingRepository: ShoppingRepository
        private set

    lateinit var chatRepository: ChatRepository
        private set

    override fun onCreate() {
        super.onCreate()

        database = AppDatabase.build(this)
        prefs = Prefs(this)
        relayClient = RelayClient(prefs)

        shoppingRepository = ShoppingRepository(
            listDao = database.shoppingListDao(),
            relayClient = relayClient,
            prefs = prefs,
        )
        chatRepository = ChatRepository(
            chatDao = database.chatDao(),
            relayClient = relayClient,
            prefs = prefs,
            mediaDir = filesDir.resolve("chat_media").apply { mkdirs() },
        )
    }
}
