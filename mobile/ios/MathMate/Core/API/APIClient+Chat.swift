import Foundation

/// What the buttons ask the tutor for (api/routers/messages.py `action`).
enum TutorAction: String, Sendable { case ask, deeper, solution, hint }

/// A started turn: the conversation (new or existing) and the job to follow.
struct StartedTurn: Decodable, Sendable {
    let conversation: Conversation
    let jobId: String
}

extension APIClient {
    /// A message to the tutor (POST /api/messages, multipart). `image` is JPEG data.
    func sendMessage(text: String, conversationId: String?, image: Data?, action: TutorAction) async throws -> StartedTurn {
        var form = MultipartForm()
        form.add("text", text)
        if let conversationId { form.add("conversation_id", conversationId) }
        if action != .ask { form.add("action", action.rawValue) }
        if let image { form.add("image", filename: "de-bai.jpg", type: "image/jpeg", data: image) }
        var request = request("messages", method: "POST")
        request.setValue(form.contentType, forHTTPHeaderField: "Content-Type")
        request.httpBody = form.body
        request.timeoutInterval = 120  // a photo upload on a slow network
        return try JSONDecoder.api.decode(StartedTurn.self, from: try await send(request))
    }

    /// Edit the student's last message; the tutor answers it again (one AI turn).
    func editMessage(_ id: String, text: String) async throws -> StartedTurn {
        struct Edit: Encodable { let text: String }
        return try await send("messages/\(id)", method: "PATCH", json: Edit(text: text))
    }

    /// Draw the figure (empty text) or refine it with a request; returns the job id.
    func drawFigure(_ conversationId: String, text: String = "") async throws -> String {
        struct Figure: Encodable { let text: String }
        struct Job: Decodable { let jobId: String }
        let job: Job = try await send("conversations/\(conversationId)/figure", method: "POST", json: Figure(text: text))
        return job.jobId
    }

    /// A file the API serves at an absolute path such as `/api/messages/…/image?v=…`
    /// (images need the session, so AsyncImage cannot load them).
    func file(at path: String) async throws -> Data {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw APIError.unexpected }
        var request = request("")
        request.url = url
        return try await send(request)
    }

    /// The job's server-sent events, as they arrive. Ends after `done` or `failed`, or when
    /// the connection drops (the caller may then follow it again: the server replays them all).
    func events(ofJob jobId: String) -> AsyncThrowingStream<JobEvent, Error> {
        var events = request("jobs/\(jobId)/events")
        events.timeoutInterval = 60 * 10  // keep-alives arrive every 15 s
        let request = events
        let session = self.session
        return AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let (bytes, response) = try await session.bytes(for: request)
                    if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                        var body = Data()
                        for try await byte in bytes { body.append(byte) }
                        throw APIClient.error(status: http.statusCode, body: body)
                    }
                    var parser = SSEParser()
                    var line = Data()
                    // `bytes.lines` drops blank lines, which end events: split by hand.
                    for try await byte in bytes {
                        if byte == UInt8(ascii: "\n") {
                            let text = String(decoding: line, as: UTF8.self).trimmingCharacters(in: CharacterSet(charactersIn: "\r"))
                            if let event = parser.feed(text) { continuation.yield(event) }
                            line.removeAll(keepingCapacity: true)
                        } else {
                            line.append(byte)
                        }
                    }
                    continuation.finish()
                } catch let error as APIError {
                    continuation.finish(throwing: error)
                } catch {
                    continuation.finish(throwing: Task.isCancelled ? CancellationError() : APIError.offline)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}

/// multipart/form-data, as FastAPI's Form and File parameters read it.
struct MultipartForm {
    private let boundary = "MathMate-\(UUID().uuidString)"
    private var parts = Data()

    var contentType: String { "multipart/form-data; boundary=\(boundary)" }
    var body: Data { parts + Data("--\(boundary)--\r\n".utf8) }

    mutating func add(_ name: String, _ value: String) {
        parts.append("--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"\r\n\r\n\(value)\r\n")
    }

    mutating func add(_ name: String, filename: String, type: String, data: Data) {
        parts.append("--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"; filename=\"\(filename)\"\r\n")
        parts.append("Content-Type: \(type)\r\n\r\n")
        parts.append(data)
        parts.append("\r\n")
    }
}

private extension Data {
    mutating func append(_ string: String) { append(Data(string.utf8)) }
}
