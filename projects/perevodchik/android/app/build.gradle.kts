import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Подпись релиза: данные берутся из android/keystore.properties (в git НЕ попадает)
val keyProps = Properties().apply {
    val f = rootProject.file("keystore.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    namespace = "com.robutpit.perevodchik"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.robutpit.perevodchik"
        minSdk = 24
        targetSdk = 35
        versionCode = 3
        versionName = "1.2"
    }

    signingConfigs {
        create("release") {
            if (keyProps.isNotEmpty()) {
                storeFile = rootProject.file(keyProps.getProperty("storeFile"))
                storePassword = keyProps.getProperty("storePassword")
                keyAlias = keyProps.getProperty("keyAlias")
                keyPassword = keyProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (keyProps.isNotEmpty()) signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    // Веб-интерфейс берём из папки сайта (projects/perevodchik), чтобы код был один
    sourceSets["main"].assets.srcDir(layout.buildDirectory.dir("webAssets"))
}

val copyWeb by tasks.registering(Copy::class) {
    from(rootProject.file("..")) {
        include("index.html", "icon.svg", "icon-192.png")
    }
    into(layout.buildDirectory.dir("webAssets/www"))
}
tasks.named("preBuild") { dependsOn(copyWeb) }

dependencies {
    implementation("androidx.webkit:webkit:1.12.1")
}
