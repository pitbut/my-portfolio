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
        versionCode = 1
        versionName = "1.0.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            // Для публикации подпишите своим ключом (см. README). Без ключа — отладочной подписью,
            // чтобы APK можно было сразу установить на телефон.
            signingConfig = signingConfigs.getByName("debug")
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
