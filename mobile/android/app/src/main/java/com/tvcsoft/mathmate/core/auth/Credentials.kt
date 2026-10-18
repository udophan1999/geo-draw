package com.tvcsoft.mathmate.core.auth

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Where the session token and the guest id live between launches. */
interface CredentialStore {
    var token: String?
    var guestId: String?
}

/**
 * The app's private preferences, with the token encrypted by a key that never leaves the
 * Android Keystore (the iOS app keeps both in the Keychain). Backups exclude these preferences
 * (data_extraction_rules.xml), so a token never reaches another device.
 */
class KeystoreCredentials(context: Context) : CredentialStore {
    private val prefs: SharedPreferences = context.getSharedPreferences("credentials", Context.MODE_PRIVATE)

    override var token: String?
        get() = prefs.getString(TOKEN, null)?.let(::decrypt)
        set(value) = prefs.edit().apply { if (value == null) remove(TOKEN) else putString(TOKEN, encrypt(value)) }.apply()

    override var guestId: String?
        get() = prefs.getString(GUEST, null)
        set(value) = prefs.edit().apply { if (value == null) remove(GUEST) else putString(GUEST, value) }.apply()

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (store.getEntry(ALIAS, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .build(),
        )
        return generator.generateKey()
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION).apply { init(Cipher.ENCRYPT_MODE, key()) }
        val sealed = cipher.iv + cipher.doFinal(value.toByteArray())
        return Base64.encodeToString(sealed, Base64.NO_WRAP)
    }

    /** null when the value cannot be read (a key lost with a restore): signed out, not a crash. */
    private fun decrypt(value: String): String? = try {
        val sealed = Base64.decode(value, Base64.NO_WRAP)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, sealed, 0, IV_LENGTH))
        String(cipher.doFinal(sealed, IV_LENGTH, sealed.size - IV_LENGTH))
    } catch (_: Exception) {
        null
    }

    private companion object {
        const val TOKEN = "token"
        const val GUEST = "guest-id"
        const val KEYSTORE = "AndroidKeyStore"
        const val ALIAS = "mathmate-credentials"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_LENGTH = 12
    }
}

/** For tests and UI tests (`-e uiTesting true`): nothing is kept after the process ends. */
class MemoryCredentials(token: String? = null, guestId: String? = null) : CredentialStore {
    @Volatile override var token: String? = token
    @Volatile override var guestId: String? = guestId
}
