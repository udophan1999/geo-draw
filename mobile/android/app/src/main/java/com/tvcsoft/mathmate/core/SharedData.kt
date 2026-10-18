package com.tvcsoft.mathmate.core

import android.content.Context
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * Data the web and iOS apps read too, bundled from shared/ (app/build.gradle.kts
 * `syncSharedData`): the symbol bar and the formula gallery. Change them there, never here.
 */
object SharedData {
    /** A symbol of the bar; one with a `template` (the roots) opens the formula editor on it. */
    @Serializable
    data class Symbol(val symbol: String, val name: String, val template: String? = null)

    @Serializable
    data class Template(
        val label: String,
        /** `#?` is an empty slot, `#@` takes the selection (MathLive's syntax on the web). */
        val latex: String,
    )

    @Serializable
    data class FormulaGroup(val id: String, val name: String, val wide: Boolean = false, val items: List<Template>)

    private val json = Json { ignoreUnknownKeys = true }

    var symbols: List<Symbol> = emptyList()
        private set
    var formulaGroups: List<FormulaGroup> = emptyList()
        private set

    fun load(context: Context) {
        symbols = read(context, "symbols.json")
        formulaGroups = read(context, "formula_templates.json")
    }

    private inline fun <reified T> read(context: Context, name: String): List<T> =
        context.assets.open(name).use { json.decodeFromString(it.readBytes().decodeToString()) }
}
