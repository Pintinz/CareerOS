import java.util.Properties
import java.io.FileInputStream

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Phase 11 release signing (spec §42-43): reads a real upload keystore from key.properties if the
// operator has created one (see key.properties.example — this file is real, git-ignored, and
// never committed; DEPLOYMENT.md documents the exact keytool command to generate one). Falls back
// to debug signing when absent, so `flutter build apk/appbundle --release` still works out of the
// box in this environment (no real signing key exists here) without ever silently shipping a
// debug-signed build without the operator knowing — see the printed warning below.
val keystorePropertiesFile = rootProject.file("key.properties")
val keystoreProperties = Properties()
val hasReleaseSigning = keystorePropertiesFile.exists()
if (hasReleaseSigning) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
} else {
    logger.warn(
        "WARNING: android/key.properties not found — release builds will be signed with the " +
        "DEBUG key, which Google Play will reject. See key.properties.example and " +
        "DEPLOYMENT.md's 'Android release signing' section before submitting a real release."
    )
}

android {
    namespace = "com.careeros.careeros"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // flutter_local_notifications requires this (Java 8+ API desugaring for older API levels).
        isCoreLibraryDesugaringEnabled = true
    }

    defaultConfig {
        // Finalized (Phase 11 §68 analog) — matches iOS's PRODUCT_BUNDLE_IDENTIFIER exactly. Do
        // not change after the first real release; Google Play ties an app's identity to this.
        applicationId = "com.careeros.careeros"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                storeFile = file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
            }
        }
    }

    buildTypes {
        release {
            // Real upload-key signing when key.properties exists; debug-signed otherwise (dev
            // convenience only — never submit a debug-signed build to a store).
            signingConfig = if (hasReleaseSigning) signingConfigs.getByName("release") else signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}

flutter {
    source = "../.."
}
