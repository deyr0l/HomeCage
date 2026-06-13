package com.homecage.kiosk.sync

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.CancellationSignal
import android.os.Looper
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

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
        val location = bestAvailableLocation(locationManager)
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

    private fun bestAvailableLocation(locationManager: LocationManager): Location? {
        val lastKnownLocation = bestLastKnownLocation(locationManager)
        if (lastKnownLocation != null && isFresh(lastKnownLocation)) {
            return lastKnownLocation
        }
        return currentLocation(locationManager) ?: lastKnownLocation
    }

    private fun isFresh(location: Location): Boolean =
        location.time > 0L && System.currentTimeMillis() - location.time <= FRESH_LOCATION_MAX_AGE_MS

    private fun bestLastKnownLocation(locationManager: LocationManager): Location? =
        locationProviders(locationManager).mapNotNull { provider ->
            runCatching { locationManager.getLastKnownLocation(provider) }.getOrNull()
        }.maxByOrNull { it.time }

    private fun currentLocation(locationManager: LocationManager): Location? {
        locationProviders(locationManager).forEach { provider ->
            requestCurrentLocation(locationManager, provider)?.let { return it }
        }
        return null
    }

    private fun requestCurrentLocation(locationManager: LocationManager, provider: String): Location? =
        runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                requestCurrentLocationApi30(locationManager, provider)
            } else {
                requestSingleUpdate(locationManager, provider)
            }
        }.getOrNull()

    private fun requestCurrentLocationApi30(locationManager: LocationManager, provider: String): Location? {
        val result = AtomicReference<Location?>()
        val latch = CountDownLatch(1)
        val cancellationSignal = CancellationSignal()
        locationManager.getCurrentLocation(provider, cancellationSignal, context.mainExecutor) { location ->
            result.set(location)
            latch.countDown()
        }
        if (!latch.await(CURRENT_LOCATION_TIMEOUT_MS, TimeUnit.MILLISECONDS)) {
            cancellationSignal.cancel()
        }
        return result.get()
    }

    @Suppress("DEPRECATION")
    private fun requestSingleUpdate(locationManager: LocationManager, provider: String): Location? {
        val result = AtomicReference<Location?>()
        val latch = CountDownLatch(1)
        val listener = LocationListener { location ->
            result.set(location)
            latch.countDown()
        }
        locationManager.requestSingleUpdate(provider, listener, Looper.getMainLooper())
        latch.await(CURRENT_LOCATION_TIMEOUT_MS, TimeUnit.MILLISECONDS)
        locationManager.removeUpdates(listener)
        return result.get()
    }

    private fun locationProviders(locationManager: LocationManager): List<String> =
        listOf(
            LocationManager.NETWORK_PROVIDER,
            LocationManager.GPS_PROVIDER,
            LocationManager.PASSIVE_PROVIDER
        ).filter { provider ->
            provider == LocationManager.PASSIVE_PROVIDER ||
                runCatching { locationManager.isProviderEnabled(provider) }.getOrDefault(false)
        }

    private companion object {
        const val STATUS_OK = "ok"
        const val STATUS_PERMISSION_DENIED = "permission_denied"
        const val STATUS_UNAVAILABLE = "unavailable"
        const val CURRENT_LOCATION_TIMEOUT_MS = 6_000L
        const val FRESH_LOCATION_MAX_AGE_MS = 5 * 60 * 1000L
    }
}
