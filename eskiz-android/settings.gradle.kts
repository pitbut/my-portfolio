pluginManagement {
    repositories {
        google()
        // Зеркало Maven Central (основной сервер иногда отвечает 429).
        maven("https://maven-central.storage-download.googleapis.com/maven2/")
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        // Зеркало Maven Central (основной сервер иногда отвечает 429).
        maven("https://maven-central.storage-download.googleapis.com/maven2/")
        mavenCentral()
    }
}
rootProject.name = "Eskiz"
include(":app")
