import Foundation
import SwiftUI

/// One server-sent event of /api/jobs/{id}/events.
struct JobEvent: Sendable, Equatable {
    let kind: String
    let data: String
}

/// Parses an SSE byte stream: `event:` and `data:` lines, a blank line ends an event, and
/// lines starting with `:` are keep-alives.
struct SSEParser {
    private var kind = "message"
    private var data: [String] = []

    mutating func feed(_ line: String) -> JobEvent? {
        if line.isEmpty {
            defer { kind = "message"; data = [] }
            return data.isEmpty ? nil : JobEvent(kind: kind, data: data.joined(separator: "\n"))
        }
        if line.hasPrefix(":") { return nil }
        let (field, value) = line.firstIndex(of: ":").map {
            (String(line[..<$0]), String(line[line.index(after: $0)...]).trimmingPrefix(" "))
        } ?? (line, "")
        switch field {
        case "event": kind = String(value)
        case "data": data.append(String(value))
        default: break
        }
        return nil
    }
}

/// The API as the app calls it: `X-Client: ios`, the guest id in `X-Guest-Id`.
actor SpikeAPI {
    let base: URL
    private(set) var guestID: String?

    init(base: URL) { self.base = base }

    private func request(_ path: String, method: String = "GET") -> URLRequest {
        var request = URLRequest(url: base.appending(path: path))
        request.httpMethod = method
        request.setValue("ios", forHTTPHeaderField: "X-Client")
        if let guestID { request.setValue(guestID, forHTTPHeaderField: "X-Guest-Id") }
        return request
    }

    private func remember(_ response: URLResponse) {
        if let id = (response as? HTTPURLResponse)?.value(forHTTPHeaderField: "X-Guest-Id") { guestID = id }
    }

    /// The first call gets a guest id back in `X-Guest-Id`.
    func me() async throws {
        let (_, response) = try await URLSession.shared.data(for: request("api/auth/me"))
        remember(response)
    }

    /// Starts a tutor turn; returns the job id.
    func send(_ text: String) async throws -> String {
        var request = request("api/messages", method: "POST")
        let boundary = "spike-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.httpBody = Data("--\(boundary)\r\nContent-Disposition: form-data; name=\"text\"\r\n\r\n\(text)\r\n--\(boundary)--\r\n".utf8)
        let (data, response) = try await URLSession.shared.data(for: request)
        remember(response)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard let job = json?["job_id"] as? String else {
            throw URLError(.badServerResponse, userInfo: [NSLocalizedDescriptionKey: String(decoding: data, as: UTF8.self)])
        }
        return job
    }

    func events(_ job: String) -> AsyncThrowingStream<JobEvent, Error> {
        let request = request("api/jobs/\(job)/events")
        return AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let (bytes, _) = try await URLSession.shared.bytes(for: request)
                    var parser = SSEParser()
                    // `lines` drops empty lines, so split on "\n" by hand to see event ends.
                    var line = Data()
                    for try await byte in bytes {
                        if byte == UInt8(ascii: "\n") {
                            if let event = parser.feed(String(decoding: line, as: UTF8.self)) {
                                continuation.yield(event)
                            }
                            line.removeAll(keepingCapacity: true)
                        } else {
                            line.append(byte)
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}

@MainActor
@Observable
final class StreamingModel {
    var log: [String] = []
    var reply = ""
    var status = "Chưa bắt đầu"
    private let api: SpikeAPI

    init(base: URL) { api = SpikeAPI(base: base) }

    func run(_ text: String) async {
        do {
            status = "Đang lấy guest id…"
            try await api.me()
            log.append("guest id: \(await api.guestID ?? "—")")
            let job = try await api.send(text)
            log.append("job: \(job)")
            status = "Đang nhận…"
            var deltas = 0
            for try await event in await api.events(job) {
                switch event.kind {
                case "delta":
                    deltas += 1
                    if let json = try? JSONSerialization.jsonObject(with: Data(event.data.utf8)) as? [String: Any],
                       let piece = json["text"] as? String { reply += piece }
                case "message", "conversation", "progress":
                    log.append(event.kind)
                default:
                    log.append(event.kind)
                }
            }
            log.append("delta × \(deltas)")
            status = "Xong"
        } catch {
            status = "Lỗi: \(error.localizedDescription)"
        }
    }
}

struct StreamingScreen: View {
    @State private var model: StreamingModel
    let prompt: String

    init(base: URL, prompt: String) {
        _model = State(initialValue: StreamingModel(base: base))
        self.prompt = prompt
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(model.status).font(.headline).accessibilityIdentifier("status")
                MathText(text: model.reply)
                Divider()
                Text(model.log.joined(separator: "\n"))
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("log")
            }
            .padding(16)
        }
        .task { await model.run(prompt) }
    }
}
