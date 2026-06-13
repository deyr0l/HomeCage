import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val releaseKeystorePropertiesFile = rootProject.file("keystore.properties")
val releaseKeystoreProperties = Properties().apply {
    if (releaseKeystorePropertiesFile.isFile) {
        releaseKeystorePropertiesFile.inputStream().use { load(it) }
    }
}
val releaseTasks = setOf("assembleRelease", "bundleRelease", "packageRelease")

android {
    namespace = "com.homecage.kiosk"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.homecage.kiosk"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    if (releaseKeystorePropertiesFile.isFile) {
        signingConfigs {
            create("release") {
                storeFile = rootProject.file(releaseKeystoreProperties.getProperty("storeFile"))
                storePassword = releaseKeystoreProperties.getProperty("storePassword")
                keyAlias = releaseKeystoreProperties.getProperty("keyAlias")
                keyPassword = releaseKeystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            if (releaseKeystorePropertiesFile.isFile) {
                signingConfig = signingConfigs.getByName("release")
            }
            isDebuggable = false
            isMinifyEnabled = false
        }
    }
}

kotlin {
    jvmToolchain(17)
}

tasks.matching { task -> task.name in releaseTasks }.configureEach {
    doFirst {
        check(releaseKeystorePropertiesFile.isFile) {
            "Release keystore is not configured. Create keystore.properties from keystore.properties.example, then run assembleRelease again."
        }
    }
}
