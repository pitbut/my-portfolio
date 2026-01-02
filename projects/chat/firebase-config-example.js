// ============================================
// ПРИМЕР FIREBASE КОНФИГУРАЦИИ
// ============================================
// Скопируйте эти строки из Firebase Console
// и вставьте в index.html на место "YOUR_API_KEY_HERE" и т.д.

const firebaseConfig = {
    apiKey: "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxx",
    authDomain: "your-project-id.firebaseapp.com",
    databaseURL: "https://your-project-id-default-rtdb.firebaseio.com",
    projectId: "your-project-id",
    storageBucket: "your-project-id.appspot.com",
    messagingSenderId: "123456789012",
    appId: "1:123456789012:web:xxxxxxxxxxxxxxxxxxxx"
};

// ============================================
// КАК ПОЛУЧИТЬ СВОЮ КОНФИГУРАЦИЮ:
// ============================================
// 1. Откройте: https://console.firebase.google.com/
// 2. Выберите ваш проект
// 3. ⚙️ Project Settings → Your apps
// 4. Нажмите на иконку </> (Web)
// 5. Скопируйте firebaseConfig
// 6. Вставьте в index.html вместо "YOUR_API_KEY_HERE"

// ============================================
// РЕГИОНЫ REALTIME DATABASE:
// ============================================
// us-central1         - США (Айова)
// europe-west1        - Бельгия
// asia-southeast1     - Сингапур
// 
// Выберите ближайший к вашим пользователям!

// ============================================
// БАЗОВЫЕ ПРАВИЛА БЕЗОПАСНОСТИ:
// ============================================
// Вставьте это в Firebase Console → Realtime Database → Rules

{
  "rules": {
    "messages": {
      ".read": true,
      ".write": true,
      "$messageId": {
        ".validate": "newData.hasChildren(['author', 'text', 'timestamp'])"
      }
    },
    "users": {
      ".read": true,
      "$userName": {
        ".write": "!data.exists() || data.child('name').val() == $userName",
        ".validate": "newData.hasChildren(['name', 'joinedAt', 'lastActive'])"
      }
    }
  }
}

// ============================================
// СТРУКТУРА ДАННЫХ В FIREBASE:
// ============================================

// messages/
//   ├── -NxYz123456 {
//   │     author: "Pit",
//   │     text: "Привет всем!",
//   │     timestamp: 1704201234567,
//   │     isSystem: false
//   │   }
//   └── -NxYz789012 {
//         author: "Система",
//         text: "Alex присоединился к чату",
//         timestamp: 1704201234890,
//         isSystem: true
//       }

// users/
//   ├── Pit {
//   │     name: "Pit",
//   │     joinedAt: 1704201234567,
//   │     lastActive: 1704201245678
//   │   }
//   └── Alex {
//         name: "Alex",
//         joinedAt: 1704201234890,
//         lastActive: 1704201256789
//       }

// ============================================
// ПОЛЕЗНЫЕ КОМАНДЫ:
// ============================================

// Проверить подключение к Firebase (в Console браузера):
// firebase.database().ref('.info/connected').on('value', snap => console.log(snap.val()));

// Посмотреть все сообщения:
// firebase.database().ref('messages').once('value', snap => console.log(snap.val()));

// Посмотреть всех пользователей:
// firebase.database().ref('users').once('value', snap => console.log(snap.val()));

// Очистить все сообщения:
// firebase.database().ref('messages').remove();

// Очистить всех пользователей:
// firebase.database().ref('users').remove();

// ============================================
// ЛИМИТЫ БЕСПЛАТНОГО ПЛАНА FIREBASE:
// ============================================
// ✅ 1 GB хранилища
// ✅ 10 GB/месяц трафика
// ✅ 100 одновременных подключений
// ✅ Достаточно для сотен активных пользователей!

// Проверить использование:
// Firebase Console → Usage and billing
