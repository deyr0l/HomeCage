package com.homecage.kiosk.data

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.graphics.drawable.Drawable
import android.os.Build
import java.text.Collator
import java.util.Locale

data class LaunchableApp(
    val label: String,
    val packageName: String,
    val icon: Drawable,
    val isSystem: Boolean
)

class AppRepository(private val context: Context) {
    private val packageManager: PackageManager = context.packageManager

    fun getLaunchableApps(): List<LaunchableApp> {
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val resolveInfos = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.queryIntentActivities(
                intent,
                PackageManager.ResolveInfoFlags.of(0L)
            )
        } else {
            @Suppress("DEPRECATION")
            packageManager.queryIntentActivities(intent, 0)
        }

        val byPackage = linkedMapOf<String, LaunchableApp>()
        for (resolveInfo in resolveInfos) {
            val packageName = resolveInfo.activityInfo?.packageName ?: continue
            if (packageName == context.packageName) continue
            if (byPackage.containsKey(packageName)) continue

            val appInfo = runCatching {
                packageManager.getApplicationInfo(packageName, 0)
            }.getOrNull() ?: continue

            val systemFlags = ApplicationInfo.FLAG_SYSTEM or ApplicationInfo.FLAG_UPDATED_SYSTEM_APP
            byPackage[packageName] = LaunchableApp(
                label = resolveInfo.loadLabel(packageManager).toString(),
                packageName = packageName,
                icon = resolveInfo.loadIcon(packageManager),
                isSystem = (appInfo.flags and systemFlags) != 0
            )
        }

        val collator = Collator.getInstance(Locale.getDefault())
        return byPackage.values.sortedWith { first, second ->
            val labelResult = collator.compare(first.label, second.label)
            if (labelResult != 0) labelResult else collator.compare(first.packageName, second.packageName)
        }
    }
}
