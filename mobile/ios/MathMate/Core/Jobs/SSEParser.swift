import Foundation

/// One server-sent event of /api/jobs/{id}/events: `progress`, `delta`, `message`,
/// `conversation`, `figure_job`, `figure_skipped`, then `done` or `failed`.
struct JobEvent: Equatable, Sendable {
    let kind: String
    let data: String
}

/// Parses an SSE stream line by line: `event:` and `data:` fields, a blank line ends an
/// event, and lines starting with `:` (the server's keep-alives) are ignored.
struct SSEParser {
    private var kind = "message"
    private var data: [String] = []

    mutating func feed(_ line: String) -> JobEvent? {
        if line.isEmpty {
            defer { kind = "message"; data = [] }
            return data.isEmpty ? nil : JobEvent(kind: kind, data: data.joined(separator: "\n"))
        }
        if line.hasPrefix(":") { return nil }
        let field: Substring
        var value: Substring
        if let colon = line.firstIndex(of: ":") {
            field = line[..<colon]
            value = line[line.index(after: colon)...]
            if value.first == " " { value = value.dropFirst() }
        } else {
            field = Substring(line)
            value = ""
        }
        switch field {
        case "event": kind = String(value)
        case "data": data.append(String(value))
        default: break
        }
        return nil
    }
}
