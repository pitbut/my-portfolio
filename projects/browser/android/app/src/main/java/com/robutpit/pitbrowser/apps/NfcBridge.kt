package com.robutpit.pitbrowser.apps

import android.app.Activity
import android.content.Intent
import android.nfc.NdefMessage
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.Ndef
import android.nfc.tech.NdefFormatable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import org.json.JSONArray
import org.json.JSONObject

/**
 * NFC для PitSDK: чтение меток (UID, тип, NDEF-записи) и запись на них.
 * Работает, только пока приложение на экране и подписано на метки (или ждёт записи);
 * в это время метки не уходят другим приложениям телефона.
 */
class NfcBridge(
    private val activity: Activity,
    private val emit: (event: String, data: JSONObject) -> Unit,
) {
    class NfcException(message: String) : Exception(message)

    private val adapter: NfcAdapter? = NfcAdapter.getDefaultAdapter(activity)
    private val main = Handler(Looper.getMainLooper())

    private var listening = false
    private var resumed = true
    private var readerOn = false

    private class PendingWrite(val message: ByteArray, val done: (Result<JSONObject>) -> Unit, val timeout: Runnable)
    private var pending: PendingWrite? = null

    fun status() = JSONObject().put("supported", adapter != null).put("enabled", adapter?.isEnabled == true)

    private fun requireReady(): NfcAdapter {
        val a = adapter ?: throw NfcException("в этом телефоне нет NFC")
        if (!a.isEnabled) throw NfcException("NFC выключен — включите его в настройках (pit.nfc.openSettings())")
        return a
    }

    fun listen(enable: Boolean) {
        if (enable) requireReady()
        listening = enable
        update()
    }

    /** Записать на следующую приложенную метку. records — массив записей (см. NdefCodec). */
    fun write(records: JSONArray, timeoutMs: Long, done: (Result<JSONObject>) -> Unit) {
        requireReady()
        val bytes = NdefCodec.encode(records)
        runCatching { NdefMessage(bytes) }.getOrElse { throw NfcException("неверные данные для записи") }
        cancelWrite()
        val timeout = Runnable { finishWrite(Result.failure(NfcException("время вышло — метку не приложили"))) }
        pending = PendingWrite(bytes, done, timeout)
        main.postDelayed(timeout, timeoutMs.coerceIn(3_000, 120_000))
        update()
    }

    fun cancelWrite() = finishWrite(Result.failure(NfcException("запись отменена")))

    private fun finishWrite(r: Result<JSONObject>) {
        val p = pending ?: return
        pending = null
        main.removeCallbacks(p.timeout)
        p.done(r)
        update()
    }

    fun openSettings() {
        runCatching { activity.startActivity(Intent(Settings.ACTION_NFC_SETTINGS)) }
            .recoverCatching { activity.startActivity(Intent(Settings.ACTION_WIRELESS_SETTINGS)) }
    }

    fun resume() { resumed = true; update() }
    fun pause() { resumed = false; update() }

    fun release() {
        listening = false
        cancelWrite()
        update()
    }

    /** Режим чтения включён, только когда он реально нужен. */
    private fun update() {
        val a = adapter ?: return
        val want = resumed && (listening || pending != null) && a.isEnabled
        if (want == readerOn) return
        runCatching {
            if (want) {
                val flags = NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B or
                    NfcAdapter.FLAG_READER_NFC_F or NfcAdapter.FLAG_READER_NFC_V
                a.enableReaderMode(activity, ::onTag, flags, Bundle().apply { putInt(NfcAdapter.EXTRA_READER_PRESENCE_CHECK_DELAY, 250) })
            } else {
                a.disableReaderMode(activity)
            }
            readerOn = want
        }
    }

    /** Вызывается в фоновом потоке NFC. */
    private fun onTag(tag: Tag) {
        val p = pending
        if (p != null) {
            val r = runCatching {
                try { writeTag(tag, p.message) } catch (e: java.io.IOException) {
                    throw NfcException("метку убрали слишком рано — держите телефон у метки до конца записи")
                } catch (e: android.nfc.FormatException) {
                    throw NfcException("не удалось подготовить метку к записи")
                }
            }
            main.post { if (pending === p) finishWrite(r) }
            return
        }
        val info = runCatching { describe(tag) }.getOrElse { JSONObject().put("id", NdefCodec.formatId(tag.id)).put("error", it.message) }
        main.post { if (listening) emit("nfc:tag", info) }
    }

    private fun describe(tag: Tag): JSONObject {
        val o = JSONObject()
            .put("id", NdefCodec.formatId(tag.id))
            .put("techs", JSONArray(tag.techList.map { it.substringAfterLast('.') }))
        val ndef = Ndef.get(tag)
        if (ndef != null) {
            o.put("ndef", true).put("type", ndef.type).put("maxSize", ndef.maxSize).put("writable", ndef.isWritable)
            val msg = ndef.cachedNdefMessage
            o.put("records", if (msg != null) NdefCodec.decode(msg.toByteArray()) else JSONArray())
        } else {
            // пустая заводская метка тоже годится для записи
            o.put("ndef", false).put("writable", NdefFormatable.get(tag) != null).put("records", JSONArray())
        }
        return o
    }

    private fun writeTag(tag: Tag, bytes: ByteArray): JSONObject {
        val message = NdefMessage(bytes)
        val ndef = Ndef.get(tag)
        if (ndef != null) {
            ndef.use {
                it.connect()
                if (!it.isWritable) throw NfcException("метка защищена от записи")
                if (bytes.size > it.maxSize) throw NfcException("данные не помещаются: ${bytes.size} байт, на метке ${it.maxSize}")
                it.writeNdefMessage(message)
            }
        } else {
            val f = NdefFormatable.get(tag) ?: throw NfcException("эта метка не поддерживает запись NDEF")
            f.use { it.connect(); it.format(message) }
        }
        return JSONObject().put("id", NdefCodec.formatId(tag.id)).put("bytes", bytes.size)
    }
}
