package com.tvcsoft.mathmate.core.jobs

/**
 * One server-sent event of /api/jobs/{id}/events: `progress`, `delta`, `message`,
 * `conversation`, `figure_job`, `figure_skipped`, then `done` or `failed`.
 */
data class JobEvent(val kind: String, val data: String)

/**
 * Parses an SSE stream line by line: `event:` and `data:` fields, a blank line ends an event,
 * and lines starting with `:` (the server's keep-alives) are ignored.
 */
class SseParser {
    private var kind = "message"
    private val data = mutableListOf<String>()

    fun feed(line: String): JobEvent? {
        if (line.isEmpty()) {
            val event = if (data.isEmpty()) null else JobEvent(kind, data.joinToString("\n"))
            kind = "message"
            data.clear()
            return event
        }
        if (line.startsWith(":")) return null
        val colon = line.indexOf(':')
        val field = if (colon >= 0) line.substring(0, colon) else line
        var value = if (colon >= 0) line.substring(colon + 1) else ""
        if (value.startsWith(" ")) value = value.substring(1)
        when (field) {
            "event" -> kind = value
            "data" -> data.add(value)
        }
        return null
    }
}
