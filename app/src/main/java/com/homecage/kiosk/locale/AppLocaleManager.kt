package com.homecage.kiosk.locale

import android.content.Context
import android.content.res.Configuration
import android.os.Build
import android.os.LocaleList
import java.util.Locale

data class AppLanguage(
    val tag: String,
    val label: String
)

object AppLocaleManager {
    const val SYSTEM_LANGUAGE_TAG = "system"
    const val KEY_APP_LANGUAGE = "app_language"

    val supportedLanguages: List<AppLanguage> = listOf(
        AppLanguage(SYSTEM_LANGUAGE_TAG, "System"),
        AppLanguage("en", "English"),
        AppLanguage("ru", "Русский"),
        AppLanguage("es", "Español"),
        AppLanguage("zh-CN", "简体中文"),
        AppLanguage("ja", "日本語")
    )

    fun getSelectedLanguageTag(context: Context): String {
        val tag = preferences(context).getString(KEY_APP_LANGUAGE, SYSTEM_LANGUAGE_TAG).orEmpty()
        return supportedLanguages.firstOrNull { it.tag == tag }?.tag ?: SYSTEM_LANGUAGE_TAG
    }

    fun setSelectedLanguageTag(context: Context, tag: String) {
        val normalizedTag = supportedLanguages.firstOrNull { it.tag == tag }?.tag ?: SYSTEM_LANGUAGE_TAG
        preferences(context).edit()
            .putString(KEY_APP_LANGUAGE, normalizedTag)
            .apply()
    }

    fun wrap(context: Context): Context {
        val selectedTag = getSelectedLanguageTag(context)
        if (selectedTag == SYSTEM_LANGUAGE_TAG) {
            Locale.setDefault(currentConfigurationLocale(context))
            return context
        }

        val locale = Locale.forLanguageTag(selectedTag)
        Locale.setDefault(locale)

        val configuration = Configuration(context.resources.configuration)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            configuration.setLocales(LocaleList(locale))
        } else {
            @Suppress("DEPRECATION")
            configuration.locale = locale
        }
        return context.createConfigurationContext(configuration)
    }

    private fun currentConfigurationLocale(context: Context): Locale =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            context.resources.configuration.locales[0]
        } else {
            @Suppress("DEPRECATION")
            context.resources.configuration.locale
        }

    private fun preferences(context: Context) =
        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    private const val PREFERENCES_NAME = "kid_kiosk_preferences"
}
