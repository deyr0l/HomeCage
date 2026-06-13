package com.homecage.kiosk.sync

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager

data class DeviceLocationReport(
    val requestId: Long,
    val status: String,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val accuracyMeters: Float? = null,
    val provider: String? = null,
    val capturedAtMillis: Long? = null
)

class DeviceLocationProvider(private val context: Context) {
    fun reportForRequest(requestId: Long): DeviceLocationReport {
        if (!hasLocationPermission()) {
            return DeviceLocationReport(requestId = requestId, status = STATUS_PERMISSION_DENIED)
        }

        val locationManager = context.getSystemService(LocationManager::class.java)
            ?: return DeviceLocationReport(requestId = requestId, status = STATUS_UNAVAILABLE)
        val location = bestLastKnownLocation(locationManager)
            ?: return DeviceLocationReport(requestId = requestId, status = STATUS_UNAVAILABLE)

        return DeviceLocationReport(
            requestId = requestId,
            status = STATUS_OK,
            latitude = location.latitude,
            longitude = location.longitude,
            accuracyMeters = location.accuracy.takeIf { location.hasAccuracy() },
            provider = location.provider,
            capturedAtMillis = location.time.takeIf { it > 0L }
        )
    }

    private fun hasLocationPermission(): Boolean =
        context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            context.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    private fun bestLastKnownLocation(locationManager: LocationManager): Location? =
        listOf(
            LocationManager.GPS_PROVIDER,
            LocationManager.NETWORK_PROVIDER,
            LocationManager.PASSIVE_PROVIDER
        ).mapNotNull { provider ->
            runCatching { locationManager.getLastKnownLocation(provider) }.getOrNull()
        }.maxByOrNull { it.time }

    private companion object {
        const val STATUS_OK = "ok"
        const val STATUS_PERMISSION_DENIED = "permission_denied"
        const val STATUS_UNAVAILABLE = "unavailable"
    }
}
