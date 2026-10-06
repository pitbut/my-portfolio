import java.util.Properties
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

/**
 * Кладёт в APK PitSDK (sdk/pit.js) и встроенные приложения (apps/<id>/ → preinstalled/<id>.pitapp).
 */
abstract class PackPitAssets : DefaultTask() {
    @get:InputDirectory abstract val appsDir: DirectoryProperty
    @get:InputFile abstract val sdkFile: RegularFileProperty
    @get:OutputDirectory abstract val outputDir: DirectoryProperty

    @TaskAction
    fun pack() {
        val out = outputDir.get().asFile
        out.deleteRecursively()
        File(out, "pit").mkdirs()
        sdkFile.get().asFile.copyTo(File(out, "pit/pit.js"))
        val pre = File(out, "preinstalled").apply { mkdirs() }
        appsDir.get().asFile.listFiles { f -> File(f, "manifest.json").isFile }.orEmpty().sortedBy { it.name }.forEach { app ->
            ZipOutputStream(File(pre, "${app.name}.pitapp").outputStream()).use { zip ->
                app.walkTopDown().filter { it.isFile && !it.name.startsWith(".") }.sortedBy { it.path }.forEach { f ->
                    zip.putNextEntry(ZipEntry(f.relativeTo(app).invariantSeparatorsPath))
                    f.inputStream().use { it.copyTo(zip) }
                    zip.closeEntry()
                }
            }
        }
    }
}

val packPitAssets = tasks.register<PackPitAssets>("packPitAssets") {
    appsDir.set(layout.projectDirectory.dir("../../apps"))
    sdkFile.set(layout.projectDirectory.file("../../sdk/pit.js"))
    outputDir.set(layout.buildDirectory.dir("generated/pitAssets"))
}

android {
    namespace = "com.robutpit.pitbrowser"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.robutpit.pitbrowser"
        minSdk = 24
        targetSdk = 35
        versionCode = 5
        versionName = "1.4.0"
    }

    signingConfigs {
        // Ключ для публикации (IlovaBozor, RuStore): файл android/keystore.properties (в git не попадает)
        // или переменные окружения PIT_KEYSTORE, PIT_KEYSTORE_PASSWORD, PIT_KEY_ALIAS, PIT_KEY_PASSWORD (GitHub Secrets).
        val props = Properties().apply {
            rootProject.file("keystore.properties").takeIf { it.isFile }?.inputStream()?.use { load(it) }
        }
        fun secret(key: String, env: String): String? = props.getProperty(key) ?: System.getenv(env)
        val releaseStore = secret("storeFile", "PIT_KEYSTORE")
        if (releaseStore != null) {
            create("release") {
                storeFile = rootProject.file(releaseStore)
                storePassword = secret("storePassword", "PIT_KEYSTORE_PASSWORD")
                keyAlias = secret("keyAlias", "PIT_KEY_ALIAS")
                keyPassword = secret("keyPassword", "PIT_KEY_PASSWORD")
            }
        }
        // открытый тестовый ключ — см. keystore/README.md; для публикации нужен свой
        create("test") {
            storeFile = file("../keystore/pitbrowser-test.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("test")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            // есть ключ для публикации — подписываем им, иначе тестовым (см. keystore/README.md)
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("test")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

androidComponents {
    onVariants { variant ->
        variant.sources.assets?.addGeneratedSourceDirectory(packPitAssets, PackPitAssets::outputDir)
    }
}

dependencies {
    implementation("androidx.webkit:webkit:1.12.1")
    testImplementation("org.json:json:20250517")
    testImplementation("junit:junit:4.13.2")
}
