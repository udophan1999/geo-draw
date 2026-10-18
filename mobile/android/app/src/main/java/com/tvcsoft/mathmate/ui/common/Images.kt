package com.tvcsoft.mathmate.ui.common

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageDecoder
import android.net.Uri
import android.os.Build
import android.util.LruCache
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import com.tvcsoft.mathmate.core.api.ApiClient
import com.tvcsoft.mathmate.core.api.ApiError
import com.tvcsoft.mathmate.core.chat.PreparedImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

/**
 * Images the API serves to their owner only, cached by their versioned URL (`?v=` changes when a
 * drawing is rendered again). An image library cannot add the session, so they load here.
 */
object ImageStore {
    private val cache = object : LruCache<String, Bitmap>(48 * 1024 * 1024) {
        override fun sizeOf(key: String, value: Bitmap) = value.allocationByteCount
    }

    fun cached(path: String): Bitmap? = cache.get(path)

    suspend fun image(path: String, api: ApiClient): Bitmap? {
        cache.get(path)?.let { return it }
        val data = try {
            api.file(path)
        } catch (_: ApiError) {
            return null
        }
        val bitmap = withContext(Dispatchers.Default) { BitmapFactory.decodeByteArray(data, 0, data.size) } ?: return null
        cache.put(path, bitmap)
        return bitmap
    }
}

/** An image of the API, with a spinner while it loads. */
@Composable
fun AuthImage(path: String, api: ApiClient, modifier: Modifier = Modifier, contentScale: ContentScale = ContentScale.Fit) {
    var image by remember(path) { mutableStateOf(ImageStore.cached(path)) }
    var failed by remember(path) { mutableStateOf(false) }
    LaunchedEffect(path) {
        if (image == null) {
            image = ImageStore.image(path, api)
            failed = image == null
        }
    }
    val current = image
    when {
        current != null -> Image(current.asImageBitmap(), contentDescription = "Ảnh", modifier = modifier, contentScale = contentScale)
        failed -> Text("Không tải được ảnh", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = modifier.padding(12.dp))
        else -> Box(modifier.fillMaxWidth().heightIn(min = 120.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
    }
}

/**
 * Photos sent to the tutor: at most 2048 px on the long side, JPEG (a phone photo can be 10 MB;
 * the server takes up to 20 MB, and OCR needs no more). The iOS app's ImagePrep.
 */
object ImagePrep {
    private const val LONG_SIDE = 2048

    suspend fun prepare(context: Context, uri: Uri): PreparedImage? = withContext(Dispatchers.IO) {
        try {
            val bitmap = decode(context, uri) ?: return@withContext null
            prepare(bitmap)
        } catch (_: Exception) {
            null
        }
    }

    fun prepare(bitmap: Bitmap): PreparedImage {
        val long = maxOf(bitmap.width, bitmap.height)
        val scaled = if (long > LONG_SIDE) {
            val scale = LONG_SIDE.toFloat() / long
            Bitmap.createScaledBitmap(bitmap, (bitmap.width * scale).toInt(), (bitmap.height * scale).toInt(), true)
        } else {
            bitmap
        }
        val out = ByteArrayOutputStream()
        scaled.compress(Bitmap.CompressFormat.JPEG, 80, out)
        return PreparedImage(out.toByteArray(), scaled.width, scaled.height)
    }

    /** Decodes a photo upright (EXIF rotation applied) and already near the target size. */
    private fun decode(context: Context, uri: Uri): Bitmap? =
        if (Build.VERSION.SDK_INT >= 28) {
            ImageDecoder.decodeBitmap(ImageDecoder.createSource(context.contentResolver, uri)) { decoder, info, _ ->
                val long = maxOf(info.size.width, info.size.height)
                if (long > LONG_SIDE) {
                    val scale = LONG_SIDE.toFloat() / long
                    decoder.setTargetSize((info.size.width * scale).toInt(), (info.size.height * scale).toInt())
                }
                decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            }
        } else {
            context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) }
        }

    fun preview(image: PreparedImage): Bitmap? = BitmapFactory.decodeByteArray(image.jpeg, 0, image.jpeg.size)
}

/**
 * A coroutine scope for UI work that stays on the main thread after a request resumes (under
 * the Compose test framework, a plain rememberCoroutineScope does not), so callbacks may touch
 * views and navigate.
 */
@Composable
fun rememberUiScope() = androidx.compose.runtime.rememberCoroutineScope { Dispatchers.Main.immediate }
